"""
Unit test suite for EdgeSAR Module 2: ATR & Explainable AI (XAI).

Verifies:
1. Parameter count constraint (< 2,000,000 parameters).
2. Ghost-ECANet forward pass tensor shapes and numerical hygiene.
3. Grad-CAM heatmap extraction and colormap overlay blending.
4. Synthetic attributed scatterer dataset generation and data augmentation invariants.
"""

import sys
from pathlib import Path
import numpy as np
import torch
import pytest

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.module2_atr.model import GhostECANet, count_parameters
from modules.module2_atr.dataset import SARDataset, SyntheticSARTargetGenerator, CLASS_NAMES
from modules.module2_atr.gradcam import GradCAM


def test_model_parameter_count():
    """Verify that Ghost-ECANet has strictly fewer than 2,000,000 parameters."""
    model = GhostECANet(in_channels=1, num_classes=3)
    total_params = count_parameters(model)
    assert total_params < 2_000_000, f"Model has {total_params:,} parameters, exceeding 2M limit!"
    # Ensure it is also not trivial (must have >= 100k parameters for deep representation)
    assert total_params > 100_000, f"Model has only {total_params:,} parameters, too small!"


def test_model_forward_pass():
    """Verify forward inference tensor shapes and absence of NaNs."""
    model = GhostECANet(in_channels=1, num_classes=3)
    model.eval()

    batch_size = 4
    dummy_input = torch.randn(batch_size, 1, 128, 128)

    with torch.no_grad():
        logits = model(dummy_input)

    assert logits.shape == (batch_size, 3)
    assert not torch.isnan(logits).any(), "Model logits contain NaN!"
    assert not torch.isinf(logits).any(), "Model logits contain Inf!"


def test_gradcam_generation():
    """Verify Grad-CAM produces normalized heatmaps and overlay images."""
    model = GhostECANet(in_channels=1, num_classes=3)
    target_layer = model.head_conv[0]
    cam_engine = GradCAM(model=model, target_layer=target_layer)

    dummy_input = torch.rand(1, 1, 128, 128)
    heatmap, pred_class, conf = cam_engine.generate_cam(dummy_input, target_class=0)

    assert heatmap.shape == (128, 128)
    assert 0 <= pred_class < 3
    assert 0.0 <= conf <= 1.0
    assert 0.0 <= np.min(heatmap)
    assert np.max(heatmap) <= 1.0
    assert not np.isnan(heatmap).any()

    # Test overlay blending
    chip = dummy_input.squeeze().numpy()
    overlay = GradCAM.overlay_heatmap(chip, heatmap)
    assert overlay.shape == (128, 128, 3)
    assert 0.0 <= np.min(overlay)
    assert np.max(overlay) <= 1.0

    cam_engine.remove_hooks()


def test_dataset_generator():
    """Verify synthetic SAR chip generation for all canonical target classes."""
    gen = SyntheticSARTargetGenerator(chip_size=128, pixel_spacing_m=0.15)

    for class_id in range(3):
        chip = gen.generate_chip(class_id=class_id, aspect_deg=60.0, noise_level=0.05, seed=42)
        assert chip.shape == (128, 128)
        assert chip.dtype == np.float32
        assert np.min(chip) >= 0.0
        assert np.max(chip) <= 1.0
        assert not np.isnan(chip).any()

    # Verify PyTorch Dataset wrapper
    dataset = SARDataset(num_samples_per_class=5, augment=True, seed=123)
    assert len(dataset) == 15

    tensor, label = dataset[0]
    assert tensor.shape == (1, 128, 128)
    assert 0 <= label < 3
    assert not torch.isnan(tensor).any()


def test_model_convergence_on_synthetic_data():
    """Verify that Ghost-ECANet loss strictly decreases when trained on a small batch of synthetic SAR chips."""
    torch.manual_seed(42)
    model = GhostECANet(in_channels=1, num_classes=3)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = torch.nn.CrossEntropyLoss()

    dataset = SARDataset(num_samples_per_class=4, augment=False, seed=42)
    loader = torch.utils.data.DataLoader(dataset, batch_size=6, shuffle=True)
    images, labels = next(iter(loader))

    losses = []
    for _ in range(10):
        optimizer.zero_grad()
        out = model(images)
        loss = criterion(out, labels)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    assert losses[-1] < losses[0], f"Model failed to converge: initial loss {losses[0]:.4f}, final loss {losses[-1]:.4f}"
    assert losses[-1] < 0.5 * losses[0], f"Loss reduction insufficient: {losses[0]:.4f} -> {losses[-1]:.4f}"


def test_energy_based_ood_score_computation():
    """Verify that Free Energy OOD score computation is mathematically sound,
    finite, and preserves temperature shift properties.
    """
    model = GhostECANet(in_channels=1, num_classes=3)
    model.eval()

    dummy_input = torch.randn(5, 1, 128, 128)
    with torch.no_grad():
        logits = model(dummy_input)

    # Free energy score S(x) = T * logsumexp(logits / T)
    t = 2.0
    energy_score = t * torch.logsumexp(logits / t, dim=1)

    assert energy_score.shape == (5,)
    assert not torch.isnan(energy_score).any()
    assert not torch.isinf(energy_score).any()

    # Shift-equivariance property: S(logits + c) == S(logits) + c
    c = 3.0
    shifted_energy = t * torch.logsumexp((logits + c) / t, dim=1)
    assert torch.allclose(shifted_energy, energy_score + c, atol=1e-5)

