# Synthetic SAR Target Dataset — Data Card (Veri Kartı)

## 1. Veri Kümesi Tanımı
- **Adı:** EdgeSAR Fizik Tabanlı Sentetik Saçıcı Merkez (Attributed Scattering Center) Veri Üreticisi
- **Kapsam:** T-72, BMP-2, BTR-70 hedefleri ve Negatif / Zemin Clutter sınıfı
- **Üretici Modül:** `modules/module2_atr/dataset.py` (`SyntheticSARTargetGenerator`)

## 2. Fiziksel Modelleme İlkeleri
- **Geometri & Saçıcı Noktalar (Attributed Scatterers):**
  - Hedefler kanonik radar saçıcı bileşenleri (taret, namlu/ototop, gövde açılı zırh plakaları, palet tekerlekleri, çift-yüzeyli arka kapı köşe reflektörleri) ile modellenmiştir.
  - 2B Gauss Nokta Yayılım Fonksiyonu (Point Spread Function - PSF) konvolüsyonu ile 0.15 m piksel aralığında çizilir.
- **En-Boy Açısı Bağımlılığı (Aspect Angle Sensitivity):** $\phi \in [0, 360^\circ]$ rastgele dönüş ile radar aydınlatma doğrultusuna göre saçılma genlikleri modüle edilir.
- **Radar Gölgesi (Radar Shadow):** Hedefin arkasında radar ışınlarının ulaşamadığı yönde depresyon açısına bağlı gölge bölgesi oluşturulur.
- **Speckle ve Zemin Clutter:** Rayleigh ve Gamma dağılımlı koherent benek gürültüsü ve rastgele zemin saçıcıları eklenir.

## 3. Sentetik Genişletme Parametreleri (Geliştirilmiş)
- **Örnek Sayısı:** Sınıf başına 1,000 örnek (toplam 3,000 hedef + 1,000 clutter/negatif örnek).
- **Stratified Split:** Eğitim (%70), Doğrulama (%15), Test (%15) dengeli en-boy açıları dağılımıyla.
- **Gürültü Seviyeleri:** SNR $\in [-5\text{ dB}, +25\text{ dB}]$.
- **Dağılım Dışı (OOD) Seti:** Aşırı düşük SNR (< -5 dB), olağandışı depresyon açıları veya yabancı clutter geometrileri.

## 4. Kullanım Amacı
- Gerçek veri kısıtlı olduğunda **ön-eğitim (pre-training)** ve **alan transferi (domain adaptation)**.
- Kontrollü SNR ve açı taraması ile modelin saçıcı merkez duyarlılığını analiz etmek.
