/**
 * @file fft_mock.h
 * @brief Deterministic Bare-Metal Radix-2 Fast Fourier Transform Preprocessor.
 * @details Conforms to CMSIS-DSP style embedded function prototypes without
 *          dynamic memory allocation or recursion. MISRA-C:2012 compliant.
 */

#ifndef FFT_MOCK_H
#define FFT_MOCK_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Maximum supported Radix-2 FFT length */
#define FFT_MAX_LENGTH          (1024U)

/**
 * @brief Return status codes for FFT operations.
 */
typedef enum {
    FFT_STATUS_OK        = 0x00U,
    FFT_STATUS_INVPARAM  = 0x01U,
    FFT_STATUS_NON_POW2  = 0x02U,
    FFT_STATUS_OVERFLOW  = 0x03U
} FFT_Status_t;

/**
 * @brief Single-precision complex number representation.
 */
typedef struct {
    float real; /**< Real in-phase component (I) */
    float imag; /**< Imaginary quadrature component (Q) */
} Complex32_t;

/**
 * @brief Forward Radix-2 Decimation-In-Time (DIT) Fast Fourier Transform.
 * @param[in,out] buffer Pointer to complex array of length elements (in-place).
 * @param[in]     length FFT transform length (must be a power of 2 <= FFT_MAX_LENGTH).
 * @return FFT_STATUS_OK on success, or error status code.
 */
FFT_Status_t FFT_Radix2_Forward(Complex32_t * const buffer, uint16_t length);

/**
 * @brief Inverse Radix-2 Decimation-In-Time (DIT) Fast Fourier Transform.
 * @param[in,out] buffer Pointer to complex array of length elements (in-place).
 * @param[in]     length FFT transform length (must be a power of 2 <= FFT_MAX_LENGTH).
 * @return FFT_STATUS_OK on success, or error status code.
 */
FFT_Status_t FFT_Radix2_Inverse(Complex32_t * const buffer, uint16_t length);

/**
 * @brief Compute power spectrum |X[k]|^2 = real^2 + imag^2 for CFAR detection.
 * @param[in]  complex_input Pointer to complex frequency spectrum array.
 * @param[out] power_output  Pointer to real power array.
 * @param[in]  length        Array length.
 * @return FFT_STATUS_OK on success, or FFT_STATUS_INVPARAM.
 */
FFT_Status_t FFT_ComputePowerSpectrum(const Complex32_t * const complex_input,
                                      float * const power_output,
                                      uint16_t length);

#ifdef __cplusplus
}
#endif

#endif /* FFT_MOCK_H */
