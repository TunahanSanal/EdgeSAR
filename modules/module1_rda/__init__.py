"""Module 1: Raw SAR Signal Processing via Range-Doppler Algorithm (RDA)."""

from .rda_pipeline import RDAPipeline, RDAParameters
from .synthetic_generator import SyntheticSARSpectrumGenerator, PointTarget

__all__ = ["RDAPipeline", "RDAParameters", "SyntheticSARSpectrumGenerator", "PointTarget"]
