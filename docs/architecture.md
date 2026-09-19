# EdgeSAR System Architecture & Data Flow

**Document ID:** EDGESAR-ARCH-001  
**Version:** 1.0.0  
**Classification:** Defense Avionics Systems Engineering Specification  
**Date:** 2026-09-18  

---

## 1. System Overview

EdgeSAR is an end-to-end embedded radar processing and Automatic Target Recognition (ATR) system spanning:
1. **Module 1: Raw SAR Signal Processing**: Range-Doppler Algorithm (RDA) 2D image reconstruction from first principles.
2. **Module 2: Automatic Target Recognition (ATR)**: Parameter-efficient Ghost-ECANet (< 2M parameters) with Grad-CAM explainability.
3. **Module 3: Embedded Signal Preprocessing**: Host-simulated bare-metal C module (STM32 HAL mock, Radix-2 FFT, CA-CFAR 1D detector) compliant with DO-178C Level B and MISRA-C:2012.
4. **Module 4: Systems Integration**: Dual-redundant MIL-STD-1553B bus scheduling and MIL-STD-882E system safety / FMEA hazard analysis.

---

## 2. End-to-End System Block Diagram

```mermaid
flowchart TD
    subgraph SENSOR["Radar Front-End & Flight Kinematics"]
        A["Airborne / UAV Radar Platform (v, H)"] -->|"LFM Chirp TX / RX Echo"| B["Quadrature Demodulator (Baseband I/Q)"]
    end

    subgraph MOD1["Module 1: Raw SAR Signal Processing (RDA)"]
        B --> C["Raw Baseband Echo Matrix s(tau, eta)"]
        C --> D["Range Matched Filtering (f_tau)"]
        D --> E["Azimuth Fourier Transform (Range-Doppler)"]
        E --> F["Range Cell Migration Correction (2D Phase Shift)"]
        F --> G["Azimuth Matched Filtering & 2D Focusing"]
        G --> H["2D Focused Complex SAR Image I(r, a)"]
    end

    subgraph MOD3["Module 3: Safety-Critical Embedded Preprocessing (C / HAL)"]
        H --> I["STM32 HAL Mock DMA Interface (Ping-Pong Buffer)"]
        I --> J["Radix-2 DIT FFT Spectral Preprocessing"]
        J --> K["Cell-Averaging CFAR Detector (CA-CFAR)"]
        K --> L["Sub-bin Peak Interpolation & SNR Estimation"]
        L --> M["Target Region of Interest (ROI) Chips (128x128)"]
    end

    subgraph MOD2["Module 2: Lightweight Deep ATR & Explainability (XAI)"]
        M --> N["Ghost-ECANet CNN (904k Parameters < 2M)"]
        N --> O["Target Classification: T-72 / BMP-2 / BTR-70"]
        N --> P["Grad-CAM Explainability Engine (Dominant Scatterers)"]
    end

    subgraph MOD4["Module 4: Aerospace Avionics & Defense Bus Integration"]
        O --> Q["MIL-STD-1553B Remote Terminal (RT Address 0x05)"]
        L --> Q
        Q --> R["Dual-Redundant Serial Bus (Bus A / Bus B)"]
        R --> S["Mission Computer / Cockpit Display Unit"]
    end
```

---

## 3. Real-Time Radar Execution & Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Radar as Radar Front-End / ADC
    participant HAL as STM32 HAL Mock DMA
    participant RDA as RDA Image Reconstruction
    participant CFAR as Embedded CA-CFAR Detector
    participant ATR as Ghost-ECANet Classifier
    participant Bus as MIL-STD-1553B Bus Controller

    Note over Radar,HAL: Pulse Repetition Interval (PRI = 1.0 ms)
    Radar->>HAL: Stream Digitized Baseband Video (DMA Buffer)
    HAL->>HAL: Half-Transfer Complete ISR (Ping Buffer)
    HAL->>HAL: Full-Transfer Complete ISR (Pong Buffer)
    
    HAL->>RDA: Hand off Raw Echo Matrix (512 pulses x 1024 bins)
    activate RDA
    RDA->>RDA: Range Compression (Fast-time FFT + Conjugate Phase)
    RDA->>RDA: Azimuth FFT to Range-Doppler Domain
    RDA->>RDA: RCMC via 2D Phase Shift Kernel
    RDA->>RDA: Azimuth Matched Filtering & IFFT
    RDA-->>CFAR: Hand off 2D Focused SAR Frame (Magnitude Power)
    deactivate RDA

    activate CFAR
    CFAR->>CFAR: Compute Sliding Window Adaptive Threshold
    CFAR->>CFAR: Detect Range Peaks & Sub-bin Vertex Interpolation
    CFAR->>CFAR: Calculate Local SNR in dB
    CFAR-->>ATR: Hand off Extracted 128x128 Target ROIs
    deactivate CFAR

    activate ATR
    ATR->>ATR: Ghost-ECANet Forward Pass (GroupNorm Normalized)
    ATR->>ATR: Compute Softmax Probabilities & Class Decision
    ATR->>ATR: Generate Grad-CAM Scatterer Heatmap Overlay
    ATR-->>Bus: Deliver Target ID, Confidence & Bounding Coordinates
    deactivate ATR

    Bus->>Bus: Transmit Subaddress 4 Telemetry via Dual Bus (A/B)
```

---

## 4. Architectural Boundaries & Data Structures

| Subsystem | Input Data Format | Output Data Format | Execution Environment | Safety Standard |
|---|---|---|---|---|
| **Module 1 (RDA)** | Complex 2D array `(512, 1024)` float64 | Focused 2D SAR image `(512, 1024)` dB | Python 3.14 (NumPy vectorized) | High-throughput DSP model |
| **Module 2 (ATR)** | Grayscale SAR chip `(1, 128, 128)` float32 | Class ID (`0, 1, 2`) + Conf + Grad-CAM | PyTorch CPU/NPU edge inference | Low-SWaP (< 2M params) |
| **Module 3 (Embedded C)** | Raw unsigned 16-bit DMA buffer | `CFAR_Result_t` static struct | Bare-metal C (Host simulated STM32) | DO-178C DAL-B, MISRA-C:2012 |
| **Module 4 (Avionics)** | Target detection struct + Health metrics | 20-bit Manchester-encoded 1553B words | MIL-STD-1553B serial bus | MIL-STD-1553B, MIL-STD-882E |
