r"""
EdgeSAR - Module 1: Range-Doppler Algorithm (RDA) Implementation from First Principles.

This module implements the complete 2D Synthetic Aperture Radar (SAR) Range-Doppler
Algorithm without any external or black-box SAR image reconstruction libraries.
All operations (Range Matched Filtering, Azimuth Fourier Transformation,
Range Cell Migration Correction [RCMC], and Azimuth Matched Filtering) are derived
analytically from the physics of electromagnetic wave propagation and airborne/satellite
SAR flight kinematics.

Mathematical Foundation:
------------------------
1. Geometry and Kinematic Phase History:
   A sensor moves along the azimuth direction (slow-time \eta) at velocity v and altitude H.
   The instantaneous slant range to a point scatterer at closest approach range R_0 is:
       R(\eta) = \sqrt{R_0^2 + v^2 (\eta - \eta_0)^2} \approx R_0 + \frac{v^2 (\eta - \eta_0)^2}{2 R_0}

2. Transmitted Chirp and Demodulated Baseband Echo:
   The transmitted Linear Frequency Modulated (LFM) pulse is:
       s_{tx}(\tau) = \text{rect}(\tau / T_p) \cdot \exp(j 2\pi f_0 \tau + j \pi K_r \tau^2)
   where K_r = B_r / T_p is the chirp frequency rate.
   Quadrature down-conversion yields the baseband signal:
       s_{rx}(\tau, \eta) = \sigma \cdot \text{rect}\left(\frac{\tau - 2R(\eta)/c}{T_p}\right)
                            \cdot w_a(\eta - \eta_0)
                            \cdot \exp\left(-j \frac{4\pi}{\lambda} R(\eta)\right)
                            \cdot \exp\left(j \pi K_r \left(\tau - \frac{2R(\eta)}{c}\right)^2\right)

3. Range Compression (Matched Filtering):
   In the range frequency domain (f_\tau):
       H_{MF}(f_\tau) = \mathcal{F}_\tau\{s_{tx}^* (-\tau)\} \approx \text{rect}(f_\tau / B_r) \cdot \exp(j \pi f_\tau^2 / K_r) \cdot W(f_\tau)
   Compressing in range contracts pulse width from T_p down to \approx 1 / B_r.

4. Azimuth FFT & Range-Doppler Domain:
   Transforming slow-time \eta to Doppler frequency f_\eta:
       S_{rd}(\tau, f_\eta) = \mathcal{F}_\eta \{ s_{rc}(\tau, \eta) \}
   By the Principle of Stationary Phase (POSP):
       \eta(f_\eta) = - \frac{\lambda R_0 f_\eta}{2 v^2}
       R(f_\eta) = R_0 + \Delta R_{rcm}(f_\eta) = R_0 + \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}

5. Range Cell Migration Correction (RCMC):
   Range migration displacement:
       \Delta R_{rcm}(f_\eta) = \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}
   In the 2D frequency domain (f_\tau, f_\eta), spatial shift \Delta R corresponds to phase multiplication:
       H_{rcmc}(f_\tau, f_\eta) = \exp\left( j 4\pi \frac{f_\tau}{c} \Delta R_{rcm}(f_\eta) \right)
                                = \exp\left( j \pi \frac{\lambda^2 R_0 f_\tau f_\eta^2}{2 v^2 c} \right)

6. Azimuth Compression:
   Doppler FM rate: K_a = - \frac{2 v^2}{\lambda R_0}.
   Azimuth matched filter in Doppler domain:
       H_{az}(f_\eta; R_0) = \exp\left( -j \pi \frac{f_\eta^2}{K_a} \right) \cdot W_{az}(f_\eta)
                            = \exp\left( -j \pi \frac{\lambda R_0}{2 v^2} f_\eta^2 \right) \cdot W_{az}(f_\eta)
   Inverse Azimuth FFT yields the final focused complex image I(r, a).
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import numpy as np


@dataclass
class RDAParameters:
    """Radar and platform operational parameters for Range-Doppler Algorithm.

    Attributes:
        c: Speed of light in vacuum (m/s).
        f0: Radar carrier frequency (Hz).
        bandwidth: Transmitted chirp pulse bandwidth (Hz).
        pulse_duration: Transmitted chirp pulse length (s).
        fs: Range fast-time sampling frequency (Hz).
        velocity: Platform velocity along azimuth track (m/s).
        r0: Reference slant range at closest approach (m).
        prf: Pulse Repetition Frequency (Hz).
        antenna_length: Real physical antenna aperture size along azimuth (m).
        window_type: Spectral weighting window ('boxcar', 'hamming', 'kaiser', 'hann').
        kaiser_beta: Shape parameter beta if window_type == 'kaiser'.
    """
    c: float = 299792458.0
    f0: float = 9.6e9  # X-band (9.6 GHz)
    bandwidth: float = 100.0e6  # 100 MHz
    pulse_duration: float = 5.0e-6  # 5 microseconds
    fs: float = 120.0e6  # 120 MHz (oversampled relative to Br)
    velocity: float = 150.0  # 150 m/s
    r0: float = 5000.0  # 5000 m
    prf: float = 1000.0  # 1 kHz PRF
    antenna_length: float = 1.5  # 1.5 m
    window_type: str = "hamming"
    kaiser_beta: float = 2.5

    @property
    def wavelength(self) -> float:
        r"""Radar wavelength \lambda = c / f_0 (m)."""
        return self.c / self.f0

    @property
    def chirp_rate(self) -> float:
        """Chirp frequency modulation rate K_r = B_r / T_p (Hz/s)."""
        return self.bandwidth / self.pulse_duration

    @property
    def range_resolution(self) -> float:
        r"""Theoretical slant range resolution \Delta r = c / (2 * B_r) (m)."""
        return self.c / (2.0 * self.bandwidth)

    @property
    def azimuth_resolution(self) -> float:
        r"""Theoretical azimuth resolution \Delta a \approx L_a / 2 (m)."""
        return self.antenna_length / 2.0

    @property
    def doppler_rate(self) -> float:
        r"""Azimuth Doppler FM rate K_a = - 2 * v^2 / (\lambda * R_0) (Hz/s)."""
        return - (2.0 * (self.velocity ** 2)) / (self.wavelength * self.r0)


class RDAPipeline:
    """Complete Range-Doppler Algorithm reconstruction engine."""

    def __init__(self, params: Optional[RDAParameters] = None):
        self.params = params if params is not None else RDAParameters()

    def _compute_frequency_window(
        self, freq: np.ndarray, bandwidth: float, window_type: str
    ) -> np.ndarray:
        """Compute centered, symmetric spectral window for frequency coordinates |f| <= B/2."""
        w_type = window_type.lower()
        norm_f = freq / (bandwidth / 2.0)  # Normalized frequency in [-1, +1]
        valid_mask = np.abs(norm_f) <= 1.0
        window = np.zeros_like(freq, dtype=np.float64)

        if w_type in ["boxcar", "rectangular", "rect"]:
            window[valid_mask] = 1.0
        elif w_type == "hamming":
            # Hamming: 0.54 + 0.46 * cos(pi * norm_f)
            window[valid_mask] = 0.54 + 0.46 * np.cos(np.pi * norm_f[valid_mask])
        elif w_type == "hann":
            # Hann: 0.50 + 0.50 * cos(pi * norm_f)
            window[valid_mask] = 0.50 + 0.50 * np.cos(np.pi * norm_f[valid_mask])
        elif w_type == "kaiser":
            # Kaiser-Bessel window
            beta = self.params.kaiser_beta
            try:
                from scipy.special import i0
                i0_denom = i0(beta)
                radicand = np.maximum(0.0, 1.0 - (norm_f[valid_mask] ** 2))
                window[valid_mask] = i0(beta * np.sqrt(radicand)) / i0_denom
            except ImportError:
                window[valid_mask] = 0.54 + 0.46 * np.cos(np.pi * norm_f[valid_mask])
        else:
            window[valid_mask] = 1.0

        return window

    def range_compression(self, raw_data: np.ndarray) -> np.ndarray:
        """Step 1: Range Matched Filtering (Pulse Compression).

        Applies frequency-domain matched filtering along each range line (fast time axis, axis=1).

        Args:
            raw_data: 2D complex array of shape (N_az, N_rng) representing baseband echoes.

        Returns:
            Range-compressed 2D complex array of shape (N_az, N_rng).
        """
        n_az, n_rng = raw_data.shape
        fs = self.params.fs
        kr = self.params.chirp_rate
        tp = self.params.pulse_duration
        br = self.params.bandwidth

        # Fast-time frequency axis f_\tau in [-fs/2, fs/2)
        f_tau = np.fft.fftfreq(n_rng, d=1.0 / fs)

        # Matched filter transfer function in range frequency domain:
        # Using the Principle of Stationary Phase (POSP):
        # Spectrum of transmitted chirp: S(f_\tau) = rect(f_\tau / B_r) * exp(-j * \pi * f_\tau^2 / K_r)
        # Matched filter H_{MF}(f_\tau) = S^*(f_\tau) = rect(f_\tau / B_r) * exp(+j * \pi * f_\tau^2 / K_r)
        h_range_mf = np.zeros(n_rng, dtype=np.complex128)
        band_mask = np.abs(f_tau) <= (br / 2.0)

        # Apply continuous spectral window within the chirp bandwidth
        window = self._compute_frequency_window(f_tau, br, self.params.window_type)

        # Phase term: exp(+j * \pi * f_\tau^2 / K_r)
        phase_mf = np.pi * (f_tau ** 2) / kr
        h_range_mf[band_mask] = window[band_mask] * np.exp(1j * phase_mf[band_mask])

        # Execute matched filtering via FFT along range axis (axis=1)
        raw_fft_range = np.fft.fft(raw_data, axis=1)
        compressed_fft = raw_fft_range * h_range_mf[np.newaxis, :]
        range_compressed = np.fft.ifft(compressed_fft, axis=1)

        return range_compressed

    def azimuth_fft(self, range_compressed: np.ndarray) -> np.ndarray:
        r"""Step 2: Azimuth Fourier Transform to Range-Doppler domain.

        Transforms slow-time \eta (axis=0) to Doppler frequency f_\eta.

        Args:
            range_compressed: 2D complex array of shape (N_az, N_rng).

        Returns:
            Range-Doppler domain 2D complex array of shape (N_az, N_rng).
        """
        # We use standard FFT along azimuth (axis=0).
        # We apply fftshift along azimuth so Doppler frequency is centered at f_\eta = 0.
        s_rd = np.fft.fftshift(np.fft.fft(range_compressed, axis=0), axes=0)
        return s_rd

    def range_cell_migration_correction(
        self, s_rd: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        r"""Step 3: Range Cell Migration Correction (RCMC) in Range-Doppler domain.

        Corrects the parabolic range migration \Delta R_{rcm}(f_\eta) = \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}.
        Implemented using exact 2D frequency-domain phase multiplication (Chirp Scaling / Phase Shift):
            H_{rcmc}(f_\tau, f_\eta) = \exp\left(j 4\pi \frac{f_\tau}{c} \Delta R_{rcm}(f_\eta)\right)
                                     = \exp\left(j \pi \frac{\lambda^2 R_0 f_\tau f_\eta^2}{2 v^2 c}\right)

        Args:
            s_rd: Range-Doppler domain 2D complex array (shifted along azimuth axis 0).

        Returns:
            Tuple of:
                s_rcmc: RCMC-corrected Range-Doppler array of shape (N_az, N_rng).
                delta_r_rcm: 1D array of range migration displacements for each Doppler bin.
        """
        n_az, n_rng = s_rd.shape
        fs = self.params.fs
        c = self.params.c
        wavelength = self.params.wavelength
        r0 = self.params.r0
        v = self.params.velocity
        prf = self.params.prf

        # Doppler frequency vector centered at 0: f_\eta \in [-PRF/2, PRF/2)
        f_eta = np.linspace(-prf / 2.0, prf / 2.0, n_az, endpoint=False)

        # Range migration displacement in meters:
        # \Delta R_{rcm}(f_\eta) = \frac{\lambda^2 R_0 f_\eta^2}{8 v^2}
        delta_r_rcm = (wavelength ** 2 * r0 * (f_eta ** 2)) / (8.0 * (v ** 2))

        # Range frequency grid f_\tau (uncentered standard FFT frequencies for axis=1)
        f_tau = np.fft.fftfreq(n_rng, d=1.0 / fs)

        # 2D phase multiplication kernel:
        # H_{rcmc}(f_\tau, f_\eta) = \exp(j 4\pi (f_\tau / c) \Delta R_{rcm}(f_\eta))
        # Shape: (N_az, N_rng) via outer product broadcasting
        phase_kernel = (4.0 * np.pi / c) * np.outer(delta_r_rcm, f_tau)
        h_rcmc_2d = np.exp(1j * phase_kernel)

        # Transform range from time delay \tau to range frequency f_\tau
        s_2d = np.fft.fft(s_rd, axis=1)

        # Multiply by phase kernel and IFFT back to fast-time
        s_rcmc_2d = s_2d * h_rcmc_2d
        s_rcmc = np.fft.ifft(s_rcmc_2d, axis=1)

        return s_rcmc, delta_r_rcm

    def azimuth_compression(self, s_rcmc: np.ndarray) -> np.ndarray:
        """Step 4: Azimuth Matched Filtering and 2D Image Focusing.

        Applies Doppler matched filter along Doppler frequency axis and performs
        inverse azimuth FFT to reconstruct the 2D spatial SAR image.

        Args:
            s_rcmc: RCMC-corrected Range-Doppler array (centered along azimuth axis 0).

        Returns:
            2D complex focused SAR image of shape (N_az, N_rng).
        """
        n_az, n_rng = s_rcmc.shape
        wavelength = self.params.wavelength
        r0 = self.params.r0
        v = self.params.velocity
        prf = self.params.prf

        # Doppler frequency vector centered at 0: f_\eta \in [-PRF/2, PRF/2)
        f_eta = np.linspace(-prf / 2.0, prf / 2.0, n_az, endpoint=False)

        # Doppler bandwidth B_d \approx 2 * v / L_a
        doppler_bw = 2.0 * v / self.params.antenna_length

        # Azimuth matched filter transfer function:
        # H_{az}(f_\eta; R_0) = \exp\left( -j \pi \frac{\lambda R_0}{2 v^2} f_\eta^2 \right) * W_{az}(f_\eta)
        az_phase = - (np.pi * wavelength * r0 / (2.0 * (v ** 2))) * (f_eta ** 2)

        # Azimuth windowing to suppress Doppler sidelobes
        az_window = self._compute_frequency_window(f_eta, doppler_bw, self.params.window_type)
        h_az = az_window * np.exp(1j * az_phase)

        # Multiply along azimuth Doppler columns
        s_focused_doppler = s_rcmc * h_az[:, np.newaxis]

        # Shift back from center and perform inverse azimuth FFT to slow-time spatial coordinates
        s_unshifted = np.fft.ifftshift(s_focused_doppler, axes=0)
        focused_image = np.fft.ifft(s_unshifted, axis=0)

        return focused_image

    def process(self, raw_data: np.ndarray) -> Dict[str, Any]:
        """Execute the complete 4-step Range-Doppler Algorithm pipeline.

        Args:
            raw_data: 2D complex NumPy array of raw SAR signal, shape (N_az, N_rng).

        Returns:
            Dictionary containing intermediate and final processing arrays:
                - 'raw_data': Input echo array
                - 'range_compressed': After range matched filtering
                - 'range_doppler': In Range-Doppler domain before RCMC
                - 'rcmc': In Range-Doppler domain after RCMC
                - 'delta_r_rcm': Range migration displacement curve
                - 'focused_image': Final 2D complex focused SAR image
                - 'magnitude': Absolute amplitude |I|
                - 'intensity_db': Logarithmic intensity in dB normalized to 0 dB peak
        """
        # Step 1: Range compression
        s_rc = self.range_compression(raw_data)

        # Step 2: Azimuth FFT to Range-Doppler domain
        s_rd = self.azimuth_fft(s_rc)

        # Step 3: Range Cell Migration Correction
        s_rcmc, delta_r = self.range_cell_migration_correction(s_rd)

        # Step 4: Azimuth matched filtering & focusing
        focused = self.azimuth_compression(s_rcmc)

        # Magnitude and logarithmic intensity in dB
        mag = np.abs(focused)
        peak = np.max(mag) if np.max(mag) > 0 else 1.0
        eps = 1e-12
        intensity_db = 20.0 * np.log10(np.clip(mag / peak, eps, 1.0))

        return {
            "raw_data": raw_data,
            "range_compressed": s_rc,
            "range_doppler": s_rd,
            "rcmc": s_rcmc,
            "delta_r_rcm": delta_r,
            "focused_image": focused,
            "magnitude": mag,
            "intensity_db": intensity_db,
        }
