/**
 * @file test_hal.c
 * @brief Unit tests for STM32 HAL Mock Peripheral Interface.
 * @details Traceable to DO-178C requirements: REQ-004, REQ-005.
 */

#include "unity.h"
#include "hal_sar_mock.h"
#include <string.h>

void test_HAL_SAR_InitAndDeInit(void)
{
    SAR_HandleTypeDef hsar;

    /* NULL check */
    TEST_ASSERT_EQUAL_INT(HAL_SAR_INVPARAM, HAL_SAR_Init(NULL));
    TEST_ASSERT_EQUAL_INT(HAL_SAR_INVPARAM, HAL_SAR_DeInit(NULL));

    /* Valid Init */
    TEST_ASSERT_EQUAL_INT(HAL_SAR_OK, HAL_SAR_Init(&hsar));
    TEST_ASSERT_EQUAL_INT(HAL_SAR_STATE_READY, HAL_SAR_GetState(&hsar));
    TEST_ASSERT_FALSE(hsar.half_transfer_complete);
    TEST_ASSERT_FALSE(hsar.full_transfer_complete);
    TEST_ASSERT_EQUAL_UINT(0U, hsar.overrun_count);

    /* Valid DeInit */
    TEST_ASSERT_EQUAL_INT(HAL_SAR_OK, HAL_SAR_DeInit(&hsar));
    TEST_ASSERT_EQUAL_INT(HAL_SAR_STATE_RESET, HAL_SAR_GetState(&hsar));
}

void test_HAL_SAR_ReceiveDMA_TransferFlow(void)
{
    SAR_HandleTypeDef hsar;
    uint16_t stream[512];

    for (uint16_t i = 0U; i < 512U; ++i) {
        stream[i] = i + 10U;
    }

    (void)HAL_SAR_Init(&hsar);

    const HAL_SAR_Status_t status = HAL_SAR_ReceiveDMA(&hsar, stream, 512U);

    TEST_ASSERT_EQUAL_INT(HAL_SAR_OK, status);
    /* Both half and full callbacks fired in mock */
    TEST_ASSERT_TRUE(hsar.half_transfer_complete);
    TEST_ASSERT_TRUE(hsar.full_transfer_complete);
    /* Returned to READY state */
    TEST_ASSERT_EQUAL_INT(HAL_SAR_STATE_READY, HAL_SAR_GetState(&hsar));

    /* Verify payload data copied accurately */
    TEST_ASSERT_EQUAL_UINT(stream[0], hsar.dma_buffer[0]);
    TEST_ASSERT_EQUAL_UINT(stream[255], hsar.dma_buffer[255]);
    TEST_ASSERT_EQUAL_UINT(stream[511], hsar.dma_buffer[511]);

    /* Test clear transfer flags */
    HAL_SAR_ClearTransferFlags(&hsar);
    TEST_ASSERT_FALSE(hsar.half_transfer_complete);
    TEST_ASSERT_FALSE(hsar.full_transfer_complete);
}

void test_HAL_SAR_ReceiveDMA_BusyStateAndOverrun(void)
{
    SAR_HandleTypeDef hsar;
    uint16_t stream[128];
    (void)memset(stream, 0, sizeof(stream));

    (void)HAL_SAR_Init(&hsar);
    /* Manually force busy state to simulate ongoing DMA processing */
    hsar.state = HAL_SAR_STATE_BUSY;

    /* Next trigger while busy must return HAL_SAR_BUSY and increment overrun */
    const HAL_SAR_Status_t status = HAL_SAR_ReceiveDMA(&hsar, stream, 128U);

    TEST_ASSERT_EQUAL_INT(HAL_SAR_BUSY, status);
    TEST_ASSERT_EQUAL_UINT(1U, hsar.overrun_count);
}

void test_HAL_SAR_ReceiveDMA_OverflowProtection(void)
{
    SAR_HandleTypeDef hsar;
    uint16_t stream[10];

    (void)HAL_SAR_Init(&hsar);

    /* Transfer requested length exceeding static DMA buffer limit */
    const HAL_SAR_Status_t status = HAL_SAR_ReceiveDMA(&hsar, stream, SAR_DMA_BUFFER_SIZE + 10U);

    TEST_ASSERT_EQUAL_INT(HAL_SAR_ERROR, status);
    TEST_ASSERT_TRUE((hsar.error_code & 0x01U) != 0U);
}
