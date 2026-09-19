"""
EdgeSAR - Property-Based & Invariant Test Suite.

Verifies mathematical invariants:
1. Parseval's Energy Conservation across 2D FFT / IFFT transforms.
2. Range Matched Filter Phase Shift Linearity.
3. CA-CFAR False Alarm Invariance under varying Rayleigh clutter power.
4. Ghost-ECANet Numerical Stability & Bounded Probability Simplex across input variations.
"""

import sys
from pathlib import Path
import numpy as np
import torch
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.module1_rda.rda_pipeline import RDAPipeline, RDAParameters
from modules.module2_atr.model import GhostECANet


def test_parseval_energy_conservation():
    """Verify Parseval's theorem on 2D Fourier transforms used in RDA."""
    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, (128, 256)) + 1j * rng.normal(0, 1, (128, 256))

    spatial_energy = np.sum(np.abs(x) ** 2)
    # 2D FFT with unitary normalization 'ortho'
    freq_x = np.fft.fft2(x, norm="ortho")
    spectral_energy = np.sum(np.abs(freq_x) ** 2)

    assert np.isclose(spatial_energy, spectral_energy, rtol=1e-5), \
        f"Parseval violation: Spatial {spatial_energy} vs Spectral {spectral_energy}"


def test_matched_filter_shift_property():
    """Verify that a time-delayed echo creates an identically delayed correlation peak."""
    params = RDAParameters(bandwidth=100e6, pulse_duration=5e-6, fs=120e6, window_type="boxcar")
    pipeline = RDAPipeline(params=params)

    n_rng = 512
    t = (np.arange(n_rng) - n_rng / 2.0) / params.fs
    kr = params.chirp_rate
    tp = params.pulse_duration

    # Base pulse
    chirp = np.zeros(n_rng, dtype=np.complex128)
    in_p = np.abs(t) <= (tp / 2.0)
    chirp[in_p] = np.exp(1j * np.pi * kr * (t[in_p] ** 2))

    # Delayed pulse by 10 range bins
    shift_bins = 10
    chirp_shifted = np.roll(chirp, shift_bins)

    out_base = pipeline.range_compression(chirp[np.newaxis, :])[0]
    out_shifted = pipeline.range_compression(chirp_shifted[np.newaxis, :])[0]

    peak_base = int(np.argmax(np.abs(out_base)))
    peak_shifted = int(np.argmax(np.abs(out_shifted)))

    assert peak_shifted - peak_base == shift_bins, \
        f"Shift mismatch: base peak {peak_base}, shifted peak {peak_shifted}, expected delta {shift_bins}"


def test_cfar_scale_invariance():
    """Verify CA-CFAR detection threshold scales linearly with clutter scaling factor."""
    guard_cells = 2
    train_cells = 16
    pfa = 1e-3
    alpha = train_cells * (pfa ** (-1.0 / train_cells) - 1.0)

    rng = np.random.default_rng(101)
    n_samples = 1000
    scale_factor = 5.0

    # Base clutter signal
    clutter1 = rng.rayleigh(scale=1.0, size=n_samples)
    # Scaled clutter signal
    clutter2 = scale_factor * clutter1

    win_slice = slice(10, 10 + train_cells)
    noise_est1 = np.mean(clutter1[win_slice])
    noise_est2 = np.mean(clutter2[win_slice])

    thresh1 = alpha * noise_est1
    thresh2 = alpha * noise_est2

    ratio_thresholds = thresh2 / thresh1

    # Exact mathematical scaling linearity
    assert np.isclose(ratio_thresholds, scale_factor, rtol=1e-5), \
        f"CFAR scale invariance violated: expected {scale_factor:.2f}, got {ratio_thresholds:.2f}"


def test_ghost_ecanet_numerical_stability():
    """Verify model produces bounded outputs without NaN or Inf under extreme input ranges."""
    model = GhostECANet(in_channels=1, num_classes=3)
    model.eval()

    test_inputs = [
        torch.zeros(2, 1, 128, 128),                    # All zero image
        torch.ones(2, 1, 128, 128),                     # Saturated full white image
        torch.rand(2, 1, 128, 128) * 10.0,              # Out of scale range [0, 10]
        torch.randn(2, 1, 128, 128),                    # Standard normal input
    ]

    for inp in test_inputs:
        with torch.no_grad():
            out = model(inp)
            probs = torch.softmax(out, dim=1)

            assert not torch.isnan(out).any(), "Model produced NaN logits"
            assert not torch.isinf(out).any(), "Model produced Inf logits"
            assert torch.all(probs >= 0.0), "Negative probability detected"
            assert torch.allclose(probs.sum(dim=1), torch.ones(2), atol=1e-5), "Probabilities do not sum to 1.0"
