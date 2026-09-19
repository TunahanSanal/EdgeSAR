"""
EdgeSAR - Module 1: Physics-Based Synthetic Raw SAR Echo Generator.

Generates analytical multi-point scatterer raw baseband radar returns from
electromagnetic propagation physics and sensor flight kinematics.
Serves as an authoritative, 100% offline verification generator when raw
airborne/satellite SAR data files are not present.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from .rda_pipeline import RDAParameters


@dataclass
class PointTarget:
    """Radar point scatterer calibration target.

    Attributes:
        range_offset: Displacement from scene center R_0 (m). Positive = farther slant range.
        azimuth_offset: Displacement along flight path y from scene center (m).
        rcs: Radar Cross Section (linear amplitude reflection coefficient).
        phase: Intrinsic target scattering phase (radians).
    """
    range_offset: float = 0.0
    azimuth_offset: float = 0.0
    rcs: float = 1.0
    phase: float = 0.0


class SyntheticSARSpectrumGenerator:
    """Physics-based raw SAR baseband echo simulator."""

    def __init__(
        self,
        params: Optional[RDAParameters] = None,
        n_azimuth: int = 512,
        n_range: int = 1024,
    ):
        self.params = params if params is not None else RDAParameters()
        self.n_az = n_azimuth
        self.n_rng = n_range

    def get_canonical_5point_constellation(self) -> List[PointTarget]:
        """Generate standard 5-point calibration constellation."""
        return [
            PointTarget(range_offset=0.0, azimuth_offset=0.0, rcs=1.0),
            PointTarget(range_offset=30.0, azimuth_offset=0.0, rcs=0.8),
            PointTarget(range_offset=-30.0, azimuth_offset=0.0, rcs=0.8),
            PointTarget(range_offset=0.0, azimuth_offset=30.0, rcs=0.7),
            PointTarget(range_offset=30.0, azimuth_offset=30.0, rcs=0.9),
        ]

    def generate_raw_echo(
        self,
        targets: Optional[List[PointTarget]] = None,
        snr_db: Optional[float] = 25.0,
        seed: Optional[int] = 42,
    ) -> np.ndarray:
        r"""Generate 2D raw baseband radar echo matrix s_{rx}(\tau, \eta).

        Args:
            targets: List of PointTarget instances. If None, uses canonical 5-point constellation.
            snr_db: Signal-to-noise ratio in decibels. If None, zero noise added.
            seed: Random seed for reproducible noise generation.

        Returns:
            Complex 2D array of shape (N_az, N_rng) representing baseband raw echoes.
        """
        if targets is None:
            targets = self.get_canonical_5point_constellation()

        if seed is not None:
            np.random.seed(seed)

        c = self.params.c
        wavelength = self.params.wavelength
        kr = self.params.chirp_rate
        tp = self.params.pulse_duration
        fs = self.params.fs
        v = self.params.velocity
        r0 = self.params.r0
        prf = self.params.prf
        la = self.params.antenna_length

        # 1. Slow-time vector \eta: centered at zero
        # Shape: (N_az,)
        eta = (np.arange(self.n_az) - self.n_az / 2.0) / prf
        y_plat = v * eta  # Platform azimuth position along track

        # 2. Fast-time sampling vector \tau: centered on closest approach delay 2*R_0/c
        # Shape: (N_rng,)
        tau_center = 2.0 * r0 / c
        tau = tau_center + (np.arange(self.n_rng) - self.n_rng / 2.0) / fs

        raw_echo = np.zeros((self.n_az, self.n_rng), dtype=np.complex128)

        # 3. Accumulate returns from each point scatterer
        for target in targets:
            r_tgt = r0 + target.range_offset
            y_tgt = target.azimuth_offset

            # Instantaneous slant range R(\eta) from platform to target
            # Shape: (N_az,)
            r_inst = np.sqrt(r_tgt ** 2 + (y_plat - y_tgt) ** 2)

            # Two-way propagation delay: t_d(\eta) = 2 * R(\eta) / c
            t_delay = 2.0 * r_inst / c  # Shape: (N_az,)

            # Two-way azimuth antenna radiation pattern w_a(\eta)
            # w_a \approx sinc^2( (L_a / \lambda) * \theta )
            theta_az = (y_plat - y_tgt) / r_inst
            # np.sinc in NumPy is sin(pi*x)/(pi*x)
            sinc_arg = (la / wavelength) * theta_az
            w_az = (np.sinc(sinc_arg)) ** 2

            # Azimuth phase modulation: \exp(-j * 4\pi / \lambda * R(\eta) + j * \phi_0)
            phase_az = - (4.0 * np.pi / wavelength) * r_inst + target.phase
            carrier_term = target.rcs * w_az * np.exp(1j * phase_az)  # Shape: (N_az,)

            # Vectorized range chirp computation:
            # delta_tau shape: (N_az, N_rng)
            delta_tau = tau[np.newaxis, :] - t_delay[:, np.newaxis]

            # Chirp pulse envelope: rect(delta_tau / T_p)
            in_pulse_mask = np.abs(delta_tau) <= (tp / 2.0)

            # Chirp phase: \exp(j * \pi * K_r * delta_tau^2)
            chirp_phase = np.pi * kr * (delta_tau ** 2)
            chirp_signal = np.exp(1j * chirp_phase)

            # Modulate carrier term along range
            target_echo = carrier_term[:, np.newaxis] * chirp_signal * in_pulse_mask
            raw_echo += target_echo

        # 4. Add complex Gaussian thermal noise if SNR is specified
        if snr_db is not None:
            sig_power = np.mean(np.abs(raw_echo) ** 2)
            if sig_power > 0:
                snr_linear = 10.0 ** (snr_db / 10.0)
                noise_power = sig_power / snr_linear
                noise_std = np.sqrt(noise_power / 2.0)
                noise = (
                    np.random.normal(0.0, noise_std, (self.n_az, self.n_rng))
                    + 1j * np.random.normal(0.0, noise_std, (self.n_az, self.n_rng))
                )
                raw_echo += noise

        return raw_echo
