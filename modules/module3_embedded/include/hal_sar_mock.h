/**
 * @file hal_sar_mock.h
 * @brief Hardware Abstraction Layer (HAL) Mock Interface for Embedded SAR Preprocessing.
 * @details Simulates STM32F4/F7/H7 microcontroller DMA, ADC/SPI double-buffering,
 *          and interrupt service routines (ISRs) on host environment.
 *          Compliant with MISRA-C:2012 guidelines.
 */

#ifndef HAL_SAR_MOCK_H
#define HAL_SAR_MOCK_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** DMA ping-pong buffer size (samples per full frame) */
#define SAR_DMA_BUFFER_SIZE       (2048U)
/** Half buffer threshold for ping-pong double buffering */
#define SAR_DMA_HALF_BUFFER_SIZE  (SAR_DMA_BUFFER_SIZE / 2U)

/**
 * @brief Return status codes for HAL operations.
 */
typedef enum {
    HAL_SAR_OK       = 0x00U,
    HAL_SAR_ERROR    = 0x01U,
    HAL_SAR_BUSY     = 0x02U,
    HAL_SAR_TIMEOUT  = 0x03U,
    HAL_SAR_INVPARAM = 0x04U
} HAL_SAR_Status_t;

/**
 * @brief Peripheral state machine states.
 */
typedef enum {
    HAL_SAR_STATE_RESET  = 0x00U,
    HAL_SAR_STATE_READY  = 0x01U,
    HAL_SAR_STATE_BUSY   = 0x02U,
    HAL_SAR_STATE_ERROR  = 0x03U
} HAL_SAR_State_t;

/**
 * @brief DMA transfer progress indicator.
 */
typedef enum {
    SAR_DMA_FLAG_NONE     = 0x00U,
    SAR_DMA_FLAG_HALF     = 0x01U,
    SAR_DMA_FLAG_COMPLETE = 0x02U
} SAR_DMA_Flag_t;

/**
 * @brief Peripheral handle structure matching STM32 HAL driver patterns.
 */
typedef struct SAR_HandleTypeDef {
    HAL_SAR_State_t state;                           /**< Current state machine state */
    uint16_t        dma_buffer[SAR_DMA_BUFFER_SIZE]; /**< Double-buffered DMA stream */
    uint16_t        buffer_len;                      /**< Length of active transfer */
    volatile bool   half_transfer_complete;          /**< Ping buffer ready flag */
    volatile bool   full_transfer_complete;          /**< Pong buffer ready flag */
    uint32_t        error_code;                      /**< Hardware error bitfield */
    uint32_t        overrun_count;                   /**< Detected buffer overrun count */
} SAR_HandleTypeDef;

/**
 * @brief Initialize SAR HAL peripheral and reset internal state.
 * @param[in,out] hsar Pointer to peripheral handle.
 * @return HAL_SAR_OK on success, or HAL_SAR_INVPARAM if handle is NULL.
 */
HAL_SAR_Status_t HAL_SAR_Init(SAR_HandleTypeDef * const hsar);

/**
 * @brief De-initialize SAR HAL peripheral and clear buffer memory.
 * @param[in,out] hsar Pointer to peripheral handle.
 * @return HAL_SAR_OK on success.
 */
HAL_SAR_Status_t HAL_SAR_DeInit(SAR_HandleTypeDef * const hsar);

/**
 * @brief Start non-blocking circular DMA acquisition from simulated radar front-end.
 * @param[in,out] hsar       Pointer to peripheral handle.
 * @param[in]     src_stream Pointer to incoming digitized radar samples.
 * @param[in]     length     Number of samples to stream (must be <= SAR_DMA_BUFFER_SIZE).
 * @return HAL_SAR_OK on initiation, HAL_SAR_BUSY if already running, or error.
 */
HAL_SAR_Status_t HAL_SAR_ReceiveDMA(SAR_HandleTypeDef * const hsar,
                                    const uint16_t * const src_stream,
                                    uint16_t length);

/**
 * @brief Half-transfer complete callback (ISR context).
 * @param[in,out] hsar Pointer to peripheral handle.
 */
void HAL_SAR_RxHalfCpltCallback(SAR_HandleTypeDef * const hsar);

/**
 * @brief Full-transfer complete callback (ISR context).
 * @param[in,out] hsar Pointer to peripheral handle.
 */
void HAL_SAR_RxCpltCallback(SAR_HandleTypeDef * const hsar);

/**
 * @brief Query current state machine status.
 * @param[in] hsar Pointer to peripheral handle.
 * @return Current HAL_SAR_State_t.
 */
HAL_SAR_State_t HAL_SAR_GetState(const SAR_HandleTypeDef * const hsar);

/**
 * @brief Reset DMA transfer event flags after buffer processing.
 * @param[in,out] hsar Pointer to peripheral handle.
 */
void HAL_SAR_ClearTransferFlags(SAR_HandleTypeDef * const hsar);

#ifdef __cplusplus
}
#endif

#endif /* HAL_SAR_MOCK_H */
