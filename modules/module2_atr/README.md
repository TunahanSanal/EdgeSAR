# Module 2: Automatic Target Recognition (ATR) & Explainable AI (XAI)

## 1. Architectural Blueprint: Ghost-ECANet

Module 2 implements **Ghost-ECANet**, a parameter-efficient, hardware-friendly convolutional neural network tailored for Automatic Target Recognition (ATR) on Synthetic Aperture Radar (SAR) imagery. Deployed on aerospace mission computers (e.g., UAV payloads, edge GPU/NPU, or DSP accelerators), EdgeSAR satisfies strict SWaP-C (Size, Weight, Power, and Cost) constraints.

### 1.1 Architecture & Parameter Verification
- **Strict Parameter Limit**: $< 2,000,000$ parameters.
- **Ghost-ECANet Measured Parameters**: **904,268** (verified via `count_parameters()`, leaving a $>54\%$ safety margin).

```
                      ┌─────────────────────────────────────┐
                      │    Input SAR Chip (1 x 128 x 128)   │
                      └──────────────────┬──────────────────┘
                                         │
                      ┌──────────────────▼──────────────────┐
                      │   Stem: Conv 3x3, s=2, GN, HardSwish │ (32 x 64 x 64)
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

### 1.2 Core Architectural Innovations

#### 1. Ghost Modules (CVPR 2020)
Standard convolution produces $C_{out}$ feature maps using $C_{out} \times C_{in} \times k^2$ parameters. In SAR feature hierarchies, many feature maps are redundant duplicates ("ghosts") of intrinsic features:
1. **Primary Convolution**: Generates $m = \lceil C_{out} / 2 \rceil$ intrinsic feature maps using cheap $1 \times 1$ point convolutions:
   $$Y' = X * W_{primary}$$
2. **Cheap Linear Operation**: Generates remaining ghost maps via depthwise $3 \times 3$ convolution:
   $$y_{i, j} = \Phi_{i, j}(y'_i)$$
3. **Concatenation**: $Y = [Y', \Phi(Y')]$.
4. **Computational Gain**: Achieves $\approx 2\times$ reduction in parameters and FLOPs without sacrificing feature richness.

#### 2. Efficient Channel Attention (ECA) (CVPR 2020)
Unlike Squeeze-and-Excitation (SE-Net) which reduces channel dimensionality by $r=16$ (destroying direct channel correspondences) and introduces heavy fully-connected layers:
1. Performs Global Average Pooling: $\mathbf{z} \in \mathbb{R}^C$.
2. Captures local cross-channel interaction via fast 1D adaptive convolution:
   $$\mathbf{\omega} = \sigma\left(\text{Conv1D}_k(\mathbf{z})\right)$$
   where kernel size $k = |\log_2(C)/\gamma + b/\gamma|_{odd} \in \{3, 5\}$.
3. Parameter overhead is merely $k$ weights $+ 1$ bias ($\approx 4\text{ to } 6$ parameters total per block!).

#### 3. Deterministic GroupNorm for Small-Batch Edge Robustness
Standard BatchNorm relies on running mean and variance statistics that diverge and drift when trained on small edge datasets or evaluated in single-frame embedded edge streams. Ghost-ECANet uses **GroupNorm** ($G=8$), ensuring exact, deterministic normalization across training, offline evaluation, and real-time flight deployment.

---

## 2. Radar Physics & Attributed Scattering Center Simulation

When external MSTAR data is unavailable offline, EdgeSAR synthesizes physics-grounded SAR target chips from first principles:
- **Canonical MSTAR 3-Class Benchmark**:
  - **T-72 (Main Battle Tank)**: Central heavy turret ($A=1.0$), 125mm gun barrel ($A=0.75$, $L=3.5\text{m}$), two parallel continuous tracks (5 road wheels each at $y=\pm 1.8\text{m}$), sloped glacis plate corner reflection ($A=0.8$), and rear engine deck.
  - **BMP-2 (Infantry Fighting Vehicle)**: Forward-offset turret ($A=0.85$), 30mm autocannon ($A=0.55$), narrower tracks ($y=\pm 1.55\text{m}$), and distinctive rear troop double-door corner reflectors ($A=0.8$).
  - **BTR-70 (Armored Personnel Carrier)**: Boat-shaped wedge nose ($A=0.7$), small conical turret, and **8 distinct rubber road wheels** ($y=\pm 1.4\text{m}$, 4 pairs) with zero continuous track returns.
- **Physical Clutter & Speckle**: Rayleigh-distributed background clutter with multiplicative Gaussian speckle ($I \leftarrow I \cdot (1 + \mathcal{N}(0, \sigma^2))$).
- **Radar Shadow**: Low-intensity radar depression shadow cast opposite illumination vector.

### Radar-Preserving Data Augmentation
- Sub-pixel translations ($\pm 4$ pixels).
- Aspect angle jitter ($\pm 5^\circ$).
- Multiplicative speckle injection.
- **Strict Prohibition**: Vertical / range-axis flipping is strictly prohibited because radar shadows are physically directional (they must always point away from the sensor line-of-sight). Flipping vertically violates radar electromagnetic physics.

---

## 3. Explainable AI (XAI) via Grad-CAM

To make target classification defensible to mission commanders and flight certification authorities:
1. Hook into the final convolutional feature maps $A^k$ of `head_conv` ($512 \times 8 \times 8$).
2. Compute gradients with respect to target class score $y^c$:
   $$\frac{\partial y^c}{\partial A^k}$$
3. Compute neuron importance weights via Global Average Pooling:
   $$\alpha_k^c = \frac{1}{U \times V} \sum_{i=1}^U \sum_{j=1}^V \frac{\partial y^c}{\partial A_{i, j}^k}$$
4. Compute ReLU-weighted combination:
   $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_{k=1}^K \alpha_k^c A^k\right)$$
5. Bilinearly interpolate to $128 \times 128$ and fuse with grayscale SAR chip using Jet colormap.
6. **Result**: Highlights vehicle gun barrels, turret corner reflectors, and road wheels as the decisive classification drivers.

---

## 4. "Neden Böyle Yaptım?" (Interview Defense Summary)

### Q1: Why GhostNet + ECA rather than a standard ResNet-18 or MobileNetV3?
* ResNet-18 has $11.7\text{M}$ parameters ($>5\times$ our strict $2.0\text{M}$ parameter budget) and high memory bandwidth demands.
* MobileNetV3 employs Hard-Swish and inverted residuals, but its SE blocks require channel reduction and re-expansion, discarding direct cross-channel interactions. Ghost-ECANet combines Ghost Modules' cheap linear feature generation with ECA's parameter-free 1D cross-channel interaction, slashing parameters to **904k** while retaining high discriminative capacity on radar scattering centers.

### Q2: Why GroupNorm instead of BatchNorm2d?
* BatchNorm tracks batch-dependent `running_mean` and `running_var`. In edge avionics deployments, inference occurs on single radar frames ($B=1$) or streaming DMA ping-pong buffers, where batch statistics do not exist. Furthermore, in safety-critical verification (DO-178C), hidden running state variables introduce nondeterministic behavior. GroupNorm computes normalization per sample across channel groups, ensuring identical, deterministic mathematical output in both training and flight operation.

### Q3: Why is vertical data augmentation forbidden for SAR imagery?
* In optical images, gravity determines vertical orientation, but flips are often tolerated. In SAR imagery, the vertical axis corresponds to slant-range or azimuth line-of-sight. The radar illumination vector determines the target shadow geometry: radar shadows **always fall behind the target away from the sensor**. Flipping along the range axis creates an unphysical target where shadow faces the radar transmitter, confusing the network's spatial reasoning.
