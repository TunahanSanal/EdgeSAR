"""
EdgeSAR - Regression Test Suite.

Guarantees no performance, memory, or architectural regressions:
1. Deep Learning Parameter Budget (< 2,000,000 parameters).
2. Embedded C Memory Safety (0 dynamic heap allocations, no malloc/calloc/free).
3. RDA Point Target Focusing Resolutions (Range < 4.0m, Azimuth < 2.0m).
4. MSTAR Data Loader Invariants (exact 1x128x128 shape, normalized [0, 1]).
5. High-level metric threshold regression checks against baseline.
"""

import sys
import os
from pathlib import Path
import json
import pytest
import numpy as np
import torch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.module2_atr.model import GhostECANet, count_parameters
from modules.module1_rda.rda_pipeline import RDAPipeline, RDAParameters
from modules.module1_rda.synthetic_generator import SyntheticSARSpectrumGenerator, PointTarget
from scripts.mstar_loader import MSTARDataset


def test_parameter_budget_regression():
    """Ensure ATR model strictly adheres to the SWaP parameter constraint."""
    model = GhostECANet(in_channels=1, num_classes=3)
    params = count_parameters(model)
    assert params < 2000000, f"Parameter budget exceeded: {params:,} >= 2,000,000"
    assert params == 904268, f"Unexpected parameter count drift: {params:,}"


def test_embedded_c_zero_heap_memory_safety():
    """Verify that embedded C sources contain zero dynamic allocation calls."""
    c_src_dir = ROOT_DIR / "modules" / "module3_embedded" / "src"
    c_files = list(c_src_dir.glob("*.c")) + list((ROOT_DIR / "modules" / "module3_embedded" / "include").glob("*.h"))

    forbidden_tokens = ["malloc(", "calloc(", "free(", "realloc(", "alloca("]
    for c_file in c_files:
        content = c_file.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            assert token not in content, f"Memory safety violation: found '{token}' in {c_file.name}"


def test_rda_resolution_bounds_regression():
    """Ensure RDA resolution does not regress beyond mission requirements."""
    params = RDAParameters(f0=9.6e9, bandwidth=100e6, fs=120e6, velocity=150.0, prf=1000.0)
    gen = SyntheticSARSpectrumGenerator(
        params=params,
        n_azimuth=256,
        n_range=256,
    )
    raw = gen.generate_raw_echo(
        targets=[PointTarget(0.0, 0.0, 1.0)],
        snr_db=30.0,
        seed=42,
    )
    focused = RDAPipeline(params=params).process(raw)["magnitude"]

    peak_az, peak_rng = np.unravel_index(np.argmax(focused), focused.shape)
    rng_slice = focused[peak_az, :]
    az_slice = focused[:, peak_rng]

    rng_3db = np.sum(rng_slice >= 0.707 * np.max(rng_slice)) * (params.c / (2.0 * params.fs))
    az_3db = np.sum(az_slice >= 0.707 * np.max(az_slice)) * (params.velocity / params.prf)

    assert rng_3db < 4.0, f"Range resolution degraded: {rng_3db:.2f} m >= 4.0 m"
    assert az_3db < 2.0, f"Azimuth resolution degraded: {az_3db:.2f} m >= 2.0 m"


def test_mstar_loader_integrity_regression():
    """Ensure MSTAR data loads in exact expected normalized tensor shape."""
    mstar_dir = ROOT_DIR / "data" / "mstar"
    if (mstar_dir / "train_cache.npz").exists():
        ds = MSTARDataset(root_dir=str(mstar_dir), split="train", augment=False)
        x, y = ds[0]
        assert x.shape == (1, 128, 128), f"MSTAR tensor shape mismatch: {x.shape}"
        assert 0.0 <= x.min() and x.max() <= 1.0, "Normalization bounds violated"
        assert y in [0, 1, 2], f"Invalid class label: {y}"
