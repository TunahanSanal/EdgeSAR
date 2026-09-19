# Original User Request

## Initial Request — 2026-09-18T13:52:50Z

Develop EdgeSAR, an end-to-end Synthetic Aperture Radar (SAR) target recognition and embedded edge processing system spanning raw signal image formation via the Range-Doppler Algorithm (from scratch), lightweight deep learning ATR with explainability (XAI), safety-critical embedded C preprocessing adhering to MISRA-C:2012 and DO-178C traceability, and aerospace/defense system integration documentation.

Working directory: C:\Users\TUNAHAN\Desktop\agy\EdgeSAR
Integrity mode: demo

## Requirements

### R1. Raw SAR Signal Processing (Range-Doppler Algorithm)
Implement a raw SAR signal processing pipeline in Python that parses complex SAR data (with automatic synthetic raw chirp signal generation as an offline test fallback) and reconstructs 2D focused SAR images using the Range-Doppler Algorithm (RDA). Range matched filtering, range cell migration correction (RCMC), and azimuth matched filtering must be implemented from first principles with clear mathematical comments and derivations, strictly avoiding black-box SAR image reconstruction libraries.

### R2. Automatic Target Recognition (ATR) & Explainable AI (XAI)
Implement a parameter-efficient lightweight convolutional neural network (< 2M parameters, such as GhostNet or ECA-based) for vehicle classification on SAR imagery (e.g., MSTAR classes: T-72, BMP-2, BTR-70). Provide a complete training pipeline with data augmentation, checkpointing, quantitative evaluation (confusion matrix, class-wise F1), and explainability maps (Grad-CAM or Integrated Gradients) highlighting the dominant radar scatterers. Document the architectural rationale in technical detail for interview defendability.

### R3. Embedded Preprocessing & Safety-Critical Verification (DO-178C / MISRA-C)
Implement a host-simulated, bare-metal-ready C signal preprocessing module (FFT / CFAR or threshold detection) using a hardware abstraction layer (HAL mock interface) enabling future migration to STM32. Follow safety-critical aerospace software rigor: author a Software Requirements Document (SRD) with numbered requirements (REQ-001, etc.), a bidirectional Requirements Traceability Matrix (RTM) linking each requirement to source code and automated unit tests (Unity framework), and ensure compliance with MISRA-C:2012 guidelines verified via static analysis.

### R4. System Integration & Defense Standard Documentation
Provide comprehensive systems engineering artifacts: end-to-end system architecture and data flow diagrams (Mermaid), a 1-page theoretical integration and bus scheduling specification for MIL-STD-1553B dual-redundant serial bus, a MIL-STD-882E compliant system safety / FMEA hazard analysis table, and transparent documentation delineating agentic boilerplate from human-defensible algorithmic design decisions.

## Acceptance Criteria

### Verification Resources & Infrastructure
- The environment uses Python (>=3.9) with standard scientific packages (NumPy, PyTorch, Matplotlib) and a host C compiler (GCC/Clang) with Unity test runner and Cppcheck.
- If external MSTAR downloading encounters network or credential restrictions, the suite must include a synthetic raw chirp / point-scatterer generator so all verification scripts run self-contained offline.

### Module 1: Sinyal İşleme (RDA)
- [ ] `python run_rda.py --input <path_or_synthetic>` executes successfully and outputs focused 2D SAR image PNGs (before/after matched filtering).
- [ ] Matched filtering and range migration calculations are written from scratch with step-by-step mathematical inline explanations.
- [ ] `pytest tests/test_rda.py` passes all unit tests, verifying filter impulse response, point target resolution/sidelobes, and array dimensions.

### Module 2: ATR & XAI
- [ ] Model parameter count is verified programmatically to be under 2,000,000 parameters.
- [ ] `python train.py --epochs 1 --dry-run` runs end-to-end without runtime errors and saves a model checkpoint.
- [ ] `python evaluate.py` outputs a confusion matrix plot, class-wise F1 table, and at least 3 Grad-CAM overlay PNGs identifying scatterer points.
- [ ] `modules/module2_atr/README.md` contains an interview-defensible technical rationale explaining the architectural trade-offs.

### Module 3: Gömülü Modül (DO-178C / MISRA-C)
- [ ] C preprocessing code compiles with `gcc -Wall -Wextra -pedantic` with zero warnings.
- [ ] Cppcheck static analysis (`cppcheck --enable=all --error-exitcode=1 ...`) reports 0 critical / severe errors.
- [ ] Automated test suite (`make test` or `ctest`) runs Unity tests and passes 100% of test cases.
- [ ] `docs/SRD.md` defines unique requirement identifiers (`REQ-001`, `REQ-002`, ...).
- [ ] `docs/RTM.md` verifies 100% bidirectional traceability: every REQ maps to specific C source functions and Unity test cases.

### Module 4: Sistem Seviyesi Belgeleme & Bütünlük
- [ ] Root `README.md` documents the end-to-end pipeline story (signal -> image -> classification -> embedded edge -> compliance) and reproducibility instructions.
- [ ] System architecture and data flow are visualized using valid Mermaid diagrams in `docs/architecture.md`.
- [ ] `docs/mil_std_1553b.md` specifies word formats, command/status/data words, and subaddress mapping.
- [ ] `docs/mil_std_882e_fmea.md` contains a structured hazard matrix (Failure Mode, Severity, Probability, RAC, Mitigation).
- [ ] Each module includes a "Neden Böyle Yaptım?" (Interview Defense Summary) section summarizing core engineering choices.
