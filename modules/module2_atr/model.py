"""
EdgeSAR - Module 2: Ghost-ECANet Lightweight Deep Learning ATR Architecture.

Combines Ghost Modules (Han et al., CVPR 2020) for redundant feature generation via cheap
linear operations and Efficient Channel Attention (ECA) (Wang et al., CVPR 2020) for local
cross-channel interactions without dimensionality reduction.

Parameter Count Constraint:
- Hard requirement: Total parameters < 2,000,000.
- Ghost-ECANet delivers deep representation capacity at ~0.85M parameters, achieving
  ultra-low inference latency for SWaP-C constrained edge mission computers.
"""

import math
from typing import List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class HardSwish(nn.Module):
    """Hard-Swish non-linearity: f(x) = x * ReLU6(x + 3) / 6."""
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * F.relu6(x + 3.0, inplace=True) / 6.0


def make_norm(channels: int) -> nn.Module:
    """GroupNorm for deterministic edge inference and zero running-statistics drift."""
    num_groups = min(channels, 8)
    while channels % num_groups != 0 and num_groups > 1:
        num_groups -= 1
    return nn.GroupNorm(num_groups, channels)


class ECALayer(nn.Module):
    """Efficient Channel Attention (ECA) module.

    Captures local cross-channel interaction by performing 1D convolution of adaptive
    kernel size k along channel dimension after Global Average Pooling.
    """

    def __init__(self, channels: int, gamma: float = 2.0, b: float = 1.0):
        super().__init__()
        # Adaptive kernel size k = |log2(C) / gamma + b / gamma|_odd
        t = int(abs((math.log2(channels) / gamma) + (b / gamma)))
        k = t if t % 2 != 0 else t + 1
        k = max(3, k)  # Minimum kernel size 3
        self.conv = nn.Conv1d(1, 1, kernel_size=k, padding=(k - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Global Average Pooling along spatial dimensions: (B, C, H, W) -> (B, C, 1, 1)
        y = x.mean(dim=[-2, -1], keepdim=True)
        # Reshape to (B, 1, C) for 1D convolution along channel axis
        y = y.squeeze(-1).transpose(-1, -2)
        y = self.conv(y)
        # Reshape back to (B, C, 1, 1)
        y = self.sigmoid(y.transpose(-1, -2).unsqueeze(-1))
        return x * y.expand_as(x)


class GhostModule(nn.Module):
    """Ghost Module: Primary 1x1 Conv + Cheap Depthwise 3x3 Conv."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 1,
        ratio: int = 2,
        dw_size: int = 3,
        stride: int = 1,
        relu: bool = True,
    ):
        super().__init__()
        self.out_channels = out_channels
        init_channels = math.ceil(out_channels / ratio)
        new_channels = init_channels * (ratio - 1)

        # Primary convolution
        self.primary_conv = nn.Sequential(
            nn.Conv2d(
                in_channels,
                init_channels,
                kernel_size,
                stride=stride,
                padding=(kernel_size - 1) // 2,
                bias=False,
            ),
            make_norm(init_channels),
            HardSwish() if relu else nn.Identity(),
        )

        # Cheap depthwise operation generating ghost feature maps
        self.cheap_operation = nn.Sequential(
            nn.Conv2d(
                init_channels,
                new_channels,
                dw_size,
                stride=1,
                padding=(dw_size - 1) // 2,
                groups=init_channels,
                bias=False,
            ),
            make_norm(new_channels),
            HardSwish() if relu else nn.Identity(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.primary_conv(x)
        x2 = self.cheap_operation(x1)
        out = torch.cat([x1, x2], dim=1)
        return out[:, : self.out_channels, :, :]


class GhostBottleneck(nn.Module):
    """Ghost Bottleneck with optional depthwise stride and ECA channel attention."""

    def __init__(
        self,
        in_channels: int,
        mid_channels: int,
        out_channels: int,
        dw_kernel_size: int = 3,
        stride: int = 1,
        use_eca: bool = True,
    ):
        super().__init__()
        self.stride = stride

        # 1st Ghost Module (Expansion)
        self.ghost1 = GhostModule(in_channels, mid_channels, relu=True)

        # Depthwise convolution if downsampling
        if stride > 1:
            self.depthwise = nn.Sequential(
                nn.Conv2d(
                    mid_channels,
                    mid_channels,
                    dw_kernel_size,
                    stride=stride,
                    padding=(dw_kernel_size - 1) // 2,
                    groups=mid_channels,
                    bias=False,
                ),
                make_norm(mid_channels),
            )
        else:
            self.depthwise = nn.Identity()

        # ECA Channel Attention
        self.eca = ECALayer(mid_channels) if use_eca else nn.Identity()

        # 2nd Ghost Module (Projection)
        self.ghost2 = GhostModule(mid_channels, out_channels, relu=False)

        # Shortcut branch
        if stride == 1 and in_channels == out_channels:
            self.shortcut = nn.Identity()
        else:
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    in_channels,
                    dw_kernel_size,
                    stride=stride,
                    padding=(dw_kernel_size - 1) // 2,
                    groups=in_channels,
                    bias=False,
                ),
                make_norm(in_channels),
                nn.Conv2d(in_channels, out_channels, 1, stride=1, padding=0, bias=False),
                make_norm(out_channels),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)
        x = self.ghost1(x)
        x = self.depthwise(x)
        x = self.eca(x)
        x = self.ghost2(x)
        return residual + x


class GhostECANet(nn.Module):
    """Ghost-ECANet Lightweight SAR ATR Architecture (< 2M parameters).

    Canonical targets:
        Class 0: T-72 Main Battle Tank
        Class 1: BMP-2 Infantry Fighting Vehicle
        Class 2: BTR-70 Armored Personnel Carrier
    """

    def __init__(self, in_channels: int = 1, num_classes: int = 3, dropout: float = 0.2):
        super().__init__()
        self.num_classes = num_classes

        # Stem: Conv 3x3, stride=2 -> (B, 32, 64, 64)
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, stride=2, padding=1, bias=False),
            make_norm(32),
            HardSwish(),
        )

        # Stage 1: (32 -> 64), stride=2 -> (B, 64, 32, 32)
        self.stage1 = nn.Sequential(
            GhostBottleneck(32, 64, 64, stride=2, use_eca=True),
            GhostBottleneck(64, 96, 64, stride=1, use_eca=True),
        )

        # Stage 2: (64 -> 128), stride=2 -> (B, 128, 16, 16)
        self.stage2 = nn.Sequential(
            GhostBottleneck(64, 128, 128, stride=2, use_eca=True),
            GhostBottleneck(128, 160, 128, stride=1, use_eca=True),
        )

        # Stage 3: (128 -> 256), stride=2 -> (B, 256, 8, 8)
        self.stage3 = nn.Sequential(
            GhostBottleneck(128, 256, 256, stride=2, use_eca=True),
            GhostBottleneck(256, 320, 256, stride=1, use_eca=True),
            GhostBottleneck(256, 320, 256, stride=1, use_eca=True),
        )

        # Stage 4: (256 -> 384), stride=1 -> (B, 384, 8, 8)
        self.stage4 = nn.Sequential(
            GhostBottleneck(256, 384, 384, stride=1, use_eca=True),
            GhostBottleneck(384, 384, 384, stride=1, use_eca=True),
        )

        # Head Conv: 1x1 conv to 512 channels
        self.head_conv = nn.Sequential(
            nn.Conv2d(384, 512, kernel_size=1, stride=1, padding=0, bias=False),
            make_norm(512),
            HardSwish(),
        )

        # Global Average Pooling & Classification Head
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(p=dropout)
        self.classifier = nn.Linear(512, num_classes)

        self._initialize_weights()

    def _initialize_weights(self) -> None:
        """Kaiming normal initialization for convolutional and linear layers."""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract spatial feature maps up to the head convolution."""
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        x = self.head_conv(x)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward classification pass.

        Args:
            x: Input tensor of shape (B, 1, 128, 128).

        Returns:
            Logits tensor of shape (B, num_classes).
        """
        features = self.forward_features(x)
        pooled = self.pool(features).flatten(1)
        dropped = self.dropout(pooled)
        logits = self.classifier(dropped)
        return logits


def count_parameters(model: nn.Module) -> int:
    """Calculate the total number of trainable parameters in the model.

    Raises:
        AssertionError: If total parameters exceed 2,000,000.
    """
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert total_params < 2_000_000, (
        f"Parameter count {total_params:,} exceeds strict 2,000,000 limit!"
    )
    return total_params
