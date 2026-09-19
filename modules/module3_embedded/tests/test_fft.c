/**
 * @file test_fft.c
 * @brief Unit tests for Radix-2 Fast Fourier Transform Preprocessor.
 * @details Traceable to DO-178C requirements: REQ-006.
 */

#include "unity.h"
#include "fft_mock.h"
#include <string.h>

void test_FFT_Radix2_ForwardAndInverseReconstruction(void)
{
    Complex32_t buffer[64];
    float orig_real[64];

    /* Synthesize simple test signal: DC offset + cosine */
    for (uint16_t i = 0U; i < 64U; ++i) {
        orig_real[i] = 1.0f + cosf((2.0f * 3.14159265f * 4.0f * (float)i) / 64.0f);
        buffer[i].real = orig_real[i];
        buffer[i].imag = 0.0f;
    }

    /* 1. Forward FFT */
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_OK, FFT_Radix2_Forward(buffer, 64U));

    /* 2. Inverse FFT */
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_OK, FFT_Radix2_Inverse(buffer, 64U));

    /* 3. Verify exact round-trip reconstruction */
    for (uint16_t i = 0U; i < 64U; ++i) {
        TEST_ASSERT_FLOAT_WITHIN(1e-4f, orig_real[i], buffer[i].real);
        TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, buffer[i].imag);
    }
}

void test_FFT_Radix2_NonPowerOfTwoRejection(void)
{
    Complex32_t buffer[100];

    /* Non-power-of-2 length */
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_NON_POW2, FFT_Radix2_Forward(buffer, 100U));
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_NON_POW2, FFT_Radix2_Inverse(buffer, 50U));

    /* NULL buffer */
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_INVPARAM, FFT_Radix2_Forward(NULL, 64U));

    /* Zero length */
    TEST_ASSERT_EQUAL_INT(FFT_STATUS_INVPARAM, FFT_Radix2_Forward(buffer, 0U));
}

void test_FFT_ComputePowerSpectrum(void)
{
    Complex32_t in[4];
    float out[4];

    in[0].real = 3.0f; in[0].imag = 4.0f; /* 3^2 + 4^2 = 25 */
    in[1].real = 1.0f; in[1].imag = 1.0f; /* 1^2 + 1^2 = 2 */
    in[2].real = 0.0f; in[2].imag = 5.0f; /* 0^2 + 5^2 = 25 */
    in[3].real = 2.0f; in[3].imag = 0.0f; /* 2^2 + 0^2 = 4 */

    TEST_ASSERT_EQUAL_INT(FFT_STATUS_OK, FFT_ComputePowerSpectrum(in, out, 4U));

    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 25.0f, out[0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 2.0f, out[1]);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 25.0f, out[2]);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 4.0f, out[3]);
}
