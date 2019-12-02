import torch
from torchvision import datasets, transforms


def get_dim(name):

    if name == "cifar":
        return 3 * 32 * 32

    if name == "mnist":
        return 28 * 28


def get_dataset(name, split):
    
    if name == "cifar" and split == "train":
        return datasets.CIFAR10("./data/cifar_10", train=True, download=True,
                                transform=transforms.Compose([transforms.RandomCrop(32, padding=4),
                                                              transforms.RandomHorizontalFlip(),
                                                              transforms.ToTensor()]))
    if name == "cifar" and split == "test":
        return datasets.CIFAR10("./data/cifar_10", train=False, download=True, 
                                transform=transforms.ToTensor())
    
    if name == "mnist" and split == "train":
        return datasets.MNIST("./data/mnist", train=True, download=True,
                              transform=transforms.ToTensor())

    if name == "mnist" and split == "test":
        return datasets.MNIST("./data/mnist", train=False, download=True, 
                              transform=transforms.ToTensor())
