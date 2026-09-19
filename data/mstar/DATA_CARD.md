# MSTAR Data Card (Veri Kartı)

## 1. Veri Seti Tanımı
- **Adı:** MSTAR (Moving and Stationary Target Acquisition and Recognition) SAR Clutter and Target Dataset
- **Sürüm:** Standart 3-Sınıflı SOC (Standard Operating Condition) Kıyaslama Kümesi
- **Hedef Sınıfları (Bilinen):**
  1. `T72`: T-72 Ana Muharebe Tankı (Etiket 0)
  2. `BMP2`: BMP-2 Zırhlı Muharebe Aracı (Etiket 1)
  3. `BTR70`: BTR-70 Zırhlı Personel Taşıyıcı (Etiket 2)
- **Hedef Sınıfları (Dağılım Dışı / Bilinmeyen - OOD):**
  - `2S1`, `BRDM2`, `BTR60`, `D7`, `T62`, `ZIL131`, `ZSU_23_4`

## 2. Sensör ve Toplanma Parametreleri
- **Radar Frekansı:** X-band (~9.6 GHz)
- **Radar Modu:** Spotlight SAR
- **Polarizasyon:** HH (Yatay iletim, yatay alım)
- **Uzamsal Çözünürlük:** Menzilde 0.3 m x Azimutta 0.3 m
- **Görüntü Boyutu:** 128 x 128 piksel
- **Depresyon Açıları:**
  - Eğitim Seti: 17° depresyon açısı (tüm 360° en-boy açılarında hedefler)
  - Test Seti: 15° depresyon açısı (farklı depresyon açısı altında genelleşme doğrulaması)

## 3. Örnek Sayıları ve Dağılım
| Sınıf Adı | Etiket | Eğitim (17°) | Test (15°) | Toplam |
|---|:---:|:---:|:---:|:---:|
| **T-72** | 0 | 232 | 196 | 428 |
| **BMP-2** | 1 | 233 | 195 | 428 |
| **BTR-70** | 2 | 233 | 196 | 429 |
| **Toplam Hedef** | — | **698** | **587** | **1,285** |
| **OOD / Bilinmeyen** | — | 0 | 1,838 | 1,838 |

## 4. Önişleme ve Normalizasyon
- Piksel değerleri $[0, 255]$ aralığından $[0.0, 1.0]$ aralığına normalize edilir: $I_{\text{norm}} = I / 255.0$.
- Model giriş boyutu: $(B, 1, 128, 128)$ tek kanal tensor.
- Veri artırma (Data Augmentation): Rastgele yatay/dikey çevirme (SAR saçılma simetrisi), rastgele küçük dönüşler ($\pm 10^\circ$), ve rastgele kırpma/kaydırma.

## 5. Bilinen Sınırlamalar
- **Sentetik-Gerçek Alan Farkı (Domain Gap):** Modül 1'de üretilen sentetik nokta-saçıcı SAR görüntüleri ile gerçek X-band speckle ve clutter içeren MSTAR görüntüleri arasında dağılım farkı mevcuttur.
- **Speckle Gürültüsü:** Gerçek radar görüntülerinde Rayleigh/Gamma dağılımlı speckle gürültüsü bulunur.
- **Sabit Zemin (Grass/Clutter):** MSTAR çipleri hedefin etrafında çimen/toprak arka planı içerir. Modelin aracı mı yoksa gölge ve arka plan izlerini mi öğrendiği Grad-CAM ile denetlenmelidir.
