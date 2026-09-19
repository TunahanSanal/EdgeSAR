"""
EdgeSAR - Range-Doppler Algorithm (RDA) CLI Runner.

Reconstructs 2D focused SAR images from raw radar echo data (or analytical synthetic
point-scatterer echo) from first principles. Produces comprehensive diagnostic
PNG figures displaying every intermediate signal processing transformation stage.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless backend for artifact generation
import matplotlib.pyplot as plt

# Ensure root EdgeSAR is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import json
from modules.module1_rda.rda_pipeline import RDAPipeline, RDAParameters
from modules.module1_rda.synthetic_generator import SyntheticSARSpectrumGenerator, PointTarget
from scripts.sar_real_loader import compute_focus_metrics, export_sample_real_sar_dataset


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EdgeSAR Range-Doppler Algorithm (RDA) 2D SAR Image Formation Pipeline"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="synthetic",
        help="Path to raw complex echo .npy file, 'synthetic', or 'real'",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="sentinel1",
        choices=["sentinel1", "open_sar", "custom"],
        help="Real SAR data source when --input real is specified (e.g. sentinel1, open_sar)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output_rda",
        help="Directory where diagnostic PNG plots will be saved",
    )
    parser.add_argument(
        "--snr",
        type=float,
        default=25.0,
        help="Thermal noise SNR in dB when generating synthetic echoes",
    )
    parser.add_argument(
        "--window",
        type=str,
        default="hamming",
        choices=["hamming", "kaiser", "hann", "boxcar"],
        help="Spectral windowing function for sidelobe control",
    )
    return parser.parse_args()


def measure_resolution_and_pslr(
    profile_1d: np.ndarray,
    sample_spacing_m: float,
    guard_bins: int = 5,
    vicinity_bins: int = 18,
) -> tuple[float, float]:
    """Measure 3dB mainlobe resolution and Peak Sidelobe Ratio (PSLR) in dB.

    Args:
        profile_1d: 1D linear magnitude array across peak.
        sample_spacing_m: Physical spacing between adjacent bins in meters.
        guard_bins: Number of bins on each side of peak excluded as mainlobe.
        vicinity_bins: Neighborhood radius to search for sidelobes.

    Returns:
        (res_3db_m, pslr_db)
    """
    peak_idx = int(np.argmax(profile_1d))
    peak_val = profile_1d[peak_idx]
    if peak_val <= 0:
        return 0.0, 0.0

    # Logarithmic normalized profile in dB
    profile_db = 20.0 * np.log10(np.clip(profile_1d / peak_val, 1e-12, 1.0))

    # 3dB beamwidth (where profile_db crosses -3.0 dB)
    half_power_mask = profile_db >= -3.01
    res_bins = np.sum(half_power_mask)
    res_m = res_bins * sample_spacing_m

    # Sidelobes: measure within the target's local neighborhood (within +/- vicinity_bins)
    # outside the mainlobe (+/- guard_bins) to avoid contamination from adjacent targets
    n = len(profile_1d)
    sidelobe_mask = np.zeros(n, dtype=bool)
    vicinity_left = max(0, peak_idx - vicinity_bins)
    vicinity_right = min(n, peak_idx + vicinity_bins + 1)
    sidelobe_mask[vicinity_left:vicinity_right] = True
    left_guard = max(0, peak_idx - guard_bins)
    right_guard = min(n, peak_idx + guard_bins + 1)
    sidelobe_mask[left_guard:right_guard] = False

    if np.any(sidelobe_mask):
        sidelobe_peak = np.max(profile_1d[sidelobe_mask])
        pslr_db = 20.0 * np.log10(max(sidelobe_peak / peak_val, 1e-12))
    else:
        pslr_db = -99.0

    return res_m, pslr_db


def measure_isolated_target_pslr(
    focused_image_db: np.ndarray,
    target_row: int,
    target_col: int,
    sample_spacing_range: float,
    sample_spacing_azimuth: float,
    guard_bins: int = 15,
) -> dict:
    nr, nc = focused_image_db.shape
    range_cut = focused_image_db[target_row, :]
    peak_col = np.argmax(range_cut)
    peak_val = range_cut[peak_col]

    sl_mask = np.zeros(nc, dtype=bool)
    sl_mask[max(0, peak_col - 20) : min(nc, peak_col + 21)] = True
    sl_mask[max(0, peak_col - guard_bins) : min(nc, peak_col + guard_bins + 1)] = False

    range_pslr = np.max(range_cut[sl_mask]) - peak_val if np.any(sl_mask) else -99.0

    az_cut = focused_image_db[:, target_col]
    peak_row = np.argmax(az_cut)
    peak_val_az = az_cut[peak_row]

    sl_mask_az = np.zeros(nr, dtype=bool)
    sl_mask_az[max(0, peak_row - 150) : min(nr, peak_row + 151)] = True
    sl_mask_az[max(0, peak_row - guard_bins) : min(nr, peak_row + guard_bins + 1)] = False

    az_pslr = np.max(az_cut[sl_mask_az]) - peak_val_az if np.any(sl_mask_az) else -99.0

    return {
        "range_pslr_db": float(range_pslr),
        "azimuth_pslr_db": float(az_pslr),
        "measurement_note": "Isolated cuts strictly bounded: range +/-20 bins, azimuth +/-150 bins, exterior to constellation neighbors (+/-24 range, +/-200 azimuth bins)",
    }



def plot_diagnostic_figures(
    results: dict,
    params: RDAParameters,
    output_dir: Path,
) -> None:
    """Generate the four mandatory diagnostic PNG figures."""
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_data = results["raw_data"]
    s_rc = results["range_compressed"]
    s_rd = results["range_doppler"]
    s_rcmc = results["rcmc"]
    focused = results["focused_image"]
    mag = results["magnitude"]
    intensity_db = results["intensity_db"]

    n_az, n_rng = raw_data.shape

    # Fast-time slant range axis (m) relative to R0
    range_axis_m = (np.arange(n_rng) - n_rng / 2.0) * (params.c / (2.0 * params.fs))
    # Slow-time azimuth spatial axis (m)
    azimuth_axis_m = (np.arange(n_az) - n_az / 2.0) * (params.velocity / params.prf)
    # Doppler frequency axis (Hz)
    doppler_axis_hz = np.linspace(-params.prf / 2.0, params.prf / 2.0, n_az, endpoint=False)

    # -------------------------------------------------------------
    # Figure 1: Raw Signal Echo (2D Real and Magnitude)
    # -------------------------------------------------------------
    fig1, axes1 = plt.subplots(1, 2, figsize=(14, 6))
    im1_0 = axes1[0].imshow(
        np.real(raw_data),
        aspect="auto",
        cmap="viridis",
        extent=[range_axis_m[0], range_axis_m[-1], azimuth_axis_m[-1], azimuth_axis_m[0]],
    )
    axes1[0].set_title("Raw Baseband Signal [Real Part]")
    axes1[0].set_xlabel("Fast-Time Slant Range Offset (m)")
    axes1[0].set_ylabel("Slow-Time Flight Track (m)")
    fig1.colorbar(im1_0, ax=axes1[0], label="Amplitude")

    im1_1 = axes1[1].imshow(
        np.abs(raw_data),
        aspect="auto",
        cmap="magma",
        extent=[range_axis_m[0], range_axis_m[-1], azimuth_axis_m[-1], azimuth_axis_m[0]],
    )
    axes1[1].set_title("Raw Baseband Signal [Magnitude Envelope]")
    axes1[1].set_xlabel("Fast-Time Slant Range Offset (m)")
    fig1.colorbar(im1_1, ax=axes1[1], label="|Echo|")

    plt.suptitle("Stage 1: Raw Unfocused SAR Chirp Signals (Hyperbolic Wavefronts)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig1_path = output_dir / "01_raw_signal.png"
    plt.savefig(fig1_path, dpi=150)
    plt.close(fig1)

    # -------------------------------------------------------------
    # Figure 2: Range Compressed Signal (Showing Range Migration Parabolas)
    # -------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    rc_mag = np.abs(s_rc)
    rc_db = 20.0 * np.log10(np.clip(rc_mag / np.max(rc_mag), 1e-4, 1.0))
    im2 = ax2.imshow(
        rc_db,
        aspect="auto",
        cmap="inferno",
        vmin=-40,
        vmax=0,
        extent=[range_axis_m[0], range_axis_m[-1], azimuth_axis_m[-1], azimuth_axis_m[0]],
    )
    ax2.set_title("After Range Matched Filtering (Notice Curved Range Migration Parabolas)", fontsize=12)
    ax2.set_xlabel("Slant Range Offset (m)")
    ax2.set_ylabel("Slow-Time Flight Track (m)")
    fig2.colorbar(im2, ax=ax2, label="Normalized Intensity (dB)")

    plt.suptitle("Stage 2: Range Compression (Pulse Width Contracted from Tp down to ~1/Br)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig2_path = output_dir / "02_range_compressed.png"
    plt.savefig(fig2_path, dpi=150)
    plt.close(fig2)

    # -------------------------------------------------------------
    # Figure 3: Range-Doppler Domain Before vs. After RCMC
    # -------------------------------------------------------------
    fig3, axes3 = plt.subplots(1, 2, figsize=(14, 6))
    rd_db = 20.0 * np.log10(np.clip(np.abs(s_rd) / np.max(np.abs(s_rd)), 1e-4, 1.0))
    rcmc_db = 20.0 * np.log10(np.clip(np.abs(s_rcmc) / np.max(np.abs(s_rcmc)), 1e-4, 1.0))

    im3_0 = axes3[0].imshow(
        rd_db,
        aspect="auto",
        cmap="jet",
        vmin=-35,
        vmax=0,
        extent=[range_axis_m[0], range_axis_m[-1], doppler_axis_hz[-1], doppler_axis_hz[0]],
    )
    axes3[0].set_title("Before RCMC (Parabolic Trajectory in Range-Doppler)")
    axes3[0].set_xlabel("Slant Range Offset (m)")
    axes3[0].set_ylabel("Doppler Frequency f_eta (Hz)")
    fig3.colorbar(im3_0, ax=axes3[0], label="Power (dB)")

    im3_1 = axes3[1].imshow(
        rcmc_db,
        aspect="auto",
        cmap="jet",
        vmin=-35,
        vmax=0,
        extent=[range_axis_m[0], range_axis_m[-1], doppler_axis_hz[-1], doppler_axis_hz[0]],
    )
    axes3[1].set_title("After RCMC (Straightened Vertical Trajectory)")
    axes3[1].set_xlabel("Slant Range Offset (m)")
    fig3.colorbar(im3_1, ax=axes3[1], label="Power (dB)")

    plt.suptitle("Stage 3: Range Cell Migration Correction (RCMC) in Range-Doppler Domain", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig3_path = output_dir / "03_rcmc_range_doppler.png"
    plt.savefig(fig3_path, dpi=150)
    plt.close(fig3)

    # -------------------------------------------------------------
    # Figure 4: Final 2D Focused SAR Image & Slices
    # -------------------------------------------------------------
    fig4 = plt.figure(figsize=(15, 9))
    gs = fig4.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_2d = fig4.add_subplot(gs[0, :])
    im4 = ax_2d.imshow(
        intensity_db,
        aspect="auto",
        cmap="gray",
        vmin=-45,
        vmax=0,
        extent=[range_axis_m[0], range_axis_m[-1], azimuth_axis_m[-1], azimuth_axis_m[0]],
    )
    ax_2d.set_title("2D Focused SAR Image Reconstructed via Range-Doppler Algorithm", fontsize=13, fontweight="bold")
    ax_2d.set_xlabel("Range Coordinate (m)")
    ax_2d.set_ylabel("Azimuth Coordinate (m)")
    fig4.colorbar(im4, ax=ax_2d, label="Log Intensity (dB)")

    # Find center target peak for 1D slices
    center_az_idx = n_az // 2
    center_rng_idx = n_rng // 2
    # Search in small window around scene center
    search_az = slice(max(0, center_az_idx - 30), min(n_az, center_az_idx + 30))
    search_rng = slice(max(0, center_rng_idx - 30), min(n_rng, center_rng_idx + 30))
    sub_mag = mag[search_az, search_rng]
    local_max = np.unravel_index(np.argmax(sub_mag), sub_mag.shape)
    peak_az = search_az.start + local_max[0]
    peak_rng = search_rng.start + local_max[1]

    # Range slice across peak
    range_slice = mag[peak_az, :]
    range_slice_db = 20.0 * np.log10(np.clip(range_slice / np.max(range_slice), 1e-4, 1.0))
    zoom_rng = slice(max(0, peak_rng - 35), min(n_rng, peak_rng + 36))

    ax_rng = fig4.add_subplot(gs[1, 0])
    ax_rng.plot(range_axis_m[zoom_rng], range_slice_db[zoom_rng], "b.-", linewidth=1.5)
    ax_rng.axhline(-3.0, color="r", linestyle="--", label="-3 dB Level")
    ax_rng.set_title("Range Impulse Response Slice (Zoomed)")
    ax_rng.set_xlabel("Slant Range Offset (m)")
    ax_rng.set_ylabel("Normalized Power (dB)")
    ax_rng.set_ylim([-45, 2])
    ax_rng.grid(True, linestyle=":", alpha=0.6)
    ax_rng.legend(loc="upper right")

    # Azimuth slice across peak
    az_slice = mag[:, peak_rng]
    az_slice_db = 20.0 * np.log10(np.clip(az_slice / np.max(az_slice), 1e-4, 1.0))
    zoom_az = slice(max(0, peak_az - 35), min(n_az, peak_az + 36))

    ax_az = fig4.add_subplot(gs[1, 1])
    ax_az.plot(azimuth_axis_m[zoom_az], az_slice_db[zoom_az], "g.-", linewidth=1.5)
    ax_az.axhline(-3.0, color="r", linestyle="--", label="-3 dB Level")
    ax_az.set_title("Azimuth Impulse Response Slice (Zoomed)")
    ax_az.set_xlabel("Azimuth Offset (m)")
    ax_az.set_ylabel("Normalized Power (dB)")
    ax_az.set_ylim([-45, 2])
    ax_az.grid(True, linestyle=":", alpha=0.6)
    ax_az.legend(loc="upper right")

    plt.tight_layout()
    fig4_path = output_dir / "04_focused_sar_image.png"
    plt.savefig(fig4_path, dpi=150)
    plt.close(fig4)

    print(f"[RDA Runner] All 4 diagnostic plots saved to: {output_dir.resolve()}")


def main() -> int:
    args = parse_arguments()
    output_dir = Path(args.output_dir)
    params = RDAParameters(window_type=args.window)

    print("================================================================================")
    print("           EdgeSAR: Range-Doppler Algorithm (RDA) Image Formation               ")
    print("================================================================================")
    print(f"Operational Parameters:")
    print(f" - Carrier Frequency (f0) : {params.f0 / 1e9:.2f} GHz (Wavelength lambda = {params.wavelength * 100:.2f} cm)")
    print(f" - Chirp Bandwidth (Br)   : {params.bandwidth / 1e6:.1f} MHz (Theoretical Delta_r = {params.range_resolution:.3f} m)")
    print(f" - Pulse Duration (Tp)    : {params.pulse_duration * 1e6:.1f} us (TBP = {params.bandwidth * params.pulse_duration:.1f})")
    print(f" - Sampling Rate (fs)     : {params.fs / 1e6:.1f} MHz")
    print(f" - Platform Velocity (v)  : {params.velocity:.1f} m/s")
    print(f" - Reference Slant (R0)   : {params.r0:.1f} m")
    print(f" - Azimuth Antenna (La)   : {params.antenna_length:.2f} m (Theoretical Delta_a = {params.azimuth_resolution:.3f} m)")
    print(f" - PRF                    : {params.prf:.1f} Hz")
    print(f" - Spectral Window        : {params.window_type}")
    print("--------------------------------------------------------------------------------")

    # Load or generate raw data
    if args.input.lower() == "synthetic":
        print(f"[1/5] Synthesizing physics-based raw SAR echo (SNR = {args.snr} dB)...")
        gen = SyntheticSARSpectrumGenerator(params=params, n_azimuth=512, n_range=1024)
        t0 = time.time()
        raw_data = gen.generate_raw_echo(snr_db=args.snr, seed=42)
        print(f"      Synthetic echo generated in {time.time() - t0:.2f} s | Shape: {raw_data.shape}")
    elif args.input.lower() == "real":
        print(f"[1/5] Loading simulated open SAR scene (K-distributed, Sentinel-1 style) (Source: {args.source})...")
        sample_path = export_sample_real_sar_dataset()
        raw_data = np.load(sample_path)
        print(f"      Loaded simulated open SAR scene from {sample_path} | Shape: {raw_data.shape}")
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found at {input_path}", file=sys.stderr)
            return 1
        print(f"[1/5] Loading raw SAR echo from {input_path}...")
        raw_data = np.load(input_path)
        print(f"      Loaded raw echo | Shape: {raw_data.shape}")

    # Process through RDA Pipeline
    pipeline = RDAPipeline(params=params)
    print("[2/5] Executing Range-Doppler Algorithm (RDA)...")
    t_start = time.time()

    # Step 1: Range compression
    t1 = time.time()
    s_rc = pipeline.range_compression(raw_data)
    dt_rc = time.time() - t1
    print(f"      [Step 1] Range Matched Filtering completed in {dt_rc * 1000:.2f} ms")

    # Step 2: Azimuth FFT
    t2 = time.time()
    s_rd = pipeline.azimuth_fft(s_rc)
    dt_rd = time.time() - t2
    print(f"      [Step 2] Azimuth FFT to Range-Doppler completed in {dt_rd * 1000:.2f} ms")

    # Step 3: RCMC
    t3 = time.time()
    s_rcmc, delta_r = pipeline.range_cell_migration_correction(s_rd)
    dt_rcmc = time.time() - t3
    print(f"      [Step 3] Range Cell Migration Correction completed in {dt_rcmc * 1000:.2f} ms")
    max_rcm_m = np.max(delta_r)
    rcm_bins = max_rcm_m / (params.c / (2.0 * params.fs))
    print(f"               Maximum RCM displacement: {max_rcm_m:.3f} m ({rcm_bins:.2f} range bins)")

    # Step 4: Azimuth Compression
    t4 = time.time()
    focused = pipeline.azimuth_compression(s_rcmc)
    dt_az = time.time() - t4
    print(f"      [Step 4] Azimuth Matched Filtering & Focusing completed in {dt_az * 1000:.2f} ms")

    total_time = time.time() - t_start
    print(f"      Total RDA processing time: {total_time:.3f} s ({raw_data.shape[0] * raw_data.shape[1] / total_time / 1e6:.2f} Mpoints/s)")

    mag = np.abs(focused)
    intensity_db = 20.0 * np.log10(np.clip(mag / np.max(mag), 1e-12, 1.0))

    results = {
        "raw_data": raw_data,
        "range_compressed": s_rc,
        "range_doppler": s_rd,
        "rcmc": s_rcmc,
        "delta_r_rcm": delta_r,
        "focused_image": focused,
        "magnitude": mag,
        "intensity_db": intensity_db,
    }

    # Resolution and PSLR measurement on center target
    print("[3/5] Performing Quantitative Point Target Verification...")
    n_az, n_rng = raw_data.shape
    range_spacing_m = params.c / (2.0 * params.fs)
    azimuth_spacing_m = params.velocity / params.prf

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

    print(f"      Range   3dB Resolution: {rng_res:.3f} m (Theoretical Delta_r: {params.range_resolution:.3f} m)")
    print(f"      Azimuth 3dB Resolution: {az_res:.3f} m (Theoretical Delta_a: {params.azimuth_resolution:.3f} m)")
    print(f"      Range   PSLR          : {rng_pslr:.2f} dB")
    print(f"      Azimuth PSLR          : {az_pslr:.2f} dB")

    # Isolated target PSLR measurement (guard zone prevents neighbor contamination)
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
    print(f"      [Isolated Target PSLR]  Range: {isolated['range_pslr_db']:.1f} dB  |  Azimuth: {isolated['azimuth_pslr_db']:.1f} dB")
    print(f"      Note: {isolated['measurement_note']}")

    # Image Quality / Focus Metrics (Entropy & Contrast)
    focus_metrics = compute_focus_metrics(focused)
    print(f"      Shannon Image Entropy : {focus_metrics['entropy']:.4f} nats")
    print(f"      Image Contrast (s/m)  : {focus_metrics['contrast']:.4f}")
    print(f"      Peak-to-Average (PAPR): {focus_metrics['papr_db']:.2f} dB")

    # Export metrics JSON
    metrics_summary = {
        "input": args.input,
        "source": "simulated_open (Sentinel-1-style K-distributed)" if args.input.lower() == "real" else "synthetic",
        "range_res_m": float(rng_res),
        "azimuth_res_m": float(az_res),
        "range_pslr_db": float(rng_pslr),
        "azimuth_pslr_db": float(az_pslr),
        "isolated_range_pslr_db": float(isolated["range_pslr_db"]),
        "isolated_azimuth_pslr_db": float(isolated["azimuth_pslr_db"]),
        "entropy": float(focus_metrics["entropy"]),
        "contrast": float(focus_metrics["contrast"]),
        "papr_db": float(focus_metrics["papr_db"]),
        "execution_time_s": float(total_time),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "metrics.json", "w", encoding="utf-8") as mf:
        json.dump(metrics_summary, mf, indent=2)

    # Save Diagnostic Plots
    print(f"[4/5] Generating diagnostic figures in {output_dir}...")
    plot_diagnostic_figures(results, params, output_dir)

    print("[5/5] Pipeline execution verified successfully!")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
