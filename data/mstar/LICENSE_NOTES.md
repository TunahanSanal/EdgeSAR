# MSTAR Dataset — Lisans ve Kullanım Notları (License & Terms of Use)

## 1. Veri Seti Kökeni
- **Proje:** MSTAR (Moving and Stationary Target Acquisition and Recognition)
- **Sağlayıcı:** Defense Advanced Research Projects Agency (DARPA) & Air Force Research Laboratory (AFRL)
- **Toplayan / Sensör:** Sandia National Laboratories (X-band SAR sensörü, 0.3m x 0.3m çözünürlük, Spotlight modu)
- **Yayın Amacı:** Kamuya açık akademik ve bilimsel SAR-ATR algoritma araştırmaları ve kıyaslamaları (benchmarking).

## 2. Kullanım Şartları ve Kısıtlamalar
- **Kullanım Amacı:** Bu veri seti yalnızca bilimsel araştırma, eğitim ve akademik portföy/kıyaslama amacıyla kullanılmaktadır.
- **Kısıtlar:** Ticari satışa konu edilemez, operasyonel askeri hedefleme amaçlı kullanılamaz.
- **Kamu Erişimi:** Veri seti, Sandia National Laboratories ve AFRL Sensor Data Management System (SDMS) tarafından kamuya açık olarak sunulmuş, akademik camiada de-facto standart referans veri seti olarak kabul edilmiştir.

## 3. Depodaki Alt Küme
Bu depoda MSTAR veri setinin standart 3-sınıflı hedef tanıma alt kümesi (T-72 ana muharebe tankı, BMP-2 zırhlı muharebe aracı, BTR-70 zırhlı personel taşıyıcı) ve dağılım dışı (OOD) test için 7 adet bilinmeyen araç sınıfı (2S1, BRDM-2, BTR-60, D7, T-62, ZIL-131, ZSU-23-4) bulunmaktadır.

- **Eğitim (Depresyon Açısı 17°):** 698 görüntü çipi (BMP-2: 233, BTR-70: 233, T-72: 232)
- **Test (Depresyon Açısı 15°):** 587 görüntü çipi (BMP-2: 195, BTR-70: 196, T-72: 196)
- **OOD / Bilinmeyen Hedefler:** 1,838 görüntü çipi
- **Format:** 128x128 piksel, 8-bit / tek kanallı gri seviye radar genlik çipleri
