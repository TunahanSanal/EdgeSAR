"""
EdgeSAR - End-to-End Integration Test Suite.

Verifies the complete operational pipeline bridging:
1. Module 1: Raw SAR Echo -> RDA (Range Compression, RCMC, Azimuth Focusing) -> 2D SAR Image
2. Module 3 (Simulated): 1D CA-CFAR Detection identifying target coordinate peaks
3. Module 2: 128x128 Target ROI extraction -> Ghost-ECANet Deep ATR Classification
4. Module 4: Target Classification -> MIL-STD-1553B Dual-Redundant Bus Telemetry Packing
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

from modules.module1_rda.rda_pipeline import RDAPipeline, RDAParameters
from modules.module1_rda.synthetic_generator import SyntheticSARSpectrumGenerator, PointTarget
from modules.module2_atr.model import GhostECANet
from modules.module2_atr.dataset import CLASS_NAMES


def pack_mil_std_1553b_telemetry_word(target_class_id: int, confidence_pct: float, range_bin: int, azimuth_bin: int) -> dict:
    """
    Simulates packing ATR target detection into MIL-STD-1553B 16-bit payload data words
    conforming to docs/mil_std_1553b.md Subaddress 1 (Target Classification Telemetry).

    Word 1: Target ID (bits 15-12), Status Flag (bit 11), Confidence 0-100% (bits 10-0)
    Word 2: Slant Range Coordinate Bin (16 bits)
    Word 3: Azimuth Coordinate Bin (16 bits)
    """
    conf_int = int(np.clip(confidence_pct, 0.0, 100.0) * 10.0) & 0x07FF  # 11 bits: 0 to 1000 (0.1% res)
    status_bit = 1 << 11  # Target Confirmed Valid
    target_id = (target_class_id & 0x0F) << 12

    word1 = target_id | status_bit | conf_int
    word2 = range_bin & 0xFFFF
    word3 = azimuth_bin & 0xFFFF

    return {
        "subaddress": 1,
        "word_count": 3,
        "raw_words": [word1, word2, word3],
        "hex_words": [f"0x{word1:04X}", f"0x{word2:04X}", f"0x{word3:04X}"],
        "target_class": CLASS_NAMES[target_class_id] if target_class_id < len(CLASS_NAMES) else "UNKNOWN",
        "confidence_pct": confidence_pct,
        "coordinates": (range_bin, azimuth_bin),
    }


def test_end_to_end_pipeline_integration():
    """Execute full flight pipeline from raw radar signal to 1553B bus output."""
    # Step 1: Synthesize raw radar echo with a known centered target
    params = RDAParameters(f0=9.6e9, bandwidth=100e6, fs=120e6, prf=1000.0, velocity=150.0)
    gen = SyntheticSARSpectrumGenerator(
        params=params,
        n_azimuth=256,
        n_range=256,
    )
    raw_echo = gen.generate_raw_echo(
        targets=[PointTarget(range_offset=0.0, azimuth_offset=0.0, rcs=1.0)],
        snr_db=25.0,
        seed=123,
    )

    # Step 2: Form 2D image via RDA
    pipeline = RDAPipeline(params=params)
    rda_out = pipeline.process(raw_echo)
    focused_mag = rda_out["magnitude"]
    assert focused_mag.shape == (256, 256)

    # Step 3: Simple CFAR / Peak detection to localize target ROI
    peak_az, peak_rng = np.unravel_index(np.argmax(focused_mag), focused_mag.shape)
    assert abs(peak_az - 128) <= 4, f"Target azimuth peak deviated: {peak_az}"
    assert abs(peak_rng - 128) <= 4, f"Target range peak deviated: {peak_rng}"

    # Step 4: Extract 128x128 normalized chip for ATR model
    half_box = 64
    r_start = max(0, peak_rng - half_box)
    r_end = min(256, r_start + 128)
    a_start = max(0, peak_az - half_box)
    a_end = min(256, a_start + 128)

    chip = focused_mag[a_start:a_end, r_start:r_end].copy()
    if chip.shape != (128, 128):
        chip = np.pad(chip, ((0, 128 - chip.shape[0]), (0, 128 - chip.shape[1])), mode="reflect")

    # Normalize to [0.0, 1.0]
    chip_norm = chip / (np.max(chip) + 1e-12)
    chip_tensor = torch.from_numpy(chip_norm.astype(np.float32)).unsqueeze(0).unsqueeze(0)
    assert chip_tensor.shape == (1, 1, 128, 128)

    # Step 5: Classify target using Ghost-ECANet
    model = GhostECANet(in_channels=1, num_classes=3)
    model.eval()
    with torch.no_grad():
        logits = model(chip_tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).numpy()
        pred_class_id = int(np.argmax(probs))
        pred_conf_pct = float(probs[pred_class_id] * 100.0)

    assert 0 <= pred_class_id < 3
    assert 0.0 <= pred_conf_pct <= 100.0

    # Step 6: Encode into MIL-STD-1553B dual-redundant telemetry
    telemetry = pack_mil_std_1553b_telemetry_word(
        target_class_id=pred_class_id,
        confidence_pct=pred_conf_pct,
        range_bin=peak_rng,
        azimuth_bin=peak_az,
    )

    assert telemetry["subaddress"] == 1
    assert len(telemetry["raw_words"]) == 3
    assert telemetry["raw_words"][0] & (1 << 11) != 0, "Valid target status bit must be set!"
    assert telemetry["coordinates"] == (peak_rng, peak_az)
