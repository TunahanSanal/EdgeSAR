/**
 * @file fft_mock.c
 * @brief Bare-Metal Radix-2 Decimation-in-Time Fast Fourier Transform.
 * @details Conforms to MISRA-C:2012 guidelines and DO-178C Level B requirements.
 *          In-place computation; zero dynamic memory allocation; deterministic bounds.
 *          Maps to requirements: REQ-006.
 */

#include "fft_mock.h"
#include <math.h>
#include <stddef.h>

#ifndef M_PI
#define M_PI (3.14159265358979323846)
#endif

/**
 * @brief Verify if an integer is a valid power of 2.
 */
static bool FFT_IsPowerOfTwo(uint16_t n)
{
    return ((n > 0U) && ((n & (n - 1U)) == 0U));
}

/**
 * @brief Bit-reversal permutation for in-place Radix-2 FFT.
 */
static void FFT_BitReversal(Complex32_t * const buffer, uint16_t length)
{
    uint32_t j = 0U;

    for (uint32_t i = 0U; i < (uint32_t)length; ++i) {
        if (i < j) {
            const Complex32_t temp = buffer[i];
            buffer[i] = buffer[j];
            buffer[j] = temp;
        }

        uint32_t bit = (uint32_t)length >> 1U;
        while ((bit > 0U) && ((j & bit) != 0U)) {
            j ^= bit;
            bit >>= 1U;
        }
        j ^= bit;
    }
}

/**
 * @brief Core in-place Radix-2 butterfly engine.
 */
static FFT_Status_t FFT_ExecuteCore(Complex32_t * const buffer, uint16_t length, bool inverse)
{
    if ((buffer == NULL) || (length == 0U)) {
        return FFT_STATUS_INVPARAM;
    }
    if (length > FFT_MAX_LENGTH) {
        return FFT_STATUS_INVPARAM;
    }
    if (!FFT_IsPowerOfTwo(length)) {
        return FFT_STATUS_NON_POW2;
    }

    /* 1. Bit-reversal permutation */
    FFT_BitReversal(buffer, length);

    /* 2. Cooley-Tukey butterfly stages */
    const double sign = inverse ? 1.0 : -1.0;

    for (uint32_t len = 2U; len <= (uint32_t)length; len <<= 1U) {
        const double angle = (sign * 2.0 * M_PI) / (double)len;
        const double w_step_real = cos(angle);
        const double w_step_imag = sin(angle);

        const uint32_t half_len = len >> 1U;

        for (uint32_t i = 0U; i < (uint32_t)length; i += len) {
            double w_real = 1.0;
            double w_imag = 0.0;

            for (uint32_t j = 0U; j < half_len; ++j) {
                const uint32_t u_idx = i + j;
                const uint32_t v_idx = i + j + half_len;

                const Complex32_t u = buffer[u_idx];
                const Complex32_t v = buffer[v_idx];

                /* Complex multiplication: v * w */
                const float v_re = (float)((double)v.real * w_real - (double)v.imag * w_imag);
                const float v_im = (float)((double)v.real * w_imag + (double)v.imag * w_real);

                buffer[u_idx].real = u.real + v_re;
                buffer[u_idx].imag = u.imag + v_im;

                buffer[v_idx].real = u.real - v_re;
                buffer[v_idx].imag = u.imag - v_im;

                /* Update twiddle factor */
                const double next_w_real = (w_real * w_step_real) - (w_imag * w_step_imag);
                const double next_w_imag = (w_real * w_step_imag) + (w_imag * w_step_real);
                w_real = next_w_real;
                w_imag = next_w_imag;
            }
        }
    }

    /* 3. Scale by 1/N for inverse FFT */
    if (inverse) {
        const float scale = 1.0f / (float)length;
        for (uint32_t i = 0U; i < (uint32_t)length; ++i) {
            buffer[i].real *= scale;
            buffer[i].imag *= scale;
        }
    }

    return FFT_STATUS_OK;
}

/**
 * @brief Forward Radix-2 Fast Fourier Transform.
 * @details Implements REQ-006.
 */
FFT_Status_t FFT_Radix2_Forward(Complex32_t * const buffer, uint16_t length)
{
    return FFT_ExecuteCore(buffer, length, false);
}

/**
 * @brief Inverse Radix-2 Fast Fourier Transform.
 * @details Implements REQ-006.
 */
FFT_Status_t FFT_Radix2_Inverse(Complex32_t * const buffer, uint16_t length)
{
    return FFT_ExecuteCore(buffer, length, true);
}

/**
 * @brief Compute power spectrum |X[k]|^2.
 * @details Implements REQ-006.
 */
FFT_Status_t FFT_ComputePowerSpectrum(const Complex32_t * const complex_input,
                                      float * const power_output,
                                      uint16_t length)
{
    if ((complex_input == NULL) || (power_output == NULL) || (length == 0U)) {
        return FFT_STATUS_INVPARAM;
    }

    for (uint32_t i = 0U; i < (uint32_t)length; ++i) {
        const float re = complex_input[i].real;
        const float im = complex_input[i].imag;
        power_output[i] = (re * re) + (im * im);
    }

    return FFT_STATUS_OK;
}
