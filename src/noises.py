import math
import numpy as np
import scipy as sp
import scipy.special
import scipy.stats
import torch
from torch.distributions import Normal, Uniform, Laplace, Gamma, Dirichlet, Pareto, Bernoulli, Beta


def atanh(x):
    return 0.5 * np.log((1 + x) / (1 - x))


class Noise(object):

    def __init__(self, sigma, device, dim, k=None):
        self.sigma = sigma
        self.device = device
        self.dim = dim
        self.k = k

    def sample(self, shape):
        raise NotImplementedError

    def certify(self, prob_lower_bound):
        raise NotImplementedError


class Clean(Noise):

    def __init__(self, sigma, device, dim):
        super().__init__(None, device, None)

    def sample(self, shape):
        return torch.zeros(shape, device=self.device)

    def certify(self, prob_lower_bound):
        return torch.zeros_like(prob_lower_bound)


class UniformNoise(Noise):

    def __init__(self, sigma, device, dim, p):
        super().__init__(sigma, device, None)
        self.lambd = 2 * sigma if p == 1 else sigma * 3 ** 0.5

    def sample(self, shape):
        return (torch.rand(shape, device=self.device) - 0.5) * 2 * self.lambd

    def certify(self, prob_lower_bound):
        return 2 * self.lambd * (prob_lower_bound - 0.5)

class GaussianNoise(Noise):

    def __init__(self, sigma, device, dim, p):
        super().__init__(sigma, device, None)
        self.lambd = sigma if p == 2 else sigma * math.sqrt(math.pi / 2)
        self.norm_dist = Normal(loc=torch.tensor(0., device=device),
                                scale=torch.tensor(self.lambd, device=device))

    def sample(self, shape):
        return self.norm_dist.sample(shape)

    def certify(self, prob_lower_bound):
        return self.norm_dist.icdf(prob_lower_bound)


class LaplaceNoise(Noise):

    def __init__(self, sigma, device, dim, p):
        super().__init__(sigma, device, None)
        self.lambd = sigma if p == 1 else sigma * 2 ** (-0.5)
        self.laplace_dist = Laplace(loc=torch.tensor(0.0, device=device),
                                    scale=torch.tensor(self.lambd, device=device))

    def sample(self, shape):
        return self.laplace_dist.sample(shape)

    def certify(self, prob_lower_bound):
        a = 0.5 * self.lambd *  torch.log(prob_lower_bound / (1 - prob_lower_bound))
        b = -self.lambd * (torch.log(2 * (1 - prob_lower_bound)))
        return torch.max(a, b)


class LomaxNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=3):
        super().__init__(sigma, device, None, k)
        if k > 2:
            self.lambd = (k - 1) * sigma if p == 1 else math.sqrt(0.5 * (k - 1) * (k - 2)) * sigma
        else:
            self.lambd = 0.01 * sigma # heuristic, todo: fix
        self.pareto_dist = Pareto(scale=torch.tensor(self.lambd, device=device, dtype=torch.float),
                                  alpha=torch.tensor(self.k, device=device, dtype=torch.float))

    def sample(self, shape):
        samples = self.pareto_dist.sample(shape) - self.lambd
        signs = torch.sign(torch.rand(shape, device=self.device) - 0.5)
        return samples * signs

    def certify(self, prob_lower_bound):
        prob_lower_bound = prob_lower_bound.numpy()
        radius = sp.special.hyp2f1(1, self.k / (self.k + 1), self.k / (self.k + 1) + 1,
                                   (2 * prob_lower_bound - 1) ** (1 + 1 / self.k)) * \
                 self.lambd * (2 * prob_lower_bound - 1) / self.k
        return torch.tensor(radius, dtype=torch.float)


class ExpInfNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=1):
        super().__init__(sigma, device, dim, k)
        self.lambd = sigma / (math.exp(math.lgamma((dim + 1) / k) - math.lgamma(dim / k)))
        self.lambd = 2 * self.lambd if p == 1 else 3 ** 0.5 * self.lambd
        self.gamma_factor = math.exp(math.lgamma((dim + k) / k) - math.lgamma((dim + k - 1) / k))
        self.gamma_dist = Gamma(concentration=torch.tensor(dim / k, device=device),
                                rate=torch.tensor((1 / self.lambd) ** k, device=device))

    def sample(self, shape):
        radius = (self.gamma_dist.sample((shape[0], 1))) ** (1 / self.k)
        noises = (2 * torch.rand(shape, device=self.device) - 1).reshape((shape[0], -1))
        sel_dims = torch.randint(noises.shape[1], size=(noises.shape[0],))
        idxs = torch.arange(0, noises.shape[0], dtype=torch.long)
        noises[idxs, sel_dims] = torch.sign(torch.rand(noises.shape[0], device=self.device) - 0.5)
        return (noises * radius).reshape(shape)

    def certify(self, prob_lower_bound, d=3*32*32):
        return 2 * self.lambd * self.gamma_factor * (prob_lower_bound - 0.5)


class Exp1Noise(Noise):

    def __init__(self, sigma, device, dim, p, k=1):
        super().__init__(sigma, device, dim, k)
        self.lambd = sigma / (math.exp(math.lgamma((dim + 1) / k) - math.lgamma(dim / k)))
        self.lambd *= dim if p == 1 else math.sqrt(0.5 * dim * (dim + 1))
        self.gamma_factor = math.exp(math.lgamma(dim / k) - math.lgamma((dim + k - 1) / k))
        self.dirichlet_dist = Dirichlet(concentration=torch.ones(dim, device=device))
        self.gamma_dist = Gamma(concentration=torch.tensor(dim / k, device=device),
                                rate=torch.tensor((1 / self.lambd) ** k, device=device))

    def sample(self, shape):
        n_samples = int(np.prod(list(shape)) / self.dim)
        radius = (self.gamma_dist.sample((n_samples, 1))) ** (1 / self.k)
        noises = self.dirichlet_dist.sample((n_samples,))
        signs = torch.sign(torch.rand_like(noises) - 0.5)
        return (noises * signs * radius).reshape(shape)

    def certify(self, prob_lower_bound, num_pts=1000, eps=1e-4):
        x = np.linspace(eps, 0.5, num_pts)
        y = sp.stats.gamma.ppf(1 - 2 * x, self.dim / self.k)
        y = 1 / (1 - sp.stats.gamma.cdf(y, (self.dim + self.k - 1) / self.k))
        y = np.repeat(y[np.newaxis,:], len(prob_lower_bound), axis=0)
        y[x < 1 - prob_lower_bound.numpy()[:, np.newaxis]] = 0
        integral = torch.tensor(np.trapz(y, dx=0.5 / num_pts), dtype=torch.float)
        return 2 * self.lambd * self.gamma_factor / self.k * integral


class Exp2Noise(Noise):

    def __init__(self, sigma, device, dim, p, k=1):
        super().__init__(sigma, device, dim, k)
        self.lambd = math.sqrt(0.5 * math.pi * dim) * sigma if p == 1 else math.sqrt(dim) * sigma
        self.lambd = self.lambd / math.exp(math.lgamma((dim + 1) / k) - math.lgamma(dim / k))
        self.beta_dist = sp.stats.beta(0.5 * (self.dim - 1), 0.5 * (self.dim - 1))
        self.gamma_dist = Gamma(concentration=torch.tensor(dim / k, device=device),
                                rate=torch.tensor((1 / self.lambd) ** k, device=device))

    def sample(self, shape):
        n_samples = int(np.prod(list(shape)) / self.dim)
        radius = (self.gamma_dist.sample((n_samples, 1))) ** (1 / self.k)
        noises = torch.randn(shape, device=self.device).view(n_samples, -1)
        noises = noises / (noises ** 2).sum(dim=1).unsqueeze(1) ** 0.5
        return (noises * radius).reshape(shape)

    def certify(self, prob_lower_bound):
        radius = self.lambd * (self.dim - 1) * \
                 atanh(1 - 2 * self.beta_dist.ppf(1 - prob_lower_bound.numpy()))
        return torch.tensor(radius, dtype=torch.float)

class GammaNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=1):
        super().__init__(sigma, device, dim)
        self.lambd = 1 / (sigma * k) if p == 1 else (1 + k) ** 0.5 / (k * sigma)
        self.bernoulli_dist = Bernoulli(torch.tensor(0.5, dtype=torch.float, device=device))
        self.gamma_dist = Gamma(torch.tensor(1 / k, dtype=torch.float, device=device), self.lambd)

    def sample(self, shape):
        noises = self.gamma_dist.sample(shape)
        sgns = torch.sign(self.bernoulli_dist.sample(shape) - 0.5)
        return noises * sgns

    def certify(self, prob_lower_bound):
        return torch.zeros_like(prob_lower_bound)


class PTailNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=2):
        super().__init__(sigma, device, dim, k)
        self.beta_dist = Beta(torch.tensor(dim / 2, dtype=torch.float, device=device),
                              torch.tensor(k, dtype=torch.float, device=device))
        self.lambd = (2 * (k - 1)) ** 0.5 * sigma if p == 2 else 0 / 0
        self.prob_lower_bounds, self.radii = np.load("./src/lib/radii_ptail.npy", allow_pickle=True)

    def sample(self, shape):
        n_samples = int(np.prod(list(shape)) / self.dim)
        beta_samples = self.beta_dist.sample((n_samples, 1))
        radius = (beta_samples / (1 - beta_samples)) ** 0.5
        noise = torch.randn(shape, device=self.device).reshape(n_samples, -1)
        noise = noise / torch.norm(noise, dim=1, p=2).unsqueeze(1)
        noise = noise * radius * self.lambd
        return noise.reshape(shape)

    def certify(self, prob_lower_bound):
        prob_lower_bound = prob_lower_bound.numpy()
        alpha = self.k + self.dim / 2
        idxs = np.searchsorted(self.prob_lower_bounds[alpha], prob_lower_bound)
        x_deltas = self.prob_lower_bounds[alpha][idxs] - self.prob_lower_bounds[alpha][idxs - 1]
        y_deltas = self.radii[alpha][idxs] - self.radii[alpha][idxs - 1]
        pcts = (prob_lower_bound - self.prob_lower_bounds[alpha][idxs - 1]) / x_deltas
        radius = (pcts * y_deltas + self.radii[alpha][idxs - 1]) * self.lambd
        return torch.tensor(radius, dtype=torch.float)


class UniformBallNoise(Noise):

    def __init__(self, sigma, device, dim, p):
        super().__init__(sigma, device, dim)
        self.lambd = (dim + 2) ** 0.5 * sigma if p == 2 else 0 / 0
        self.beta_dist = sp.stats.beta(0.5 * (self.dim + 1), 0.5 * (self.dim + 1))

    def sample(self, shape):
        n_samples = int(np.prod(list(shape)) / self.dim)
        radius = torch.rand((n_samples, 1), device=self.device) ** (1 / self.dim) * self.lambd
        noise = torch.randn(shape, device=self.device).reshape(n_samples, -1)
        noise = noise / torch.norm(noise, dim=1, p=2).unsqueeze(1) * radius
        return noise.reshape(shape)

    def certify(self, prob_lower_bound):
        radius = self.lambd * (2 - 4 * self.beta_dist.ppf(0.75 - 0.5 * prob_lower_bound.numpy()))
        return torch.tensor(radius, dtype=torch.float)


class Exp2PolyNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=1):
        super().__init__(sigma, device, dim, k)
        self.lambd = (2 * dim / k) ** 0.5 * sigma
        self.gamma_dist = Gamma(torch.tensor(0.5 * self.k, device=device),
                                torch.tensor((1 / self.lambd) ** 2, device=device))
        self.prob_lower_bounds, self.radii = np.load("./src/lib/radii_exp2poly.npy", allow_pickle=True)

    def sample(self, shape):
        n_samples = int(np.prod(list(shape)) / self.dim)
        radius = self.gamma_dist.sample((n_samples, 1)) ** 0.5
        noise = torch.randn(shape, device=self.device).reshape(n_samples, -1)
        noise = noise / torch.norm(noise, dim=1, p=2).unsqueeze(1) * radius
        return noise.reshape(shape)

    def certify(self, prob_lower_bound):
        prob_lower_bound = prob_lower_bound.numpy()
        alpha = self.dim - self.k
        idxs = np.searchsorted(self.prob_lower_bounds[alpha], prob_lower_bound)
        x_deltas = self.prob_lower_bounds[alpha][idxs] - self.prob_lower_bounds[alpha][idxs - 1]
        y_deltas = self.radii[alpha][idxs] - self.radii[alpha][idxs - 1]
        pcts = (prob_lower_bound - self.prob_lower_bounds[alpha][idxs - 1]) / x_deltas
        radius = (pcts * y_deltas + self.radii[alpha][idxs - 1]) * self.lambd
        return torch.tensor(radius, dtype=torch.float)


class MaskNoise(Noise):

    def __init__(self, sigma, device, dim, p):
        super().__init__(sigma, device, dim)
        self.lambd = 1 - dim * sigma ** 2 / 750 if p == 2 else 1 - dim * sigma / 125

    def sample(self, shape, x):
        noises = torch.rand(shape, device=self.device)
        mask = (noises < self.lambd).to(torch.float)
        return mask * torch.zeros_like(x) - (1 - mask) * x

    def certify(self, prob_lower_bound):
        return (prob_lower_bound - 0.5) / self.lambd


class MaskGaussianNoise(Noise):

    def __init__(self, sigma, device, dim, p, k=2):
        """
        k is reciprocal of fraction of pixels retained (default 1/10)
        """
        super().__init__(sigma, device, dim, k)
        self.n_pixels_retained = dim // k
        #self.lambd = (k * (sigma ** 2 - (1 - 1 / k) * 0.06329)) ** 0.5
        self.lambd = sigma
        self.norm_dist = Normal(loc=torch.tensor(0., device=device),
                                scale=torch.tensor(self.lambd, device=device))

    def sample(self, x):
        x_copy = x.reshape(-1, self.dim)
        batch_size = x_copy.shape[0]
        noise = self.norm_dist.sample(x_copy.shape) + x_copy
        perm = torch.stack([torch.randperm(self.dim) for _ in range(batch_size)])
        idxs = perm[:, :self.dim - self.n_pixels_retained]
        rng = torch.arange(batch_size)
        for batch_no in range(batch_size):
            #noise[batch_no, idxs[batch_no]] = 0.4734
            noise[batch_no, idxs[batch_no]] = -1
        return noise.reshape(x.shape)

    def certify(self, prob_lower_bound):
        return self.lambd * Normal(0, 1).icdf(prob_lower_bound) / self.n_pixels_retained ** 0.5


