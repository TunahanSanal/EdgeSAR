/**
 * @file cfar_detector.h
 * @brief Safety-Critical CA-CFAR 1D Detector for SAR Radar Video Preprocessing.
 * @details Adheres strictly to MISRA-C:2012 guidelines and DO-178C Level B rigor.
 *          Zero dynamic memory allocation; deterministic bounded loop counts;
 *          full input parameter boundary validation.
 */

#ifndef CFAR_DETECTOR_H
#define CFAR_DETECTOR_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Maximum allowed detections stored in static output buffer (MISRA Rule 21.3 compliant) */
#define CFAR_MAX_DETECTIONS       (64U)
/** Maximum supported signal array length */
#define CFAR_MAX_SIGNAL_LEN        (2048U)
/** Absolute minimum allowed training cells on each side */
#define CFAR_MIN_TRAIN_CELLS       (2U)
/** Absolute maximum allowed training cells on each side */
#define CFAR_MAX_TRAIN_CELLS       (64U)
/** Absolute maximum allowed guard cells on each side */
#define CFAR_MAX_GUARD_CELLS       (16U)

/**
 * @brief Status return codes for CFAR operations.
 */
typedef enum {
    CFAR_STATUS_OK               = 0x00U,
    CFAR_STATUS_INVALID_PARAM    = 0x01U,
    CFAR_STATUS_BUFFER_TOO_SMALL = 0x02U,
    CFAR_STATUS_OVERFLOW         = 0x03U
} CFAR_Status_t;

/**
 * @brief Configuration parameters for CA-CFAR detector.
 */
typedef struct {
    uint16_t train_cells;      /**< Number of training cells on each side (N_T) */
    uint16_t guard_cells;      /**< Number of guard cells on each side (N_G) */
    float    threshold_factor; /**< Multiplier alpha derived from target P_fa */
    float    noise_floor_min;  /**< Minimum linear noise floor cutoff */
} CFAR_Config_t;

/**
 * @brief Individual detected target descriptor.
 */
typedef struct {
    uint16_t range_bin;        /**< Range bin index of detected target peak */
    float    sub_bin_offset;   /**< Sub-bin peak offset via parabolic interpolation */
    float    power_linear;     /**< Peak power magnitude */
    float    snr_estimate_db;  /**< Estimated SNR in decibels relative to local noise */
} CFAR_Detection_t;

/**
 * @brief Static output container for CFAR detection results.
 */
typedef struct {
    CFAR_Detection_t targets[CFAR_MAX_DETECTIONS]; /**< Static detection records */
    uint16_t         num_targets;                  /**< Total detected targets */
    float            mean_noise_level;             /**< Global average noise floor */
    bool             overflow_flag;                /**< Set if detections exceeded buffer */
} CFAR_Result_t;

/**
 * @brief Initialize CFAR detector configuration with safety parameter checks.
 * @param[in] config Pointer to configuration struct.
 * @return CFAR_STATUS_OK if parameters are valid; CFAR_STATUS_INVALID_PARAM otherwise.
 */
CFAR_Status_t CFAR_Init(const CFAR_Config_t * const config);

/**
 * @brief Execute 1D Cell-Averaging CFAR detection across a linear power signal.
 * @param[in]  signal      Pointer to input signal magnitude/power array.
 * @param[in]  signal_len  Number of elements in signal array.
 * @param[in]  config      Pointer to valid CFAR configuration.
 * @param[out] result      Pointer to output result container.
 * @return CFAR_STATUS_OK on success, or error status code.
 */
CFAR_Status_t CFAR_Detect1D(const float * const signal,
                            uint16_t signal_len,
                            const CFAR_Config_t * const config,
                            CFAR_Result_t * const result);

/**
 * @brief Estimate local Signal-to-Noise Ratio (SNR) in decibels.
 * @param[in] peak_power  Linear peak power.
 * @param[in] noise_power Linear local noise estimate.
 * @return SNR in dB clamped to [0.0, 99.0].
 */
float CFAR_CalculateSNR_dB(float peak_power, float noise_power);

#ifdef __cplusplus
}
#endif

#endif /* CFAR_DETECTOR_H */
