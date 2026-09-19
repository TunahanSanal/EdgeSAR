# EdgeSAR — Kapsam Beyanı (Scope Statement)

> **Proje Türü:** Bireysel Araştırma, Öğrenme ve Mühendislik Portföy Projesi  
> **Tarih:** 2026-09-20  
> **Durum:** Aktif Geliştirme / Deneysel Doğrulama  

---

## 1. Projenin Amacı ve Kapsamı

Bu proje bir bireysel öğrenme ve ileri mühendislik portföy projesidir. Temel hedefleri şunlardır:

1. **Radar Sinyal İşleme:** Sentetik Açıklıklı Radar (SAR) görüntüleme zincirinin (Range-Doppler Algorithm - RDA, Range Matched Filtering, Kaiser pencereleme, menzil göçü düzeltmesi - RCMC, Azimut eşlenik filtreleme) teorik temellerini sıfırdan Python ile uygulayarak derinlemesine öğrenmek.
2. **SWaP Kısıtlı Derin Öğrenme:** Boyut, Ağırlık ve Güç (SWaP) kısıtlı gömülü ortamlar için parametre-verimli (< 2M parametre), dikkat mekanizmalı (ECA) hafif bir CNN mimarisi (Ghost-ECANet) tasarlamak ve Açıklanabilir Yapay Zeka (XAI / Grad-CAM) ile saçıcı merkezleri doğrulamak.
3. **Emniyet-Bilinçli Gömülü C Tasarımı:** Havacılık ve savunma standartlarından (DO-178C DAL-B ilkeleri, MISRA-C:2012 rehberi) ilham alarak sıfır dinamik bellek (`malloc` yok), statik tamponlama, Radix-2 DIT FFT ve 1D CA-CFAR algoritmalarını C diliyle gerçeklemek ve birim testlerle (%100 Unity) doğrulamak.
4. **Gerçek ve Açık Verilerle Doğrulama:** Sentetik veri simülatörünün ötesine geçerek açık kaynaklı radar kıyaslama verileri (Sandia MSTAR SAR hedef tanıma seti ve açık SAR SLC sahneleri) ile modeli ve algoritmaları nesnel olarak test etmek.

---

## 2. Bu Proje Ne DEĞİLDİR?

Şeffaflık ve bilimsel dürüstlük adına sınırların net çizilmesi zorunludur:

- **Sertifikalı Bir Aviyonik Sistem DEĞİLDİR:** DO-178C, MISRA-C:2012, MIL-STD-1553B ve MIL-STD-882E standartları projenin mimari disiplinine rehberlik etmiş ve bu standartların felsefesi uygulanmıştır; ancak yazılım akredite bir bağımsız denetim kuruluşu (FAA/EASA/SSB vb.) tarafından resmi olarak sertifikalandırılmamıştır.
- **Operasyonel Bir Askeri Ürün DEĞİLDİR:** Herhangi bir savunma sanayii kurumunun resmî projesi veya tedarik ürünü olmayıp, akademik ve teknik prensipleri gösteren bağımsız bir AR-GE prototipidir.
- **Gerçek Uçuş Donanımında Test Edilmiş Bir Sistem DEĞİLDİR:** Modül 3 gömülü kodları standart x86_64 host simülasyonunda ve donanım soyutlama katmanı (HAL Mock) üzerinde test edilmiştir. Mikrodenetleyiciye (STM32/CMSIS-DSP) taşınabilirliği hedeflenmiş olmakla birlikte gerçek aviyonik veri yolunda uçurulmamıştır.

---

## 3. Hedef ve Genelleştirilebilir Kullanım Alanları

Her ne kadar model MSTAR'daki standart 3 kara aracı sınıfı (T-72, BMP-2, BTR-70) üzerinde kıyaslansa da, önerilen hafif mimari ve sinyal işleme hattı şu sivil/çift-kullanımlı SAR-ATR senaryolarına genelleşebilir:

- **Afet ve Kriz İzleme:** Deprem, heyelan veya sel sonrası enkaz ve çöken yapı tespiti.
- **Denizcilik ve Arama-Kurtarma:** Açık denizlerde gemi, cankurtaran filikası veya buzdağı tespiti (CFAR + hafif sınıflandırıcı).
- **Çevresel Gözlem:** Kaçak orman tahribatı, petrol sızıntısı ve kutup buzulu takibi.

---

## 4. İddia Seviyesi ve Doğrulama Taahhüdü

Bu depoda sunulan tüm başarım metrikleri (çözünürlük, PSLR, F1-skoru, çıkarım süresi, bellek kullanımı):
- Hangi veri kümesinde (sentetik vs. gerçek MSTAR),
- Hangi test protokolüyle (stratified split, 17° train / 15° test veya 5-fold CV),
- Hangi donanım ortamında (CPU/GPU/Host C) elde edildiği şeffafça açıklanarak raporlanır.
- Hatalar, sınırlamalar ve out-of-distribution (dağılım dışı) düşüşleri gizlenmez, `docs/LIMITATIONS.md` içerisinde dokümante edilir.
