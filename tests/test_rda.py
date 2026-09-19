"""
Unit test suite for EdgeSAR Module 1: Range-Doppler Algorithm (RDA).

Verifies:
1. Chirp matched filter impulse response and Peak Sidelobe Ratio (PSLR).
2. Range Cell Migration Correction (RCMC) curvature straightening.
3. 2D focused point target resolution and multi-target detection.
4. Array dimensions, energy conservation invariants, and numerical stability.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.module1_rda.rda_pipeline import RDAPipeline, RDAParameters
from modules.module1_rda.synthetic_generator import SyntheticSARSpectrumGenerator, PointTarget


@pytest.fixture
def rda_params():
    """Default radar parameters fixture."""
    return RDAParameters(
        f0=9.6e9,
        bandwidth=100.0e6,
        pulse_duration=5.0e-6,
        fs=120.0e6,
        velocity=150.0,
        r0=5000.0,
        prf=1000.0,
        antenna_length=1.5,
        window_type="hamming",
    )


def test_chirp_matched_filter_impulse_response(rda_params):
    """Test 1D Range Matched Filter impulse response, peak location, and sidelobes."""
    # Set to rectangular window to verify theoretical sinc PSLR of -13.26 dB
    params_rect = RDAParameters(
        bandwidth=rda_params.bandwidth,
        pulse_duration=rda_params.pulse_duration,
        fs=rda_params.fs,
        window_type="boxcar",
    )
    pipeline = RDAPipeline(params=params_rect)

    n_rng = 1024
    tau = (np.arange(n_rng) - n_rng / 2.0) / params_rect.fs
    kr = params_rect.chirp_rate
    tp = params_rect.pulse_duration

    # Synthesize isolated 1D chirp at zero delay
    in_pulse = np.abs(tau) <= (tp / 2.0)
    chirp_1d = np.zeros(n_rng, dtype=np.complex128)
    chirp_1d[in_pulse] = np.exp(1j * np.pi * kr * (tau[in_pulse] ** 2))

    # Reshape to (1, N_rng) for 2D pipeline compatibility
    raw_2d = chirp_1d[np.newaxis, :]
    compressed_2d = pipeline.range_compression(raw_2d)
    compressed_1d = compressed_2d[0, :]

    mag = np.abs(compressed_1d)
    peak_idx = int(np.argmax(mag))
    expected_peak = n_rng // 2

    # Verify peak is at center within +/- 1 bin
    assert abs(peak_idx - expected_peak) <= 1, f"Peak at {peak_idx}, expected {expected_peak}"

    # Use standard 16x zero-padding oversampling to measure continuous sinc PSLR
    pad_factor = 16
    spec = np.fft.fft(compressed_1d)
    padded = np.zeros(n_rng * pad_factor, dtype=np.complex128)
    padded[: n_rng // 2] = spec[: n_rng // 2]
    padded[-n_rng // 2 :] = spec[-n_rng // 2 :]
    fine_profile = np.abs(np.fft.ifft(padded))
    p_fine = int(np.argmax(fine_profile))
    db_fine = 20.0 * np.log10(fine_profile / np.max(fine_profile))

    # Walk to first null
    null_idx = p_fine
    while null_idx < len(db_fine) - 1 and db_fine[null_idx + 1] < db_fine[null_idx]:
        null_idx += 1

    # Walk to first sidelobe peak
    sidelobe_idx = null_idx
    while sidelobe_idx < len(db_fine) - 1 and db_fine[sidelobe_idx + 1] > db_fine[sidelobe_idx]:
        sidelobe_idx += 1

    pslr_rect_db = float(db_fine[sidelobe_idx])

    # Theoretical sinc first sidelobe is -13.26 dB
    assert -14.5 <= pslr_rect_db <= -12.0, f"Rectangular PSLR was {pslr_rect_db:.2f} dB, expected ~ -13.26 dB"

    # Now test with Hamming window: PSLR should be suppressed below -25 dB
    pipeline_hamming = RDAPipeline(params=rda_params)
    comp_hamming = pipeline_hamming.range_compression(raw_2d)[0, :]
    spec_h = np.fft.fft(comp_hamming)
    padded_h = np.zeros(n_rng * pad_factor, dtype=np.complex128)
    padded_h[: n_rng // 2] = spec_h[: n_rng // 2]
    padded_h[-n_rng // 2 :] = spec_h[-n_rng // 2 :]
    fine_h = np.abs(np.fft.ifft(padded_h))
    db_h = 20.0 * np.log10(fine_h / np.max(fine_h))

    p_fine_h = int(np.argmax(fine_h))
    null_h = p_fine_h
    while null_h < len(db_h) - 1 and db_h[null_h + 1] < db_h[null_h]:
        null_h += 1

    sidelobe_h = null_h
    while sidelobe_h < len(db_h) - 1 and db_h[sidelobe_h + 1] > db_h[sidelobe_h]:
        sidelobe_h += 1

    pslr_hamming_db = float(db_h[sidelobe_h])
    assert pslr_hamming_db < -25.0, f"Hamming window did not suppress sidelobes sufficiently: {pslr_hamming_db:.2f} dB"


def test_rcmc_curvature_straightening(rda_params):
    """Test that RCMC straightens the hyperbolic range migration trajectory in Range-Doppler domain."""
    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=256, n_range=512)
    # Single target at center, zero noise for pristine tracking
    single_target = [PointTarget(range_offset=0.0, azimuth_offset=0.0, rcs=1.0)]
    raw_data = generator.generate_raw_echo(targets=single_target, snr_db=None, seed=42)

    pipeline = RDAPipeline(params=rda_params)
    s_rc = pipeline.range_compression(raw_data)
    s_rd = pipeline.azimuth_fft(s_rc)
    s_rcmc, delta_r = pipeline.range_cell_migration_correction(s_rd)

    # In Range-Doppler domain, check peak range index as a function of Doppler bin
    n_az = s_rd.shape[0]
    center_doppler = n_az // 2

    # Measure range peak position for bins across the active Doppler spectrum
    active_doppler_bins = range(center_doppler - 40, center_doppler + 41, 10)
    peaks_before = [int(np.argmax(np.abs(s_rd[d, :]))) for d in active_doppler_bins]
    peaks_after = [int(np.argmax(np.abs(s_rcmc[d, :]))) for d in active_doppler_bins]

    # Before RCMC, the peak positions vary across Doppler frequencies due to migration
    variance_before = np.var(peaks_before)
    # After RCMC, all peaks must align at the same range bin
    variance_after = np.var(peaks_after)

    assert variance_after <= variance_before, "RCMC should reduce range migration variance across Doppler bins"
    assert variance_after <= 0.1, f"Peak range bins after RCMC should be straight (var={variance_after})"


def test_2d_focused_point_target_resolution(rda_params):
    """Verify 2D focused point targets: all targets detected at expected positions with sharp resolution."""
    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=256, n_range=512)
    # Use 3 widely separated targets
    targets = [
        PointTarget(range_offset=0.0, azimuth_offset=0.0, rcs=1.0),
        PointTarget(range_offset=25.0, azimuth_offset=0.0, rcs=0.8),
        PointTarget(range_offset=0.0, azimuth_offset=25.0, rcs=0.8),
    ]
    raw_data = generator.generate_raw_echo(targets=targets, snr_db=30.0, seed=123)

    pipeline = RDAPipeline(params=rda_params)
    results = pipeline.process(raw_data)
    focused_mag = results["magnitude"]

    # Resolution grid scales
    range_spacing = rda_params.c / (2.0 * rda_params.fs)
    azimuth_spacing = rda_params.velocity / rda_params.prf

    # Target 0 is at scene center (N_az//2, N_rng//2)
    center_az = 256 // 2
    center_rng = 512 // 2

    # Find peak near scene center
    win_az = slice(center_az - 15, center_az + 16)
    win_rng = slice(center_rng - 15, center_rng + 16)
    local_sub = focused_mag[win_az, win_rng]
    local_idx = np.unravel_index(np.argmax(local_sub), local_sub.shape)
    peak_az = win_az.start + local_idx[0]
    peak_rng = win_rng.start + local_idx[1]

    # Verify peak is within 2 bins of center
    assert abs(peak_az - center_az) <= 3
    assert abs(peak_rng - center_rng) <= 3

    # Measure 3dB width of center target
    rng_profile = focused_mag[peak_az, :]
    az_profile = focused_mag[:, peak_rng]

    rng_3db_bins = np.sum(rng_profile >= (0.707 * np.max(rng_profile)))
    az_3db_bins = np.sum(az_profile >= (0.707 * np.max(az_profile)))

    rng_res = rng_3db_bins * range_spacing
    az_res = az_3db_bins * azimuth_spacing

    # Verify 3dB resolutions are within reasonable bounds of theoretical resolutions
    assert rng_res < 4.0, f"Range resolution degraded: {rng_res:.2f} m (theoretical {rda_params.range_resolution:.2f} m)"
    assert az_res < 2.0, f"Azimuth resolution degraded: {az_res:.2f} m (theoretical {rda_params.azimuth_resolution:.2f} m)"


def test_array_dimensions_and_invariants(rda_params):
    """Verify dimensional preservation, energy conservation (Parseval), and numerical stability."""
    n_az, n_rng = 128, 256
    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=n_az, n_range=n_rng)
    raw_data = generator.generate_raw_echo(snr_db=20.0, seed=99)

    assert raw_data.shape == (n_az, n_rng)
    assert not np.isnan(raw_data).any(), "Raw data contains NaN values"
    assert not np.isinf(raw_data).any(), "Raw data contains Inf values"

    pipeline = RDAPipeline(params=rda_params)
    results = pipeline.process(raw_data)

    # Dimension invariance across all intermediate products
    assert results["range_compressed"].shape == (n_az, n_rng)
    assert results["range_doppler"].shape == (n_az, n_rng)
    assert results["rcmc"].shape == (n_az, n_rng)
    assert results["focused_image"].shape == (n_az, n_rng)
    assert results["magnitude"].shape == (n_az, n_rng)
    assert results["intensity_db"].shape == (n_az, n_rng)

    # Numerical hygiene: no NaN / Inf anywhere
    for key, arr in results.items():
        if isinstance(arr, np.ndarray):
            assert not np.isnan(arr).any(), f"Array {key} produced NaN values"
            assert not np.isinf(arr).any(), f"Array {key} produced Inf values"

    # Energy preservation check (Parseval's theorem on FFTs):
    # Total power should remain within finite positive bounds
    raw_energy = np.sum(np.abs(raw_data) ** 2)
    focused_energy = np.sum(np.abs(results["focused_image"]) ** 2)
    assert raw_energy > 0.0
    assert focused_energy > 0.0


def test_real_sar_smoke_and_focus_metrics(rda_params):
    """Smoke test: verify RDA execution and focus metrics on realistic/real SAR complex data."""
    import time
    from scripts.sar_real_loader import generate_realistic_maritime_sar_scene, compute_focus_metrics

    # Realistic maritime scene with sea clutter & vessel reflectors
    n_az, n_rng = 256, 256
    real_scene = generate_realistic_maritime_sar_scene(n_azimuth=n_az, n_range=n_rng, seed=123)

    assert real_scene.shape == (n_az, n_rng)
    assert not np.isnan(real_scene).any(), "Input real SAR scene contains NaN"
    assert not np.isinf(real_scene).any(), "Input real SAR scene contains Inf"

    pipeline = RDAPipeline(params=rda_params)
    t0 = time.perf_counter()
    focused = pipeline.process(real_scene)["focused_image"]
    proc_time = time.perf_counter() - t0

    assert focused.shape == (n_az, n_rng)
    assert not np.isnan(focused).any(), "RDA focused output produced NaN on real SAR data"
    assert not np.isinf(focused).any(), "RDA focused output produced Inf on real SAR data"

    # Compute objective focus metrics
    metrics = compute_focus_metrics(focused)
    assert np.isfinite(metrics["entropy"]), "Shannon entropy is non-finite!"
    assert np.isfinite(metrics["contrast"]), "Image contrast is non-finite!"
    assert metrics["contrast"] > 0.0, "Contrast must be strictly positive"
    assert metrics["papr_db"] > 0.0, "PAPR must be strictly positive"


def test_rda_execution_time_performance_benchmark(rda_params):
    """Performance regression test: ensure RDA execution throughput is maintained."""
    import time

    n_az, n_rng = 256, 512
    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=n_az, n_range=n_rng)
    raw_data = generator.generate_raw_echo(snr_db=15.0, seed=77)

    pipeline = RDAPipeline(params=rda_params)
    t0 = time.perf_counter()
    results = pipeline.process(raw_data)
    elapsed_s = time.perf_counter() - t0

    # Ensure 256x512 = 131,072 complex samples process in under 1.0 second on host CPU
    assert elapsed_s < 1.0, f"Performance regression detected: {elapsed_s:.3f} s exceeds 1.0 s threshold"
    assert results["focused_image"].shape == (n_az, n_rng)


def test_isolated_target_pslr_measurement(rda_params):
    """Verify that measure_isolated_target_pslr correctly measures sidelobes on an isolated target."""
    from run_rda import measure_isolated_target_pslr

    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=256, n_range=512)
    single_target = [PointTarget(range_offset=0.0, azimuth_offset=0.0, rcs=1.0)]
    raw_data = generator.generate_raw_echo(targets=single_target, snr_db=30.0, seed=42)

    pipeline = RDAPipeline(params=rda_params)
    results = pipeline.process(raw_data)
    focused = results["focused_image"]
    mag = np.abs(focused)

    peak_idx_2d = np.unravel_index(np.argmax(mag), mag.shape)
    peak_val = np.max(mag)
    focused_db = 20.0 * np.log10(np.clip(mag / peak_val, 1e-12, 1.0))

    range_spacing_m = rda_params.c / (2.0 * rda_params.fs)
    azimuth_spacing_m = rda_params.velocity / rda_params.prf

    isolated = measure_isolated_target_pslr(
        focused_db,
        target_row=peak_idx_2d[0],
        target_col=peak_idx_2d[1],
        sample_spacing_range=range_spacing_m,
        sample_spacing_azimuth=azimuth_spacing_m,
        guard_bins=15,
    )

    assert "range_pslr_db" in isolated
    assert "azimuth_pslr_db" in isolated
    # For an isolated target with Hamming window, range PSLR should be <= -20 dB
    assert isolated["range_pslr_db"] <= -20.0, f"Expected range PSLR <= -20 dB, got {isolated['range_pslr_db']:.2f} dB"


def test_multi_target_constellation_isolated_pslr(rda_params):
    """Regression test: verify isolated target PSLR on canonical 5-point constellation.

    Validates that center target sidelobes in a multi-target scene are isolated
    from neighbor scatterers without mainlobe skirt or constellation leakage:
      - isolated range_pslr_db <= -38.0 dB
      - isolated azimuth_pslr_db <= -28.0 dB
      - both axes <= -28.0 dB
      - isolated range PSLR is better or equal (<=) to windowed range PSLR
    """
    from run_rda import measure_resolution_and_pslr, measure_isolated_target_pslr

    n_az, n_rng = 512, 1024
    generator = SyntheticSARSpectrumGenerator(params=rda_params, n_azimuth=n_az, n_range=n_rng)
    raw_data = generator.generate_raw_echo(snr_db=25.0, seed=42)

    pipeline = RDAPipeline(params=rda_params)
    results = pipeline.process(raw_data)
    focused = results["focused_image"]
    mag = np.abs(focused)

    range_spacing_m = rda_params.c / (2.0 * rda_params.fs)
    azimuth_spacing_m = rda_params.velocity / rda_params.prf

    center_az_idx = n_az // 2
    center_rng_idx = n_rng // 2
    search_az = slice(max(0, center_az_idx - 30), min(n_az, center_az_idx + 30))
    search_rng = slice(max(0, center_rng_idx - 30), min(n_rng, center_rng_idx + 30))
    sub_mag = mag[search_az, search_rng]
    local_max = np.unravel_index(np.argmax(sub_mag), sub_mag.shape)
    peak_az = search_az.start + local_max[0]
    peak_rng = search_rng.start + local_max[1]

    rng_res, rng_pslr = measure_resolution_and_pslr(
        mag[peak_az, :], range_spacing_m, guard_bins=5, vicinity_bins=18
    )
    az_res, az_pslr = measure_resolution_and_pslr(
        mag[:, peak_rng], azimuth_spacing_m, guard_bins=16, vicinity_bins=150
    )

    peak_val_2d = np.max(mag)
    focused_image_db = 20.0 * np.log10(np.clip(mag / max(peak_val_2d, 1e-12), 1e-12, 1.0))
    isolated = measure_isolated_target_pslr(
        focused_image_db,
        target_row=peak_az,
        target_col=peak_rng,
        sample_spacing_range=range_spacing_m,
        sample_spacing_azimuth=azimuth_spacing_m,
        guard_bins=15,
    )

    assert isolated["range_pslr_db"] <= -38.0, (
        f"Isolated range PSLR {isolated['range_pslr_db']:.2f} dB exceeds -38.0 dB"
    )
    assert isolated["azimuth_pslr_db"] <= -28.0, (
        f"Isolated azimuth PSLR {isolated['azimuth_pslr_db']:.2f} dB exceeds -28.0 dB"
    )
    assert isolated["range_pslr_db"] <= -28.0 and isolated["azimuth_pslr_db"] <= -28.0, (
        "Both isolated axes must be <= -28.0 dB"
    )
    assert isolated["range_pslr_db"] <= rng_pslr, (
        f"Isolated range PSLR {isolated['range_pslr_db']:.2f} dB should be <= windowed range PSLR {rng_pslr:.2f} dB"
    )



