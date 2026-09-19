# Open SAR / Sentinel-1 Civil SAR Dataset — Data Card

## 1. Veri Seti Tanımı
- **Adı:** EdgeSAR Sivil Açık SAR ve Kıyı Gözlem Veri Seti (Open SAR / Sentinel-1 Maritime Sample)
- **Kapsam:** Kıyı gözetleme, açık deniz gemi tespiti (vessel detection) ve heterojen deniz clutter'ı (K-dağılımı).
- **Format:** Single Look Complex (SLC) / Kompleks I/Q Matrisi `(512 x 512, complex64)`
- **Dosya Konumu:** `data/open_sar/sentinel1_maritime_sample.npy`

## 2. Sensör ve Radar Parametreleri
- **Esinlenilen Radar:** Sentinel-1 C-Band (~5.405 GHz) Stripmap / IW modları.
- **Polarizasyon:** VV veya VH.
- **Clutter Dağılımı:** K-dağılımlı deniz yüzeyi (Bileşik Gauss / Gamma doku saçılması).
- **Hedefler:** 4 adet sivil deniz aracı (konteyner gemisi, petrol tankeri, balıkçı teknesi, kargo gemisi) belirgin parlak saçıcı kümeleriyle.

## 3. Odaklama ve Kalite Değerlendirme Metrikleri
- **Shannon Görüntü Entropisi ($S$):** Odak keskinliği göstergesi.
  $$S = -\sum_{i,j} p_{i,j} \ln(p_{i,j} + \epsilon), \quad p_{i,j} = \frac{I_{i,j}}{\sum I}$$
- **Görüntü Kontrastı ($C$):** Enerji tepe yoğunlaşması göstergesi.
  $$C = \frac{\sigma(I)}{\mu(I)}$$
- **PAPR (Peak-to-Average Power Ratio):** Tepe gücün ortalama arka plan clutter gücüne oranı (dB).

## 4. Kullanım Amacı
- Modül 1 (RDA sinyal işleme) ve Modül 3 (CFAR hedef tespit) algoritmalarını sivil arama-kurtarma ve deniz izleme senaryosunda doğrulamak.
- Sistemin askeri hedeflerin ötesinde sivil afet/deniz gözetimine genelleşebilirliğini göstermek.
