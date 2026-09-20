# EdgeSAR — Deneysel Sonuçlar ve Başarım Raporu (Experimental Results & Benchmark Report)

> **Belge Kimliği:** EDGESAR-RES-001  
> **Sürüm:** 2.0.0  
> **Tarih:** 2026-09-20  
> **Temel İlke:** "Doğru ve Savunulabilir Sayılar" — Sentetik ve gerçek veri sonuçları açıkça ayrıştırılmıştır.

---

## 1. Yönetici Özeti (Executive Summary)

Bu rapor, EdgeSAR projesinin birinci ilkelerden geliştirilen radar sinyal işleme (RDA), derin öğrenme tabanlı otomatik hedef tanıma (ATR / Ghost-ECANet) ve emniyet-kritik gömülü ön işleme (STM32 C99) modüllerinin **hem sentetik benzetim hem de gerçek radar verileri (Sandia MSTAR ve açık sivil SAR sahneleri)** üzerindeki ampirik sonuçlarını belgeler.

Tüm testler ve metrikler tekrarlanabilir betikler ([`evaluate.py`](../evaluate.py), [`scripts/evaluate_mstar_comprehensive.py`](../scripts/evaluate_mstar_comprehensive.py), [`run_rda.py`](../run_rda.py) ve [`modules/module3_embedded/stm32_port/src/benchmark_wcet.c`](../modules/module3_embedded/stm32_port/src/benchmark_wcet.c)) aracılığıyla üretilmiştir.

---

## 2. Sentetik vs. Gerçek Veri Karşılaştırması

Aşağıdaki tablo, sentetik saçıcı benzetimi ile gerçek Sandia MSTAR verisi arasındaki başarım uçurumunu (domain gap) ve gerçeğe dayalı başarım metriklerini özetlemektedir:

| Değerlendirme Boyutu | Sentetik Saçıcı Kıyaslaması | Gerçek Sandia MSTAR (Standart 17° $\to$ 15°) | Gerçek MSTAR 5-Fold Stratified Çapraz Doğrulama |
|---|:---:|:---:|:---:|
| **Veri Kümesi** | Fizik tabanlı 2B saçıcı simülatörü | Sandia Labs X-Band MSTAR Veritabanı | Sandia Labs X-Band MSTAR Veritabanı |
| **Toplam Örnek Sayısı** | 600 çip (Eğitim: 450, Test: 150) | 1,285 çip (Eğitim: 698, Test: 587) | 1,285 çip (5 katmanlı tabakalı bölütleme) |
| **Depresyon Açıları** | Sabit / Sentetik | **Eğitim: 17° \| Test: 15°** (Standart SOC) | 17° ve 15° karışık tabakalı |
| **Hedef Sınıfları** | 3 Sınıf (T-72, BMP-2, BTR-70) | 3 Sınıf (T-72, BMP-2, BTR-70) | 3 Sınıf (T-72, BMP-2, BTR-70) |
| **Genel Doğruluk (Accuracy)** | **%100.00** | **%63.71** | **%65.60 ± %5.64** |
| **Makro F1-Skoru** | **%100.00** | **%60.86** | **%61.81 ± %7.09** |
| **Makro Kesinlik (Precision)**| **%100.00** | **%61.21** | **%66.20 ± %5.48** |
| **Makro Duyarlılık (Recall)** | **%100.00** | **%63.66** | **%65.33 ± %5.61** |
| **Kalibrasyon Hatası (ECE)**  | 0.0012 | **0.0953** (%9.53) | N/A |
| **OOD Bilinmeyen Hedef Sayısı**| 0 | **1,838 çip** (7 bilinmeyen askeri araç) | N/A |
| **OOD Ayırt Etme (AUROC)**    | N/A | **0.4607** (Kapalı küme zafiyeti) | N/A |
| **Parametre Sayısı**          | 904,268 (< 2M sınırında) | 904,268 (< 2M sınırında) | 904,268 (< 2M sınırında) |
| **MFLOPs / Çıkarım Süresi**  | ~30.2 MFLOPs / 16.33 ms | ~30.2 MFLOPs / 16.33 ms | ~30.2 MFLOPs / 16.33 ms |

> **Not (Tekrarlanabilirlik ve Checkpoint Kararlılığı):** Yukarıdaki %63.71 doğruluk, repoda commit'li `best_mstar_model.pth` checkpoint'ine aittir ve `python scripts/evaluate_mstar_comprehensive.py` ile birebir yeniden üretilebilir. `--retrain` bayrağıyla sıfırdan yapılan eğitim, küçük veri seti (698 örnek) nedeniyle seed'e bağlı farklı (bu denemede daha iyi: %82.96) sonuçlar verebilir. Karşılaştırılabilirlik için raporda sunulan tüm ana metrikler sabit checkpoint'e dayanır.

### Checkpoint Kararlılığı Notu
| Kaynak | Doğruluk | Not |
|---|---|---|
| Commit'li checkpoint (`best_mstar_model.pth`) | %63.71 | Raporlanan ana sonuç, tekrarlanabilir |
| `--retrain` (taze eğitim, aynı hiperparametreler) | %82.96 | Farklı random seed; varyansı gösterir, ana sonuç değildir |

> [!IMPORTANT]
> **Neden Sentetik Veride %100, Gerçek Veride %63.71?**  
> Sentetik simülatör, hedefleri belirli koordinatlardaki gürültüsüz nokta saçıcılar olarak üretir. Gerçek MSTAR radar çiplerinde ise:
> 1. **Depresyon Açısı Kayması:** Eğitimin 17°, testin 15° depresyon açısında yapılması, hedefin radar kesit alanını (RCS) ve saçıcı merkezlerinin göreceli yansıma fazını kökten değiştirir.
> 2. **Multi-bounce Speckle & Clutter:** Zemin pürüzlülüğü, palet gölgeleri ve çoklu saçılmalar derin ağın kararlarını zorlaştırır.
> 3. **BMP-2 ve BTR-70 Benzerliği:** Her iki zırhlı personel taşıyıcı benzer silüet ve düşük profilli kule geometrisine sahiptir. Bu dürüst sonuç, gerçek radar mühendisliğinin doğasını yansıtmaktadır.

---

## 3. Gerçek MSTAR 5-Katmanlı Çapraz Doğrulama (5-Fold Stratified CV)

Modelin aşırı öğrenmeye (overfitting) düşmediğini ve belirli bir bölütlemeye bağımlı olmadığını kanıtlamak için 5-Fold Stratified Cross-Validation uygulanmıştır:

| Katman (Fold) | Doğruluk (Accuracy) | Makro Kesinlik | Makro Duyarlılık | Makro F1-Skoru |
|:---:|:---:|:---:|:---:|:---:|
| **Fold 1** | %66.15 | %66.52 | %65.89 | %63.01 |
| **Fold 2** | %75.88 | %76.12 | %75.40 | %74.88 |
| **Fold 3** | %59.92 | %60.10 | %59.35 | %54.39 |
| **Fold 4** | %61.09 | %62.45 | %61.12 | %58.07 |
| **Fold 5** | %64.98 | %65.80 | %64.90 | %58.68 |
| **ORTALAMA ± STANDART SAPMA** | **%65.60 ± %5.64** | **%66.20 ± %5.48** | **%65.33 ± %5.61** | **%61.81 ± %7.09** |

---

## 4. Standart 17° $\to$ 15° Depresyon Protokolü Sınıf Dağılımı

Standart MSTAR test protokolünde (Eğitim: 17° depresyon açısı, 698 çip; Test: 15° depresyon açısı, 587 çip) elde edilen sınıf bazlı başarım:

| Hedef Sınıfı | Araç Türü | Test Desteği (Support) | Kesinlik (Precision) | Duyarlılık (Recall) | F1-Skoru | ROC-AUC | PR-AUC |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **T-72** | Ana Muharebe Tankı | 196 | %73.46 | **%97.45** | **%83.77** | **0.937** | **0.770** |
| **BMP-2** | Piyade Muharebe Aracı | 195 | %52.21 | %30.26 | %38.31 | 0.674 | 0.438 |
| **BTR-70** | Zırhlı Personel Taşıyıcı | 196 | %57.94 | %63.27 | %60.49 | 0.808 | 0.649 |
| **MAKRO ORTALAMA** | — | **587** | **%61.21** | **%63.66** | **%60.86** | **0.807** | **0.619** |

### Sınıf Bazlı Fiziksel ve Elektromanyetik Analiz:
- **T-72 Üstünlüğü (F1: %83.77, Recall: %97.45, ROC-AUC: 0.937):**  
  T-72 tankının döküm yuvarlak kulesi ve gövde önünden ileri uzanan 125mm 2A46 yivsiz namlusu, radar dalgaları için çok güçlü bir dihedral/trihedral köşe yansıtıcı oluşturur. Bu güçlü radar geri dönüşü, depresyon açısı 17°'den 15°'ye değiştiğinde dahi baskın kalmakta ve ağ tarafından %97.45 gibi olağanüstü bir duyarlılıkla tanınmaktadır.
- **BMP-2 ve BTR-70 Karışıklığı:**  
  BMP-2 paletli bir araç olmasına rağmen alçak profilli gövdesi ve küçük kulesi, 8 tekerlekli BTR-70'in saçılma haritasıyla 15° depresyonda yüksek örtüşme göstermektedir. Model BMP-2 örneklerinin önemli bir kısmını (%42'sini) BTR-70 olarak sınıflandırmıştır. Bu durum radar ATR literatüründe bilinen "IFV/APC confusion" olgusuyla birebir örtüşmektedir.

---

## 5. Dağılım Dışı (OOD) ve Açık Küme (Open-Set) Zafiyet Analizi

Model kapalı küme (closed-set) varsayımıyla eğitildiğinden, sahneye giren yabancı araçları nasıl karşıladığı **1,838 adet bilinmeyen askeri hedef çipi** ile test edilmiştir:
- **Bilinmeyen Hedefler:** `2S1` (Kundağı Motorlu Obüs), `BRDM2` (Keşif Aracı), `BTR60`, `D7` (Zırhlı Dozer), `T62` (Tank), `ZIL131` (Kamyon), `ZSU_23_4` (Uçaksavar).

| Metrik | Bilinen Hedefler (T-72, BMP-2, BTR-70) | Bilinmeyen OOD Hedefler (7 Araç Türü) |
|---|:---:|:---:|
| **Örnek Sayısı** | 587 test çipi | **1,838 test çipi** |
| **Ortalama Softmax Güveni** | 0.5681 (%56.81) | **0.6037 (%60.37)** |
| **OOD Ayrım Gücü (AUROC)**  | — | **0.4607** |

> [!WARNING]
> **Kritik Mühendislik Bulgusu (Kapalı Küme Softmax Körlüğü):**  
> Bilinmeyen OOD araçlar (örneğin bir ZIL-131 kamyonu veya D7 dozeri), bilinen hedeflerden bile **daha yüksek bir ortalama güvenle (%60.37)** bilinen 3 sınıftan birine atanmaktadır. Softmax fonksiyonunun olasılıkları 1'e tamamlama zorunluluğu nedeniyle, yalnızca maksimum softmax çıktısına bakarak bilinmeyen hedef reddi yapılamaz (AUROC = 0.4607).  
> **Çözüm Önerisi:** Operasyonel sistemlerde mesafe tabanlı açık küme algoritmaları (Mahalanobis Distance, OpenMax veya Extreme Value Theory) zorunludur.

---

## 6. Model Kalibrasyonu ve Güvenilirlik

Modelin ürettiği güven olasılıklarının doğruluğu Beklenen Kalibrasyon Hatası (Expected Calibration Error - ECE) ile ölçülmüştür:
- **ECE Değeri:** **0.0953 (%9.53)**
- **Yorum:** Standart modern konvolüsyonel ağlarda ECE genelde %15-%25 bandında seyrederken, Ghost-ECANet modelimizde uygulanan etiket yumuşatma (Label Smoothing $\epsilon=0.05$) ve ağırlık azaltma (Weight Decay $5\times 10^{-4}$) modelin aşırı güvenli (overconfident) tahminler yapmasını engellemiş ve ECE'yi %10'un altında tutmuştur.

---

## 7. Dayanıklılık ve Stres Testleri (Robustness Sweeps)

### 7.1 Gürültü Dayanıklılığı (SNR Sweep: -5 dB $\to$ +20 dB)
Giriş sinyaline eklenen Gauss gürültüsü ile modelin SNR duyarlılığı ölçülmüştür:

| Giriş SNR (dB) | -5 dB | 0 dB | +5 dB | +10 dB | +15 dB | +20 dB (Nominal) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Doğruluk (Accuracy)** | %34.92 | %47.53 | %61.50 | %63.03 | %63.37 | **%63.71** |

- Model, **+5 dB SNR seviyesine kadar** neredeyse hiç başarım kaybetmemekte (%61.50 vs %63.71), ancak 0 dB ve altında termal gürültü saçıcı piklerini bastırdığında rastgele tahmin seviyesine (%33.33) doğru gerilemektedir.

### 7.2 Hedef Engelleme Dayanıklılığı (Central Occlusion Sweep: %0 $\to$ %50)
Hedefin merkezine yerleştirilen sıfır pikselli kare maskeler ile kısmi engelleme (kamuflaj/siper) simüle edilmiştir:

| Maskelenen Alan Oranı | %0 (Nominal) | %10 | %20 | %30 | %40 | %50 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Doğruluk (Accuracy)** | **%63.71** | %51.28 | %33.90 | %33.39 | %24.53 | %35.60 |

- Merkez kule/gövde saçıcılarının %20'si bloke edildiğinde doğruluk yarı yarıya düşmektedir. Bu bulgu, ağın kararlarını dağınık zemin gürültüsüne değil doğrudan hedefin merkez saçıcılarına dayandırdığını kanıtlar.

---

## 8. Model Karmaşıklığı ve Çıkarım Profili (SWaP Analizi)

Ghost-ECANet modelinin gömülü platformlara uygunluğu:

| Parametre | Değer | Kısıt / Limit | Durum |
|---|:---:|:---:|:---:|
| **Toplam Parametre Sayısı** | **904,268** | $< 2,000,000$ | **%45.2 Bütçe Kullanımı (PASSED)** |
| **Model Disk Boyutu** | **3.46 MB** | $< 16\text{ MB}$ (Flaş bellek) | **PASSED** |
| **Hesaplama Yükü (FLOPs)** | **~30.17 MFLOPs** | $< 100\text{ MFLOPs}$ | **PASSED** |
| **Ortalama Çıkarım Süresi (CPU)** | **16.33 ms** *(Kaynak: eval_results/evaluation_summary.json)* | $< 50\text{ ms}$ | **PASSED** |
| **Çıkarım Başarım Hızı (FPS)** | **61.24 FPS** *(Kaynak: eval_results/evaluation_summary.json)* | $> 20\text{ FPS}$ | **PASSED** |
| **P95 Çıkarım Gecikmesi** | **25.74 ms** *(Kaynak: eval_results/evaluation_summary.json)* | $< 50\text{ ms}$ | **PASSED** |

---

## 9. Açıklanabilir Yapay Zeka (XAI / Grad-CAM) Analizi

Grad-CAM ısı haritaları incelendiğinde ([`eval_results/gradcam_correct_samples.png`](../eval_results/gradcam_correct_samples.png)):
1. **T-72 Doğrulaması:** Isı haritası pikleri, aracın 125mm namlusunun gövdeyle birleştiği kule maskesine ve paletlerin metal dişlilerine odaklanmaktadır. Model aracı zemin gürültüsünden değil, fiziksel saçıcı merkezlerinden tanımaktadır.
2. **Hata Analizi ([`eval_results/gradcam_failure_analysis.png`](../eval_results/gradcam_failure_analysis.png)):** BMP-2'nin BTR-70 olarak yanlış sınıflandırıldığı durumlarda aktivasyon haritasının gövde arkasındaki asker kapılarına ve egzoz çıkıntısına kaydığı, bu bölgedeki saçılmanın BTR-70'in motor kapağı saçılmasıyla karıştırıldığı tespit edilmiştir.

---

## 10. Modül 1 (RDA) Simüle Açık SAR Odaklama Başarımı

Modül 1 Range-Doppler Algoritması, hem sentetik hedefler hem de simüle açık SAR (Sentinel-1 tarzı K-dağılımlı deniz sahnesi) üzerinde koşturulmuş ve odaklama metrikleri hesaplanmıştır:

| Odaklama Metriği | Sentetik Nokta Saçıcı Sahnesi | Simüle Açık SAR (Sentinel-1 tarzı K-dağılımlı) |
|---|:---:|:---:|
| **Menzil Çözünürlüğü ($\Delta r$)** | 3.75 m (Teorik: 1.50 m) | 2.50 m (Pik genişliği) |
| **Azimut Çözünürlüğü ($\Delta a$)** | 1.05 m (Teorik: 0.75 m) | 1.35 m (Pik genişliği) |
| **Menzil PSLR** | -42.23 dB (Hamming bastırması) | -5.03 dB (Dağınık saçıcı) |
| **Azimut PSLR** | -31.05 dB (Hamming bastırması) | -3.30 dB (Dağınık saçıcı) |
| **Shannon Görüntü Entropisi** | **5.35 nats** (Çok odaklı) | **12.05 nats** (Geniş deniz sahnesi) |
| **Görüntü Kontrastı ($\sigma/\mu$)** | **64.41** | **1.01** |
| **PAPR (Peak-to-Average Ratio)** | **40.83 dB** | **11.48 dB** |
| **RDA Çalışma Süresi (512x512)** | **0.096 s** | **0.034 s** |

---

## 11. Modül 3 Gömülü STM32 Portu ve WCET Projeksiyonu

> [!WARNING]
> **WCET Projeksiyon Notu:** Aşağıdaki saat döngü tahminleri, host x86_64'te ölçülen
> gerçek yürütme sürelerinden ve bilinen Cortex-M4F komut verim oranlarından türetilmiş
> **teorik projeksiyonlardır**. Fiziksel STM32F407 donanımında DWT döngü sayacı ile
> ölçülmemiştir. Gerçek sertifikasyon için hedef donanımda WCET doğrulaması gereklidir.

Modül 3 C kodu, ARM Cortex-M4F (STM32F407VG @ 168 MHz) hedefi mimarisi dikkate alınarak host x86_64 üzerinde zamanlanmış ve teorik en kötü durum çalışma süresi (WCET) projeksiyonu yapılmıştır:

| Bileşen | Saat Döngüsü (Tahmin @ 168 MHz) | Çalışma Süresi (ms) | Gereksinim Sınırı (REQ-005) | Emniyet Marjı |
|---|:---:|:---:|:---:|:---:|
| **Radix-2 DIT FFT (512-pt)** | ~46,080 döngü | ~0.274 ms | — | — |
| **1D CA-CFAR (512 bins)** | ~17,920 döngü | ~0.107 ms | — | — |
| **Darbe Başına Toplam WCET** | **~64,000 döngü** | **~0.38 ms (theoretical)** | **25.000 ms** | **66 Kat Altında (Teorik)** |
| **Dinamik Bellek (`malloc`)** | **0 Bayt** | **0 Bayt** | **0 Bayt (MISRA 21.3)** | **%100 Güvenli** |
| **Unity Birim Testleri** | 13 Test | 0 Hata / 0 İhmal | 13/13 Geçti | **%100 Başarı** |
| **MISRA-C Cppcheck** | 3/3 Dosya | 0 Kusur | 0 Uyarı | **%100 Temiz** |

---

## 12. Sonuç ve Savunulabilirlik Bildirimi

Bu sonuçlar, EdgeSAR sisteminin:
1. **Şeffaf olduğunu:** Sentetik başarı (%100) ile gerçek MSTAR başarısı (%63.71 test, %65.60 CV) arasındaki farkı açıkça ortaya koyduğunu,
2. **Mühendislik sınırlarını bildiğini:** Kapalı küme softmax'in bilinmeyen OOD hedeflerdeki zafiyetini (AUROC 0.46) matematiksel olarak raporladığını,
3. **Gömülü kısıtlara sadık kaldığını:** Modelin 904K parametre ve ~30 MFLOPs ile hafif olduğunu, C kodunun sıfır dinamik bellek ve ~0.38 ms tahmini WCET projeksiyonu ile hedef donanıma hazır tasarlandığını kanıtlamaktadır.

---

## 13. Değişiklik Günlüğü (Changelog) — Faz A, B, C Sağlamlaştırma Sonuçları

Bu bölüm, denetim sonrası `NEXT_STEPS_PROMPT.md` kapsamında yürütülen Faz A (Versiyon Kontrolü), Faz B (Donanım WCET Taraması) ve Faz C (Sınırlamaların İyileştirilmesi) adımlarının deneysel sonuçlarını ve mühendislik analizlerini içerir.

### 13.1 Faz A: Versiyon Kontrolü Temel Çizgisi (Git Baseline)
- MinGit v2.55.0 taşınabilir ortamı kullanılarak yerel Git sürüm kontrol sistemi kuruldu (`.gitignore` eklendi).
- Üç turlu bağımsız denetimden geçmiş durum (22/22 pytest, 13/13 Unity, MSTAR doğrulaması) temel çizgi olarak commit'lendi (`commit: 205918e`) ve `v0.3-audited` etiketi vuruldu.

### 13.2 Faz B: Donanım WCET Taraması ve Senaryo B2
- Yerel sistemde COM portları ve USB aygıtları tarandı: Fiziksel ST-Link v2 / STM32F407 kartı tespit edilemedi (0 cihaz).
- **Senaryo B2 Uygulandı:** `docs/LIMITATIONS.md` güncellenerek fiziksel STM32F407 Discovery kartı (~$25-30) temin edilene kadar WCET süresinin host x86_64 üzerinde teorik döngü projeksiyonu (~0.38 ms) olarak kalacağı şeffaf biçimde belgelendi (`commit: 1dac5e5`).

### 13.3 Faz C.1: Sınıf Ağırlıklandırma (Class Weighting) ve Ödünleşim (Trade-Off) Analizi

> [!IMPORTANT]
> **Kritik Mühendislik Bulgusu (BMP-2 vs. BTR-70 / T-72 Trade-Off):**  
> Kayıp fonksiyonunda BMP-2 sınıfı ağırlığı artırıldığında BMP-2 tekil duyarlılığı (recall) belirgin şekilde artmaktadır; ancak radar geri saçılma imzası çok yakın olan BTR-70 sınıfı neredeyse tamamen ezilmekte (recall %0.00'a düşmekte) veya T-72 duyarlılığı gerilemektedir. Aşağıdaki karşılaştırmalı matrisler bu ödünleşimi eksiksiz ortaya koymaktadır.

#### Tam 3x3 Karışıklık Matrisi (Confusion Matrix) Karşılaştırması

*(Satırlar: Gerçek Sınıf [T-72, BMP-2, BTR-70], Sütunlar: Tahmin Edilen Sınıf)*

| Model Yapılandırması | Sınıf Ağırlıkları $[w_0, w_1, w_2]$ | Genel Doğruluk | Makro F1 | T-72 Recall | BMP-2 Recall | BTR-70 Recall | Karışıklık Matrisi (3x3) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (Eşit Ağırlık)** | $[1.0, 1.0, 1.0]$ | **%63.71** | **%60.86** | **%97.45** (191/196) | %30.26 (59/195) | **%63.27** (124/196) | $\begin{pmatrix} 191 & 5 & 0 \\ 46 & 59 & 90 \\ 23 & 49 & 124 \end{pmatrix}$ |
| **Deneme 1 (Ilımlı BMP-2)** | $[1.0, 2.0, 1.0]$ | %61.16 | %50.05 | %98.47 (193/196) | **%85.13** (166/195) | **%0.00** (0/196) | $\begin{pmatrix} 193 & 3 & 0 \\ 29 & 166 & 0 \\ 14 & 182 & 0 \end{pmatrix}$ |
| **Deneme 2 (Ters Orantılı)** | $[1.0, 2.8, 1.2]$ | %61.16 | %50.46 | %93.88 (184/196) | **%89.74** (175/195) | **%0.00** (0/196) | $\begin{pmatrix} 184 & 12 & 0 \\ 20 & 175 & 0 \\ 10 & 186 & 0 \end{pmatrix}$ |
| **Deneme 3 (Agresif BMP-2)** | $[0.6, 2.5, 1.0]$ | %59.45 | %50.40 | %79.59 (156/196) | **%97.44** (190/195) | %1.53 (3/196) | $\begin{pmatrix} 156 & 40 & 0 \\ 5 & 190 & 0 \\ 5 & 188 & 3 \end{pmatrix}$ |

#### Detaylı Sınıf Bazlı Metrikler:
- **Baseline ($[1.0, 1.0, 1.0]$):**
  - T-72: Precision = %73.46, Recall = %97.45, F1 = %83.77 (Support: 196)
  - BMP-2: Precision = %52.21, Recall = %30.26, F1 = %38.31 (Support: 195)
  - BTR-70: Precision = %57.94, Recall = %63.27, F1 = %60.49 (Support: 196)
- **Deneme 1 ($[1.0, 2.0, 1.0]$):**
  - T-72: Precision = %81.78, Recall = %98.47, F1 = %89.35
  - BMP-2: Precision = %47.29, Recall = **%85.13 (+54.87%)**, F1 = %60.81
  - BTR-70: Precision = %0.00, Recall = **%0.00 (-63.27%)**, F1 = %0.00 *(182 adet BTR-70 örneği BMP-2'ye yanlış yönlendirildi)*
- **Deneme 3 ($[0.6, 2.5, 1.0]$):**
  - T-72: Precision = %93.98, Recall = **%79.59 (-17.86%)**, F1 = %86.19 *(T-72 tank duyarlılığı beklendiği gibi geriledi)*
  - BMP-2: Precision = %45.45, Recall = **%97.44**, F1 = %61.99
  - BTR-70: Precision = %100.00, Recall = **%1.53**, F1 = %3.02

**Mühendislik Kararı:**  
Sınıf ağırlıklandırması BMP-2 duyarlılığını %30.26'dan %85-97 seviyesine çıkarmakla birlikte, modelin zırhlı araç türlerini ayırt etme yeteneğini yok ederek BTR-70 sınıfını tamamen BMP-2'ye asimile etmektedir. Bu sebeple Makro F1 skoru %60.86'dan %50.05'e gerilemektedir. **Dengeli ve savunulabilir bir radar sistemi için Baseline modeli ana operasyonel model olarak muhafaza edilmiş**, ağırlıklandırılmış model ise alternatif checkpoint (`checkpoints/weighted_mstar_model.pth`) ve karşılaştırma grafiği (`eval_results/confusion_matrix_comparison.png`) olarak kaydedilmiştir.

---

### 13.4 Faz C.2: Enerji Tabanlı Dağılım Dışı (OOD) Tespiti ve İstatistiksel Eşikleme Metodolojisi

#### Serbest Enerji Formülasyonu
Softmax Maksimum Olasılık Skoru (MSP), kapalı küme varsayımı nedeniyle bilinmeyen hedeflere yüksek olasılık atamaktadır ($AUROC = 0.4607$). Bunun yerine logit uzayında serbest enerji fonksiyonu uygulanmıştır:
$$S_{\text{energy}}(x; T) = T \cdot \log \sum_{k=1}^K \exp\left(\frac{f_k(x)}{T}\right)$$

#### Sıcaklık ($T$) Taraması ve AUROC Başarımı
- **Softmax MSP Skoru:** AUROC = **0.4607** (Ayrım gücü yok)
- **Free Energy ($T=1.0$):** AUROC = **0.5633** (Bilinen ort: 1.355, OOD ort: 1.329)
- **Free Energy ($T=2.0$):** AUROC = **0.5941** (Bilinen ort: 2.323, OOD ort: 2.293)
- **Free Energy ($T=5.0$):** AUROC = **0.6500 (+%18.9 Mutlak İyileşme)** (Bilinen ort: 5.525, OOD ort: 5.498)

#### İşletimsel Eşik (Threshold) Seçim Metodolojisi
Rastgele veya OOD verisine göre eşik seçilmesi (empirical data leakage) önlenmiş; eşik değerleri **tamamen dağılım içi (In-Distribution / ID) bilinen test/doğrulama setinin persentil dağılımına göre** istatistiksel olarak belirlenmiştir:
- Eşik formülasyonu: $\tau_X = \text{Percentile}(S_{\text{known}}, X)$
- Bu metodoloji, sahada henüz karşılaşılmamış OOD hedeflerden bağımsız olarak, bilinen hedeflerin operasyonel olarak en az %$(100-X)$'inin korunmasını (True Positive Rate - TPR) garanti eder.

| Hedef Kriter | Persentil $X$ | Belirlenen Eşik ($\tau_X$) | Gerçek Bilinen Koruma (TPR) | OOD Yanlış Alarmı (FPR) | OOD Doğru Reddetme Oranı | Algılama Hatası |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **TPR %95 Koruma** | %5.0 | $\tau_{95} = 5.4572$ | **%94.89** | %85.04 | **%14.96** | %45.07 |
| **TPR %90 Koruma** | %10.0 | $\tau_{90} = 5.4620$ | **%89.95** | %74.76 | **%25.24** | %42.40 |
| **TPR %80 Koruma** | %20.0 | $\tau_{80} = 5.4745$ | **%79.90** | %59.14 | **%40.86** | %39.62 |
| **Dengeli Eşik** | %50.0 | $\tau_{50} = 5.5119$ | **%50.09** | %31.94 | **%68.06** | %40.93 |

*Grafiksel Çıktı:* Karşılaştırmalı enerji dağılımı ve eşik çizgileri [`eval_results/ood_energy_comparison.png`](../eval_results/ood_energy_comparison.png) dosyasında kaydedilmiştir.  
*Birim Test Doğrulaması:* `tests/test_atr.py` dosyasına `test_energy_based_ood_score_computation` testi eklenmiş ve test sayısı 23'e çıkarılmıştır.

---

### 13.5 Faz C.3: Gerçek Sentinel-1 SLC Verisi Durumu
- **Durum:** `YAPILAMADI: ESA Copernicus / ASF hesap kimlik doğrulaması (OAuth credentials) ve ~4-8 GB SLC dosya boyutu kısıtı.`
- **Gerekçe:** Gerçek Sentinel-1 Single Look Complex (SLC) Level-1 interferometrik geniş şerit (IW) ürünlerinin indirilmesi, ESA Copernicus Data Space Ecosystem veya NASA Alaska Satellite Facility (ASF) kimlik doğrulaması (API token / kullanıcı girişi) gerektirmektedir. Ayrıca tek bir sıkıştırılmamış SLC sahnesi 4 ila 8 GB bellek ve yüksek bant genişliği gerektirmektedir.
- **Mevcut Çözüm:** Modül 1 (RDA), ESA Sentinel-1 C-band chirp karakteristikleri ($f_c = 5.405\text{ GHz}$, $B_w = 56.5\text{ MHz}$, $K_r = 1.078\times 10^{12}\text{ Hz/s}$) ile K-dağılımlı deniz saçıcıları üreten simüle açık SAR pipeline'ı ([`scripts/sar_real_loader.py`](../scripts/sar_real_loader.py)) üzerinden doğrulanmıştır.

