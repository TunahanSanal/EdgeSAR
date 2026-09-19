# EdgeSAR — Veri Kartları Kataloğu (Data Cards Master Document)

Bu doküman, EdgeSAR sisteminde kullanılan tüm veri kaynaklarının (gerçek, sivil açık veri ve sentetik) künyelerini, lisanslarını, parametrelerini ve kısıtlarını bir arada sunar.

---

## 1. Veri Kaynakları Özeti

| Veri Kaynağı | Tür | Sensör / Mod | Boyut / Format | Kullanım Alanı | Detaylı Kart |
|---|---|---|---|---|---|
| **MSTAR** | Gerçek Askeri Radar | X-Band (9.6 GHz) Spotlight | 128x128 gri seviye (1,285 hedef + 1,838 OOD) | Modül 2 ATR Eğitimi, 5-Fold CV, OOD Testi | [`data/mstar/DATA_CARD.md`](../data/mstar/DATA_CARD.md) |
| **Open SAR (Sentinel-1)** | Simüle/Gerçekçi (K-dağılımlı, prosedürel) Sivil | C-Band (5.4 GHz) Stripmap/IW | 512x512 SLC kompleks I/Q | Modül 1 RDA Odaklama, Entropi/Kontrast, CFAR | [`data/open_sar/DATA_CARD.md`](../data/open_sar/DATA_CARD.md) |
| **Sentetik ASC** | Fizik Simülatörü | LFM Chirp & Saçıcı Merkez | Parametrik (128x128 çip & 512x1024 ham) | Ön-eğitim (Pre-training), Kontrollü SNR/Açı analizleri | [`data/synthetic/DATA_CARD.md`](../data/synthetic/DATA_CARD.md) |

---

## 2. Karşılaştırmalı Veri Kümesi Özellikleri

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 EdgeSAR Veri Dağılımı                  │
                  └────────────────────────────────────────────────────────┘
                                               │
             ┌─────────────────────────────────┼─────────────────────────────────┐
             ▼                                 ▼                                 ▼
   [ MSTAR SAR Benchmark ]          [ Open SAR / Sentinel-1 ]         [ Sentetik Fizik ASC ]
   • Gerçek X-band verisi           • Sivil deniz/kıyı sahnesi        • LFM Chirp dalga formu
   • T-72, BMP-2, BTR-70            • K-dağılımlı deniz clutter'ı    • Gauss PSF konvolüsyonu
   • 17° Eğitim / 15° Test          • Gemi hedefleri (4 adet)         • Kontrollü gürültü / açı
   • 7 adet OOD sınıfı              • SLC Kompleks (512x512)          • Ön-eğitim & dayanıklılık
```

### 2.1 MSTAR (Moving and Stationary Target Acquisition and Recognition)
- **Toplayan Kuruluş:** Sandia National Laboratories & DARPA / AFRL.
- **Kullanım Lisansı:** Kamuya açık araştırma ve kıyaslama (Bkz. [`data/mstar/LICENSE_NOTES.md`](../data/mstar/LICENSE_NOTES.md)).
- **Standart Protokol:** 17° depresyon açısı eğitim (698 çip), 15° depresyon açısı test (587 çip).
- **Rolü:** Modül 2 derin ATR modelinin literatür standardında dürüstçe test edilmesi.

### 2.2 Open SAR / Sentinel-1 Civil Maritime
- **Kaynak / Esinlenme:** ESA Copernicus Sentinel-1 Single Look Complex (SLC).
- **Hedef:** Deniz gözetleme, sivil arama-kurtarma, kıyı gemi tespiti.
- **Odaklama Metrikleri:** Shannon Görüntü Entropisi ve Görüntü Kontrastı ($\sigma / \mu$).
- **Rolü:** Sistemin salt askeri hedeflerle sınırlı kalmayıp sivil radar sahnelerinde de sinyal işleme ve CFAR zincirini doğrulayabildiğini göstermek.

### 2.3 Sentetik Saçıcı Merkez (Attributed Scattering Center)
- **Modelleme:** Noktasal saçıcılar, köşe yansıtıcılar, silindirik gövde yansımaları, radar gölgesi ve Rayleigh benek gürültüsü.
- **Rolü:** Sıfırdan transfer öğrenme (Transfer Learning) için ön-eğitim verisi sağlamak; kontrollü gürültü enjeksiyonu (-5 dB ile +20 dB SNR) testleri yapmak.

---

## Veri Bütünlüğü Doğrulama (Integrity Verification)

| Dosya | SHA-256 Hash | Boyut |
|-------|-------------|-------|
| `data/mstar/train_cache.npz` | `7691faebeac8f42a43376353441faeb5042bbfc28a6e6e2bf660aff0e3f5f5d7` | 14,772,938 bytes |
| `data/mstar/test_cache.npz` | `748e3658d22f44417f997674869c4500913a76158141ae69fbbc297976a0daad` | 12,299,637 bytes |

**Doğrulama komutu:**
```bash
python -c "import hashlib; f=open('data/mstar/train_cache.npz','rb'); print(hashlib.sha256(f.read()).hexdigest())"
```

