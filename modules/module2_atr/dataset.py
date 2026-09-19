r"""
EdgeSAR - Module 2: SAR Vehicle Dataset & Synthetic Attributed Scattering Center Generator.

Generates realistic single-channel SAR chips (1 x 128 x 128) simulating canonical MSTAR targets:
1. T-72: Main Battle Tank (continuous tracks, central turret, long 125mm gun barrel)
2. BMP-2: Infantry Fighting Vehicle (tracked, forward turret, rear troop door reflectors)
3. BTR-70: Armored Personnel Carrier (8 rubber wheels, wedge nose, conical turret)

Integrates radar scattering physics:
- Aspect angle sensitivity \phi \in [0, 360^\circ]
- Attributed scattering centers with 2D Gaussian Point Spread Function (PSF)
- Coherent speckle noise (Rayleigh / multiplicative gamma)
- Radar shadow depression zone cast opposite radar illumination
"""

import math
from typing import Optional, Tuple, List, Dict
import numpy as np
import torch
from torch.utils.data import Dataset


CLASS_NAMES: List[str] = ["T-72", "BMP-2", "BTR-70"]


class SyntheticSARTargetGenerator:
    """Physics-based Attributed Scattering Center generator for canonical SAR targets."""

    def __init__(self, chip_size: int = 128, pixel_spacing_m: float = 0.15):
        self.chip_size = chip_size
        self.pixel_spacing_m = pixel_spacing_m
        self.scene_span_m = chip_size * pixel_spacing_m  # 19.2 m

    def _get_target_scatterers(self, class_id: int) -> List[Tuple[float, float, float]]:
        """Return canonical (x_m, y_m, amplitude) coordinates in vehicle frame (meters)."""
        if class_id == 0:
            # T-72 Main Battle Tank
            scatterers = [
                # Central heavy turret
                (0.0, 0.0, 1.0),
                (0.4, 0.3, 0.7),
                (0.4, -0.3, 0.7),
                # 125mm Gun Barrel
                (1.5, 0.0, 0.6),
                (2.5, 0.0, 0.65),
                (3.5, 0.0, 0.75),  # Muzzle brake
                # Glacis front plate
                (2.8, 0.5, 0.8),
                (2.8, -0.5, 0.8),
                # Continuous left track (5 road wheels)
                (-2.8, 1.7, 0.6),
                (-1.4, 1.7, 0.6),
                (0.0, 1.7, 0.65),
                (1.4, 1.7, 0.6),
                (2.8, 1.7, 0.6),
                # Continuous right track (5 road wheels)
                (-2.8, -1.7, 0.6),
                (-1.4, -1.7, 0.6),
                (0.0, -1.7, 0.65),
                (1.4, -1.7, 0.6),
                (2.8, -1.7, 0.6),
                # Rear engine deck
                (-3.0, 0.0, 0.7),
                (-2.8, 0.8, 0.5),
                (-2.8, -0.8, 0.5),
            ]
        elif class_id == 1:
            # BMP-2 Infantry Fighting Vehicle
            scatterers = [
                # Forward-offset turret
                (0.8, 0.0, 0.85),
                (1.1, 0.25, 0.6),
                # 30mm Autocannon
                (1.8, 0.0, 0.55),
                (2.4, 0.0, 0.5),
                # Sloped glacis front
                (2.6, 0.4, 0.75),
                (2.6, -0.4, 0.75),
                # Narrower tracks
                (-2.2, 1.5, 0.5),
                (-1.1, 1.5, 0.55),
                (0.0, 1.5, 0.55),
                (1.1, 1.5, 0.5),
                (2.2, 1.5, 0.5),
                (-2.2, -1.5, 0.5),
                (-1.1, -1.5, 0.55),
                (0.0, -1.5, 0.55),
                (1.1, -1.5, 0.5),
                (2.2, -1.5, 0.5),
                # Rear troop double doors (distinct dihedral corner reflectors)
                (-3.2, 0.7, 0.8),
                (-3.2, -0.7, 0.8),
            ]
        else:
            # BTR-70 8-Wheeled Armored Personnel Carrier
            scatterers = [
                # Boat-shaped pointed front wedge
                (3.4, 0.5, 0.7),
                (3.4, -0.5, 0.7),
                (2.2, 0.0, 0.65),
                # Small conical turret
                (0.5, 0.0, 0.6),
                # 4 distinct wheel pairs (8 rubber tires - NO continuous tracks!)
                (-2.2, 1.4, 0.8),
                (-0.7, 1.4, 0.8),
                (0.8, 1.4, 0.8),
                (2.3, 1.4, 0.8),
                (-2.2, -1.4, 0.8),
                (-0.7, -1.4, 0.8),
                (0.8, -1.4, 0.8),
                (2.3, -1.4, 0.8),
                # Rear hull exhaust
                (-3.4, 0.0, 0.55),
            ]
        return scatterers

    def generate_chip(
        self,
        class_id: int,
        aspect_deg: float = 45.0,
        noise_level: float = 0.08,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """Generate a synthetic 128x128 SAR chip for the specified target class.

        Args:
            class_id: 0 (T-72), 1 (BMP-2), or 2 (BTR-70).
            aspect_deg: Vehicle aspect angle in degrees [0, 360).
            noise_level: Multiplicative speckle and clutter standard deviation.
            seed: Random seed for reproducible generation.

        Returns:
            Normalized 2D float32 array of shape (128, 128) with values in [0, 1].
        """
        if seed is not None:
            np.random.seed(seed)

        chip = np.zeros((self.chip_size, self.chip_size), dtype=np.float32)
        center_pix = self.chip_size / 2.0
        theta = math.radians(aspect_deg)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # 1. Background Clutter (Rayleigh distributed speckle)
        # Radar clutter has exponential/Rayleigh intensity distribution
        clutter = np.random.rayleigh(scale=0.08, size=(self.chip_size, self.chip_size)).astype(np.float32)
        chip += clutter

        # 2. Scatterer 2D Point Spread Function (PSF) accumulation
        # 3dB resolution width \approx 1.5 m -> sigma \approx 0.64 m = ~4.2 pixels
        psf_sigma = 3.2
        two_sigma_sq = 2.0 * (psf_sigma ** 2)

        scatterers = self._get_target_scatterers(class_id)
        y_grid, x_grid = np.ogrid[:self.chip_size, :self.chip_size]

        for x_m, y_m, amp in scatterers:
            # Rotate target coordinates by aspect angle \phi
            rx_m = x_m * cos_t - y_m * sin_t
            ry_m = x_m * sin_t + y_m * cos_t

            # Convert meters to pixel coordinates relative to center
            px = center_pix + (rx_m / self.pixel_spacing_m)
            py = center_pix + (ry_m / self.pixel_spacing_m)

            # Accumulate Gaussian PSF
            dist_sq = (x_grid - px) ** 2 + (y_grid - py) ** 2
            # Bounded cutoff at 3 * sigma
            mask = dist_sq <= ((3.0 * psf_sigma) ** 2)
            chip[mask] += amp * np.exp(-dist_sq[mask] / two_sigma_sq).astype(np.float32)

        # 3. Radar Shadow (cast opposite illumination direction: assume radar from top/left)
        # Radar shadow creates a low-intensity depression region behind target
        shadow_dist_m = 4.0
        sx_m = -shadow_dist_m * 0.5
        sy_m = -shadow_dist_m * 0.5
        spx = center_pix + (sx_m / self.pixel_spacing_m)
        spy = center_pix + (sy_m / self.pixel_spacing_m)

        shadow_mask = (
            (np.abs(x_grid - spx) <= (4.5 / self.pixel_spacing_m)) &
            (np.abs(y_grid - spy) <= (3.5 / self.pixel_spacing_m)) &
            (chip < 0.25)
        )
        chip[shadow_mask] *= 0.15

        # 4. Multiplicative coherent speckle noise
        speckle = np.random.normal(1.0, noise_level, chip.shape).astype(np.float32)
        chip = np.clip(chip * speckle, 0.0, None)

        # 5. Normalization to [0.0, 1.0]
        max_val = np.max(chip)
        if max_val > 0:
            chip = chip / max_val

        return chip.astype(np.float32)


class SARDataset(Dataset):
    """PyTorch Dataset for SAR vehicle classification with data augmentation."""

    def __init__(
        self,
        num_samples_per_class: int = 100,
        augment: bool = True,
        seed: int = 42,
    ):
        self.num_samples_per_class = num_samples_per_class
        self.augment = augment
        self.generator = SyntheticSARTargetGenerator(chip_size=128, pixel_spacing_m=0.15)
        self.total_samples = num_samples_per_class * len(CLASS_NAMES)
        self.seed = seed

    def __len__(self) -> int:
        return self.total_samples

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        class_id = idx % len(CLASS_NAMES)
        sample_idx = idx // len(CLASS_NAMES)

        # Diverse aspect angles uniformly spanning [0, 360)
        base_aspect = (sample_idx * 360.0 / self.num_samples_per_class) % 360.0

        if self.augment:
            aspect_jitter = np.random.uniform(-15.0, 15.0)
            aspect_deg = (base_aspect + aspect_jitter) % 360.0
            noise_level = np.random.uniform(0.04, 0.14)
        else:
            aspect_deg = base_aspect
            noise_level = 0.08

        item_seed = None if self.augment else (self.seed + idx)
        chip = self.generator.generate_chip(
            class_id=class_id,
            aspect_deg=aspect_deg,
            noise_level=noise_level,
            seed=item_seed,
        )

        if self.augment:
            # Sub-pixel translation: shift +/- 6 pixels
            shift_x = int(np.random.randint(-6, 7))
            shift_y = int(np.random.randint(-6, 7))
            chip = np.roll(chip, shift_x, axis=1)
            chip = np.roll(chip, shift_y, axis=0)

            # Horizontal flip (50% chance)
            if np.random.random() > 0.5:
                chip = np.flip(chip, axis=1).copy()

            # Random intensity scale (85% - 115%)
            scale = np.random.uniform(0.85, 1.15)
            chip = np.clip(chip * scale, 0.0, 1.0)

            # Additive noise perturbation
            chip += np.random.normal(0.0, 0.025, chip.shape).astype(np.float32)
            chip = np.clip(chip, 0.0, 1.0)

        # Convert to tensor: shape (1, 128, 128)
        tensor = torch.from_numpy(chip).unsqueeze(0).float()
        return tensor, class_id
