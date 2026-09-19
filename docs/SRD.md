# Software Requirements Document (SRD)
## EdgeSAR Embedded Signal Preprocessing, RDA Focusing & ATR Subsystems

**Document ID:** EDGESAR-SRD-001  
**Version:** 1.1.0  
**DO-178C Safety Level:** Design Assurance Level B (DAL-B)  
**Date:** 2026-09-18  
**Applicable Standards:** DO-178C, MISRA-C:2012, IEEE 830  

---

## 1. Scope & System Overview

This Software Requirements Document (SRD) specifies the system and software requirements for the end-to-end EdgeSAR synthetic aperture radar pipeline across three primary operational subsystems:
1. **Module 1 (RDA):** Range-Doppler SAR Image Focusing and Point Target Simulation.
2. **Module 2 (ATR & XAI):** Parameter-efficient deep learning Automatic Target Recognition with Ghost-ECANet and Grad-CAM explainability.
3. **Module 3 (Embedded Preprocessing):** MISRA-C:2012 compliant bare-metal hardware abstraction, ping-pong circular DMA streaming, Radix-2 DIT FFT transformation, and adaptive CA-CFAR target detection.

```
+---------------------------------------------------------------------------------------+
|                               EdgeSAR Radar Sensor System                             |
|                                                                                       |
|  +--------------------+      +--------------------+      +-------------------------+  |
|  | Simulated Front-End| ===> |  Embedded Preproc  | ===> | Deep ATR Classification |  |
|  | (RDA Synthetic Gen)|      |   (FFT + CA-CFAR)  |      |  (Ghost-ECANet + XAI)   |  |
|  +--------------------+      +--------------------+      +-------------------------+  |
|     [REQ-RDA-001..003]         [REQ-EMB-001..008]            [REQ-ATR-001..004]       |
+---------------------------------------------------------------------------------------+
```

---

## 2. Numbered Software Requirements

### 2.1 Module 1: Range-Doppler SAR Image Focusing Subsystem

#### REQ-RDA-001: Range-Doppler SAR Image Focusing Algorithm
- **Description**: The RDA pipeline shall implement the complete 2D Range-Doppler Algorithm from scratch without external blackbox SAR libraries. The processing flow shall perform:
  1. Range compression via frequency-domain chirp matched filtering with Hamming windowing.
  2. Range-Doppler transformation via azimuth forward FFT.
  3. Range Cell Migration Correction (RCMC) via exact 2D frequency-domain phase multiplication (Chirp Scaling / Phase Shift).
  4. Azimuth compression using range-dependent azimuth matched filtering.
  5. 2D inverse FFT to reconstruct the focused spatial complex radar image and compute calibrated magnitude and dB intensity arrays.
- **Rationale**: Provides calibrated, high-resolution radar imagery from raw phase history echo data for downstream target detection and classification.
- **Verification Method**: Automated Unit Test (`tests/test_rda.py::test_2d_focused_point_target_resolution`, `tests/test_rda.py::test_array_dimensions_and_invariants`).

#### REQ-RDA-002: Matched Filtering & RCMC Accuracy
- **Description**: Range compression shall achieve a 3dB impulse response mainlobe width matching theoretical chirp bandwidth limits ($c / (2B)$). Range Cell Migration Correction (RCMC) shall correct quadratic range trajectory curvature across azimuth Doppler frequencies, aligning dispersed energy into straight range bins with residual migration error under $0.5$ range bins.
- **Rationale**: Eliminates Doppler-induced blurring and spatial distortions across the swath.
- **Verification Method**: Automated Unit Test (`tests/test_rda.py::test_chirp_matched_filter_impulse_response`, `tests/test_rda.py::test_rcmc_curvature_straightening`).

#### REQ-RDA-003: Synthetic Target Simulation & SNR Analysis
- **Description**: The synthetic echo generator shall simulate airborne/spaceborne SAR geometry with configurable carrier frequency, chirp bandwidth, sampling rate, PRF, flight velocity, and platform altitude. It shall generate multi-target point scatterer raw echoes with additive white Gaussian noise and Rayleigh speckle clutter across specified SNR levels ($10\text{ dB}$ to $40\text{ dB}$).
- **Rationale**: Enables end-to-end verification and regression testing of imaging algorithms under known ground truth target geometry.
- **Verification Method**: Automated Unit Test (`tests/test_rda.py::test_array_dimensions_and_invariants`, `run_rda.py` CLI).

---

### 2.2 Module 2: Automatic Target Recognition (ATR) & XAI Subsystem

#### REQ-ATR-001: Ghost-ECANet Deep Learning Architecture (< 2M Parameters)
- **Description**: The ATR classifier shall implement the Ghost-ECANet architecture consisting of Ghost modules for cheap linear feature generation, Efficient Channel Attention (ECA) for cross-channel interaction without dimensionality reduction, and Group Normalization (GroupNorm) for batch-size independent numerical stability on edge devices. Total trainable parameters shall strictly not exceed $2,000,000$ (target $< 1.0\text{M}$).
- **Rationale**: Meets SWaP-C (Size, Weight, Power, and Cost) constraints for edge deployment on embedded airborne processors.
- **Verification Method**: Automated Unit Test (`tests/test_atr.py::test_model_parameter_count`, `tests/test_atr.py::test_model_forward_pass`).

#### REQ-ATR-002: Multi-Class SAR Target Recognition (Macro F1 > 60% on Synthetic Benchmark)
- **Description**: The classifier shall classify SAR vehicle chips into target classes (T-72 Main Battle Tank, BMP-2 Infantry Fighting Vehicle, BTR-70 Armored Personnel Carrier) on the synthetic attributed scatterer SAR test benchmark. Trained models shall achieve a Macro-averaged F1 score $> 60\%$ (target $> 70\%$) with every individual target class achieving an F1 score $> 40\%$, resolving class collapse.
- **Rationale**: Guarantees reliable battlefield target classification without collapsing to majority classes under coherent speckle clutter.
- **Verification Method**: Automated Unit Test (`tests/test_atr.py::test_model_convergence_on_synthetic_data`), Quantitative Evaluation (`evaluate.py`, `eval_results/f1_metrics.txt`).

#### REQ-ATR-003: Radar-Aware Data Augmentation
- **Description**: The ATR training pipeline shall employ radar-preserving data augmentations including aspect angle jitter ($\pm 15^\circ$), multiplicative coherent speckle noise ($[0.04, 0.14]$), sub-pixel translation shifts ($\pm 6\text{ px}$), horizontal mirror reflection ($50\%$ probability), random intensity scaling ($[0.85, 1.15]$), and additive noise perturbations ($\sigma = 0.025$). Augmentations shall preserve physical scatterer geometry while diversifying training distributions.
- **Rationale**: Prevents overfitting and class collapse caused by narrow aspect angles and synthetic radar speckle artifacts.
- **Verification Method**: Automated Unit Test (`tests/test_atr.py::test_dataset_generator`).

#### REQ-ATR-004: Grad-CAM Explainable AI (XAI)
- **Description**: The ATR system shall integrate Gradient-weighted Class Activation Mapping (Grad-CAM) targeting the final convolutional feature extractor stage. Grad-CAM shall generate normalized visual heatmaps $[0.0, 1.0]$ highlighting the physical dominant radar scatterers (gun barrel, turret, tracks, hull corners) that contributed to the model's classification decision, blended onto original SAR chips.
- **Rationale**: Provides transparent explainability and auditability for military decision support systems.
- **Verification Method**: Automated Unit Test (`tests/test_atr.py::test_gradcam_generation`), Visual Artifact Inspection (`evaluate.py`, `eval_results/gradcam_*.png`).

---

### 2.3 Module 3: Embedded Signal Preprocessing Subsystem

### REQ-EMB-001 (REQ-001): CA-CFAR Parameter Validation & Boundary Safety
- **Description**: The CFAR module shall validate all configuration parameters prior to signal evaluation. If any pointer (`signal`, `config`, `result`) is NULL, if `train_cells < 2` or `train_cells > 64`, if `guard_cells > 16`, if `threshold_factor <= 0.0`, or if `signal_len <= 2 * (train_cells + guard_cells)`, the function shall reject execution immediately without modifying peripheral memory and return `CFAR_STATUS_INVALID_PARAM` or `CFAR_STATUS_BUFFER_TOO_SMALL`.
- **Rationale**: Prevents buffer underflows, array out-of-bounds access, division by zero, and silent pointer dereferences in flight-critical avionics.
- **Safety Criticality**: DAL-B (Catastrophic/Hazardous mitigation).
- **Verification Method**: Automated Unit Test (`test_CFAR_Init_ValidAndInvalidParams`, `test_CFAR_Detect1D_BufferTooSmallHandling`).

### REQ-002: CA-CFAR 1D Target Detection & Local Maximum Assertion
- **Description**: The CFAR detector shall implement a 1D Cell-Averaging sliding window algorithm. For each Cell Under Test (CUT) within the valid margin, the local noise floor $\mu[i]$ shall be computed from $2 N_T$ surrounding reference cells (excluding $2 N_G$ guard cells). If the CUT power exceeds the adaptive threshold $T[i] = \alpha \mu[i] + T_{\text{floor}}$ AND constitutes a local maximum ($x[i] \ge x[i-1]$ and $x[i] \ge x[i+1]$), the target range bin index and power shall be recorded in the output results container.
- **Rationale**: Guarantees constant probability of false alarms ($P_{fa}$) across non-stationary radar clutter while suppressing duplicate shoulder triggers.
- **Safety Criticality**: DAL-B.
- **Verification Method**: Automated Unit Test (`test_CFAR_Detect1D_SinglePeakDetection`, `test_CFAR_Detect1D_MultiTargetResolution`, `test_CFAR_Detect1D_SilentRadarZeroDetections`).

### REQ-003: Sub-Bin Peak Interpolation & SNR Estimation
- **Description**: For each detected target, the detector shall compute the sub-bin coordinate offset $\Delta x \in [-0.5, +0.5]$ using a 3-point parabolic interpolation vertex formula:
  $$\Delta x = \frac{y_{-1} - y_{+1}}{2(y_{-1} - 2y_0 + y_{+1})}$$
  and calculate estimated Signal-to-Noise Ratio in decibels:
  $$\text{SNR}_{dB} = 10 \log_{10}\left(\frac{P_{\text{peak}}}{\max(\mu_{\text{noise}}, 10^{-12})}\right)$$
  clamped between $0.0\text{ dB}$ and $99.0\text{ dB}$.
- **Rationale**: Enables sub-cell range resolution refinement for down-stream ATR target bounding and target classification confidence weighting.
- **Safety Criticality**: DAL-B.
- **Verification Method**: Automated Unit Test (`test_CFAR_CalculateSNR_dB_Accuracy`, `test_CFAR_Detect1D_SinglePeakDetection`).

### REQ-004: STM32 HAL Mock Handle & State Machine Management
- **Description**: The HAL mock subsystem shall encapsulate peripheral state within a `SAR_HandleTypeDef` structure. Initialization via `HAL_SAR_Init` shall transition the peripheral to `HAL_SAR_STATE_READY` and zero all internal buffers. Invoking `HAL_SAR_DeInit` shall transition state to `HAL_SAR_STATE_RESET`. Any function called with a NULL handle shall safely return `HAL_SAR_INVPARAM` without modifying CPU registers.
- **Rationale**: Provides strict architectural isolation matching STM32Cube HAL driver conventions, facilitating host emulation and future hardware-in-the-loop target deployment.
- **Safety Criticality**: DAL-B.
- **Verification Method**: Automated Unit Test (`test_HAL_SAR_InitAndDeInit`).

### REQ-005: Ping-Pong Circular DMA Buffer Transfer & Overrun Management
- **Description**: The HAL subsystem shall simulate double-buffered circular DMA reception via `HAL_SAR_ReceiveDMA`. When initiated in `HAL_SAR_STATE_READY`, it shall transition to `HAL_SAR_STATE_BUSY`, copy the first half to trigger `HAL_SAR_RxHalfCpltCallback`, copy the second half to trigger `HAL_SAR_RxCpltCallback`, and return to `HAL_SAR_STATE_READY`. If invoked while state is `HAL_SAR_STATE_BUSY`, it shall reject the call with `HAL_SAR_BUSY` and increment `overrun_count`. If requested length exceeds `SAR_DMA_BUFFER_SIZE`, it shall return `HAL_SAR_ERROR` and set error bit `0x01`.
- **Rationale**: Ensures real-time ping-pong continuous streaming without race conditions or buffer corruption during radar pulse reception.
- **Safety Criticality**: DAL-B.
- **Verification Method**: Automated Unit Test (`test_HAL_SAR_ReceiveDMA_TransferFlow`, `test_HAL_SAR_ReceiveDMA_BusyStateAndOverrun`, `test_HAL_SAR_ReceiveDMA_OverflowProtection`).

### REQ-006: Radix-2 Decimation-In-Time (DIT) FFT Preprocessor
- **Description**: The FFT module shall compute in-place forward and inverse discrete Fourier transforms for power-of-2 lengths up to $1024$. The function shall reject non-power-of-2 lengths with `FFT_STATUS_NON_POW2` and NULL buffers with `FFT_STATUS_INVPARAM`. Forward followed by inverse FFT shall reconstruct the original time-domain signal within $10^{-4}$ numerical precision. The module shall also provide `FFT_ComputePowerSpectrum` calculating $|X[k]|^2 = \text{real}^2 + \text{imag}^2$.
- **Rationale**: Prepares digitized radar range lines for frequency-domain pulse compression and CFAR detection on bare-metal architectures without heavy external math libraries.
- **Safety Criticality**: DAL-B.
- **Verification Method**: Automated Unit Test (`test_FFT_Radix2_ForwardAndInverseReconstruction`, `test_FFT_Radix2_NonPowerOfTwoRejection`, `test_FFT_ComputePowerSpectrum`).

### REQ-007: Zero Dynamic Memory Allocation (MISRA-C:2012 Rule 21.3)
- **Description**: The entire embedded C codebase shall execute with zero dynamic memory allocation (`malloc`, `calloc`, `realloc`, `free`). All buffer sizes, target lists, and state variables shall be statically allocated at compile time.
- **Rationale**: Prepares system for flight certification by eliminating heap fragmentation and non-deterministic allocation failures.
- **Safety Criticality**: DAL-B / System-wide.
- **Verification Method**: Static Analysis (Cppcheck Rule 21.3 check, GCC build inspection).

### REQ-008: Bounded Deterministic Loop Execution (MISRA-C:2012 Rule 17.2)
- **Description**: The embedded C codebase shall contain zero recursive function calls. All loops shall have fixed, compile-time provable upper iteration bounds to guarantee deterministic worst-case execution time (WCET).
- **Rationale**: Prevents stack overflows and guarantees real-time responsiveness within radar Pulse Repetition Intervals (PRI).
- **Safety Criticality**: DAL-B / System-wide.
- **Verification Method**: Static Analysis and code review.

---

## 3. Traceability Summary

All 15 requirements defined above (3 RDA focusing requirements `REQ-RDA-001..003`, 4 ATR classification & XAI requirements `REQ-ATR-001..004`, and 8 safety-critical embedded C requirements `REQ-EMB-001..008`) are mapped bidirectionally in [`docs/RTM.md`](file:///C:/Users/TUNAHAN/Desktop/agy/EdgeSAR/docs/RTM.md) to specific source implementations, automated Pytest test cases, and embedded Unity test suites, achieving 100% verification coverage.
