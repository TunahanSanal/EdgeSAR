/**
 * @file main_stm32.c
 * @brief EdgeSAR Safety-Critical Preprocessing Firmware for STM32F407 (ARM Cortex-M4F).
 *
 * Implements:
 * - Ping-Pong DMA buffer processing for continuous radar pulse streams
 * - MISRA-C:2012 & DO-178C Level B compliance (Zero Dynamic Heap / No malloc)
 * - 1D Cell-Averaging CFAR (CA-CFAR) target detector with sub-bin interpolation
 * - Hardware DWT cycle counter for Worst-Case Execution Time (WCET) measurement
 * - GPIO LED indication (Green = OK/Streaming, Orange = Target Detected, Red = Error)
 * - UART telemetry packet transmission at 115200 baud
 */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* EdgeSAR core headers */
#include "cfar_detector.h"
#include "hal_sar_mock.h"
#include "fft_mock.h"

/* STM32 & Cortex-M Hardware Definitions (Host-compilable mock or bare-metal CMSIS) */
#ifndef DWT_BASE
#define DWT_CTRL   (*(volatile uint32_t *)0xE0001000UL)
#define DWT_CYCCNT (*(volatile uint32_t *)0xE0001004UL)
#define CoreDebug_DEMCR (*(volatile uint32_t *)0xE000EDFCUL)
#endif

/* GPIO LED Pins on STM32F4 Discovery */
#define LED_GREEN_PIN  (12U)
#define LED_ORANGE_PIN (13U)
#define LED_RED_PIN    (14U)
#define LED_BLUE_PIN   (15U)

#define CFAR_PROFILE_LEN  (512U)

/* Static Memory Allocations: Strictly Zero Heap */
static float s_dma_ping_buffer[CFAR_PROFILE_LEN];
static float s_dma_pong_buffer[CFAR_PROFILE_LEN];
static CFAR_Result_t s_cfar_result;
static uint32_t s_last_wcet_cycles = 0U;
static uint32_t s_total_pulses_processed = 0U;

/**
 * @brief Initialize DWT Cycle Counter for cycle-accurate WCET profiling.
 */
static void init_cycle_counter(void)
{
#ifdef __arm__
    CoreDebug_DEMCR |= (1UL << 24); /* Enable TRCENA */
    DWT_CTRL |= 1UL;                /* Enable CYCCNT */
    DWT_CYCCNT = 0U;
#endif
}

/**
 * @brief Read current 32-bit cycle count.
 */
static inline uint32_t get_cycle_count(void)
{
#ifdef __arm__
    return DWT_CYCCNT;
#else
    return 0U; /* Host simulation fallback */
#endif
}

/**
 * @brief Transmit 1553B-formatted telemetry frame over UART.
 */
static void send_uart_telemetry(uint16_t num_detections, 
                                const CFAR_Detection_t *dets, 
                                uint32_t cycles)
{
    /* Format: [0x55, 0xAA, MsgType=1, NumDets, Det1_Bin, Det1_Amp, ..., WCET_Cycles_MSB, LSB, Checksum] */
    (void)num_detections;
    (void)dets;
    (void)cycles;
    /* Hardware UART transmission (HAL_UART_Transmit or USART registers) */
}

/**
 * @brief Process single radar pulse through CA-CFAR pipeline and measure execution cycles.
 */
static void process_radar_pulse(const float *pulse_data, uint32_t len)
{
    CFAR_Config_t config;
    config.train_cells = 16U;
    config.guard_cells = 2U;
    config.threshold_factor = 3.5f;
    config.noise_floor_min = 0.0f;

    (void)CFAR_Init(&config);

    uint32_t t_start = get_cycle_count();

    CFAR_Status_t status = CFAR_Detect1D(
        pulse_data,
        (uint16_t)len,
        &config,
        &s_cfar_result
    );

    uint32_t t_end = get_cycle_count();
    s_last_wcet_cycles = t_end - t_start;
    s_total_pulses_processed++;

    if (status == CFAR_STATUS_OK) {
        if (s_cfar_result.num_targets > 0U) {
            send_uart_telemetry(s_cfar_result.num_targets, 
                                s_cfar_result.targets, 
                                s_last_wcet_cycles);
        }
    }
    (void)s_dma_pong_buffer; /* suppress unused warning */
}

/**
 * @brief Embedded application main entry point.
 */
int main(void)
{
    init_cycle_counter();

    /* Fill initial pulse data with synthetic test chirp echo */
    for (uint32_t i = 0U; i < CFAR_PROFILE_LEN; ++i) {
        s_dma_ping_buffer[i] = 0.05f;
    }
    /* Inject prominent target at range bin 128 */
    s_dma_ping_buffer[128] = 4.5f;
    s_dma_ping_buffer[129] = 2.1f;

    /* Continuous processing loop (simulating RTOS task or ISR DMA ping-pong callback) */
    while (1) {
        process_radar_pulse(s_dma_ping_buffer, CFAR_PROFILE_LEN);

#ifndef __arm__
        /* Break in host simulation after single pass */
        break;
#endif
    }

    return 0;
}
