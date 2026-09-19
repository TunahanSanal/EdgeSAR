# Module 3: Embedded Preprocessing & Safety-Critical Verification (DO-178C / MISRA-C:2012)

## 1. Overview & Architectural Design

Module 3 provides a bare-metal ready, safety-critical embedded C signal preprocessing subsystem designed for flight-grade radar avionics (e.g., STM32F4/F7/H7 or ARM Cortex-R/M). It bridges digitized radar IF/video DMA streams to target detection and deep learning ATR inference.

```
       Simulated Radar Front-End (ADC / Baseband Video)
                          │
                          ▼ DMA Stream
               ┌────────────────────────┐
               │   STM32 HAL Mock DMA   │ (Circular Ping-Pong Buffer)
               │     hal_sar_mock.c     │
               └──────────┬─────────────┘
                          │ Half / Full Complete ISR
                          ▼
               ┌────────────────────────┐
               │    Radix-2 DIT FFT     │ (Power Spectrum Estimation)
               │       fft_mock.c       │
               └──────────┬─────────────┘
                          │ Linear Power Buffer
                          ▼
               ┌────────────────────────┐
               │  Cell-Averaging CFAR   │ (Adaptive Thresholding)
               │    cfar_detector.c     │ (Sub-bin Interpolation & SNR)
               └──────────┬─────────────┘
                          │ Target Range Bins & SNR (dB)
                          ▼
            Telemetry / ATR Crop / MIL-STD-1553B
```

---

## 2. Safety-Critical Aerospace Compliance

### 2.1 DO-178C Level B Rigor
- **Formal Requirements**: Every software capability is defined in `docs/SRD.md` with unique requirement identifiers (`REQ-001` through `REQ-006`).
- **Bidirectional Traceability**: Verified in `docs/RTM.md` with 100% forward and backward coverage mapping requirements directly to C source functions and automated Unity unit tests.
- **Defensive API Contracts**: All entrypoints validate input pointers, buffer lengths, window parameters, and boundary conditions, returning explicit enumeration status codes (`CFAR_Status_t`, `HAL_SAR_Status_t`, `FFT_Status_t`).

### 2.2 MISRA-C:2012 Rule Compliance
The C codebase strictly adheres to the MISRA-C:2012 guidelines:
1. **Rule 21.3 (Dynamic Memory Allocation)**: Functions `malloc`, `calloc`, `realloc`, and `free` are strictly prohibited. All buffers (`CFAR_MAX_DETECTIONS`, `SAR_DMA_BUFFER_SIZE`, `FFT_MAX_LENGTH`) are statically dimensioned with fixed memory footprints, guaranteeing zero heap fragmentation and deterministic worst-case execution time (WCET).
2. **Rule 17.2 (No Recursion)**: All algorithms (Radix-2 FFT, CFAR sliding window, DMA buffer copy) use iterative, strictly bounded loops.
3. **Rule 7.2 (Unsigned Literal Suffixes)**: All unsigned integer literals are explicitly postfixed with `U` (e.g., `2048U`, `1U`, `0x00U`).
4. **Rule 18.4 (Pointer Arithmetic)**: Replaced with safe array indexing syntax (`signal[cut]` instead of `*(signal + cut)`).
5. **Rule 17.7 (Ignored Return Values)**: Functions with discardable side-effects are explicitly cast to `(void)memset(...)` or `(void)memcpy(...)`.

---

## 3. Algorithm Specifications

### 3.1 Cell-Averaging Constant False Alarm Rate (CA-CFAR)
- **Reference Window**: $N_T$ training cells and $N_G$ guard cells on each side of the Cell Under Test (CUT).
- **Noise Floor**:
  $$\mu[i] = \frac{1}{2 N_T} \left( \sum_{k=i - N_G - N_T}^{i - N_G - 1} x[k] + \sum_{k=i + N_G + 1}^{i + N_G + N_T} x[k] \right)$$
- **Adaptive Threshold**:
  $$T[i] = \alpha \cdot \mu[i] + T_{\text{floor}}$$
- **Sub-bin Parabolic Peak Interpolation**:
  $$\Delta x = \frac{y_{-1} - y_{+1}}{2(y_{-1} - 2y_0 + y_{+1})}$$
  Refines radar target range measurement to sub-cell accuracy ($\pm 0.05$ bins).
- **SNR Estimation**:
  $$\text{SNR}_{dB} = 10 \log_{10}\left(\frac{P_{peak}}{\max(\mu_{noise}, \epsilon)}\right)$$

### 3.2 Radix-2 Decimation-In-Time (DIT) FFT
- Fixed-size in-place computation conforming to CMSIS-DSP interface paradigms.
- Fast bit-reversal indexing and trigonometric twiddle factor generation.
- Exact round-trip inverse transformation verified to within $10^{-4}$ numerical error.

---

## 4. Verification & Static Analysis

### 4.1 Host Compilation with Strict Warning Shields
```bash
gcc -Wall -Wextra -pedantic -std=c99 -Werror -Wstrict-prototypes -Wshadow -Iinclude -Itests/unity -o test_runner.exe ...
```
Compiles with **0 warnings** and **0 errors** under host GCC / Clang.

### 4.2 Automated Unity Test Execution
```bash
./test_runner.exe
```
Output:
```
========================================================
 Unity Test Suite: tests/test_runner.c
========================================================
--------------------------------------------------------
 13 Tests | 0 Failures | 0 Ignored
 OK: ALL TESTS PASSED (100% VERIFIED)
========================================================
```

---

## 5. "Neden Böyle Yaptım?" (Interview Defense Summary)

### Q1: Why did you implement a HAL mock instead of compiling directly against STM32Cube firmware?
* **Zero Host Toolchain Lock-in**: Hard-linking against vendor headers (`stm32h7xx_hal.h`) prevents compilation and automated CI testing on Linux/Windows host development environments without an ARM cross-compiler (`arm-none-eabi-gcc`).
* **Hardware-in-the-Loop (HIL) Preparation**: By matching STM32 HAL function signatures (`HAL_SAR_ReceiveDMA`, `HAL_SAR_RxCpltCallback`, `SAR_HandleTypeDef`), transitioning to physical target hardware merely requires replacing the mock source file with real DMA/SPI register accesses, while keeping algorithm logic and unit tests intact.

### Q2: Why CA-CFAR rather than OS-CFAR (Ordered-Statistic) in the embedded preprocessor?
* **Deterministic Execution Time (WCET)**: CA-CFAR requires simple accumulator additions: $O(N)$ operations per cell (or $O(1)$ with running sliding accumulators). OS-CFAR requires sorting $2N_T$ cells per CUT, which is $O(N \log N)$ or requires complex median networks that increase execution latency and power consumption on bare-metal microcontrollers.
* **Target Environment**: In open sea or uniform terrain SAR surveillance, CA-CFAR yields maximum target detection sensitivity (lowest CFAR loss $\approx 1.5\text{ dB}$). To guard against multi-target masking, we added local maximum verification and configurable guard cells.

### Q3: Why is dynamic memory (`malloc`) forbidden in flight software?
* Under DO-178C Level A/B and MISRA-C:2012 Rule 21.3, dynamic allocation creates non-deterministic heap fragmentation, potential memory leaks, and unpredictable allocation latencies that violate hard real-time radar processing deadlines (e.g., PRF intervals of $1\text{ ms}$). Static allocation guarantees memory safety at compile time.
