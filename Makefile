# EdgeSAR Root Makefile
# Provides single-command verification, testing, and full pipeline reproduction.

PYTHON ?= python
PYTEST ?= pytest

.PHONY: all test test-python test-c check reproduce-all clean help

all: test

help:
	@echo "EdgeSAR Build and Verification Targets:"
	@echo "  make test          - Run all Python and C test suites"
	@echo "  make test-python   - Run pytest suite (RDA, ATR, Integration, Property)"
	@echo "  make test-c        - Compile and run Unity embedded C unit tests"
	@echo "  make check         - Run Cppcheck static analysis on embedded C module"
	@echo "  make reproduce-all - Run full end-to-end pipeline (RDA, ATR evaluation, C tests)"
	@echo "  make clean         - Remove temporary artifacts and binaries"

test: test-python test-c check

test-python:
	$(PYTEST) tests/ -v

test-c:
	$(MAKE) -C modules/module3_embedded test

check:
	$(MAKE) -C modules/module3_embedded check

reproduce-all:
	@echo "=== [1/4] Range-Doppler Algorithm (RDA) Synthetic Execution ==="
	$(PYTHON) run_rda.py --input synthetic --output-dir ./output_rda
	@echo "=== [2/4] Range-Doppler Algorithm (RDA) Real SAR Execution ==="
	$(PYTHON) run_rda.py --input real --source sentinel1 --output-dir ./output_rda_real
	@echo "=== [3/4] MSTAR Comprehensive Evaluation ==="
	$(PYTHON) scripts/evaluate_mstar_comprehensive.py
	@echo "=== [4/4] Embedded C Verification & Static Analysis ==="
	$(MAKE) -C modules/module3_embedded test
	$(MAKE) -C modules/module3_embedded check
	@echo "=== EdgeSAR Full Pipeline Reproduction Complete ==="

clean:
	$(MAKE) -C modules/module3_embedded clean
	rm -rf output_rda/*.png output_rda_real/*.png
