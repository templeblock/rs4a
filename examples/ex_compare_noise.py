import numpy as np
import seaborn as sns
from argparse import ArgumentParser
from matplotlib import pyplot as plt
from scipy.stats import gaussian_kde
from src.noises import *
from src.utils import get_trailing_number


if __name__ == "__main__":

    argparser = ArgumentParser()
    argparser.add_argument("--dim", type=int, default=3000)
    argparser.add_argument("--batch-size", type=int, default=200)
    argparser.add_argument("--sigma", type=float, default=0.25)
    args = argparser.parse_args()

    #noises = ["GaussianNoise", "LaplaceNoise", "UniformNoise"]
    #noises = ["GaussianNoise", "Exp2PolyNoise2048", "PTailNoise100"]
    #noises = ["GammaNoise3", "GammaNoise4", "GammaNoise5"]
    #noises = ["ExpInfNoise", "UniformNoise"]
#    noises = ["GaussianNoise", "PTailNoise8", "PTailNoise100", "PTailNoise2"]
    #noises = ["Exp1Noise1", "Exp1Noise10"]#, "Exp1Noise20"]
    noises = ["GaussianNoise", "PTailNoise8", "PTailNoise2", "UniformBallNoise"]

    sns.set_style("whitegrid")
    sns.set_palette("husl")

    plt.figure(figsize=(8, 8))
    axis = np.linspace(0, 1, 400)
    linf_axis = np.linspace(0, 2.5, 400)

    for noise_str in noises:

        k = get_trailing_number(noise_str)
        if k:
            noise = eval(noise_str[:-len(str(k))])(sigma=args.sigma, device="cpu",
                                                   dim=args.dim, k=k)
        else:
            noise = eval(noise_str)(sigma=args.sigma, device="cpu", dim=args.dim)
        noise_str = noise_str.replace("Noise", "")

        rvs = noise.sample(torch.zeros(args.batch_size, args.dim))
        rvs = rvs.reshape((args.batch_size, -1))

        l1_norms = rvs.norm(p=1, dim=1) / args.dim
        l2_norms = rvs.norm(p=2, dim=1).pow(2) / args.dim
        linf_norms = rvs.norm(p=float("inf"), dim=1)

        plt.subplot(2, 2, 1)
        plt.plot(axis, gaussian_kde(np.abs(rvs).flatten())(axis), label=noise_str)
        plt.subplot(2, 2, 2)
        plt.plot(axis, gaussian_kde(l2_norms ** 0.5)(axis), label=noise_str)
        plt.subplot(2, 2, 3)
        plt.plot(linf_axis, gaussian_kde(linf_norms)(linf_axis), label=noise_str)
        plt.subplot(2, 2, 4)
        plt.plot(axis, gaussian_kde(l1_norms)(axis), label=noise_str)

    plt.subplot(2, 2, 1)
    plt.legend()
    plt.xlabel("$|x_i|$")
    plt.subplot(2, 2, 2)
    plt.legend()
    plt.xlabel("$\sqrt{||x||_2^2/ d}$")
    plt.subplot(2, 2, 3)
    plt.legend()
    plt.xlabel("$||x||_\infty$")
    plt.subplot(2, 2, 4)
    plt.legend()
    plt.xlabel("$||x||_1 / d$")

    plt.tight_layout()
    plt.show()

