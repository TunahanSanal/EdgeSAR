/**
 * @file test_runner.c
 * @brief Automated Unity Test Runner for EdgeSAR Embedded Preprocessing.
 * @details Executes 100% of unit tests for CFAR, HAL mock, and FFT modules.
 */

#include "unity.h"

/* test_cfar declarations */
extern void test_CFAR_Init_ValidAndInvalidParams(void);
extern void test_CFAR_Detect1D_SinglePeakDetection(void);
extern void test_CFAR_Detect1D_MultiTargetResolution(void);
extern void test_CFAR_Detect1D_SilentRadarZeroDetections(void);
extern void test_CFAR_Detect1D_BufferTooSmallHandling(void);
extern void test_CFAR_CalculateSNR_dB_Accuracy(void);

/* test_hal declarations */
extern void test_HAL_SAR_InitAndDeInit(void);
extern void test_HAL_SAR_ReceiveDMA_TransferFlow(void);
extern void test_HAL_SAR_ReceiveDMA_BusyStateAndOverrun(void);
extern void test_HAL_SAR_ReceiveDMA_OverflowProtection(void);

/* test_fft declarations */
extern void test_FFT_Radix2_ForwardAndInverseReconstruction(void);
extern void test_FFT_Radix2_NonPowerOfTwoRejection(void);
extern void test_FFT_ComputePowerSpectrum(void);

void setUp(void)
{
    /* Per-test fixture setup */
}

void tearDown(void)
{
    /* Per-test fixture teardown */
}

int main(void)
{
    UNITY_BEGIN();

    /* Suite 1: CA-CFAR 1D Detector Tests (REQ-001, REQ-002, REQ-003) */
    RUN_TEST(test_CFAR_Init_ValidAndInvalidParams);
    RUN_TEST(test_CFAR_Detect1D_SinglePeakDetection);
    RUN_TEST(test_CFAR_Detect1D_MultiTargetResolution);
    RUN_TEST(test_CFAR_Detect1D_SilentRadarZeroDetections);
    RUN_TEST(test_CFAR_Detect1D_BufferTooSmallHandling);
    RUN_TEST(test_CFAR_CalculateSNR_dB_Accuracy);

    /* Suite 2: STM32 HAL Mock Peripheral Tests (REQ-004, REQ-005) */
    RUN_TEST(test_HAL_SAR_InitAndDeInit);
    RUN_TEST(test_HAL_SAR_ReceiveDMA_TransferFlow);
    RUN_TEST(test_HAL_SAR_ReceiveDMA_BusyStateAndOverrun);
    RUN_TEST(test_HAL_SAR_ReceiveDMA_OverflowProtection);

    /* Suite 3: Radix-2 FFT Preprocessing Tests (REQ-006) */
    RUN_TEST(test_FFT_Radix2_ForwardAndInverseReconstruction);
    RUN_TEST(test_FFT_Radix2_NonPowerOfTwoRejection);
    RUN_TEST(test_FFT_ComputePowerSpectrum);

    return UNITY_END();
}
