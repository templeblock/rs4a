import numpy as np
import scipy as sp
import scipy.stats
import pandas as pd
import os
import pickle
import matplotlib as mpl
import seaborn as sns
from argparse import ArgumentParser
from collections import defaultdict
from dfply import *
from matplotlib import pyplot as plt
from src.utils import get_trailing_number


if __name__ == "__main__":

    argparser = ArgumentParser()
    argparser.add_argument("--dir", default="./ckpts", type=str)
    argparser.add_argument("--debug", action="store_true")
    argparser.add_argument("--eps-max", default=0.1, type=float)
    args = argparser.parse_args()

    dataset = args.dir.split("_")[0]
    experiment_names = list(filter(lambda x: x.startswith(dataset), os.listdir(args.dir)))

    sns.set_style("whitegrid")
    sns.set_palette("husl")

    df = defaultdict(list)
    eps_range = np.linspace(0, args.eps_max, 81)

    for experiment_name in experiment_names:

        save_path = f"{args.dir}/{experiment_name}"
        results = {}

        for k in  ("preds_smooth", "labels", "radius_smooth", "prob_lower_bound", "acc_train"):
            results[k] = np.load(f"{save_path}/{k}.npy")

        top_1_preds_smooth = np.argmax(results["preds_smooth"], axis=1)
        top_1_acc_pred = (top_1_preds_smooth == results["labels"]).mean()

        _, noise, sigma = experiment_name.split("_")
        sigma = float(sigma)

        if noise == "GaussianNoise":
            results["radius_smooth"] = results["radius_smooth"] / 3072 ** 0.5
        elif noise == "LaplaceNoise":
            results["radius_smooth"] = sp.stats.norm.ppf(results["prob_lower_bound"]) * sigma / 2 ** 0.5 / 3072 ** 0.5
        elif noise == "UniformNoise":
            results["radius_smooth"] = 2 * 3 ** 0.5 * sigma * (1 - (1.5 - results["prob_lower_bound"]) ** (1 / 3072))
#        elif noise == "ExpInfNoise":
#           results["radius_smooth"] = 3 ** 0.5 / 3072 * sigma * np.log(0.5 / (1 - results["prob_lower_bound"]))
        else:
            continue

        noise = noise.replace("Noise", "")

        for eps in eps_range:

            top_1_acc_cert = ((results["radius_smooth"] >= eps) & \
                              (top_1_preds_smooth == results["labels"])).mean()
            df["experiment_name"].append(experiment_name)
            df["sigma"].append(sigma)
            df["noise"].append(noise)
            df["eps"].append(eps * 255)
            df["top_1_acc_train"].append(results["acc_train"][0])
            df["top_1_acc_cert"].append(top_1_acc_cert)
            df["top_1_acc_pred"].append(top_1_acc_pred)

    # save the experiment results
    df = pd.DataFrame(df)
    df.to_csv(f"{args.dir}/results_{dataset}.csv", index=False)


    if args.debug:
        breakpoint()

    # plot clean training accuracy against certified accuracy at eps
    tmp = df >> mask(abs(X.eps - 0.01 * 255) < 1e-4) >> arrange(X.noise)
    plt.figure(figsize=(3, 3))
    sns.scatterplot(x="top_1_acc_train", y="top_1_acc_cert", hue="noise", style="noise",
                    size="sigma", data=tmp, legend=False)
    plt.plot(np.linspace(0.0, 1.0), np.linspace(0.0, 1.0), "--", color="gray")
    plt.ylim((0, 1))
    plt.xlim((0.0, 1.0))
    plt.xlabel("Top-1 training accuracy")
    plt.ylabel("Top-1 certified accuracy, $\epsilon$ = 2.55/255")
    plt.tight_layout()
    plt.savefig(f"{args.dir}/train_vs_certified.eps")
    plt.show()

    # plot certified accuracies
#    selected = df >> mask(X.noise != "Clean")
#    sns.relplot(x="eps", y="top_1_acc_cert", hue="noise", kind="line", col="sigma",
#                col_wrap=2, data=selected, height=2, aspect=1.5)
#    plt.ylim((0, 1))
#    plt.suptitle(args.dir)
#    plt.tight_layout()
#    plt.show()

#    df = pd.concat((df >> mask(X.noise != "ExpInf"), df >> mask(X.noise == "ExpInf")))

    # plot top certified accuracy per epsilon, per type of noise
    grouped = df >> mask(X.noise != "Clean") \
                 >> group_by(X.eps, X.noise) \
                 >> arrange(X.top_1_acc_cert, ascending=False) \
                 >> summarize(top_1_acc_cert=first(X.top_1_acc_cert),
                              noise=first(X.noise))

    grouped = pd.concat((grouped >> mask(X.noise != "ExpInf"), df >> mask(X.noise == "ExpInf")))

    plt.figure(figsize=(3, 3))
    sns.lineplot(x="eps", y="top_1_acc_cert", data=grouped, hue="noise", style="noise")
    plt.ylim((0, 1))
    plt.xlabel("$\epsilon \\times 255$")
    plt.ylabel("Top-1 certified accuracy")
    plt.tight_layout()
    plt.savefig(f"{args.dir}/certified_accuracies_linf.eps")
    plt.show()

