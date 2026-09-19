# EdgeSAR — Denetçi Düzeltme Görevi (Bağımsız Denetim TUR-3 Çıktısı)

> **Alıcı:** Geliştirme Ajanı ("Tatlım")
> **Veren:** Bağımsız Yazılım Denetçisi (DO-178C / MISRA-C / MIL-STD uyum)
> **Kural:** Beyana **GÜVENME**. Her madde diskteki koda, dokümana ve terminal çıktısına dayanmalıdır.
> **Kanıt şartı:** Her madde için çalıştırdığın komutun + ham terminal çıktısının (özet DEĞİL) yanına dosya yolu ve `LastWriteTime` bilgisini ekle. Kanıt sunulmayan madde = BAŞARISIZ sayılır.

---

## 0. Genel Hükümler (Tüm Maddeler İçin Geçerli)

1. **MEVCUT BAŞARILARA DOKUNMA:** Aşağıdakiler **KESİNLİKLE değiştirilmeyecek** ve yeniden üretilmeyecek:
   - `modules/module1_rda/` (rda_pipeline.py, synthetic_generator.py) — doğrulandı, çalışıyor.
   - `modules/module2_atr/`, `model.py`, `train.py`, `evaluate.py`, `eval_results/` ve `*.pth` checkpoint'leri.
   - `modules/module3_embedded/` (cfar_detector.c, hal_sar_mock.c, fft_mock.c, main_stm32.c, benchmark_wcet.c) ve Unity testleri.
   - `data/mstar/*.npz` ve `data/synthetic/*.npz` (yeniden üretme, sadece oku).
   - `scripts/mstar_loader.py` CLASS_MAPPING — **bu koddur, doğru kabul edilir; dokunma.**
   - `.github/workflows/ci.yml`.
2. **Her değişiklikten sonra** aşağıdaki doğrulama zincirini çalıştır ve çıktıları gönder:
   - `python -m pytest tests/ -q` → **beklenen: 22 passed** (21 mevcut + 1 yeni)
   - `python run_rda.py --input synthetic --snr 25.0 --output-dir ./output_rda` → beklenen değerler Madde 5'te.
   - `python run_rda.py --input real --output-dir ./output_rda_real`
   - `mingw32-make test` (module3_embedded) → 13/13
   - C derleme: `gcc -Wall -Wextra -pedantic -std=c99 -Werror -Wstrict-prototypes -Wshadow` → 0 hata / 0 uyarı
   - `cppcheck --enable=all --error-exitcode=1` (module3 Makefile `check` hedefi) → exit 0
   - `sha256sum -c docs/DATA_CARDS.md` (Windows'ta `Get-FileHash`) → PASS
3. Kapsam DIŞI taleplere (yeni özellik, model eğitimi, donanım ölçümü) girme. Yalnız aşağıdaki maddeler.

---

## 1. [BLOKER-1] MSTAR LABEL HARİTASI — DOKÜMAN-KOD ÇELİŞKİSİ

**Numaralandırma:** `scripts/mstar_loader.py:24-29` gerçeği şudur (dokunma):
`T72=0, BMP2=1, BTR70=2`. Npz içeriği bunu kanıtlar: train bincount `[232,233,233]`, test bincount `[196,195,196]` → etiket 0 = T-72 (232/196), etiket 1 = BMP-2 (233/195), etiket 2 = BTR-70 (233/196).

**HATALI OLAN:** `data/mstar/DATA_CARD.md:26-28` tablosu hâlâ önceki ters haritalamayı yazıyor (BMP-2=0, BTR-70=1, T-72=2). Bu dosyanın son değişikliği **20.09 00:50** — düzeltme hiç yapılmamış.

**YAPILACAK (sadece `data/mstar/DATA_CARD.md`):**
- Tablo satırlarını şu şekilde kod ile birebir hizala:

```
| **T-72**   | 0 | 232 | 196 | 428 |
| **BMP-2**  | 1 | 233 | 195 | 428 |
| **BTR-70** | 2 | 233 | 196 | 429 |
```

- Aynı dosyanın metin bölümünde "0=BMP-2" veya başka ters sıralama geçiyorsa güncelle. `data/mstar/LICENSE_NOTES.md` ve `docs/DATA_CARDS.md` içinde de sınıf sırası yanlış yazılmış bir liste varsa denetçi kaydıyla not et (Bu maddede dokunma sınırı: `data/mstar/DATA_CARD.md`).

**KANIT:** Tablo içerikli satırların diff'i + dosya `LastWriteTime`'ı + `mstar_loader.py` ile çapraz kontrol.

---

## 2. [YÜKSEK] "GERÇEK SAR" ABARTISI — DÜRÜSTLÜK DÜZELTMESİ

**Gerçek:** `data/open_sar/sentinel1_maritime_sample.npy`, gerçek Sentinel-1 SLC **DEĞİLDİR**. `scripts/sar_real_loader.py` (L64-120) `generate_realistic_maritime_sar_scene()` ile **prosedürel K-dağılımlı deniz clutter simülasyonu** üretiyor. `data/open_sar/DATA_CARD.md` bunu dürüstçe yazıyor ("Esinlenilen Radar", "K-dağılımlı"). Sunum dokümanları ise "Gerçek" diyor.

**HÂLÂ "GERÇEK" İDDİASI TAŞIYAN YERLER (hepsi düzeltilecek):**

| Dosya:Satır | Mevcut (HATALI) | Olması Gereken |
|---|---|---|
| `docs/RESULTS.md:152` | `## 10. Modül 1 (RDA) Gerçek Sivil SAR Odaklama Başarımı` | `## 10. Modül 1 (RDA) Simüle Açık SAR Odaklama Başarımı` |
| `docs/RESULTS.md:154` | `...açık sivil SAR (Sentinel-1 SLC deniz sahnesi)` | `...simüle açık SAR (Sentinel-1 tarzı K-dağılımlı deniz sahnesi)` |
| `docs/RESULTS.md:156` | `Gerçek Açık SAR (Sentinel-1 Deniz)` | `Simüle Açık SAR (Sentinel-1 tarzı K-dağılımlı)` |
| `docs/DATA_CARDS.md:12` | `Open SAR (Sentinel-1) ... Gerçek/Gerçekçi Sivil` | `... Simüle/Gerçekçi (K-dağılımlı, prosedürel) Sivil` |
| `README.md:33` | `(Real Sentinel)` | `(Simulated Sentinel-style)` |
| `README.md:44` | `Real Sentinel-1 SLC Scene` | `Simulated Sentinel-1-style Scene` |
| `README.md:154` | `real civilian SAR data (Sentinel-1 SLC style)` | `simulated civilian SAR scene (Sentinel-1-style K-distributed)` |
| `run_rda.py:375` | `Loading real/open SAR data` | `Loading simulated open SAR scene (K-distributed, Sentinel-1 style)` |

**Ayrıca:**
- `docs/LIMITATIONS.md` Modül 1 bölümüne **açık bir ifşa maddesi** ekle: "Açık SAR örneği gerçek Sentinel-1 SLC verisi değildir; `sar_real_loader.generate_realistic_maritime_sar_scene` ile üretilmiş prosedürel K-dağılımlı deniz sahnesidir. Bu yüzden gerçek Sentinel-1 spekle/geometri karakteri simülasyonla sınırlıdır."
- `run_rda.py:481-492` içindeki `metrics_summary["source"]` değeri `args.input=="real"` iken `"real"` yazıyor → `"simulated_open"` veya en azından `"real (simulated Sentinel-1-style)"` olarak değiştir; `metrics.json` şemayı değiştiriyorsan README/RESULTS'taki ilgili satırları da güncelle.

**KANIT:** Değiştirilen her satırın diff'i + `scripts/sar_real_loader.py` içindeki üretim fonksiyonuna referans.

---

## 3. [YÜKSEK] TEST SAYAÇLARI 20/20 → 21/21 (7 RDA)

Gerçek durum: `python -m pytest tests/ -q` → **21 passed** (7 RDA, 5 ATR, 1 Integration, 4 Property, 4 Regression). Aşağıdaki bayat sayılar düzeltilecek:

| Dosya:Satır | Mevcut | Yeni |
|---|---|---|
| `README.md:6` | `Pytest-20%2F20%20Passing` | `Pytest-21%2F21%20Passing` |
| `README.md:52` | `20 / 20 Pytest Passing` | `21 / 21 Pytest Passing` |
| `README.md:239` | `===== 20 passed in 7.14s =====` (bayat konsol kopyası) | Güncel çıktı: `21 passed in ...` |
| `README.md:281` | `20 / 20 Pytest tests passing` | `21 / 21` |
| `docs/RTM.md:19` | `Automated Python Pytest Suite: 20 / 20 Passing (6 RDA, ...)` | `21 / 21 Passing (7 RDA, 5 ATR, 1 Integration, 4 Property, 4 Regression)` |
| `docs/RTM.md:20` | — | Alt maddeye "7 RDA" dağılımını yansıt (6→7) |
| `docs/RTM.md:97` | `20 / 20 Tests Passed in ~7s` | `21 / 21 Tests Passed in ~7s` |

**RTM ek görevi:** `docs/RTM.md` geriye dönük izlenebilirlik tablosuna yeni test `test_isolated_target_pslr_measurement` için satır ekle (Madde 4'teki fonksiyon ve ilgili REQ-RDA-PSLR maddesiyle iki yönlü bağ). "Requirements Traced to Tests: 15/15" üst sayacını yeni eşleşmeye göre güncelle (değişmezse gerekçesiyle koru).

**NOT (scan):** Depoda "20/20" veya "6 RDA" yazan başka belge (ör. `docs/RTM.md`, `README.md`, `.agents/*`) bulursan denetçi kaydıyla aynı kurala uyarsın; her bulduğunu rapora listele.

**KANIT:** `pytest tests/ -q` ham çıktısı + güncellenen satırlar.

---

## 4. [YÜKSEK] İZOLE PSLR İÇİN ÇOK HEDEFLİ GERİLEME TESTİ (EKSİK)

Mevcut `tests/test_rda.py:285-318` (`test_isolated_target_pslr_measurement`) **yalnız TEK hedefli sahneyi** test ediyor; `run_rda.py`'nin 5-hedefli takımyıldız CLI yolunu korumuyor. Denetçinin bir önceki turda istediği gerileme testi eklenmemiş.

**YAPILACAK:** `tests/test_rda.py`'ye yeni test ekle (mevcut testi bozma):
- `SyntheticSARSpectrumGenerator` ile `n_azimuth=512, n_range=1024`, 5 hedefli kanonik takımyıldızı (`get_canonical_5point_constellation` veya `[PointTarget(0,0,1.0), (+30,0,0.8), (-30,0,0.8), (0,+30,0.7), (+30,+30,0.9)]`), `snr_db=25.0, seed=42` üret.
- `RDAPipeline` ile odakla; merkez hedefi `measure_resolution_and_pslr` ve `measure_isolated_target_pslr(..., guard_bins=15)` ile ölç.
- **Geçme koşulları (deterministik beklenen değerler):**
  - izole **range_pslr_db ≤ −38.0 dB** (mevcut: −43.9)
  - izole **azimuth_pslr_db ≤ −28.0 dB** (mevcut: −31.1)
  - izole değerler, komşu RCS oranı değil gerçek yan lob olsun diye **her ikisi de ≤ −28 dB** ve ayrıca izole range, ±18 pencere range PSLR'inden **daha iyi veya eşit** (≤) olsun.
- Testi RTM geriye dönük tablosuna "Madde 3" kapsamında bağla.

**KANIT:** Yeni test fonksiyonu + `pytest tests/test_rda.py::<yeni_test> -v` çıktısı + tam suite (22 passed).

---

## 5. [ORTA] AZİMUT PSLR ANA-LOB KESİM ARTERAKTI (-7.44 dB)

**Tanı:** `run_rda.py:101-118` içindeki `measure_resolution_and_pslr`, azimut ekseninde ana lobu ±5 bin kapsamıyor. Azimut ana lobu ~±7 bine, geçiş (skirt) bölgesi ~±15 bine uzanıyor (satır 250'de −7.4 dB, satır 249/263'te −10.6 dB, satır 244/266'da −29.9/−31.0 dB). Bu yüzden ±18 penceresine ana lob eteği sızıyor ve CLI `Azimuth PSLR: -7.44 dB` basıyor — bu değer **gerçek yan lob değil**, ana lob/geçiş bölgesi artefaktıdır. Gerçek azimut ilk yan lobu −31.1 dB'dir (izole ölçümün kanıtı; izole ölçümde guard=15, gerçek ilk yan lob bandı satır ~238-240 / ~273-275'tir).

**YAPILACAK:**
1. `measure_resolution_and_pslr`'ye **eksen bazlı** ana-lob koruması ekle (`mainlobe_guard_bins_per_axis` parametresi):
   - **range ±5** (dokunma; mevcut −42.23 dB gerçek Hamming yan lobudur, teori −42.7 dB).
   - **azimut ±16** (ana lob + geçiş bölgesinin tamamını dışlar; hedef değer **≤ −28 dB**, beklenen ~−31 dB).
   - Uygulamadan önce azimut profili üzerinde (satır 233-280 aralığında) yeni korumanın sonuç değerini doğrula: sonuç −28 dB'den iyi değilse koruma genişliğini artır.
2. Değişikliklerden sonra **tüm üretilmiş ölçüm artefaktlarını yeniden üret** ve rakamları güncelle:
   - `output_rda/metrics.json`, `output_rda_real/metrics.json` (Madde 0 zinciriyle `run_rda.py --input real` dahil) — azimut PSLR değeri eskisinden (−7.44) yenisine geçecek.
   - `docs/RESULTS.md` ve `README.md` içinde RDA tablosunda listelenen azimut PSLR değeri varsa yeni değerle hizala.
3. **DOKUNMA:** `docs/RTM.md` satır bağları doğru; sadece değer atıf yerlerini güncelle.

**KANIT:** Değişen fonksiyon diff'i + CLI çıktısı (yeni azimut PSLR değeri) + pytest tam suite + metrics.json yeni değerleri.

---

## 6. [ORTA] LATANS SAYILARI — RESULTS.md ↔ eval JSON ÇELİŞKİSİ

`eval_results/evaluation_summary.json` (buna uy): **latency mean = 16.33 ms, p95 = 25.74 ms, FPS = 61.24**.
`docs/RESULTS.md:138-140` hâlâ eski değerleri yazıyor: 17.60 ms / 56.8 FPS / 21.25 ms p95. Ayrıca `docs/RESULTS.md:36` "…/ 17.6 ms" hücresi de eski.

**YAPILACAK:** `docs/RESULTS.md` içindeki tüm gecikme/başarım hızı/P95 hücrelerini JSON değerleriyle hizala; hücreyi `eval_results/evaluation_summary.json` kaynağına atıfla ("Kaynak: eval_results/evaluation_summary.json") güncelle. README'de aynı rakam geçiyorsa orayı da güncelle.

**KANIT:** diff + JSON dosyasındaki ilgili satırlara referans.

---

## 7. [DÜŞÜK] İZOLE ÖLÇÜM NOTU YANLIŞ (`run_rda.py:154`)

`measure_isolated_target_pslr`'nin `measurement_note`'u her iki eksen için "±20 bins" diyor; oysa **menzil ±20, azimut ±150**. Notu gerçeği yansıtacak şekilde düzelt, örnek:

```
"Isolated cuts strictly bounded: range +/-20 bins, azimuth +/-150 bins, exterior to constellation neighbors (+/-24 range, +/-200 azimuth bins)"
```

Ayrıca fonksiyonda `guard_bins` default `4` iken CLI onu `15` ile çağırıyor; bu kafa karışıklığını gidermek için default'u `15` ile tutarlı yap (CLI davranışı değişmeyecek).

**KANIT:** diff + `python run_rda.py --input synthetic` çıktısında Note satırı.

---

## 8. KAPANIŞ / TESLİM KOŞULU

1. Tüm maddeler bittiğinde Madde 0'daki **tam doğrulama zincirini** tek seferde çalıştır ve **ham çıktıları** (kırpmadan) gönder.
2. Aşağıdaki tabloyu doldur:

| Madde | Durum (PASS/FAIL) | Kanıt (dosya + komut + çıktı özeti) |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |

3. **Yasak:** Bu görevde "yaptım / tamam / hallettim" tarzı kanıtsız beyan. Her satırın karşısında ham terminal çıktısı veya diff olmalı.
4. Mevcut denetim sertifikası sadece 1, 4, 5 numaralı kod maddeleri ve kanıtlı 2/3/6/7 maddeleri tamamlandığında "GEÇTİ"ye çevrilir.