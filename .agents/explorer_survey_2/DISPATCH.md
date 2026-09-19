## 2026-09-18T13:58:48Z

You are Explorer 2 (SAR Signal Processing and ATR Domain Specialist) for EdgeSAR.
Your working directory is: C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\.agents\explorer_survey_2\
The target project root is: C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\
The authoritative user request is at: C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\.agents\ORIGINAL_REQUEST.md

MANDATORY INSTRUCTIONS:
1. You MUST read C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\.agents\ORIGINAL_REQUEST.md before starting work.
2. Investigate the algorithmic requirements and mathematical formulation:
   - Range-Doppler Algorithm (RDA) for raw SAR signal processing: chirp generation (carrier freq, bandwidth, pulse duration, sampling rate), range matched filtering (frequency domain replica multiplication), Range Cell Migration Correction (RCMC, range interpolation or range frequency/azimuth frequency domain correction), azimuth matched filtering (Doppler centroid, Doppler rate calculation).
   - Point-scatterer synthetic raw SAR signal simulator for offline testing.
   - Script requirements for `run_rda.py --input <path_or_synthetic>` saving focused 2D SAR image PNGs (before and after matched filtering).
   - ATR Model architecture: lightweight CNN (< 2M parameters, GhostNet or ECA-Net based), target classes (e.g. MSTAR T-72, BMP-2, BTR-70), synthetic SAR target generator if offline, training pipeline with augmentation and checkpointing (`train.py --epochs 1 --dry-run`), evaluation (`evaluate.py`) with confusion matrix, class-wise F1, and >= 3 Grad-CAM overlay PNGs.
   - Mathematical and architectural rationale for `modules/module2_atr/README.md`.
3. Write your findings to C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\.agents\explorer_survey_2\survey_algorithms.md and C:\Users\TUNAHAN\Desktop\agy\EdgeSAR\.agents\explorer_survey_2\handoff.md.
4. Send a message to the orchestrator with a summary of your findings and the path to your handoff file.
