/**
 * @file test_cfar.c
 * @brief Unit tests for CA-CFAR 1D Radar Detector.
 * @details Traceable to DO-178C requirements: REQ-001, REQ-002, REQ-003.
 */

#include "unity.h"
#include "cfar_detector.h"
#include <string.h>

/**
 * @brief Test REQ-001: CFAR initialization and boundary validation.
 */
void test_CFAR_Init_ValidAndInvalidParams(void)
{
    CFAR_Config_t cfg;

    /* 1. NULL pointer check */
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_INVALID_PARAM, CFAR_Init(NULL));

    /* 2. Valid standard configuration */
    cfg.train_cells = 8U;
    cfg.guard_cells = 2U;
    cfg.threshold_factor = 3.5f;
    cfg.noise_floor_min = 0.05f;
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_OK, CFAR_Init(&cfg));

    /* 3. Too few training cells */
    cfg.train_cells = 1U;
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_INVALID_PARAM, CFAR_Init(&cfg));

    /* 4. Too many training cells */
    cfg.train_cells = 128U;
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_INVALID_PARAM, CFAR_Init(&cfg));

    /* 5. Negative threshold factor */
    cfg.train_cells = 8U;
    cfg.threshold_factor = -1.0f;
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_INVALID_PARAM, CFAR_Init(&cfg));

    /* 6. Negative noise floor */
    cfg.threshold_factor = 3.5f;
    cfg.noise_floor_min = -0.1f;
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_INVALID_PARAM, CFAR_Init(&cfg));
}

/**
 * @brief Test REQ-002: Detect single high-contrast radar target in noise.
 */
void test_CFAR_Detect1D_SinglePeakDetection(void)
{
    float signal[256];
    CFAR_Config_t cfg;
    CFAR_Result_t res;

    /* Fill with uniform noise floor 1.0 */
    for (uint32_t i = 0; i < 256U; ++i) {
        signal[i] = 1.0f;
    }

    /* Inject target peak at bin 100 with power 10.0 (10x noise floor) */
    signal[99] = 5.0f;
    signal[100] = 10.0f;
    signal[101] = 5.0f;

    cfg.train_cells = 8U;
    cfg.guard_cells = 2U;
    cfg.threshold_factor = 3.0f;
    cfg.noise_floor_min = 0.1f;

    const CFAR_Status_t status = CFAR_Detect1D(signal, 256U, &cfg, &res);

    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_OK, status);
    TEST_ASSERT_EQUAL_UINT(1U, res.num_targets);
    TEST_ASSERT_EQUAL_UINT(100U, res.targets[0].range_bin);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 10.0f, res.targets[0].power_linear);
    TEST_ASSERT_FLOAT_WITHIN(0.05f, 0.0f, res.targets[0].sub_bin_offset);
    TEST_ASSERT_TRUE(res.targets[0].snr_estimate_db > 8.0f);
}

/**
 * @brief Test REQ-002: Multi-target resolution in presence of clutter.
 */
void test_CFAR_Detect1D_MultiTargetResolution(void)
{
    float signal[512];
    CFAR_Config_t cfg;
    CFAR_Result_t res;

    for (uint32_t i = 0; i < 512U; ++i) {
        signal[i] = 0.5f;
    }

    /* Target A at bin 120 */
    signal[120] = 8.0f;
    /* Target B at bin 250 */
    signal[250] = 6.0f;
    /* Target C at bin 380 */
    signal[380] = 7.5f;

    cfg.train_cells = 6U;
    cfg.guard_cells = 2U;
    cfg.threshold_factor = 3.5f;
    cfg.noise_floor_min = 0.1f;

    const CFAR_Status_t status = CFAR_Detect1D(signal, 512U, &cfg, &res);

    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_OK, status);
    TEST_ASSERT_EQUAL_UINT(3U, res.num_targets);
    TEST_ASSERT_EQUAL_UINT(120U, res.targets[0].range_bin);
    TEST_ASSERT_EQUAL_UINT(250U, res.targets[1].range_bin);
    TEST_ASSERT_EQUAL_UINT(380U, res.targets[2].range_bin);
}

/**
 * @brief Test REQ-002: Zero radar video produces zero false alarms.
 */
void test_CFAR_Detect1D_SilentRadarZeroDetections(void)
{
    float signal[128];
    CFAR_Config_t cfg;
    CFAR_Result_t res;

    (void)memset(signal, 0, sizeof(signal));

    cfg.train_cells = 4U;
    cfg.guard_cells = 1U;
    cfg.threshold_factor = 3.0f;
    cfg.noise_floor_min = 0.5f; /* Non-zero threshold floor prevents division/false alarms */

    const CFAR_Status_t status = CFAR_Detect1D(signal, 128U, &cfg, &res);

    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_OK, status);
    TEST_ASSERT_EQUAL_UINT(0U, res.num_targets);
}

/**
 * @brief Test REQ-001: Signal array smaller than CFAR window rejected safely.
 */
void test_CFAR_Detect1D_BufferTooSmallHandling(void)
{
    float signal[10];
    CFAR_Config_t cfg;
    CFAR_Result_t res;

    cfg.train_cells = 8U;
    cfg.guard_cells = 2U; /* 2 * (8 + 2) = 20 cells required */
    cfg.threshold_factor = 3.0f;
    cfg.noise_floor_min = 0.1f;

    const CFAR_Status_t status = CFAR_Detect1D(signal, 10U, &cfg, &res);
    TEST_ASSERT_EQUAL_INT(CFAR_STATUS_BUFFER_TOO_SMALL, status);
}

/**
 * @brief Test REQ-003: Verify SNR in dB formula: 10 * log10(P / N).
 */
void test_CFAR_CalculateSNR_dB_Accuracy(void)
{
    /* 10x ratio = +10.0 dB */
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 10.0f, CFAR_CalculateSNR_dB(10.0f, 1.0f));

    /* 100x ratio = +20.0 dB */
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 20.0f, CFAR_CalculateSNR_dB(100.0f, 1.0f));

    /* 2x ratio \approx +3.01 dB */
    TEST_ASSERT_FLOAT_WITHIN(0.02f, 3.01f, CFAR_CalculateSNR_dB(2.0f, 1.0f));

    /* Peak equal to or lower than noise -> 0.0 dB */
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, CFAR_CalculateSNR_dB(0.5f, 1.0f));
}
