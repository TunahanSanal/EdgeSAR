"""Module 2: Automatic Target Recognition (ATR) & Explainable AI (XAI)."""

from .model import GhostECANet, count_parameters
from .dataset import SARDataset, SyntheticSARTargetGenerator
from .gradcam import GradCAM

__all__ = [
    "GhostECANet",
    "count_parameters",
    "SARDataset",
    "SyntheticSARTargetGenerator",
    "GradCAM",
]
