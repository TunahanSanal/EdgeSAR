"""
EdgeSAR - Module 2: Explainable AI (XAI) via Grad-CAM from First Principles.

Implements Gradient-weighted Class Activation Mapping (Grad-CAM) (Selvaraju et al., ICCV 2017)
to visually justify deep learning radar ATR decisions. Identifies dominant electromagnetic
scattering centers (gun barrels, turrets, road wheels, dihedral reflectors) responsible
for vehicle classification.
"""

from typing import Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class GradCAM:
    """Gradient-weighted Class Activation Mapping (Grad-CAM) Engine."""

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None
        self.hook_handles = []
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register forward and backward hooks on the target convolutional layer."""
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0]

        h1 = self.target_layer.register_forward_hook(forward_hook)
        h2 = self.target_layer.register_full_backward_hook(backward_hook)
        self.hook_handles.extend([h1, h2])

    def remove_hooks(self) -> None:
        """Remove all registered hooks."""
        for handle in self.hook_handles:
            handle.remove()
        self.hook_handles.clear()

    def generate_cam(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """Compute Grad-CAM heatmap for the given input tensor.

        Args:
            input_tensor: Tensor of shape (1, 1, H, W).
            target_class: Target class index. If None, uses model's predicted class.

        Returns:
            Tuple of:
                cam_heatmap: 2D float32 numpy array of shape (H, W) in [0, 1].
                predicted_class: Integer index of predicted class.
                confidence: Softmax probability for predicted class.
        """
        self.model.eval()
        self.activations = None
        self.gradients = None

        # Enable gradients even in eval mode
        with torch.enable_grad():
            input_var = input_tensor.clone().detach().requires_grad_(True)
            output = self.model(input_var)

            probs = F.softmax(output, dim=1)
            pred_class = int(torch.argmax(output, dim=1).item())
            confidence = float(probs[0, pred_class].item())

            if target_class is None:
                target_class = pred_class

            # Clear existing gradients
            self.model.zero_grad()
            # Target class logit
            score = output[0, target_class]
            score.backward(retain_graph=True)

            assert self.activations is not None, "Target layer forward activations not captured!"
            assert self.gradients is not None, "Target layer backward gradients not captured!"

            # 1. Neuron importance weights \alpha_k^c via Global Average Pooling of gradients:
            # \alpha_k^c = \frac{1}{Z} \sum_i \sum_j \frac{\partial y^c}{\partial A_{i,j}^k}
            weights = torch.mean(self.gradients, dim=[2, 3], keepdim=True)  # (1, C, 1, 1)

            # 2. Weighted combination of activation maps:
            cam = torch.sum(weights * self.activations, dim=1, keepdim=True)  # (1, 1, H_act, W_act)

            # 3. Apply ReLU: only positive contributions indicate target class evidence
            cam = F.relu(cam)

            # 4. Bilinear upsampling to match input resolution (H, W)
            cam = F.interpolate(
                cam,
                size=(input_tensor.shape[2], input_tensor.shape[3]),
                mode="bilinear",
                align_corners=False,
            )

            # 5. Normalize heatmap to [0, 1]
            cam = cam.squeeze().detach().cpu().numpy()
            max_val = np.max(cam)
            if max_val > 0:
                cam = cam / max_val
            else:
                cam = np.zeros_like(cam)

        return cam.astype(np.float32), pred_class, confidence

    @staticmethod
    def overlay_heatmap(
        image_np: np.ndarray,
        cam_np: np.ndarray,
        alpha: float = 0.5,
        colormap_name: str = "jet",
    ) -> np.ndarray:
        """Fuse grayscale SAR image with Grad-CAM heatmap into an RGB overlay.

        Args:
            image_np: 2D numpy array of shape (H, W) in [0, 1].
            cam_np: 2D numpy array of shape (H, W) in [0, 1].
            alpha: Heatmap blend transparency.
            colormap_name: Matplotlib colormap name.

        Returns:
            RGB array of shape (H, W, 3) in [0, 1].
        """
        cmap = plt.get_cmap(colormap_name)
        heatmap_rgb = cmap(cam_np)[:, :, :3]  # (H, W, 3)

        # Convert grayscale SAR image to RGB
        sar_rgb = np.stack([image_np, image_np, image_np], axis=-1)

        # Alpha blend: overlay = (1 - alpha) * SAR + alpha * Heatmap
        overlay = (1.0 - alpha) * sar_rgb + alpha * heatmap_rgb
        return np.clip(overlay, 0.0, 1.0)
