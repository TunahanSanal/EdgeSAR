/**
 * @file cfar_detector.c
 * @brief Safety-Critical Cell-Averaging CFAR Detector Implementation.
 * @details Conforms to MISRA-C:2012 guidelines and DO-178C Level B software requirements.
 *          Deterministic execution time; zero dynamic memory; full parameter bounds validation.
 *          Maps to requirements: REQ-001, REQ-002, REQ-003.
 */

#include "cfar_detector.h"
#include <math.h>
#include <stddef.h>

/* Defensive parameter check constants */
#define CFAR_MIN_THRESHOLD_FACTOR (0.01f)
#define CFAR_MAX_THRESHOLD_FACTOR (100.0f)
#define CFAR_LOG10_EPSILON        (1e-12f)

/**
 * @brief Initialize CFAR detector configuration with safety parameter checks.
 * @details Implements REQ-001.
 */
CFAR_Status_t CFAR_Init(const CFAR_Config_t * const config)
{
    CFAR_Status_t status = CFAR_STATUS_OK;

    if (config == NULL) {
        status = CFAR_STATUS_INVALID_PARAM;
    } else if ((config->train_cells < CFAR_MIN_TRAIN_CELLS) ||
               (config->train_cells > CFAR_MAX_TRAIN_CELLS)) {
        status = CFAR_STATUS_INVALID_PARAM;
    } else if (config->guard_cells > CFAR_MAX_GUARD_CELLS) {
        status = CFAR_STATUS_INVALID_PARAM;
    } else if ((config->threshold_factor < CFAR_MIN_THRESHOLD_FACTOR) ||
               (config->threshold_factor > CFAR_MAX_THRESHOLD_FACTOR)) {
        status = CFAR_STATUS_INVALID_PARAM;
    } else if (config->noise_floor_min < 0.0f) {
        status = CFAR_STATUS_INVALID_PARAM;
    } else {
        /* Parameters valid - retain current values */
        status = CFAR_STATUS_OK;
    }

    return status;
}

/**
 * @brief Calculate Signal-to-Noise Ratio (SNR) in decibels.
 * @details Implements REQ-003.
 */
float CFAR_CalculateSNR_dB(float peak_power, float noise_power)
{
    float snr_db = 0.0f;
    float denom = noise_power;

    if (denom < CFAR_LOG10_EPSILON) {
        denom = CFAR_LOG10_EPSILON;
    }

    if (peak_power > denom) {
        const float ratio = peak_power / denom;
        snr_db = 10.0f * (float)log10((double)ratio);
        if (snr_db > 99.0f) {
            snr_db = 99.0f;
        }
    } else {
        snr_db = 0.0f;
    }

    return snr_db;
}

/**
 * @brief 3-point quadratic sub-bin peak interpolator.
 * @details Computes sub-bin offset \Delta x = (y_{-1} - y_{+1}) / (2 * (y_{-1} - 2*y_0 + y_{+1})).
 */
static float CFAR_InterpolatePeakOffset(float y_left, float y_center, float y_right)
{
    float offset = 0.0f;
    const float denom = 2.0f * (y_left - (2.0f * y_center) + y_right);

    if (fabsf(denom) > 1e-6f) {
        offset = (y_left - y_right) / denom;
        if (offset > 0.5f) {
            offset = 0.5f;
        } else if (offset < -0.5f) {
            offset = -0.5f;
        } else {
            /* offset within [-0.5, 0.5] */
        }
    }

    return offset;
}

/**
 * @brief Execute 1D Cell-Averaging CFAR detection.
 * @details Implements REQ-002, REQ-003.
 */
CFAR_Status_t CFAR_Detect1D(const float * const signal,
                            uint16_t signal_len,
                            const CFAR_Config_t * const config,
                            CFAR_Result_t * const result)
{
    CFAR_Status_t status = CFAR_STATUS_OK;
    uint32_t window_margin = 0U;
    uint32_t total_train_cells = 0U;
    float global_noise_sum = 0.0f;
    uint32_t global_noise_count = 0U;

    /* 1. Defensive parameter validation (DO-178C robust defensive design) */
    if ((signal == NULL) || (config == NULL) || (result == NULL)) {
        return CFAR_STATUS_INVALID_PARAM;
    }

    window_margin = (uint32_t)config->train_cells + (uint32_t)config->guard_cells;
    total_train_cells = 2U * (uint32_t)config->train_cells;

    if (signal_len > CFAR_MAX_SIGNAL_LEN) {
        return CFAR_STATUS_INVALID_PARAM;
    }
    if ((uint32_t)signal_len <= (2U * window_margin)) {
        return CFAR_STATUS_BUFFER_TOO_SMALL;
    }
    if (CFAR_Init(config) != CFAR_STATUS_OK) {
        return CFAR_STATUS_INVALID_PARAM;
    }

    /* 2. Initialize result structure */
    result->num_targets = 0U;
    result->mean_noise_level = 0.0f;
    result->overflow_flag = false;

    /* 3. Sliding window over valid CUT range */
    const uint32_t cut_start = window_margin;
    const uint32_t cut_end = (uint32_t)signal_len - window_margin;

    for (uint32_t cut = cut_start; cut < cut_end; ++cut) {
        float train_sum = 0.0f;

        /* Sum left training cells */
        const uint32_t left_start = cut - window_margin;
        const uint32_t left_end = cut - (uint32_t)config->guard_cells;
        for (uint32_t i = left_start; i < left_end; ++i) {
            train_sum += signal[i];
        }

        /* Sum right training cells */
        const uint32_t right_start = cut + (uint32_t)config->guard_cells + 1U;
        const uint32_t right_end = cut + window_margin + 1U;
        for (uint32_t i = right_start; i < right_end; ++i) {
            train_sum += signal[i];
        }

        /* Calculate local noise floor \mu[i] */
        const float local_noise = train_sum / (float)total_train_cells;
        global_noise_sum += local_noise;
        global_noise_count++;

        /* Compute adaptive threshold T[i] = \alpha * \mu[i] + T_floor */
        float threshold = (config->threshold_factor * local_noise) + config->noise_floor_min;

        const float cut_val = signal[cut];

        /* Peak detection & local maximum assertion */
        if (cut_val > threshold) {
            const float val_left = signal[cut - 1U];
            const float val_right = signal[cut + 1U];

            /* Only record if CUT is a local maximum to avoid duplicate trigger on shoulder */
            if ((cut_val >= val_left) && (cut_val >= val_right)) {
                if (result->num_targets < CFAR_MAX_DETECTIONS) {
                    CFAR_Detection_t * const tgt = &result->targets[result->num_targets];
                    tgt->range_bin = (uint16_t)cut;
                    tgt->power_linear = cut_val;
                    tgt->sub_bin_offset = CFAR_InterpolatePeakOffset(val_left, cut_val, val_right);
                    tgt->snr_estimate_db = CFAR_CalculateSNR_dB(cut_val, local_noise);
                    result->num_targets++;
                } else {
                    result->overflow_flag = true;
                    status = CFAR_STATUS_OVERFLOW;
                }
            }
        }
    }

    if (global_noise_count > 0U) {
        result->mean_noise_level = global_noise_sum / (float)global_noise_count;
    }

    return status;
}
