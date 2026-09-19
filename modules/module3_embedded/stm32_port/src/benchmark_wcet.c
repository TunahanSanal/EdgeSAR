/**
 * @file benchmark_wcet.c
 * @brief Benchmark harness: EdgeSAR Radix-2 DIT FFT numerical accuracy
 *        and host-measured execution timing with Cortex-M4 projection.
 *
 * IMPORTANT: Clock cycle projections for ARM Cortex-M4F @ 168 MHz are
 * THEORETICAL ESTIMATES derived from known instruction throughput ratios.
 * They have NOT been measured on physical STM32 hardware via DWT registers.
 * For validated WCET, deploy main_stm32.c on target and read DWT_CYCCNT.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <time.h>

#include "fft_mock.h"
#include "cfar_detector.h"

#define BENCHMARK_FFT_SIZE   (512U)
#define BENCHMARK_ITERATIONS (1000U)

/* Static buffers — zero heap */
static float s_real_in[BENCHMARK_FFT_SIZE];
static float s_imag_in[BENCHMARK_FFT_SIZE];
static Complex32_t s_complex_fft[BENCHMARK_FFT_SIZE];
static Complex32_t s_complex_cfar[BENCHMARK_FFT_SIZE];

/* CFAR buffers */
static float s_power_spectrum[BENCHMARK_FFT_SIZE];
static CFAR_Config_t s_cfar_config;
static CFAR_Result_t s_cfar_result;

int run_fft_and_wcet_benchmark(void)
{
    printf("========================================================\n");
    printf("  EdgeSAR: Embedded FFT & WCET Benchmark Verification  \n");
    printf("========================================================\n\n");

    /* Populate test input with two sinusoidal pulses */
    for (uint32_t i = 0U; i < BENCHMARK_FFT_SIZE; ++i) {
        float f1 = (float)i * 0.05f;
        float f2 = (float)i * 0.12f;
        s_real_in[i] = sinf(f1) + 0.5f * cosf(f2);
        s_imag_in[i] = 0.0f;
    }

    /* ========== SECTION 1: Numerical Accuracy ========== */
    for (uint32_t i = 0U; i < BENCHMARK_FFT_SIZE; ++i) {
        s_complex_fft[i].real = s_real_in[i];
        s_complex_fft[i].imag = s_imag_in[i];
    }

    FFT_Status_t status_fft = FFT_Radix2_Forward(s_complex_fft, (uint16_t)BENCHMARK_FFT_SIZE);
    if (status_fft != FFT_STATUS_OK) {
        printf("[FAIL] EdgeSAR FFT returned error code %d\n", (int)status_fft);
        return -1;
    }

    /* Golden DFT reference (first 32 bins) */
    float max_error = 0.0f;
    for (uint32_t k = 0U; k < 32U; ++k) {
        float sum_r = 0.0f, sum_i = 0.0f;
        for (uint32_t n = 0U; n < BENCHMARK_FFT_SIZE; ++n) {
            float angle = -2.0f * 3.14159265358979f * (float)(k * n) / (float)BENCHMARK_FFT_SIZE;
            sum_r += s_real_in[n] * cosf(angle);
            sum_i += s_real_in[n] * sinf(angle);
        }
        float err_r = fabsf(s_complex_fft[k].real - sum_r);
        float err_i = fabsf(s_complex_fft[k].imag - sum_i);
        if (err_r > max_error) { max_error = err_r; }
        if (err_i > max_error) { max_error = err_i; }
    }

    printf("  1. Numerical Accuracy Verification:\n");
    printf("     - Max |error| vs Golden DFT: %.6e\n", max_error);
    printf("     - Status: %s\n\n", (max_error < 1e-3f) ? "PASSED" : "FAILED");
    if (max_error >= 1e-3f) { return -1; }

    /* ========== SECTION 2: Host Execution Timing ========== */
    printf("  2. Host Execution Timing (%u iterations averaged):\n", BENCHMARK_ITERATIONS);

    /* --- FFT Timing --- */
    clock_t fft_start = clock();
    for (uint32_t iter = 0U; iter < BENCHMARK_ITERATIONS; ++iter) {
        for (uint32_t i = 0U; i < BENCHMARK_FFT_SIZE; ++i) {
            s_complex_fft[i].real = s_real_in[i];
            s_complex_fft[i].imag = 0.0f;
        }
        FFT_Radix2_Forward(s_complex_fft, (uint16_t)BENCHMARK_FFT_SIZE);
    }
    clock_t fft_end = clock();
    double fft_avg_us = ((double)(fft_end - fft_start) / CLOCKS_PER_SEC) * 1e6 / BENCHMARK_ITERATIONS;

    /* --- CFAR Timing --- */
    /* Prepare power spectrum from FFT output */
    FFT_ComputePowerSpectrum(s_complex_fft, s_power_spectrum, (uint16_t)BENCHMARK_FFT_SIZE);

    s_cfar_config.train_cells = 16U;
    s_cfar_config.guard_cells = 4U;
    s_cfar_config.threshold_factor = 3.5f;
    (void)CFAR_Init(&s_cfar_config);

    clock_t cfar_start = clock();
    for (uint32_t iter = 0U; iter < BENCHMARK_ITERATIONS; ++iter) {
        CFAR_Detect1D(s_power_spectrum, (uint16_t)BENCHMARK_FFT_SIZE,
                      &s_cfar_config, &s_cfar_result);
    }
    clock_t cfar_end = clock();
    double cfar_avg_us = ((double)(cfar_end - cfar_start) / CLOCKS_PER_SEC) * 1e6 / BENCHMARK_ITERATIONS;

    double total_avg_us = fft_avg_us + cfar_avg_us;

    printf("     - Host FFT  (512-pt)  : %.1f us / iteration\n", fft_avg_us);
    printf("     - Host CFAR (512 bins) : %.1f us / iteration\n", cfar_avg_us);
    printf("     - Host Total Pipeline  : %.1f us / iteration\n\n", total_avg_us);

    /* ========== SECTION 3: Cortex-M4 Theoretical Projection ========== */
    /*
     * NOTE: These are THEORETICAL ESTIMATES, not hardware measurements.
     * Cortex-M4F single-precision FPU executes most float ops in 1-2 cycles.
     * N*log2(N) butterfly operations: 512 * 9 * ~10 cycles = ~46,080 cycles.
     * CA-CFAR: 512 * ~35 cycles (sliding window + compare) = ~17,920 cycles.
     * These estimates assume O2 optimization, no cache misses, no interrupts.
     */
    uint32_t est_fft_cycles  = (uint32_t)(512U * 9U * 10U);  /* ~46,080 */
    uint32_t est_cfar_cycles = (uint32_t)(512U * 35U);        /* ~17,920 */
    uint32_t est_total       = est_fft_cycles + est_cfar_cycles;
    double   est_total_ms    = (double)est_total / 168000.0;  /* 168 MHz */

    printf("  3. Cortex-M4F @ 168 MHz THEORETICAL Projection:\n");
    printf("     *** NOT MEASURED ON HARDWARE — USE FOR ESTIMATION ONLY ***\n");
    printf("     - Est. FFT  cycles     : ~%u\n", est_fft_cycles);
    printf("     - Est. CFAR cycles     : ~%u\n", est_cfar_cycles);
    printf("     - Est. Total cycles    : ~%u (~%.3f ms @ 168 MHz)\n", est_total, est_total_ms);
    printf("     - REQ-005 Limit (25 ms): %.0fx theoretical margin\n", 25.0 / est_total_ms);
    printf("     - Validation Status    : REQUIRES STM32 DWT MEASUREMENT\n");
    printf("========================================================\n");

    (void)s_complex_cfar; /* Suppress unused variable warning if applicable */
    return 0;
}

#ifndef EDGESAR_TEST_RUNNER
int main(void)
{
    return run_fft_and_wcet_benchmark();
}
#endif
