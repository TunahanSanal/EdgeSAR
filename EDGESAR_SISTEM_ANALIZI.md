# EdgeSAR — Sistem Analizi ve Bağımsız Denetim Özet Raporu (Kendi Kendine Yeterli Brifing)

> **Bu doküman:** Proje kodlarına erişimi olmayan bir analist/LLM'in EdgeSAR sistemini anlayabilmesi ve teknik/emniyet açısından eleştirel analiz yapabilmesi için hazırlanmış, **kendi kendine yeterli** bir Sistem Analizi Brifingi'dir.
> **Önem:** Buradaki bütün sayılar, 20.09.2026 tarihinde sistem üzerinde bizzat çalıştırılan komutlar (derleme, test, ölçüm, hash doğrulama) tarafından bağımsız bir denetçi tarafından **doğrulanmıştır**; beyana dayalı değildir.
> **Dil:** Türkçe teknik terminoloji korunarak hazırlanmıştır.

---

## 1. Sistemin Amacı ve Mimari Genel Bakış

**EdgeSAR**, havadan uçak/İHA platformlarında kullanılabilmek üzere tasarlanmış bir **Sentetik Açıklık Radar (SAR)** görüntüleme + araç hedef tanıma (ATR) + gömülü saha işleme zinciridir. Üç ana modülden oluşur:

| Modül | Ad | Görev | Teknolojisi |
|---|---|---|---|
| 1 | Sinval İşleme (RDA) | Ham SAR ham verisinden odaklı görüntü üretimi; menzil 3dB çözünürlük, PSLR, entropi/kontrast ölçümü | Python + NumPy, Range-Doppler Algorithm (RDA) |
| 2 | ATR & XAI (GhostNet+ECA) | 128×128 SAR çipinden 3 sınıflı hedef tanıma (T-72, BMP-2, BTR-70) + Grad-CAM açıklanabilirlik | PyTorch, ~904K parametre CNN |
| 3 | Gömülü C (DO-178C tarzı) | FFT + CA-CFAR + DMA ping-pong HAL; bare-metal hedef donanım hazırlığı | C99, sıfır heap, MISRA-C tarzı, Unity testleri |

Destekleyici unsurlar: `docs/SRD.md` (gereksinimler), `docs/RTM.md` v2.2.0 (izlenebilirlik matrisi), `docs/mil_std_882e_fmea.md` (FMEA/tehlike analizi), `docs/mil_std_1553b.md` (aviyonik veri yolu simülasyonu), `docs/RESULTS.md`, `docs/LIMITATIONS.md`, `docs/DATA_CARDS.md`, `.github/workflows/ci.yml` (3 iş: python test, gömülü C test + cppcheck, veri bütünlüğü sha256).

---

## 2. Modül 1 — RDA Sinyal İşleme

### 2.1 Radar Parametreleri (RDAParameters / SCF)

| Parametre | Değer | Not |
|---|---|---|
| Taşıyıcı frekans f0 | 9.6 GHz (X-Band), λ=3.12 cm | |
| Chirp bant genişliği Br | 100 MHz | Teorik menzil çözünürlüğü Δr = c/(2Br) = **1.499 m** |
| Darbe süresi Tp | 5.0 µs | Darbe Sıkıştırma Oranı TBP = 500 |
| Örnekleme frekansı fs | 120 MHz | Menzil bin aralığı = c/(2·fs) = **1.25 m/bin** |
| Platform hızı v | 150 m/s | Azimut bin aralığı = v/PRF = **0.15 m/bin** |
| Referans eğik mesafe R0 | 5000 m | |
| Anten boyu La | 1.50 m | Teorik azimut çözünürlüğü Δa = La/2 = **0.750 m** |
| PRF | 1000 Hz | |
| Spektral pencere | **Hamming** | Teorik ilk yan lob ≈ −43 dB |

Sahne boyutu: sentetik = **512 azimut × 1024 menzil**; açık (simüle) SAR = 512×512.

### 2.2 Algoritma Akışı (Range-Doppler Algorithm)

1. **Menzil Eşleşik Filtre (Range Compression):** Menzil frekans domeninde CRP-chirp eşleniği ile sıkıştırma (FFT-domain matched filter).
2. **Azimut FFT → Range-Doppler:** Azimut yönünde FFT ile doppler domenine geçiş.
3. **Menzil Hücre Göç Düzeltmesi (RCMC):** Azimutla artan eğik mesafe kaymasının düzeltilmesi. Maksimum RCM ≈ **6.77 m = 5.42 menzil bin'i**. (Teorik beklenen kayma değeriyle tutarlı: ΔR≈(λ v² t²)/(2R0) formu.)
4. **Azimut Sıkıştırma (Azimuth Matched Filter):** Azimut eşlenik filtre ile odaklama.
5. **Görüntü kalitesi ölçümleri:** Çözünürlük, PSLR (en yüksek yan lob oranı), Shannon entropi, kontrast (σ/µ), PAPR.

### 2.3 Kanonik 5-Hedefli Kalibrasyon Takımyıldızı

Sentetik üretimde fizik tabanlı 5 nokta saçıcı kullanılır (menzil kayması m, azimut kayması m, RCS):

| Hedef | Menzil (m) | Azimut (m) | RCS |
|---|---|---|---|
| Merkez | 0 | 0 | 1.0 |
| A | +30 | 0 | 0.8 |
| B | −30 | 0 | 0.8 |
| C | 0 | +30 | 0.7 |
| D | +30 | +30 | 0.9 |

30 m ≈ **24 menzil bin'i** (1.25 m/bin) ve **200 azimut bin'i** (0.15 m/bin). Yani takımyıldız komşuları merkez hedeften menzilde ±24, azimutta ±200 bin uzaktadır. **Bu mesafeler "PSLR ölçüm pencerelerinin" kalitesini belirler** (bkz. bölüm 2.4 ve denetim tarihçesi).

### 2.4 PSLR Ölçüm Metrikleri (Denetimle Olgunlaşan Kısım)

- `measure_resolution_and_pslr`: 3dB çözünürlük + yerel yan lob. Parametreli: **menzil ekseni** guard=5 bin / tarama=±18 bin; **azimut ekseni** guard=16 bin / tarama=±150 bin (azimut ana lobunun geniş eteğini dışlamak için menzile göre daha geniş guard gerekir).
- `measure_isolated_target_pslr`: **izole hedef** yan lobu. Menzil penceresi ±20 bin, azimut penceresi ±150 bin; guard default 15 bin. Pencereler takımyıldız komşuları (±24 / ±200 bin) **dışında** kaldığı için ölçüm, komşu hedef RCS oranı yerine **gerçek Hamming yan lobunu** verir.

### 2.5 Ölçülen Sonuçlar (deterministik, seed=42, SNR=25 dB)

**Sentetik sahne (512×1024):**

| Metrik | Ölçülen | Teorik/kural |
|---|---|---|
| Range 3dB Çözünürlük | **3.747 m** | Δr=1.499 m (Hamming genişletmesi ≈1.5× beklenir) |
| Azimut 3dB Çözünürlük | **1.050 m** | Δa=0.750 m |
| Range PSLR | **−42.23 dB** | Hamming teorik ≈ −42.7 dB ✓ |
| Azimut PSLR | **−31.05 dB** | Gerçek ilk azimut yan lobu; ±5-bin'lik eski guard ana lob eteğini ölçüyordu (−7.44 dB artefaktı), guard 16'ya çıkarıldı |
| İzole Range PSLR | **−43.9 dB** | |
| İzole Azimut PSLR | **−31.1 dB** | |
| Shannon Entropi | 5.3472 nats | Nokta hedefli sahne için düşük (iyi odaklama) |
| Kontrast (σ/µ) | 64.4107 | |
| PAPR | 40.83 dB | |
| Toplam RDA süresi | ≈0.06 s | ~8.3 Mpoints/s (NumPy) |

**Simüle Açık SAR (Sentinel-1 tarzı K-dağılımlı deniz sahnesi, 512×512):**

| Metrik | Ölçülen |
|---|---|
| Range / Azimut 3dB Çözünürlük | 2.498 m / 1.350 m |
| Range / Azimut PSLR | −5.03 dB / −3.30 dB (izole: −5.9 / −3.3 dB) |
| Shannon Entropi / Kontrast | 12.0471 nats / 1.0125 |
| PAPR | 11.48 dB |

> ⚠️ **Önemli metodolojik not:** Simüle clutter sahnesinde PSLR, nokta hedef yan lobu DEĞİLDİR; sahnenin en güçlü clutter pikine göre hesaplanmış göreli kontrast değeridir. "İzole hedef" kavramı burada anlamsızdır.

**Teşhis çıktıları:** 4 adet PNG (ham sinyal, menzil sıkıştırma, Range-Doppler/RCMC, odaklı görüntü) + `metrics.json` (çözünürlük, PSLR, izole PSLR, entropi, kontrast, PAPR, süre; kaynak etiketi dahil).

---

## 3. Modül 2 — ATR & XAI (GhostNet + ECA)

### 3.1 Mimari ve Kısıtlar

- **GhostECANet:** Ghost convolution + Efficient Channel Attention (ECA). **Çalıştırılabilir parametre = 904,268** (< 2M bütçesi → **%45.2** kullanım). Hesaplama yükü ≈ **30.17 MFLOPs** (< 100 M kuralı). Model disk boyutu 3.46 MB.
- **GroupNorm kullanılır (BatchNorm DEĞİL):** Uçuş sürecinde batch=1 ve DMA bağlam kayması riskine karşı emniyetli normalize seçimi (önemli tasarım kararı).
- **Grad-CAM:** Son konvolüsyon aktivasyonlarından ısı haritası (16×16 → 128×128 enterpole). Heap-değil, teslime hazır.
- Giriş: (B,1,128,128) tek kanal, piksel [0,1].

### 3.2 Veri Seti: MSTAR (Gerçek Açık Askeri Radar Verisi)

- Standart kamu **3-sınıf SOC (Standard Operating Condition)** alt kümesi; **gerçeklik doğrulandı**: dizin yapısı, HB*.jpeg dosya adları ve örnek sayıları resmî protokolle birebir; SHA-256 hash'leri dokümante.
- X-Band (9.6 GHz), Spotlight, HH polarizasyon, 0.3 m × 0.3 m resimleme, 128×128.
- Eğitim 17° depresyon, Test 15° depresyon (farklı açı genelleşmesi).

| Sınıf | Etiket | Eğitim (17°) | Test (15°) |
|---|---|---|---|
| T-72 | **0** | 232 | 196 |
| BMP-2 | **1** | 233 | 195 |
| BTR-70 | **2** | 233 | 196 |
| **Toplam** | | 698 | 587 |

- **OOD (bilinmeyen 7 sınıf):** 2S1(274), BRDM-2(274), BTR-60(195), D7(274), T-62(273), ZIL-131(274), ZSU-23-4(274) → **1,838 çip**.
- npz dosyaları: `train_cache.npz` (14,772,938 B; SHA256 `7691faeb…f5d7`), `test_cache.npz` (12,299,637 B; SHA256 `748e3658…a0daad`).
- Etiket haritası (kod + veri kartı çapraz doğrulanmış): **T72=0, BMP2=1, BTR70=2**.

### 3.3 Eğitim Metrikleri (Doğrulanmış)

| Metrik | Değer |
|---|---|
| Test doğruluğu (best_mstar_model.pth) | **63.71 %** (63.714) |
| Sınıf geri çağırma | **T-72: %97.45** | **BMP-2: %30.26** | **BTR-70: %63.27** |
| 5-Fold Stratified CV | **%65.60 ± 5.64** (fold'lar ≈ 66.2/75.9/59.9/61.1/65.0) |
| ECE (kalibrasyon hatası) | 0.0953 |
| OOD Ayırma (softmax güven AUROC) | **0.4607** (< 0.5 → **OOD reddi ÇALIŞMIYOR**; belgeli, dürüst negatif) |
| CPU Çıkarım süresi | ortalama **16.33 ms**, P95 **25.74 ms**, **61.24 FPS** (kural <50 ms) |
| Sentetik "oyuncak" kıyas | %100 F1 (yalnızca sentetik saçıcı sahnesi; "Toy" olarak etiketli) |

- **Grad-CAM bulgusu:** T-72 örneğinde ısı haritası namlu/gövde birleşim noktası ve paletlere odaklanıyor → modelin aracı arka plandan değil fiziksel saçıcılardan tanıdığına dair görsel kanıt.
- **Checkpoint koruması:** dry-run `checkpoint_dry_run.pth` yazar; `best_mstar_model.pth` korunur.

---

## 4. Modül 3 — Gömülü C (Bare-Metal Pipeline)

### 4.1 Bileşenler ve Güvenlik Özellikleri

- `cfar_detector.c`: **CA-CFAR** (Cell-Averaging Constant False Alarm Rate) 1D tarama + **alt-bin parabolik tepe interpolasyonu** (REQ-EMB-003) + SNR hesabı.
- `fft_mock.c`: Radix-2 DIT FFT (512-nokta) + ters FFT + güç spektrumu.
- `hal_sar_mock.c`: **ping-pong çift tamponlu DMA** HAL soyutlaması (Init/DeInit/ReceiveDMA/HalfComplete/Complete/GetState).
- **MISRA-C Rule 21.3:** Kodda `malloc/calloc/free/realloc` **YOK** — sıfır dinamik bellek, statik tamponlar.
- Derleme: `gcc -Wall -Wextra -pedantic -std=c99 -Werror -Wstrict-prototypes -Wshadow` → **0 hata, 0 uyarı**.
- **cppcheck** `--enable=all --error-exitcode=1` → **0 kusur** (sadece bilinçli suppress: unusedFunction, staticFunction, missingIncludeSystem vb.).
- **Unity:** **13 test | 0 hata | 0 ignore** (test_runner.c).

### 4.2 WCET / Zamanlama (KRİTİK ETİKET)

> **TANIM VE DÜRÜSTLÜK:** WCET **host (x86_64) ortamında ölçülmüş**, hedef Cortex-M4F @ 168 MHz için **teorik projeksiyon** yapılmıştır. **Fiziksel STM32 üzerinde DWT sayacı ile doğrulama HENÜZ YAPILMAMIŞTIR.** Bu durum README/RESULTS/LIMITATIONS'ta açıkça ifade edilir.

- Host ölçümü: FFT ≈ 5.0 µs/iter, CFAR ≈ 3.0 µs/iter (toplam ≈ 8.0 µs/iter).
- M4F teorik projeksiyon: 512-pt FFT ≈ 46,080 döngü (≈0.274 ms) + 512-bin CA-CFAR ≈ 17,920 döngü (≈0.107 ms) = **≈64,000 döngü ≈ 0.381 ms**; 25 ms REQ-005 bütçesine karşı **~66× marj**.
- Doğruluk: Altın standart DFT'ye karşı **Max |hata| = 1.662970e-04**.

---

## 5. Dokümantasyon ve İzlenebilirlik

| Doküman | İçerik / Durum |
|---|---|
| `SRD.md` | REQ-RDA-001… (menzil çözünürlüğü, PSLR ≤ −40 dB…), REQ-EMB-001… (sıfır heap, 512-nokta FFT, sub-bin interpolasyon), REQ-ATR-… (parametre bütçesi, ≤50 ms) |
| `RTM.md` **v2.2.0** | İki yönlü matris; "Requirements Traced to Tests: 15/15"; pytest **22/22** (8 RDA, 5 ATR, 1 Entegrasyon, 4 Özellik, 4 Regresyon); Unity 13/13; kod satır bağları denetçi tarafından doğrulanmış |
| `mil_std_882e_fmea.md` | FMEA; örn. HAZ-003 → label smoothing ε=0.05 (kod/RESULTS ile tutarlı) |
| `mil_std_1553b.md` | Aviyonik veri yolu mantığı, çift yedekli mimari, Manchester kodlama — **yazılımsal simülasyon**, fiziksel transceiver elektrik testi yok |
| `RESULTS.md` | Tüm metriklik tablolar; gecikme JSON'dan atıflı |
| `LIMITATIONS.md` | Dürüst sınırlamalar listesi (bkz. §7) |
| `DATA_CARDS.md` | Veri kartları + SHA-256 doğrulama |

**Test piramidi (pytest 22):** `test_rda.py` 8 (chirp matched filter, RCMC curvature, 2D odaklı çözünürlük, boyut/ilaveler, real-SAR smoke+focus, süre-kıyas, izole PSLR, **çok hedefli takımyıldız izole PSLR**), `test_atr.py` 5, `test_integration.py` 1, `test_property.py` 4 (Parseval, matched-filter kayma vb.), `test_regression.py` 4 (malloc/free regex taraması vb.).

---

## 6. Denetim Tarihçesi (Üç Bağımsız Tur — NEYİN NEREDEN DÜZELDİĞİ)

| Tur | Sonuç & Bulgular |
|---|---|
| **Tur 1** | ŞARTLI GEÇTİ. İlk ajan raporundaki iddialar beyana dayalıydı; WCET "ölçüldü" söylemi, µhika kokulu "temiz" sayılar, test sayıları vs. diskle tutarsızdı. |
| **Tur 2** | ŞARTLI GEÇTİ. Ajan "8 düzeltme" sundu: 7 & kısmen doğrulandı (benchmark sayıları üretilebilirdi ve artık "teorik" etiketli, main_stm32 strict derleme 0/0, MSTAR gerçek & hash doğrulu, checkpoint 63.71% birebir). **AMA yeni kusur:** "izole PSLR" guard'ı (15) takımyıldız komşularından (24/200 bin) küçüktü → CLI mağlup edildi: "İzole Range −2.0 dB / Azimuth −6.3 dB" = komşu RCS oranı. Ayrıca etiket tablosu, "Gerçek SAR" abartısı, 20/20 sayaçlar, gecikme senkronu eksikti. |
| **Tur 3** | **GEÇTİ.** Ajan 7 düzeltme yaptı; hepsini diskten ve canlı koşuyla yeniden doğruladım: (1) etiket tablosu kodla hizalandı (T72=0), (2) "Gerçek SAR"→"Simüle Sentinel-1 tarzı K-dağılımlı" (4 belge), (3) sayaçlar 22/22 (RTM 2.2.0), (4) çok hedefli izole-PSLR regresyon testi eklendi (kısıtlar: range ≤−38 dB, az ≤−28 dB, izole ≤ pencere), (5) azimut PSLR ana-lob artefaktı −7.44→−31.05 dB (eksen bazlı guard), (6) gecikme JSON ile senkron (16.33 ms / 61.24 FPS / 25.74 ms P95), (7) izole ölçüm notu ve default guard düzeltildi. Tüm doğrulama zinciri (22 pytest, 8 RDA, 13 Unity, strict gcc, cppcheck, sha256) **bizzat ben** yeniden çalıştırdım: hepsi geçti. |

---

## 7. Bilinen Sınırlamalar ve Dürüst Negatifler (Analiz İçin Önemli)

1. **OOD ayırt etme başarısız:** AUROC 0.4607 (< 0.5) — softmax kapalı dünya; bilinmeyen hedefler yüksek güvenle yanlış sınıfa atanabilir. Güven eşiklemesi + OOD mekanizması gerekli.
2. **Sınıf dengesiz başarım:** BMP-2 geri çağırma %30 → büyük karışıklık; T-72 %97 baskın. CV standart sapması ±5.64 → varyans yüksek.
3. **"Gerçek veri" uçurumu:** Açık SAR örneği `sentinel1_maritime_sample.npy` **gerçek Sentinel-1 değil**; `sar_real_loader.generate_realistic_maritime_sar_scene` ile üretilen **prosedürel K-dağılımlı deniz sahnesi** (spekle geometrisi simülasyonla sınırlı). MSTAR ise gerçektir.
4. **WCET donanımda doğrulanmamış:** Host zamanlaması → teorik M4F projeksiyonu; DWT ile fiziksel ölçüm açık madde.
5. **CFAR 1D, heterojen zemin** için 2D OS-CFAR/log-t CFAR önerilir.
6. **Hareket kompanzasyonu yok:** RDA ideal düz hat, stop-and-hop, düz dünya varsayar; gerçek uçuş için IMU/GPS MoCo veya PGA autofocus gerekir (PGA basitleştirilmiş).
7. **MIL-STD belgeleri analitik şablon:** Normal şartlarda tam FHA/SSA ve gerçek saha arıza verisi içermez; 1553B elektriksel olarak test edilmemiş (yazılımsal simülasyon).
8. **Clutter sahnesinde "izole PSLR" anlamsızdır** (nokta hedef yok; değerler göreli kontrasttır).

---

## 8. Proje Ortamı ve Araçlar

- OS: Windows / PowerShell. Git ve ripgrep **kurulu değil** (tarama araçları ile değiştirildi).
- Python **3.14.2**, numpy 2.4.1, torch 2.13.0+cpu, pytest 9.1.1, anyio.
- C: `gcc` = clang 22.1.8 (Windows); `mingw32-make`; cppcheck 2.21.0.
- CI (GitHub Actions): (a) python-tests ubuntu matrix 3.11/3.12 → 22 test + smoke; (b) embedded-c-tests → gcc + cppcheck strict; (c) data-integrity → sha256sum -c (git-LFS).
- Kök Makefile: `test`, `test_python`, `test_c`, `check`, `reproduce-all`, `clean`.

---

## 9. Analist İçin Önerilen Eleştirel Sorular (Opsiyonel Çerçeve)

Bir LLM/analist bu brifingden şu değerlendirmeleri üretebilir:
1. **Savunma sanayii hazırlığı:** "WCET donanımda ölçülmedi" maddesi DO-178C darbe öncesi hangi açık bırakıyor? Geçme kriteri nasıl olmalı?
2. **OOD/emniyet:** AUROC 0.4607 göz önüne alındığında, kapalı dünya softmax'ı gerçek bir askeri senaryoda kabul edilebilir mi? Öneriler (OS-CFAR benzeri OOD başlıkları, cosine/energy-based OOD).
3. **Sınıf dengesi:** BMP-2 %30 geri çağırma varsa, eğitim (class weighting, doğru örnek seçimi) ve operasyonel güven eşiklemesi nasıl düzeltilmeli?
4. **Metrik doğruluğu:** Çözünürlüğün teorik 1.499/0.750 m'ye karşı 3.747/1.050 m ölçülmesi Hamming genişletmesiyle tutarlı mı? PSLR −42.23 dB'nin teori (−42.7) ile uyumu ne anlatır?
5. **Veri dürüstlüğü:** "Simüle Sentinel-1" etiketi yeterli mi, yoksa "gerçek SLC" alınmadan da RDA doğrulaması kabul edilebilir mi?

---

*Bu brifing, EdgeSAR sistemi üzerinde 20.09.2026 tarihinde yapılan üç bağımsız denetim turunun, tüm komutların yeniden çalıştırılmasıyla doğrulanmış çıktılarının özüdür. Sayılar çoğaltılabilir; beyan sayıları değildir.*