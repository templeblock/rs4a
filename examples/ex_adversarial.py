import numpy as np
from argparse import ArgumentParser
from matplotlib import pyplot as plt


if __name__ == "__main__":

    argparser = ArgumentParser()
    argparser.add_argument("--experiment-name", default="cifar", type=str)
    argparser.add_argument("--idx", default=6, type=int)
    args = argparser.parse_args()

    label_names = ["plane", "car", "bird", "cat", "deer", "dog", "frog",
                   "horse", "ship", "truck"]

    save_path = f"ckpts/{args.experiment_name}"
    results = {}

    for k in ("preds", "preds_adv", "preds_smooth", "imgs", "imgs_adv", 
              "labels", "radius_smooth"):
        results[k] = np.load(f"{save_path}/{k}.npy")

    top_1_preds = np.argmax(results["preds"], axis=1)
    top_1_preds_adv = np.argmax(results["preds_adv"], axis=1)
    top_1_preds_smooth = np.argmax(results["preds_smooth"], axis=1)
    top_1_acc = np.mean(top_1_preds == results["labels"])
    top_1_acc_adv = np.mean(top_1_preds_adv == results["labels"])
    top_1_acc_smooth = np.mean(top_1_preds_smooth == results["labels"])

    print(top_1_acc)
    print(top_1_acc_adv)
    print(top_1_acc_smooth)

    plt.figure(figsize=(12, 3))
    plt.subplot(1, 3, 1)
    plt.imshow(results["imgs"][args.idx].transpose(1, 2, 0))
    pred_probs = np.max(results["preds"], axis=1)
    plt.title(f"{label_names[top_1_preds[args.idx]]} {pred_probs[args.idx]:.2f}")
    print(results["preds"][args.idx])
    plt.subplot(1, 3, 2)
    plt.imshow(results["imgs_adv"][args.idx].transpose(1, 2, 0))
    pred_probs = np.max(results["preds_adv"], axis=1)
    plt.title(f"{label_names[top_1_preds_adv[args.idx]]} {pred_probs[args.idx]:.2f}")
    print(results["preds_adv"][args.idx])
    plt.subplot(1, 3, 3)
    plt.imshow(results["imgs_adv"][args.idx].transpose(1, 2, 0))
    pred_probs = np.max(results["preds_smooth"], axis=1)
    plt.title(f"{label_names[top_1_preds_smooth[args.idx]]} {pred_probs[args.idx]:.2f}")
    print(results["preds_smooth"][args.idx])
    plt.show()
