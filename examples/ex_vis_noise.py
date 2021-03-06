import torch
from argparse import ArgumentParser
from torchvision import datasets, transforms
from matplotlib import pyplot as plt
from src.noises import *
from src.datasets import get_dataset, get_dim


def plot_image(x, dataset):
    if dataset == "cifar":
        plt.imshow(x.numpy().transpose(1, 2, 0))
    if dataset == "mnist":
        plt.imshow(x[0].numpy())


if __name__ == "__main__":

    argparser = ArgumentParser()
    argparser.add_argument("--idx", type=int, default=1)
    argparser.add_argument("--sigma", type=float, default=0.1)
    argparser.add_argument("--n-samples", type=int, default=4)
    argparser.add_argument("--dataset", type=str, default="cifar")
    args = argparser.parse_args()

    dataset = get_dataset(args.dataset, "test")

    plt.figure(figsize=(2 * args.n_samples, 7))

    x, y = dataset[args.idx]
    x = x.unsqueeze(0) if dataset == "cifar" else x

    dim = get_dim(args.dataset)

    for i in range(args.n_samples):

        noise = LaplaceNoise(sigma=args.sigma + 0.1 * i, device="cpu", dim=dim)
        sample = (noise.sample(x)).clamp(0, 1)
        plt.subplot(4, args.n_samples, i + 1)
        plot_image(sample, args.dataset)
        plt.axis("off")
        plt.title(f"Laplace {args.sigma + 0.1 * i:.1f}")

    for i in range(args.n_samples):

        noise = GaussianNoise(sigma=args.sigma + 0.1 * i, device="cpu", dim=dim)
        sample = (noise.sample(x)).clamp(0, 1)
        plt.subplot(4, args.n_samples, i + 1 + args.n_samples)
        plot_image(sample, args.dataset)
        plt.axis("off")
        plt.title(f"Gaussian {args.sigma + 0.1 * i:.1f}")

    for i in range(args.n_samples):

        noise = PowerInfNoise(sigma=args.sigma + 0.1 * i, device="cpu", dim=dim, a=3200)
        sample = (noise.sample(x.reshape(1, -1)).reshape(x.shape)).clamp(0, 1)
        plt.subplot(4, args.n_samples, i + 1 + args.n_samples * 2)
        plot_image(sample, args.dataset)
        plt.axis("off")
        plt.title(f"PowerLaw {args.sigma + 0.1 * i:.1f}")

    for i in range(args.n_samples):

        noise = UniformNoise(sigma=args.sigma + 0.1 * i, device="cpu", dim=dim)
        sample = (noise.sample(x)).clamp(0, 1)
        plt.subplot(4, args.n_samples, i + 1 + args.n_samples * 3)
        plot_image(sample, args.dataset)
        plt.axis("off")
        plt.title(f"Uniform {args.sigma + 0.1 * i:.1f}")

    plt.tight_layout()
    plt.show()

