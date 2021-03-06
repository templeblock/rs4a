import numpy as np
import torch
from argparse import ArgumentParser
from scipy.stats import gaussian_kde
from src.noises import *
from src.utils import get_trailing_number


if __name__ == "__main__":

    argparser = ArgumentParser()
    argparser.add_argument("--noise", type=str, default="GaussianNoise")
    argparser.add_argument("--dim", type=int, default=3*32*32)
    argparser.add_argument("--batch-size", type=int, default=500)
    argparser.add_argument("--sigma", type=float, default=0.25)
    args = argparser.parse_args()

    lower_bounds = torch.tensor([0.6, 0.7, 0.8, 0.9, 0.95, 0.99])

    axis = np.linspace(0, 2, 200)

    k = get_trailing_number(args.noise)
    if k:
        noise = eval(args.noise[:-len(str(k))])(sigma=args.sigma, device="cpu", dim=args.dim, k=k)
    else:
        noise = eval(args.noise)(sigma=args.sigma, device="cpu", dim=args.dim)

    x = torch.zeros((args.batch_size, args.dim))
    rvs = noise.sample(x)
    print("== L2 Match")
    print("Root L2 norm (divided by dimension):", (rvs.norm(p=2, dim=1).pow(2) / args.dim).mean() ** 0.5)
    print(noise.certify(lower_bounds, p=1))

