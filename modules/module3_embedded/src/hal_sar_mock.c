/**
 * @file hal_sar_mock.c
 * @brief Hardware Abstraction Layer Mock Implementation for STM32 Radar DMA.
 * @details Conforms to MISRA-C:2012 guidelines and DO-178C Level B requirements.
 *          Maps to requirements: REQ-004, REQ-005.
 */

#include "hal_sar_mock.h"
#include <string.h>
#include <stddef.h>

/**
 * @brief Initialize SAR HAL peripheral and configure initial state.
 * @details Implements REQ-004.
 */
HAL_SAR_Status_t HAL_SAR_Init(SAR_HandleTypeDef * const hsar)
{
    if (hsar == NULL) {
        return HAL_SAR_INVPARAM;
    }

    hsar->state = HAL_SAR_STATE_READY;
    hsar->buffer_len = 0U;
    hsar->half_transfer_complete = false;
    hsar->full_transfer_complete = false;
    hsar->error_code = 0U;
    hsar->overrun_count = 0U;

    (void)memset(hsar->dma_buffer, 0, sizeof(hsar->dma_buffer));

    return HAL_SAR_OK;
}

/**
 * @brief De-initialize SAR HAL peripheral.
 * @details Implements REQ-004.
 */
HAL_SAR_Status_t HAL_SAR_DeInit(SAR_HandleTypeDef * const hsar)
{
    if (hsar == NULL) {
        return HAL_SAR_INVPARAM;
    }

    hsar->state = HAL_SAR_STATE_RESET;
    hsar->buffer_len = 0U;
    hsar->half_transfer_complete = false;
    hsar->full_transfer_complete = false;

    return HAL_SAR_OK;
}

/**
 * @brief Start DMA reception of simulated radar stream.
 * @details Implements REQ-004, REQ-005.
 */
HAL_SAR_Status_t HAL_SAR_ReceiveDMA(SAR_HandleTypeDef * const hsar,
                                    const uint16_t * const src_stream,
                                    uint16_t length)
{
    if ((hsar == NULL) || (src_stream == NULL) || (length == 0U)) {
        return HAL_SAR_INVPARAM;
    }

    if (length > SAR_DMA_BUFFER_SIZE) {
        hsar->error_code |= 0x01U; /* Buffer overflow error */
        return HAL_SAR_ERROR;
    }

    if (hsar->state != HAL_SAR_STATE_READY) {
        hsar->overrun_count++;
        return HAL_SAR_BUSY;
    }

    hsar->state = HAL_SAR_STATE_BUSY;
    hsar->buffer_len = length;
    hsar->half_transfer_complete = false;
    hsar->full_transfer_complete = false;

    /* Copy first half (ping buffer) */
    const uint16_t half_len = length / 2U;
    (void)memcpy(&hsar->dma_buffer[0], &src_stream[0], (size_t)half_len * sizeof(uint16_t));
    HAL_SAR_RxHalfCpltCallback(hsar);

    /* Copy second half (pong buffer) */
    const uint16_t second_half_len = length - half_len;
    (void)memcpy(&hsar->dma_buffer[half_len], &src_stream[half_len], (size_t)second_half_len * sizeof(uint16_t));
    HAL_SAR_RxCpltCallback(hsar);

    return HAL_SAR_OK;
}

/**
 * @brief Half-transfer complete callback (ISR context).
 * @details Implements REQ-005.
 */
void HAL_SAR_RxHalfCpltCallback(SAR_HandleTypeDef * const hsar)
{
    if (hsar != NULL) {
        hsar->half_transfer_complete = true;
    }
}

/**
 * @brief Full-transfer complete callback (ISR context).
 * @details Implements REQ-005.
 */
void HAL_SAR_RxCpltCallback(SAR_HandleTypeDef * const hsar)
{
    if (hsar != NULL) {
        hsar->full_transfer_complete = true;
        hsar->state = HAL_SAR_STATE_READY;
    }
}

/**
 * @brief Query current state machine status.
 * @details Implements REQ-004.
 */
HAL_SAR_State_t HAL_SAR_GetState(const SAR_HandleTypeDef * const hsar)
{
    if (hsar == NULL) {
        return HAL_SAR_STATE_ERROR;
    }
    return hsar->state;
}

/**
 * @brief Reset transfer event flags.
 * @details Implements REQ-005.
 */
void HAL_SAR_ClearTransferFlags(SAR_HandleTypeDef * const hsar)
{
    if (hsar != NULL) {
        hsar->half_transfer_complete = false;
        hsar->full_transfer_complete = false;
    }
}
