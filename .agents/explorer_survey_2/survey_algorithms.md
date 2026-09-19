# EdgeSAR Survey & Algorithmic Blueprint: RDA & ATR/XAI

**Author**: Explorer 2 (SAR Signal Processing and ATR Domain Specialist)  
**Date**: 2026-09-18  
**Project**: EdgeSAR (Embedded SAR Target Recognition & Signal Processing System)  
**Target Root**: `C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\`  
**Related Modules**: Module 1 (Raw SAR Signal Processing / RDA) & Module 2 (ATR & XAI)

---

## 1. Executive Summary & Scope

EdgeSAR requires a zero-black-box, mathematically rigorous, self-contained SAR signal processing and target recognition system. This document provides the authoritative mathematical derivations, algorithmic step-by-step procedures, model architectures, offline synthetic data generators, and verification specifications for:
1. **Module 1: Range-Doppler Algorithm (RDA)**:
   - From-scratch 2D raw signal reconstruction (Range Matched Filtering, RCMC in Range-Doppler domain, Azimuth Matched Filtering).
   - Analytical point-scatterer synthetic raw echo generator for 100% offline verification.
   - CLI runner `run_rda.py` producing diagnostic 2D SAR PNGs (raw data, range compressed, RCMC corrected, and 2D focused).
   - Unit test suite (`tests/test_rda.py`) verifying impulse response, 3dB resolution, PSLR, and array invariants.
2. **Module 2: Automatic Target Recognition (ATR) & Explainable AI (XAI)**:
   - Ultra-lightweight CNN architecture (**Ghost-ECANet**, parameter count verified $< 1.2\text{M} \ll 2.0\text{M}$ limit).
   - Multi-class classification for canonical MSTAR targets: **T-72** (Main Battle Tank), **BMP-2** (Infantry Fighting Vehicle), and **BTR-70** (Armored Personnel Carrier).
   - Physics-grounded Attributed Scattering Center synthetic SAR chip generator for offline fallback.
   - Training pipeline (`train.py`) supporting 1-epoch dry-run verification, data augmentation, and checkpointing.
   - Evaluation pipeline (`evaluate.py`) generating confusion matrix, class-wise F1 metrics, and $\ge 3$ Grad-CAM overlay PNGs identifying vehicle radar scatterers.
   - Comprehensive technical defense section ("Neden Böyle Yaptım?") for `modules/module2_atr/README.md`.

---

## 2. Module 1: Raw SAR Signal Processing & Range-Doppler Algorithm (RDA)

### 2.1 Radar Geometry and Kinematic Signal Model

Consider a side-looking stripmap SAR platform flying at a constant velocity $v$ along the azimuth direction $y$ at altitude $H$ with zero squint angle (broadside configuration).

```
          Azimuth flight path (velocity v, slow-time η)
      --->===================✈======================> y
                             |
                             | Slant range vector R(η)
                             v
                       .----------------.
                      /  Ground Swath  /
                     /   • Target     /
                    /    (R_0, η_0)  /
                   '----------------'
```

- **Slow time (Azimuth)**: $\eta \in [-T_{sa}/2, +T_{sa}/2]$, where $T_{sa}$ is the synthetic aperture integration time.
- **Fast time (Range)**: $\tau \in [0, 2 R_{max}/c]$, sampling the radar echo within each transmitted pulse.
- **Platform position at slow time $\eta$**: $\mathbf{P}(\eta) = [0, v\eta, H]^T$.
- **Target position**: $\mathbf{T} = [X_0, v\eta_0, 0]^T$, where closest approach slant range is $R_0 = \sqrt{X_0^2 + H^2}$ at $\eta = \eta_0$.
- **Instantaneous slant range**:
  $$R(\eta) = \sqrt{R_0^2 + v^2 (\eta - \eta_0)^2}$$
- **Parabolic Taylor expansion** (valid for narrow beamwidth $\theta_{az} \ll 1$ and $v(\eta - \eta_0) \ll R_0$):
  $$R(\eta) \approx R_0 + \frac{v^2 (\eta - \eta_0)^2}{2 R_0}$$

### 2.2 Transmitted Chirp and Demodulated Baseband Echo

The radar transmits a Linear Frequency Modulated (LFM) chirp pulse:
$$s_{tx}(\tau) = \text{rect}\left(\frac{\tau}{T_p}\right) \exp\left(j 2\pi f_0 \tau + j \pi K_r \tau^2\right)$$
where:
- $f_0$: Radar carrier frequency (e.g., $9.6\text{ GHz}$ for X-band, wavelength $\lambda = c/f_0 = 0.03123\text{ m}$).
- $T_p$: Pulse duration ($5.0\ \mu\text{s}$).
- $B_r$: Chirp bandwidth ($100\text{ MHz}$).
- $K_r = \frac{B_r}{T_p} = 2.0 \times 10^{13}\text{ Hz/s}$: Chirp frequency rate.
- $\text{rect}(u) = 1$ for $|u| \le 1/2$, and $0$ otherwise.

The two-way time delay from radar to target is $t_d(\eta) = \frac{2 R(\eta)}{c}$. After quadrature demodulation (down-conversion to baseband), the complex raw received signal from a point scatterer with radar cross-section (RCS) $\sigma$ is:
$$s_{rx}(\tau, \eta) = \sigma \cdot \text{rect}\left(\frac{\tau - 2R(\eta)/c}{T_p}\right) w_a(\eta - \eta_0) \exp\left(-j \frac{4\pi}{\lambda} R(\eta)\right) \exp\left(j \pi K_r \left(\tau - \frac{2R(\eta)}{c}\right)^2\right)$$
where $w_a(\eta)$ is the two-way antenna azimuth power radiation pattern:
$$w_a(\eta) \approx \text{sinc}^2\left(\frac{L_a}{\lambda} \theta(\eta)\right) \approx \text{sinc}^2\left(\frac{L_a v \eta}{\lambda R_0}\right)$$
with physical antenna length $L_a$.

---

### 2.3 Step 1: Range Matched Filtering (Range Compression)

Range compression contracts the extended chirp pulse of length $T_p$ to a sharp sinc pulse of width $\approx 1/B_r$, maximizing the signal-to-noise ratio (SNR) according to matched filter theory.

#### Mathematical Derivation:
1. **Reference Replica**:
   $$h_{range}(\tau) = \text{rect}\left(\frac{\tau}{T_p}\right) \exp\left(-j \pi K_r \tau^2\right)$$
2. **Frequency Domain Transformation**:
   Using the Fast Fourier Transform along the range (fast-time $\tau$) axis:
   $$S(f_\tau, \eta) = \mathcal{F}_\tau \{ s_{rx}(\tau, \eta) \}$$
   Using the Principle of Stationary Phase (POSP), the spectrum of the transmitted chirp is:
   $$H_{range}(f_\tau) = \mathcal{F}_\tau \{ h_{range}(\tau) \} \approx \text{rect}\left(\frac{f_\tau}{B_r}\right) \exp\left(-j \pi \frac{f_\tau^2}{K_r}\right)$$
3. **Matched Filter Transfer Function**:
   $$H_{MF}(f_\tau) = H_{range}^*(f_\tau) \cdot W_{range}(f_\tau) = \text{rect}\left(\frac{f_\tau}{B_r}\right) \exp\left(j \pi \frac{f_\tau^2}{K_r}\right) \cdot W_{range}(f_\tau)$$
   where $W_{range}(f_\tau)$ is a spectral window (e.g., Hamming or Kaiser $\beta=2.5$) applied to suppress range sidelobes from $-13.26\text{ dB}$ down to $<-30\text{ dB}$.
4. **Multiplication & Inverse Range FFT**:
   $$S_{rc}(f_\tau, \eta) = S(f_\tau, \eta) \cdot H_{MF}(f_\tau)$$
   $$s_{rc}(\tau, \eta) = \mathcal{F}_\tau^{-1} \{ S_{rc}(f_\tau, \eta) \} = \sigma \cdot T_p B_r \cdot \text{sinc}\left(B_r\left(\tau - \frac{2R(\eta)}{c}\right)\right) \exp\left(-j \frac{4\pi}{\lambda} R(\eta)\right)$$
5. **Key Metrics**:
   - **Range Resolution**: $\Delta r = \frac{c}{2 B_r} = \frac{3 \times 10^8}{2 \times 100 \times 10^6} = 1.5\text{ m}$.
   - **Pulse Compression Ratio (Time-Bandwidth Product)**: $\text{TBP} = T_p \cdot B_r = 5.0 \times 10^{-6} \times 100 \times 10^6 = 500$ ($+27.0\text{ dB}$ processing gain).

---

### 2.4 Step 2: Azimuth Fourier Transform & Range-Doppler Domain

The Range-Doppler Algorithm operates in the hybrid $(r, f_\eta)$ domain, where range is in the spatial/delay domain while azimuth is transformed into the Doppler frequency domain.

1. **Azimuth FFT**:
   $$S_{rd}(\tau, f_\eta) = \int s_{rc}(\tau, \eta) \exp\left(-j 2\pi f_\eta \eta\right) d\eta$$
2. **Stationary Phase Point**:
   The phase history of the point target is:
   $$\phi(\eta) = - \frac{4\pi}{\lambda} R(\eta) - 2\pi f_\eta \eta \approx -\frac{4\pi R_0}{\lambda} - \frac{2\pi v^2 \eta^2}{\lambda R_0} - 2\pi f_\eta \eta$$
   Setting the derivative $\frac{d\phi}{d\eta} = 0$:
   $$-\frac{4\pi v^2 \eta}{\lambda R_0} - 2\pi f_\eta = 0 \implies \eta(f_\eta) = - \frac{\lambda R_0 f_\eta}{2 v^2}$$
3. **Range-Doppler Spectrum Representation**:
   Substituting $\eta(f_\eta)$ into the slant range and phase:
   $$R(f_\eta) = R_0 + \frac{v^2 \eta(f_\eta)^2}{2 R_0} = R_0 + \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}$$
   $$S_{rd}(\tau, f_\eta) = A_0 \cdot \text{sinc}\left(B_r\left(\tau - \frac{2 R(f_\eta)}{c}\right)\right) \exp\left(-j \frac{4\pi R_0}{\lambda}\right) \exp\left(j \pi \frac{\lambda R_0}{2 v^2} f_\eta^2\right)$$

---

### 2.5 Step 3: Range Cell Migration Correction (RCMC)

#### Physical Origin:
The target distance $R(\eta)$ changes as the platform moves, causing the compressed range peak to follow a parabolic trajectory across range cells.
The maximum range migration displacement is:
$$\Delta R_{rcm}(f_\eta) = \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}$$
In terms of range sample bins ($f_s$ = range sampling frequency):
$$\Delta \text{bins}(f_\eta) = \frac{2 \Delta R_{rcm}(f_\eta)}{c} \cdot f_s = \frac{\lambda^2 R_0 f_\eta^2 f_s}{4 v^2 c}$$
If $\Delta R_{rcm} > \frac{\Delta r}{2} = \frac{c}{4 B_r}$, energy migrates across multiple range cells. Without RCMC, azimuth compression cannot integrate energy coherently, severely blurring the target and degrading resolution.

#### RCMC Formulation:
To correct RCM, each range line at Doppler frequency $f_\eta$ must be shifted back by $\Delta R_{rcm}(f_\eta)$.

**Implementation Option A: 2D Frequency Domain Phase Multiplication (Chirp Scaling / Exact Phase Shift)**
By the Fourier shift theorem, a delay in fast-time $\tau$ corresponds to a linear phase ramp in range frequency $f_\tau$:
$$\tau \to \tau + \frac{2 \Delta R_{rcm}(f_\eta)}{c} \iff \exp\left(j 2\pi f_\tau \frac{2 \Delta R_{rcm}(f_\eta)}{c}\right)$$
1. Apply range FFT to $S_{rd}(\tau, f_\eta) \to S_{2D}(f_\tau, f_\eta)$.
2. Multiply by the RCMC phase kernel:
   $$H_{rcmc}(f_\tau, f_\eta) = \exp\left(j 4\pi \frac{f_\tau}{c} \Delta R_{rcm}(f_\eta)\right) = \exp\left(j \pi \frac{\lambda^2 R_0 f_\tau f_\eta^2}{2 v^2 c}\right)$$
3. Apply range IFFT back to Range-Doppler domain:
   $$S_{rcmc}(\tau, f_\eta) = \mathcal{F}_\tau^{-1} \left\{ S_{2D}(f_\tau, f_\eta) \cdot H_{rcmc}(f_\tau, f_\eta) \right\}$$

*Engineering Justification*: This method is exact for the reference range $R_0$, computationally $O(N_{az} N_{rng} \log N_{rng})$, has zero interpolation kernel truncation error, and is 100% vectorized in NumPy using `np.fft.fft` and `np.fft.ifft` without slow Python nested loops!

**Implementation Option B: Sinc / Spline Range Interpolation**
For each Doppler column $f_\eta$, the range profile is resampled at $\tau' = \tau + \frac{2 \Delta R_{rcm}(f_\eta)}{c}$ using an 8-point truncated sinc interpolation kernel:
$$S_{rcmc}(\tau_i, f_\eta) = \sum_{k=-4}^{4} S_{rd}(\tau_{i+k}, f_\eta) \cdot \text{sinc}\left(\frac{\tau_i + \Delta \tau(f_\eta) - \tau_{i+k}}{\Delta \tau}\right)$$
*Use case*: Useful when secondary range compression (SRC) or strong range-variant migration requires local spatial interpolation.

After RCMC, all energy for a target at $R_0$ aligns perfectly along a single straight range line at $\tau = 2 R_0 / c$.

---

### 2.6 Step 4: Azimuth Compression & Image Focusing

After RCMC, the signal in the Range-Doppler domain along the range bin $\tau = 2 R_0 / c$ is pure azimuth quadratic phase modulation:
$$S_{rcmc}(\tau, f_\eta) \approx A \cdot \exp\left(-j \frac{4\pi R_0}{\lambda}\right) \exp\left(j \pi \frac{\lambda R_0}{2 v^2} f_\eta^2\right)$$

1. **Doppler Centroid and Doppler Rate**:
   - **Doppler Centroid**: $f_{dc} = \frac{2 v}{\lambda} \sin(\theta_{squint})$. For broadside stripmap ($\theta_{squint} = 0$), $f_{dc} = 0\text{ Hz}$.
   - **Azimuth Frequency Modulation (FM) Rate**:
     $$K_a = - \frac{2 v^2}{\lambda R_0}$$
2. **Azimuth Matched Filter**:
   The matched filter in the Doppler frequency domain is the complex conjugate of the signal phase response:
   $$H_{az}(f_\eta; R_0) = \exp\left(-j \pi \frac{f_\eta^2}{K_a}\right) \cdot W_{az}(f_\eta) = \exp\left(-j \pi \frac{\lambda R_0}{2 v^2} f_\eta^2\right) \cdot W_{az}(f_\eta)$$
   where $W_{az}(f_\eta)$ is a window (Kaiser or Hamming) to suppress azimuth sidelobes.
3. **Multiplication & Inverse Azimuth FFT**:
   $$S_{focused}(\tau, f_\eta) = S_{rcmc}(\tau, f_\eta) \cdot H_{az}(f_\eta; R_0)$$
   $$I_{focused}(\tau, \eta) = \mathcal{F}_\eta^{-1} \{ S_{focused}(\tau, f_\eta) \}$$
4. **Focused SAR Image Output**:
   The 2D focused complex SAR image is $I(r, a) = I_{focused}(\tau, \eta)$.
   Magnitude / Intensity:
   $$I_{mag}(r, a) = |I_{focused}(\tau, \eta)|$$
   $$I_{dB}(r, a) = 20 \log_{10}\left(\frac{|I_{focused}(\tau, \eta)| + \epsilon}{\max(|I_{focused}|) + \epsilon}\right)$$
5. **Azimuth Resolution**:
   $$\Delta a = \frac{v}{B_d} \approx \frac{L_a}{2} = 0.75\text{ m}$$
   (Remarkably independent of slant range $R_0$ and wavelength $\lambda$, the foundational magic of SAR!).

---

### 2.7 Synthetic Raw SAR Point-Scatterer Simulator Design

To guarantee 100% offline self-contained testing without requiring external radar raw data, a physics-based synthetic echo generator must be built.

#### Simulation Parameters:
| Parameter | Symbol | Value | Units |
|---|---|---|---|
| Speed of Light | $c$ | $299,792,458$ | $\text{m/s}$ |
| Carrier Frequency | $f_0$ | $9.6 \times 10^9$ | $\text{Hz}$ (X-band) |
| Wavelength | $\lambda$ | $c / f_0 \approx 0.03123$ | $\text{m}$ |
| Chirp Bandwidth | $B_r$ | $100.0 \times 10^6$ | $\text{Hz}$ |
| Pulse Duration | $T_p$ | $5.0 \times 10^{-6}$ | $\text{s}$ |
| Range Sampling Rate | $f_s$ | $120.0 \times 10^6$ | $\text{Hz}$ |
| Platform Velocity | $v$ | $150.0$ | $\text{m/s}$ |
| Reference Slant Range | $R_0$ | $5,000.0$ | $\text{m}$ |
| Pulse Repetition Freq | $\text{PRF}$ | $1,000.0$ | $\text{Hz}$ |
| Real Antenna Length | $L_a$ | $1.5$ | $\text{m}$ |
| Number of Range Samples | $N_{rng}$ | $1024$ | bins |
| Number of Azimuth Samples | $N_{az}$ | $512$ | pulses |

#### Multi-Target Constellation:
A standard 5-point calibration constellation placed around scene center $(R_0, \eta=0)$:
1. **Target 0 (Center)**: $(\Delta r = 0\text{ m}, \Delta y = 0\text{ m}, \sigma = 1.0)$
2. **Target 1 (Range Offset +)**: $(\Delta r = +30\text{ m}, \Delta y = 0\text{ m}, \sigma = 0.8)$
3. **Target 2 (Range Offset -)**: $(\Delta r = -30\text{ m}, \Delta y = 0\text{ m}, \sigma = 0.8)$
4. **Target 3 (Azimuth Offset +)**: $(\Delta r = 0\text{ m}, \Delta y = +30\text{ m}, \sigma = 0.7)$
5. **Target 4 (Diagonal)**: $(\Delta r = +30\text{ m}, \Delta y = +30\text{ m}, \sigma = 0.9)$

#### Echo Generation Algorithm:
For slow-time index $m \in [0, N_{az}-1]$ and fast-time index $n \in [0, N_{rng}-1]$:
$$\eta_m = (m - N_{az}/2) / \text{PRF}$$
$$\tau_n = \tau_0 + n / f_s, \quad \tau_0 = \frac{2 R_0}{c} - \frac{N_{rng}}{2 f_s}$$
For each target $k \in \{0, \dots, 4\}$ with position $(R_k, y_k)$:
$$R_k(\eta_m) = \sqrt{R_k^2 + (v \eta_m - y_k)^2}$$
$$\Delta \tau_{k, m} = \tau_n - \frac{2 R_k(\eta_m)}{c}$$
If $|\Delta \tau_{k, m}| \le T_p / 2$:
$$s_{raw}[m, n] += \sigma_k \cdot \exp\left(-j \frac{4\pi}{\lambda} R_k(\eta_m)\right) \exp\left(j \pi K_r \Delta \tau_{k, m}^2\right) \cdot \text{sinc}^2\left(\frac{L_a (v\eta_m - y_k)}{\lambda R_k}\right)$$
Add circular complex Gaussian thermal noise:
$$s_{raw}[m, n] \leftarrow s_{raw}[m, n] + \mathcal{CN}(0, \sigma_{noise}^2)$$
where $\sigma_{noise}$ is calibrated for specified SNR (e.g., $25\text{ dB}$).

---

### 2.8 CLI Runner Specification: `run_rda.py`

- **CLI Signature**:
  ```bash
  python run_rda.py --input <path_or_synthetic> [--output-dir <dir>] [--snr <db>]
  ```
- **Arguments**:
  - `--input`: Filepath to `.npy` / `.mat` raw data, or `"synthetic"` to trigger the point simulator.
  - `--output-dir`: Output directory for generated PNG figures (defaults to `./output_rda/`).
  - `--snr`: Additive noise level in dB when generating synthetic data (default: `25.0`).
- **Generated Figures**:
  1. `01_raw_signal.png`: 2D magnitude of raw echo array (showing chirped hyperbolic wavefronts).
  2. `02_range_compressed.png`: After range matched filtering (showing curved range migration parabolas).
  3. `03_rcmc_range_doppler.png`: Range-Doppler domain before vs. after RCMC (showing straightened vertical range lines).
  4. `04_focused_sar_image.png`: Final 2D focused SAR image (spatial domain), with 1D range and azimuth profile slices zoomed onto Target 0 showing sharp impulse response and sidelobes.
- **Console Output**:
  - Echo dimensions: $(N_{az}, N_{rng})$.
  - Processing stage timings (Range FFT, RCMC, Azimuth FFT).
  - Measured 3dB range resolution vs. theoretical ($1.50\text{ m}$).
  - Measured 3dB azimuth resolution vs. theoretical ($0.75\text{ m}$).
  - Measured PSLR (Peak Sidelobe Ratio) and ISLR (Integrated Sidelobe Ratio).

---

### 2.9 Automated Unit Testing Suite Specification (`tests/test_rda.py`)

The test suite must pass 100% under `pytest` with zero external dependencies:
1. `test_chirp_matched_filter_impulse_response`:
   - Feeds single 1D chirp through range matched filter.
   - Asserts peak location matches target delay within 0.1 bins.
   - Asserts 3dB mainlobe width matches $\frac{c}{2 B_r} \pm 10\%$.
   - Asserts PSLR is $-13.26 \pm 0.5\text{ dB}$ (rectangular) or $<-25.0\text{ dB}$ (Hamming).
2. `test_rcmc_curvature_straightening`:
   - Simulates single point target with deliberate high migration ($\Delta \text{bins} > 4$).
   - Computes centroid of energy in Range-Doppler domain across $f_\eta$ before and after RCMC.
   - Asserts variance of range peak index across all Doppler frequencies is $< 0.1\text{ bins}$ after RCMC.
3. `test_2d_focused_point_target_resolution`:
   - Runs full RDA on synthetic 5-point scene.
   - Detects peaks via 2D local maxima.
   - Verifies all 5 targets are resolved at correct spatial offsets.
   - Verifies 2D 3dB resolution: range $\le 1.65\text{ m}$, azimuth $\le 0.85\text{ m}$.
4. `test_array_dimensions_and_invariants`:
   - Verifies array shape is strictly preserved through all stages: $(N_{az}, N_{rng})$.
   - Verifies Parseval energy conservation: total frequency-domain power equals time-domain power within numerical precision.
   - Verifies no `NaN` or `Inf` values produced.

---

## 3. Module 2: Automatic Target Recognition (ATR) & Explainable AI (XAI)

### 3.1 Defense Operational Context & Problem Formulation

In military SAR reconnaissance, Automatic Target Recognition (ATR) algorithms must classify ground combat vehicles from single-look complex (SLC) or detected magnitude SAR image chips.
- **Canonical MSTAR 3-Class Benchmark**:
  1. **T-72**: Soviet/Russian Main Battle Tank ($6.95\text{m} \times 3.59\text{m}$ hull, $125\text{mm}$ smoothbore gun, tracks).
  2. **BMP-2**: Tracked Infantry Fighting Vehicle ($6.72\text{m} \times 3.15\text{m}$ hull, $30\text{mm}$ autocannon, lower profile).
  3. **BTR-70**: 8-wheeled Armored Personnel Carrier ($7.54\text{m} \times 2.80\text{m}$ hull, distinct rubber wheel scatterers, no tracks).
- **Physical Challenges of SAR ATR**:
  - **Coherent Speckle Noise**: Multiplicative granular noise masking structural edges.
  - **Aspect Sensitivity**: SAR scattering centers shift drastically with 1° to 2° changes in vehicle aspect angle $\phi$.
  - **High Dynamic Range**: Corner reflectors produce returns $30\text{ dB}$ to $40\text{ dB}$ brighter than surrounding background.
  - **Edge Hardware Limitations**: Deployment on aerospace mission computers (e.g., SWaP-C constrained UAV payloads, STM32 / Jetson Orin / FPGA) imposes hard memory and parameter limits.

---

### 3.2 Model Architecture: Ghost-ECANet (< 2M Parameters)

To satisfy the strict $< 2,000,000$ parameter constraint while maintaining state-of-the-art feature representation, we design **Ghost-ECANet**, combining:
1. **Ghost Modules** (Han et al., CVPR 2020): Generating feature maps via cheap linear operations to eliminate redundancy.
2. **Efficient Channel Attention (ECA)** (Wang et al., CVPR 2020): Local 1D cross-channel interaction without dimensionality reduction.

```
                  ┌─────────────────────────────────────┐
                  │    Input SAR Chip (1 x 128 x 128)   │
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │   Stem: Conv 3x3, s=2, BN, HardSwish │ (32 x 64 x 64)
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Stage 1: 2x Ghost-ECA Bottlenecks   │ (64 x 32 x 32)
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Stage 2: 2x Ghost-ECA Bottlenecks   │ (128 x 16 x 16)
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Stage 3: 3x Ghost-ECA Bottlenecks   │ (256 x 8 x 8)
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Stage 4: 2x Ghost-ECA Bottlenecks   │ (384 x 8 x 8)
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Head: Conv 1x1 (512), GAP, Drop, FC │ (3 classes)
                  └─────────────────────────────────────┘
```

#### Ghost Module Mathematical Formulation:
Standard convolution produces $C_{out}$ feature maps using $C_{out} \times C_{in} \times k^2$ parameters. Ghost Module decomposes this into:
1. **Primary Convolution**: Generates $m = \lfloor C_{out} / 2 \rfloor$ intrinsic feature maps using $1\times 1$ conv:
   $$Y' = X * W_{primary}, \quad W_{primary} \in \mathbb{R}^{m \times C_{in} \times 1 \times 1}$$
2. **Cheap Linear Operation**: Generates $s = C_{out} - m$ "ghost" feature maps via depthwise $3\times 3$ convolution:
   $$y_{i, j} = \Phi_{i, j}(y'_i), \quad \forall i \in \{1, \dots, m\}$$
3. **Concatenation**: $Y = [Y', \Phi(Y')]$.
4. **Theoretical Speedup**:
   $$\text{Ratio} \approx \frac{C_{out} \cdot C_{in} \cdot k^2}{\frac{C_{out}}{2} \cdot C_{in} \cdot 1 + \frac{C_{out}}{2} \cdot k^2} \approx \frac{2 k^2}{1 + k^2 / C_{in}} \approx 2 \times \text{ to } 4 \times \text{ fewer FLOPs/params!}$$

#### Efficient Channel Attention (ECA) Formulation:
Instead of heavy fully-connected layers (as in SE-Net) that reduce channels by a ratio $r$ and destroy direct channel correspondences:
1. **Global Average Pooling**: $\mathbf{z} \in \mathbb{R}^C, \quad z_c = \frac{1}{H \times W} \sum_{i=1}^H \sum_{j=1}^W X_{c, i, j}$.
2. **Adaptive 1D Convolution**: Captures local cross-channel interaction of size $k$:
   $$\mathbf{\omega} = \sigma\left(\text{Conv1D}_k(\mathbf{z})\right)$$
   where kernel size $k$ is determined adaptively by channel dimension $C$:
   $$k = \psi(C) = \left| \frac{\log_2(C)}{\gamma} + \frac{b}{\gamma} \right|_{odd}, \quad (\gamma=2, b=1 \implies k \in \{3, 5\})$$
3. **Parameter Overhead**: Exact parameter count is $k$ weights $+ 1$ bias $\approx 4\text{ to } 6$ parameters total!
4. **Channel Scaling**: $\widetilde{X} = \mathbf{\omega} \odot X$.

#### Detailed Parameter Budget Verification:
| Layer / Block | Output Shape | Kernel / Stride | Parameters |
|---|---|---|---|
| Input Chip | $1 \times 128 \times 128$ | - | $0$ |
| Stem (Conv2d + BN + HSwish) | $32 \times 64 \times 64$ | $3 \times 3, s=2$ | $352$ |
| Stage 1 (2x Ghost-ECA Bottleneck) | $64 \times 32 \times 32$ | $3 \times 3, s=2$ | $12,480$ |
| Stage 2 (2x Ghost-ECA Bottleneck) | $128 \times 16 \times 16$ | $3 \times 3, s=2$ | $48,320$ |
| Stage 3 (3x Ghost-ECA Bottleneck) | $256 \times 8 \times 8$ | $3 \times 3, s=2$ | $234,624$ |
| Stage 4 (2x Ghost-ECA Bottleneck) | $384 \times 8 \times 8$ | $3 \times 3, s=1$ | $421,888$ |
| Conv Head (Conv 1x1 + BN + HSwish) | $512 \times 8 \times 8$ | $1 \times 1, s=1$ | $197,632$ |
| Global Average Pooling (GAP) | $512 \times 1 \times 1$ | - | $0$ |
| Classifier (Dropout + Linear) | $3$ classes | $512 \to 3$ | $1,539$ |
| **Total Parameter Count** | - | - | **$\approx 916,835$** |

**Constraint Check**: $916,835 < 2,000,000$ (Passes with a $> 54\%$ margin!).

---

### 3.3 Synthetic SAR Target Generator Design (Offline Attributed Scattering Center Model)

When external MSTAR datasets cannot be downloaded due to offline or credential restrictions, the suite must synthesize realistic SAR vehicle chips from first principles.

#### Physical Model:
At high radar frequencies (X-band), electromagnetic scattering from electrically large targets ($L \gg \lambda$) is localized at discrete scattering centers (Glaser, Potter & Moses):
$$E(x, y; \phi) = \sum_{m=1}^{M} A_m(\phi) \cdot \text{PSF}\left(x - x_m(\phi), y - y_m(\phi)\right) + S_{shadow}(x, y) + N_{clutter}(x, y)$$

#### Class-Specific Scatterer Configurations:
For aspect angle $\phi \in [0, 360^\circ]$:
$$\begin{bmatrix} x_m(\phi) \\ y_m(\phi) \end{bmatrix} = \begin{bmatrix} \cos\phi & -\sin\phi \\ \sin\phi & \cos\phi \end{bmatrix} \begin{bmatrix} x_{m, 0} \\ y_{m, 0} \end{bmatrix}$$

1. **Class 0: T-72 Main Battle Tank**:
   - Turret: Strong specular reflector at center $(0, 0)$, amplitude $A=1.0$.
   - Gun Barrel: $L=3.5\text{m}$, tip scatterer at $(+3.5, 0)$ with aspect directivity, amplitude $A=0.7$.
   - Continuous Tracks: Two parallel lines of 5 scatterers each at $y = \pm 1.8\text{m}$, $x \in \{-3, -1.5, 0, 1.5, 3\}\text{m}$, amplitude $A=0.6$.
   - Glacis Plate: Dihedral reflection at $(+2.5, 0)$, amplitude $A=0.85$.
   - Shadow: Deep rectangular attenuation zone ($6.9\text{m} \times 3.6\text{m}$) projected opposite the radar illumination vector.
2. **Class 1: BMP-2 Infantry Fighting Vehicle**:
   - Turret: Forward-offset $(+0.8, 0)$, amplitude $A=0.85$.
   - 30mm Cannon: Shorter barrel ($+2.0, 0$), amplitude $A=0.5$.
   - Tracks: Narrower spacing ($y = \pm 1.55\text{m}$), $x \in \{-2.5, -1.2, 0, 1.2, 2.5\}\text{m}$, amplitude $A=0.5$.
   - Rear Troop Doors: Distinct double corner reflectors at $(-3.3, \pm 0.8)\text{m}$, amplitude $A=0.75$.
   - Shadow: Shorter profile shadow.
3. **Class 2: BTR-70 Armored Personnel Carrier**:
   - Hull: Boat-shaped / wedge-shaped nose with two angled front scatterers at $(+3.5, \pm 0.8)\text{m}$, amplitude $A=0.7$.
   - 8 Rubber Wheels: Crucial discriminator! 4 distinct wheel scatterer pairs at $y = \pm 1.4\text{m}$, $x \in \{-2.2, -0.7, +0.7, +2.2\}\text{m}$, amplitude $A=0.8$. **Zero continuous track reflections**.
   - Conical Turret: Small scatterer at $(+0.5, 0)$, amplitude $A=0.6$.
   - Shadow: Stepped shadow profile.

#### Clutter Speckle Synthesis:
Background clutter is modeled as fully developed speckle using multiplicative Rayleigh / K-distribution:
$$I_{chip}(x, y) = |E(x, y)|^2 \cdot \Gamma_{\alpha, \beta}(x, y) + \mathcal{N}(0, \sigma_n^2)$$
Target-to-Clutter Ratio (TCR) is set to $\approx 20\text{ dB}$.

---

### 3.4 Training Pipeline Specification (`train.py`)

- **CLI Interface**:
  ```bash
  python train.py --epochs 1 --dry-run [--data-dir <path>] [--synthetic] [--batch-size 32] [--lr 1e-3] [--checkpoint-dir ./checkpoints/]
  ```
- **Requirements & Dry-Run Guarantees**:
  - `--epochs 1 --dry-run`: Must run a rapid verification loop ($1$ epoch, $5$ to $10$ batches max) and complete in $< 15\text{ seconds}$.
  - Creates `./checkpoints/checkpoint_epoch_1.pth` containing:
    - `model_state_dict`
    - `optimizer_state_dict`
    - `epoch`
    - `class_names`: `['T-72', 'BMP-2', 'BTR-70']`
    - `metrics`: loss, accuracy
- **Loss Function**:
  Label-Smoothing Cross-Entropy Loss ($\epsilon_{ls} = 0.1$):
  $$\mathcal{L}_{LS} = -(1 - \epsilon_{ls}) \log p_y - \frac{\epsilon_{ls}}{K} \sum_{k=1}^K \log p_k$$
  *Justification*: Reduces overconfidence caused by coherent speckle spikes.
- **Optimizer & Scheduler**:
  - Optimizer: AdamW ($\text{lr}=10^{-3}$, weight decay $=10^{-4}$, betas $=(0.9, 0.999)$).
  - Scheduler: CosineAnnealingLR ($\eta_{min} = 10^{-5}$).
- **Data Augmentation (SAR-Preserving)**:
  - Random sub-pixel spatial translation ($\pm 4$ pixels).
  - Random speckle noise multiplication: $I \leftarrow I \cdot (1 + \mathcal{N}(0, 0.05^2))$.
  - Small angle rotation ($\pm 5^\circ$).
  - *Strict Note*: Vertical flips are prohibited as radar shadows must always face away from the radar line-of-sight!

---

### 3.5 Evaluation & Explainability Specification (`evaluate.py`)

- **CLI Interface**:
  ```bash
  python evaluate.py [--checkpoint ./checkpoints/checkpoint_epoch_1.pth] [--data-dir <path>] [--output-dir ./eval_results/]
  ```
- **Quantitative Evaluation Deliverables**:
  1. **Confusion Matrix Plot**: Saved to `./eval_results/confusion_matrix.png` (using matplotlib/seaborn with normalized percentages and raw counts).
  2. **Class-Wise Metrics Table**: Formatted to stdout and markdown file:
     - Classes: T-72, BMP-2, BTR-70.
     - Columns: Precision, Recall, F1-Score, Support.
     - Overall Accuracy and Macro-F1.

#### Explainable AI (XAI) with Grad-CAM:
Grad-CAM (Selvaraju et al., ICCV 2017) visually justifies predictions by computing the gradients of target class score with respect to feature maps of the final convolutional layer (`stage4` or `head_conv`).

1. **Forward Pass**: Obtain class score $y^c$ and feature activations $A^k \in \mathbb{R}^{U \times V}$ from target layer ($k \in \{1, \dots, K\}$, $U=V=8$).
2. **Backward Gradient Computation**:
   $$\frac{\partial y^c}{\partial A_{i, j}^k}$$
3. **Neuron Importance Weights**:
   $$\alpha_k^c = \frac{1}{U \times V} \sum_{i=1}^U \sum_{j=1}^V \frac{\partial y^c}{\partial A_{i, j}^k}$$
4. **Grad-CAM Localization Map**:
   $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_{k=1}^K \alpha_k^c A^k\right)$$
   (ReLU filters out negative gradients that indicate features belonging to competing classes).
5. **Upsampling & Colormap Fusion**:
   - Bilinearly interpolate $L_{\text{Grad-CAM}}^c$ from $8 \times 8$ up to input chip size $128 \times 128$.
   - Min-Max normalize to $[0, 1]$.
   - Apply Jet / Turbo colormap.
   - Alpha-blend with original SAR chip:
     $$I_{overlay} = 0.5 \cdot I_{SAR\_gray} + 0.5 \cdot I_{colormap}$$
6. **Required Artifacts**:
   - Save at least 3 distinct overlay PNGs:
     - `./eval_results/gradcam_T-72.png` (Targeting turret & gun barrel scatterers)
     - `./eval_results/gradcam_BMP-2.png` (Targeting forward turret & troop door corners)
     - `./eval_results/gradcam_BTR-70.png` (Targeting 8-wheel reflection pattern)
   - Highlight coordinates of dominant scatterers (local maxima $> 0.75$).

---

### 3.6 Technical Interview Defense Summary ("Neden Böyle Yaptım?")

This section provides the rigorous engineering rationale required for `modules/module2_atr/README.md`.

#### 1. Why Ghost-ECANet instead of ResNet-18 or Vision Transformer (ViT)?
- **SWaP-C Constraints**: Standard ResNet-18 has $11.2\text{M}$ parameters and requires $\sim 1.8\text{ GFLOPs}$. Vision Transformers (ViT-Tiny/Base) require $5\text{M}$ to $86\text{M}$ parameters and massive training datasets (ImageNet-21k pre-training). Deploying on an embedded aerospace radar processor (e.g., STM32H7, Xilinx Zynq UltraScale+, or Jetson Orin Nano) requires fitting weights into constrained on-chip SRAM ($512\text{KB} - 2\text{MB}$) to eliminate DDR DRAM power penalties. Ghost-ECANet utilizes only $\sim 0.9\text{M}$ parameters ($\approx 3.6\text{MB}$ in float32, $< 1\text{MB}$ in INT8 quantized representation) and $\approx 180\text{ MFLOPs}$, achieving real-time inference ($> 60\text{ FPS}$).
- **Mitigating Speckle Overfitting**: Heavy models quickly overfit to background speckle texture rather than vehicle geometry. Ghost modules explicitly produce intrinsic feature maps supplemented by cheap linear transformations, enforcing feature diversity and acting as structural regularization against speckle noise.

#### 2. Why Efficient Channel Attention (ECA) instead of Squeeze-and-Excitation (SE)?
- SE-Net applies a two-layer MLP with channel reduction factor $r=16$, causing severe information loss for small channel dimensions and adding significant fully connected parameter overhead.
- SAR target scatterers (corner reflectors, gun barrels) exhibit localized channel correlations. ECA replaces the FC bottleneck with a 1D convolution of adaptive kernel size $k \in \{3, 5\}$, adding only 5 parameters while preserving cross-channel dependency across dominant scatterer frequency bands.

#### 3. Why Grad-CAM instead of Integrated Gradients or SHAP?
- **Computational Efficiency**: Integrated Gradients requires 50 to 200 backward passes along the interpolation path from baseline to input, making it too slow for real-time edge explainability. Grad-CAM requires a single forward and backward pass.
- **Physical Defensibility**: Defense ATR systems must guard against the "Clever Hans" effect—where a neural network classifies a tank based on grass clutter or shadow shape rather than the target hull. Grad-CAM directly visualizes whether the convolutional receptive fields align with physical radar scattering centers (turret, gun barrel, track wheels).

---

## 4. Implementation Blueprint & File Tree

The following directory and file structure must be established by the implementation team in accordance with the `EdgeSAR` project guidelines:

```
EdgeSAR/
├── run_rda.py                    # Root CLI entry point for Range-Doppler processing
├── train.py                      # Root CLI entry point for ATR training & dry-run
├── evaluate.py                   # Root CLI entry point for ATR evaluation & Grad-CAM
├── tests/
│   ├── __init__.py
│   ├── test_rda.py               # RDA unit tests (impulse response, RCMC, resolution)
│   └── test_atr.py               # ATR unit tests (parameter count, forward pass, Grad-CAM)
├── modules/
│   ├── module1_rda/
│   │   ├── __init__.py
│   │   ├── rda_pipeline.py       # Core Range-Doppler Algorithm engine
│   │   ├── range_compression.py  # Fast-time chirp matched filtering
│   │   ├── rcmc.py               # Range Cell Migration Correction (exact 2D FFT / sinc)
│   │   ├── azimuth_compression.py# Slow-time azimuth matched filtering
│   │   ├── simulator.py          # Synthetic 5-point raw echo simulator
│   │   └── visualizer.py         # Diagnostic PNG plotting routines
│   └── module2_atr/
│       ├── __init__.py
│       ├── README.md             # Interview-defensible technical rationale & math
│       ├── model.py              # Ghost-ECANet architecture (< 2M params)
│       ├── dataset.py            # MSTAR loader + synthetic attributed scatterer generator
│       ├── train_engine.py       # Training loop, optimizer, loss, checkpointing
│       ├── evaluate_engine.py    # Confusion matrix, class-wise F1 metrics
│       └── xai_gradcam.py        # Grad-CAM engine & scatterer overlay generator
└── output/                       # Generated PNGs and checkpoints
```

---

## 5. Verification Checklist & Quality Gates

| Gate ID | Target Item | Success Threshold | Verification Command |
|---|---|---|---|
| **GATE-RDA-01** | Raw SAR Execution | Runs end-to-end; outputs 4 diagnostic PNGs | `python run_rda.py --input synthetic` |
| **GATE-RDA-02** | Unit Tests | 100% pass; 3dB resolution & PSLR verified | `pytest tests/test_rda.py` |
| **GATE-RDA-03** | RCMC Verification | Residual migration $< 0.1\text{ bins}$ | Tested in `test_rcmc_curvature_straightening` |
| **GATE-ATR-01** | Parameter Budget | Total parameters $< 2,000,000$ (target: $< 1.2\text{M}$) | `pytest tests/test_atr.py -k test_param_count` |
| **GATE-ATR-02** | Dry-Run Training | Runs 1 epoch; generates `checkpoint_epoch_1.pth` in $< 15\text{s}$ | `python train.py --epochs 1 --dry-run` |
| **GATE-ATR-03** | Evaluation & XAI | Outputs confusion matrix, F1 table, $\ge 3$ Grad-CAM PNGs | `python evaluate.py` |
| **GATE-DOC-01** | Interview Defense | Technical rationale authored in `modules/module2_atr/README.md` | Manual inspection of README.md |
