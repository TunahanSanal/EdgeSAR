# Contributing to EdgeSAR

Thank you for your interest in contributing to **EdgeSAR**! This project is an open-source engineering exploration of radar signal processing, lightweight deep learning ATR, and safety-conscious embedded systems.

---

## 1. Development Principles

- **Zero Black-Box RDA:** Radar signal transformations (Range matched filtering, RCMC, Azimuth focusing) must remain mathematically transparent and implemented from first principles.
- **Model Efficiency:** ATR models must stay strictly under the 2,000,000 parameter budget and maintain low-latency inference suitable for embedded edge deployment.
- **Memory Safety (Embedded C):**
  - Strictly **no dynamic memory allocation** (`malloc`, `calloc`, `free` are prohibited).
  - Adhere to MISRA-C:2012 guidelines.
  - 100% unit test coverage using Unity.
  - Zero critical defects reported by `cppcheck`.
- **Honest Claim Calibration:** All experimental metrics must specify dataset provenance (synthetic vs. MSTAR), sensor conditions (depression angles), and execution environment. Refer to [`SCOPE.md`](SCOPE.md) and [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## 2. Setting Up Your Environment

1. Clone the repository and install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Verify host C toolchain and static analysis:
   ```bash
   gcc --version
   cppcheck --version
   ```

---

## 3. Running Verification Suites

- Run all Python tests:
  ```bash
  pytest tests/
  ```
- Compile and run embedded C Unity unit tests:
  ```bash
  make -C modules/module3_embedded test
  ```
- Run static analysis:
  ```bash
  make -C modules/module3_embedded check
  ```

---

## 4. Submitting Pull Requests

1. Create a descriptive feature branch (`git checkout -b feature/improved-focusing`).
2. Ensure all unit and regression tests pass without warnings or errors.
3. Update relevant documentation in `docs/` and add test traceability to `docs/RTM.md`.
4. Open a Pull Request with a clear description of changes and quantitative before/after verification metrics.
