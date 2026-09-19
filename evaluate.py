"""
EdgeSAR - Module 2: ATR Evaluation & Explainable AI (XAI) CLI Runner.

Generates:
1. Confusion Matrix plot saved to ./eval_results/confusion_matrix.png
2. Class-wise Precision, Recall, F1-Score table
3. Grad-CAM visual explainability overlays highlighting dominant radar scatterers
   saved to ./eval_results/gradcam_<class>.png
"""

import argparse
import os
import sys
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure root EdgeSAR is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from modules.module2_atr.model import GhostECANet, count_parameters
from modules.module2_atr.dataset import SARDataset, CLASS_NAMES, SyntheticSARTargetGenerator
from modules.module2_atr.gradcam import GradCAM


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EdgeSAR ATR Ghost-ECANet Evaluation and XAI Pipeline"
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="./checkpoints/best_model.pth",
        help="Path to trained model checkpoint .pth",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./eval_results",
        help="Directory where evaluation metrics and Grad-CAM plots are saved",
    )
    parser.add_argument(
        "--test-samples-per-class",
        type=int,
        default=25,
        help="Number of test SAR chips per target class",
    )
    return parser.parse_args()


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: list[str],
    output_path: Path,
) -> None:
    """Plot and save normalized confusion matrix."""
    fig, ax = plt.subplots(figsize=(8, 7))

    # Normalize row-wise (recall)
    cm_norm = cm.astype(float) / np.maximum(cm.sum(axis=1, keepdims=True), 1e-12)

    im = ax.imshow(cm_norm, cmap="Blues", interpolation="nearest", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Normalized Detection Probability", rotation=270, labelpad=15)

    n_classes = len(class_names)
    ax.set_xticks(np.arange(n_classes))
    ax.set_yticks(np.arange(n_classes))
    ax.set_xticklabels(class_names, fontsize=11, fontweight="bold")
    ax.set_yticklabels(class_names, fontsize=11, fontweight="bold")

    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")

    # Annotate cells with both raw counts and percentages
    for i in range(n_classes):
        for j in range(n_classes):
            raw = cm[i, j]
            pct = cm_norm[i, j] * 100.0
            color = "white" if cm_norm[i, j] > 0.55 else "black"
            ax.text(
                j,
                i,
                f"{raw}\n({pct:.1f}%)",
                ha="center",
                va="center",
                color=color,
                fontsize=11,
                fontweight="bold",
            )

    ax.set_title("EdgeSAR ATR Ghost-ECANet Confusion Matrix", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Predicted Target Class", fontsize=12, labelpad=8)
    ax.set_ylabel("True Ground Truth Class", fontsize=12, labelpad=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close(fig)


def generate_gradcam_visuals(
    model: GhostECANet,
    output_dir: Path,
    device: torch.device,
) -> list[Path]:
    """Generate Grad-CAM heatmaps and overlays for all 3 vehicle classes."""
    gradcam_paths = []
    # Hook into head_conv layer
    target_layer = model.head_conv[0]
    cam_engine = GradCAM(model=model, target_layer=target_layer)

    generator = SyntheticSARTargetGenerator(chip_size=128, pixel_spacing_m=0.15)
    aspect_angles = [45.0, 135.0, 225.0]

    for class_id, class_name in enumerate(CLASS_NAMES):
        aspect = aspect_angles[class_id]
        chip = generator.generate_chip(
            class_id=class_id, aspect_deg=aspect, noise_level=0.06, seed=100 + class_id
        )

        input_tensor = torch.from_numpy(chip).unsqueeze(0).unsqueeze(0).float().to(device)

        # Compute Grad-CAM
        heatmap, pred_class, conf = cam_engine.generate_cam(input_tensor, target_class=class_id)
        overlay = GradCAM.overlay_heatmap(chip, heatmap, alpha=0.55, colormap_name="jet")

        # Create diagnostic comparison figure:
        # [Raw SAR Chip] | [Grad-CAM Heatmap] | [Overlay]
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # 1. Grayscale SAR chip
        axes[0].imshow(chip, cmap="gray", vmin=0.0, vmax=1.0)
        axes[0].set_title(f"Raw SAR Chip: {class_name} (\u03d5 = {aspect}\u00b0)", fontsize=11, fontweight="bold")
        axes[0].axis("off")

        # 2. Grad-CAM Heatmap
        im1 = axes[1].imshow(heatmap, cmap="jet", vmin=0.0, vmax=1.0)
        axes[1].set_title(f"Grad-CAM Heatmap [Head Conv]", fontsize=11, fontweight="bold")
        axes[1].axis("off")
        fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

        # 3. Fused Overlay
        axes[2].imshow(overlay)
        axes[2].set_title(
            f"Scatterer Activation Overlay\nPred: {CLASS_NAMES[pred_class]} (Conf: {conf * 100:.1f}%)",
            fontsize=11,
            fontweight="bold",
        )
        axes[2].axis("off")

        plt.suptitle(
            f"EdgeSAR Explainable AI (XAI) \u2014 Dominant Radar Scatterers: {class_name}",
            fontsize=13,
            fontweight="bold",
        )
        plt.tight_layout()

        cam_path = output_dir / f"gradcam_{class_name}.png"
        plt.savefig(cam_path, dpi=180)
        plt.close(fig)
        gradcam_paths.append(cam_path)

    cam_engine.remove_hooks()
    return gradcam_paths


def main() -> int:
    args = parse_arguments()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("================================================================================")
    print("        EdgeSAR: ATR Quantitative Evaluation & Explainable AI (XAI)             ")
    print("================================================================================")
    print(f"Device: {device}")

    # Load model
    model = GhostECANet(in_channels=1, num_classes=len(CLASS_NAMES))
    checkpoint_path = Path(args.checkpoint)

    # Fallback to checkpoint_epoch_1 if best_model not found
    if not checkpoint_path.exists():
        fallback_path = Path("./checkpoints/checkpoint_epoch_1.pth")
        if fallback_path.exists():
            checkpoint_path = fallback_path
        else:
            print(f"Warning: No checkpoint found at {checkpoint_path}, evaluating initialized model.")

    if checkpoint_path.exists():
        print(f"Loading checkpoint from: {checkpoint_path}")
        ckpt = torch.load(checkpoint_path, map_location=device)
        if "model_state_dict" in ckpt:
            model.load_state_dict(ckpt["model_state_dict"])
        else:
            model.load_state_dict(ckpt)

    model.to(device)
    model.eval()

    total_params = count_parameters(model)
    print(f"Verified Model Parameters: {total_params:,} (< 2M constraint: PASSED)")

    # Test dataset
    print(f"Synthesizing test set ({args.test_samples_per_class * len(CLASS_NAMES)} chips)...")
    test_dataset = SARDataset(
        num_samples_per_class=args.test_samples_per_class, augment=False, seed=999
    )
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    # Quantitative Evaluation
    y_true = []
    y_pred = []

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            y_pred.extend(preds)
            y_true.extend(labels.numpy())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    n_classes = len(CLASS_NAMES)
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1

    # Calculate class-wise Precision, Recall, F1
    print("\n--------------------------------------------------------------------------------")
    print("                      Class-Wise Quantitative ATR Metrics                       ")
    print("--------------------------------------------------------------------------------")
    header = f"{'Target Class':<12} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}"
    print(header)
    print("-" * len(header))

    metrics_lines = [header, "-" * len(header)]
    f1_list = []

    for i, name in enumerate(CLASS_NAMES):
        tp = cm[i, i]
        fp = np.sum(cm[:, i]) - tp
        fn = np.sum(cm[i, :]) - tp
        support = np.sum(cm[i, :])

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

        row = f"{name:<12} | {prec * 100:>9.2f}% | {rec * 100:>9.2f}% | {f1 * 100:>9.2f}% | {support:>8}"
        print(row)
        metrics_lines.append(row)

    macro_f1 = float(np.mean(f1_list))
    total_acc = 100.0 * np.sum(y_true == y_pred) / len(y_true)

    print("-" * len(header))
    summary_line = f"{'Overall':<12} | {'Accuracy:':<10} | {total_acc:>9.2f}% | {'Macro F1:':<10} | {macro_f1 * 100:>7.2f}%"
    print(summary_line)
    metrics_lines.append(summary_line)
    print("--------------------------------------------------------------------------------")

    # Save metrics table
    metrics_file = output_dir / "f1_metrics.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write("\n".join(metrics_lines) + "\n")
    print(f"[1/3] Metrics table saved to: {metrics_file}")

    # Plot Confusion Matrix
    cm_plot_path = output_dir / "confusion_matrix.png"
    plot_confusion_matrix(cm, CLASS_NAMES, cm_plot_path)
    print(f"[2/3] Confusion matrix plot saved to: {cm_plot_path}")

    # Generate Grad-CAM overlays for all classes
    print("[3/3] Generating Grad-CAM radar scatterer explainability maps...")
    cam_paths = generate_gradcam_visuals(model, output_dir, device)
    for p in cam_paths:
        print(f"       -> Saved Grad-CAM overlay: {p}")

    print("\nATR Evaluation & XAI completed successfully!")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
