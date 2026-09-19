# EdgeSAR — Sınırlamalar ve Mühendislik Kısıtları (Limitations & Constraints)

> **Belge Amacı:** Bu doküman, EdgeSAR sisteminin sınırlarını, basitleştirmelerini, varsayımlarını ve operasyonel kullanım için eksik olan yönlerini şeffaf ve bilimsel bir dürüstlükle listeler. Projenin hiçbir iddiası bu kısıtların ötesine geçmez.

---

## 1. Standart Uyumluluğu ve Sertifikasyon Kısıtları

- **Resmî Sertifikasyon Yoktur:**
  Projede **DO-178C DAL-B**, **MISRA-C:2012**, **MIL-STD-1553B** ve **MIL-STD-882E** standartlarının felsefesi, mimari prensipleri ve kodlama kuralları benimsenmiştir. Ancak sistem akredite bir havacılık/savunma sertifikasyon otoritesi (FAA, EASA, SSB, TÜBİTAK vb.) tarafından denetlenmemiştir ve resmî uçuş sertifikasına sahip DEĞİLDİR.
- **MIL-STD-1553B Protokolü Simülatiftir:**
  Aviyonik veri yolu mantığı, çift-yedekli mimari, Manchester kodlama soyutlaması ve subaddress eşlemeleri yazılımsal olarak simüle edilmiştir. Gerçek 1553B alıcı-verici hibrit donanımı (örneğin Holt HI-6110 veya DDC transreceiver) üzerinde elektriksel sinyal seviyesi doğrulaması yapılmamıştır.
- **FMEA / MIL-STD-882E Analiz Derinliği:**
  Risk matrisi ve tehlike analizleri sistem mimarisi seviyesinde analitik bir şablon olarak geliştirilmiştir. Gerçek bir hava aracının tam sistem emniyet değerlendirmesi (FHA/SSA) düzeyinde saha arıza geçmişi verisi içermez.

---

## 2. Modül 1 (RDA Radar Sinyal İşleme) Sınırlamaları

- **Düz Hat Uçuş Varsayımı (İdeal Trajectory):**
  RDA kodunda radar platformunun sabit hızda ve mükemmel bir düz doğrultuda uçtuğu varsayılmıştır. Gerçek uçuşlarda atmosferik türbülans nedeniyle oluşan sapmalar için Ataletsel Ölçüm Birimi (IMU/GPS) destekli **Hareket Kompanzasyonu (Motion Compensation - MoCo)** veya **Autofocus (PGA - Phase Gradient Autofocus)** gereklidir; mevcut sürümde PGA basitleştirilmiştir.
- **Stop-and-Hop Yaklaşımı:**
  Radar darbesinin iletimi ve alımı süresince platformun hareket etmediği ("stop-and-go" / "stop-and-hop") kabul edilmiştir. Yüksek hızlı platformlarda veya çok geniş açılı sentetik açıklıklarda bu varsayım menzilde hafif distorsiyona yol açabilir.
- **Topografya ve Düz Dünya Yaklaşımı:**
  Görüntüleme düzlemi yer yüzeyinin eğriliğini ve arazi yükseltilerini hesaba katmayan düzlem yaklaşımıyla modellenmiştir.
- **Açık SAR Simülasyon Kısıtı:**
  Açık SAR örneği gerçek Sentinel-1 SLC verisi değildir; `sar_real_loader.generate_realistic_maritime_sar_scene` ile üretilmiş prosedürel K-dağılımlı deniz sahnesidir. Bu yüzden gerçek Sentinel-1 spekle/geometri karakteri simülasyonla sınırlıdır.

---

## 3. Modül 2 (Derin ATR & XAI) Sınırlamaları

- **Sentetik vs. Gerçek Veri Uçurumu (Domain Gap):**
  Sentetik saçıcı simülatöründe elde edilen %100 F1 skoru, basitleştirilmiş saçıcı modellerinden kaynaklanmaktadır. Gerçek MSTAR verisinde zemin clutter'ı, speckle, depresyon açısı farkları (17° eğitim vs 15° test) ve hedef konfigürasyon varyasyonları nedeniyle başarım daha gerçekçi seviyelerde seyreder.
- **Açık Küme (Open-Set) ve Bilinmeyen Hedef Kör Noktası:**
  Standart Softmax katmanı kapalı dünya varsayımıyla çalışır (görülen her şeyi 3 sınıftan birine atamaya zorlanır). Gerçek dünyada radar sahnesine giren sivil araçlar, binalar veya bilinmeyen askeri araçlar (2S1, BRDM vb.) yüksek güvenle yanlış sınıfa atanabilir. Bu durumu azaltmak için güven eşiklemesi ve OOD analizi gereklidir.
- **Grad-CAM Yorumlama Sınırları:**
  Grad-CAM son konvolüsyon katmanının aktivasyon haritalarına dayandığından kaba bir uzamsal çözünürlüğe sahiptir (16x16 aktivasyon haritası 128x128'e enterpole edilir). Hedefin kesin piksel seviyesi saçıcı koordinatlarını tam olarak göstermek yerine genel ilgi bölgesini işaret eder.

---

## 4. Modül 3 (Gömülü C & Donanım) Sınırlamaları

- **Host Simülasyonu vs. Hedef Mikrodenetleyici:**
  Gömülü C kodu (CFAR, FFT, DMA HAL) x86_64 host ortamında (GCC/Clang) derlenip test edilmiştir. Sıfır heap ve MISRA-C uyumluluğu bare-metal geçişine hazır olsa da, bellek önbelleği (L1/L2 cache), dal tahmincisi (branch predictor) ve mimari farklar nedeniyle masaüstü çalışma süreleri gerçek bir Cortex-M4/M7 mikrodenetleyiciden farklıdır.
- **WCET Ölçüm Ortamı:**
  Gömülü C pipeline (FFT + CFAR) yalnızca **host x86_64 ortamında** zamanlanmıştır ve Cortex-M4F @ 168 MHz için **teorik projeksiyon** yapılmıştır (~0.38 ms tahmin). Bu tahmin derleyici optimizasyonu (-O2), önbellek isabet oranı, ve kesme gecikmesi varsayımlarına dayanır. Gerçek WCET doğrulaması için `main_stm32.c` dosyasının fiziksel STM32F407 kartına yüklenerek DWT döngü sayacından (Data Watchpoint and Trace) okunması gerekmektedir. **Donanım ölçümü henüz yapılmamıştır; fiziksel STM32F407 Discovery kartı (~yaklaşık 25-30$) temin edildiğinde bu doğrulama tamamlanacaktır — kod ve build sistemi PlatformIO ile tam hazır durumdadır, sadece donanım kartı eksiktir.**
- **1D CFAR vs. 2D CA-CFAR:**
  Uygulanan CFAR algoritması her menzil hattı üzerinde 1D pencere kaydırmaktadır. Karmaşık heterojen zeminlerde (deniz-kara sınırı, kentsel alan) 2B OS-CFAR (Ordered Statistic CFAR) veya Log-t-CFAR daha yüksek tespit başarımı sağlar.

---

## 5. Çevresel ve Operasyonel Sınırlamalar

- **Atmosferik Zayıflama ve Yağış:** X-band sinyalleri yoğun yağmur, sis ve fırtınada zayıflamaya uğrar; sistem modellerinde atmosferik zayıflama katsayısı nominal kuru hava olarak alınmıştır.
- **Elektronik Karıştırma (ECM/Jamming):** Sistem aktif radar karıştırıcıları (noise jamming, deceptive chirp jamming) veya aldatıcı sahte hedeflere karşı elektronik koruma (ECCM/EPM) önlemleri içermemektedir.
