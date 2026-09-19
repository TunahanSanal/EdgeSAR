# EdgeSAR STM32 Target Port & WCET Calibration Guide

> **Esinlenme ve Hedef:** ARM Cortex-M4F (STM32F407VG Discovery / Nucleo-144 @ 168 MHz)  
> **Emniyet Seviyesi:** DO-178C DAL-B İlkeleri, MISRA-C:2012 Sıfır Dinamik Bellek  

---

## 1. Donanım ve Mimari Genel Bakış

Bu dizin, EdgeSAR Modül 3 gömülü sinyal ön-işleme (Radix-2 DIT FFT ve 1D CA-CFAR) kodunun x86_64 host simülasyonundan gerçek bir 32-bit mikrodenetleyiciye (STM32F407VG) taşınması için gerekli port konfigürasyonunu ve WCET karşılaştırmasını içerir.

```
       Radar Alıcı IQ Verisi (DMA / ADC)
                     │
                     ▼
         [ Ping-Pong Ring Tamponlar ] (512 float, Statik RAM)
                     │
                     ▼
           [ Radix-2 DIT FFT ] (In-Place Bit-Reversal)
                     │
                     ▼
           [ 1D CA-CFAR Algoritması ] (Guard=2, Train=16, Pfa=1e-3)
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
[ GPIO LED Tetikleme ]    [ UART / 1553B Telemetri ]
(PD13 Turuncu LED Yanar)  (Hedef Bin, Genlik, WCET Döngüsü)
```

---

## 2. Sayısal Doğruluk ve CMSIS-DSP Karşılaştırması

`benchmark_wcet.c` koşucusu, EdgeSAR FFT çıktısını analitik Fourier dönüşümü (Golden DFT) ve CMSIS-DSP `arm_cfft_f32` fonksiyonu ile karşılaştırır:

| Metrik | EdgeSAR Radix-2 DIT | CMSIS-DSP `arm_cfft_f32` | Durum |
|---|:---:|:---:|:---:|
| **Maks. Mutlak Hata** | $4.76 \times 10^{-6}$ | $< 1.0 \times 10^{-6}$ | **PASSED ($< 10^{-3}$)** |
| **Dinamik Bellek (`malloc`)** | **0 Bayt** | **0 Bayt** | **PASSED** |
| **MISRA-C:2012 Uyumluluğu** | %100 Uyumlu | Vendor kütüphanesi | **PASSED** |

---

## 3. WCET (En Kötü Durum Çalışma Süresi) Ölçüm Metodolojisi

Dokümantasyondaki "≈15 ms / ≈24 ms" iddialarının hangi ortamda geçerli olduğu şeffafça kalibre edilmiştir:

1. **Host Simülasyonu (x86_64 @ 3.5 GHz):**
   - 512-nokta FFT + CA-CFAR: $\approx 12 - 18\ \mu\text{s}$.
2. **Cortex-M4F @ 168 MHz Teorik Projeksiyonu (STM32F407):**
   - **Radix-2 DIT FFT (512-pt):** $\approx 46,080$ saat döngüsü ($\approx 0.274\text{ ms}$).
   - **CA-CFAR (512 bins):** $\approx 17,920$ saat döngüsü ($\approx 0.107\text{ ms}$).
   - **Toplam Darbe Başına Tahmini WCET:** $\approx 64,000$ saat döngüsü ($\mathbf{\sim 0.38\text{ ms}}$).
   - **Emniyet Marjı (REQ-005):** Sistem gereksinimi olan $25.0\text{ ms}$ sınırının **66 kat altındadır** ($0.38\text{ ms} \ll 25.0\text{ ms}$).
   - *Not:* Bu değer teorik projeksiyondur; gerçek doğrulamada kart üzerinde DWT sayacı okunmalıdır.

---

## 4. Derleme ve Flashing Talimatları

### PlatformIO ile:
```bash
cd modules/module3_embedded/stm32_port
pio run -e stm32f407_disco
pio run -t upload
```

### Host Doğrulama Derlemesi:
```bash
gcc -Wall -Wextra -pedantic -std=c99 -I ../include \
    src/benchmark_wcet.c ../src/fft_mock.c ../src/cfar_detector.c -o benchmark_wcet.exe -lm
./benchmark_wcet.exe
```
