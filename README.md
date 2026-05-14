# 📱 SMS Güvenlik Kalkanı - Smishing Tespit Sistemi

> **Süleyman Demirel Üniversitesi - Bilgisayar Mühendisliği**  
> **Öğrenci:** Batuhan Can Aracı - 2211012609

SMS tabanlı oltalama (Smishing) saldırılarını tespit eden, makine öğrenmesi destekli mobil uygulama ve backend sistemi.

---

## 📋 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Model Performansı](#-model-performansı)
- [Teknik Detaylar](#-teknik-detaylar)
- [Proje Yapısı](#-proje-yapısı)
- [API Dokümantasyonu](#-api-dokümantasyonu)

---

## 🎯 Proje Hakkında

Smishing (SMS + Phishing), dolandırıcıların SMS mesajları aracılığıyla kullanıcıları sahte web sitelerine yönlendirerek kişisel ve finansal bilgilerini çalmaya çalıştığı bir siber saldırı türüdür.

Bu proje, Türkiye'deki SMS dolandırıcılığını tespit etmek için geliştirilmiş **hibrit bir makine öğrenmesi sistemi** sunar. Sistem, hem metin analizi (TF-IDF) hem de elle çıkarılmış özellikler ile kural tabanlı düzeltmeleri birleştirerek yüksek doğrulukla zararlı mesajları tespit eder.

### Çözülen Problem
- Türkçe SMS dolandırıcılığı tespiti
- Meşru ticari SMS'lerin yanlışlıkla spam olarak işaretlenmesi (false positive) sorunu
- BTK/MERSIS/IYS kodlarının kopyalanarak yapılan gelişmiş dolandırıcılık tespiti

---

## ✨ Özellikler

### Makine Öğrenmesi
- 🤖 **3 model karşılaştırması**: Naive Bayes, SVM (RBF), Random Forest
- 📊 **Hibrit yaklaşım**: TF-IDF vektörleri + 19 manuel özellik
- 🔄 **5-fold Cross Validation** ile overfitting kontrolü
- 📈 **F1 Score: %95.85** (hedef %95 aşıldı)

### Akıllı Özellik Mühendisliği
- 🏛️ **BTK B-Kodu tespiti**: Resmi ticari SMS'leri tanıma (B001, B002, B243...)
- 🏢 **MERSIS numarası tespiti**: Şirket kayıt numarası kontrolü
- 📋 **IYS (İleti Yönetim Sistemi)** bilgisi tespiti
- 🌐 **Resmi domain whitelisti**: 150+ güvenilir domain
- 👤 **Gönderici analizi**: Alfanümerik ID, kısa kod, mobil numara sınıflandırma
- 🔗 **URL kısaltıcı tespiti**: bit.ly, t2m.io, fstpy.cc vb.
- ⚠️ **Şüpheli TLD tespiti**: .xyz, .top, .click, .cc vb.
- 🏷️ **Marka taklit tespiti**: Domain içinde marka adı + resmi olmayan domain
- 🚨 **Kumarhane/bahis kelime tespiti**: çark, casino, slot, bahis vb.

### Güvenlik
- 🛡️ **İki yönlü kural tabanlı düzeltme**:
  - Model spam dedi → Resmi gönderici + BTK kodu → GÜVENLİ'ye çevir
  - Model meşru dedi → Mobil numara + URL kısaltıcı → ZARALI'ya çevir
- 🔒 **BTK kodu kopyalama saldırısı tespiti**: Kişisel numaradan gelen mesajlarda BTK/MERSIS kodlarına güvenilmez

### Mobil Uygulama
- 📱 **Flutter** ile geliştirilmiş Android uygulaması
- 📨 **Gelen kutusu tarama**: Tüm SMS'leri otomatik analiz
- ✍️ **Manuel test**: SMS metnini yapıştırarak analiz
- 🎨 Modern ve kullanıcı dostu arayüz

---

## 🏗️ Mimari

```
┌─────────────────────┐     HTTP POST     ┌──────────────────────┐
│                     │   /predict        │                      │
│  Flutter Mobil App  │ ───────────────▶  │  FastAPI Backend     │
│  (Android)          │                   │  (Python)            │
│                     │ ◀───────────────  │                      │
│  • SMS okuma        │   JSON Response   │  • TF-IDF + ML Model │
│  • UI gösterim      │                   │  • Özellik çıkarma   │
│  • Manuel test      │                   │  • Kural düzeltme    │
└─────────────────────┘                   └──────────────────────┘
                                                    │
                                                    ▼
                                          ┌──────────────────────┐
                                          │  Model Pipeline      │
                                          │                      │
                                          │  • Türkçe NLP        │
                                          │  • TF-IDF (3000 ft)  │
                                          │  • 19 Manuel Özellik │
                                          │  • Random Forest     │
                                          │  • Kural Tabanlı     │
                                          │    Düzeltme          │
                                          └──────────────────────┘
```

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.10+
- Flutter SDK 3.x+
- Android SDK (fiziksel cihaz veya emülatör)

### Backend Kurulumu

```bash
# 1. Proje dizinine gir
cd "SMS Smishing"

# 2. Python bağımlılıklarını kur
pip install -r requirements.txt

# 3. Modeli eğit
python train_model.py

# 4. API sunucusunu başlat
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### Mobil Uygulama Kurulumu

```bash
# 1. Flutter dizinine gir
cd smishing_app

# 2. Bağımlılıkları kur
flutter pub get

# 3. Uygulamayı cihaza yükle
flutter run
```

### Bağımlılıklar (requirements.txt)

```
pandas
numpy
scikit-learn
scipy
fastapi
uvicorn
pydantic
```

---

## 📖 Kullanım

### 1. Backend'i Başlat
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### 2. Bilgisayarın Yerel IP Adresini Bul
```bash
# Windows
ipconfig
# Kablosuz LAN adaptörü > IPv4 Adresi (örn: 192.168.1.2)
```

### 3. Mobil Uygulamayı Aç
- IP adresini uygulamaya gir
- **Gelen Kutusu** sekmesinden tüm SMS'leri tara
- **Manuel Test** sekmesinden tek bir SMS analiz et

### 4. Sonuçları Yorumla

| Renk | Anlam | Açıklama |
|------|-------|----------|
| 🟢 Yeşil | GÜVENLİ (Meşru) | Güvenilir mesaj |
| 🔴 Kırmızı | ZARALI (Smishing/Spam) | Dolandırıcılık şüphesi |

Her sonuçta gösterilen bilgiler:
- **Gönderici tipi**: resmi_id, alfanumerik, mobil_tr, uluslararası
- **Güven skoru**: Gönderici güvenilirlik puanı (0-1)
- **Tehlike skoru**: Mesajdaki tehlikeli kelime sayısı
- **URL durumu**: Resmi domain, taklit veya şüpheli
- **BTK Kodu**: ✅ Var / ❌ Yok
- **MERSIS**: ✅ Var / ❌ Yok
- **IYS Bilgisi**: ✅ Var / ❌ Yok

---

## 📊 Model Performansı

### Son Eğitim Sonuçları

| Model | Test F1 | Train F1 | CV F1 (5-fold) | Gap | Durum |
|-------|---------|----------|----------------|-----|-------|
| **Random Forest** ⭐ | **95.85%** | 100% | 94.67% | 0.04 | ✅ Sağlıklı |
| Naive Bayes | 95.03% | 98.12% | 94.05% | 0.03 | ✅ Sağlıklı |
| SVM (RBF) | 78.01% | 82.14% | 80.81% | 0.04 | ✅ Sağlıklı |

### Confusion Matrix (Random Forest)

```
              Tahmin: Ham  Tahmin: Spam
Gerçek: Ham      227          4
Gerçek: Spam       9        150
```

- **Accuracy**: %96.7
- **Precision**: %97.4
- **Recall**: %94.3
- **F1 Score**: %95.85

### Veri Seti

| Metrik | Değer |
|--------|-------|
| Toplam SMS | 1.557 |
| Spam (zararlı) | 635 (%40.8) |
| Ham (meşru) | 921 (%59.2) |
| Train/Test oranı | %75 / %25 |

---

## 🔧 Teknik Detaylar

### Metin Ön İşleme Pipeline

```python
SMS Metni
  ├── Küçük harfe dönüştürme
  ├── URL tokenizasyonu (resmi/şüpheli/kısaltıcı)
  ├── Özel karakter temizleme
  ├── Türkçe stop word kaldırma (100+ kelime)
  └── Temiz metin çıktısı
```

### Özellik Seti (19 Manuel Özellik)

| # | Özellik | Açıklama |
|---|---------|----------|
| 1 | `uzunluk` | Mesaj karakter sayısı |
| 2 | `banka_bildirimi` | Banka bildirimi deseni varlığı |
| 3 | `url_var` | URL içeriyor mu |
| 4 | `unlem_sayisi` | Ünlem işareti sayısı |
| 5 | `rakam_orani` | Mesajdaki rakam yoğunluğu |
| 6 | `buyuk_harf_orani` | Büyük harf oranı |
| 7 | `tehlike_skoru` | Tehlikeli anahtar kelime sayısı |
| 8 | `iban_var` | IBAN numarası varlığı |
| 9 | `soru_var` | Soru işareti varlığı |
| 10 | `resmi_domain_var` | Resmi domain tespiti |
| 11 | `domain_taklit` | Marka taklit tespiti |
| 12 | `domain_suphe` | Şüpheli domain skoru |
| 13 | `url_kisaltma` | URL kısaltıcı tespiti |
| 14 | `aciliyet_skoru` | Aciliyet yaratan kelime sayısı |
| 15 | `mesru_banka_deseni` | Meşru banka bildirimi kalıbı |
| 16 | `has_btk_code` | BTK B-kodu varlığı (B001-B999) |
| 17 | `has_mersis` | MERSIS şirket kaydı varlığı |
| 18 | `has_iys_info` | IYS opt-out bilgisi varlığı |
| 19 | `gonderen_guven` | Gönderici güven skoru |

### Kural Tabanlı Düzeltme Akışı

```
Model tahmini alındı
│
├── Model "SPAM" dedi
│   ├── Gönderici güvensiz (mobil/uluslararası) + URL kısaltıcı
│   │   └── SPAM kalsın (BTK kodları kopyalanmış olabilir)
│   ├── Gönderici güvensiz + MERSIS/IYS var
│   │   └── SPAM kalsın (hafif güven düşürülür)
│   ├── Gönderici güvenilir + BTK kodu var
│   │   └── → GÜVENLİ'ye çevir
│   ├── MERSIS + IYS + güvenilir gönderici
│   │   └── → GÜVENLİ'ye çevir
│   └── Resmi domain + resmi gönderici
│       └── → GÜVENLİ'ye çevir
│
└── Model "HAM" dedi
    ├── Gönderici güvensiz + URL kısaltıcı
    │   └── → ZARALI'ya çevir (dolandırıcı taklidi)
    ├── Gönderici güvensiz + şüpheli domain
    │   └── → ZARALI'ya çevir
    └── Gönderici güvensiz + domain taklit
        └── → ZARALI'ya çevir
```

---

## 📁 Proje Yapısı

```
SMS Smishing/
├── train_model.py          # Model eğitim pipeline (835 satır)
│   ├── turkce_on_isleme()  # Türkçe NLP ön işleme
│   ├── ozellik_cikar()     # 19 manuel özellik çıkarma
│   ├── gonderen_analiz()   # Gönderici güven analizi
│   ├── _url_analiz()       # URL domain analizi
│   ├── modeli_egit()       # Model eğitim ve karşılaştırma
│   └── sms_tahmin_et()     # Tek SMS tahmin fonksiyonu
│
├── app/
│   └── api.py              # FastAPI REST API endpoint
│
├── data/
│   ├── turkce_sms_dataset.csv       # Eğitim veri seti (1557 SMS)
│   └── turkce_sms_dataset_backup.csv # Yedek veri seti
│
├── models/
│   └── smishing_model.pkl  # Eğitilmiş model (pickle)
│
├── smishing_app/           # Flutter mobil uygulama
│   ├── lib/
│   │   └── main.dart       # Uygulama kodu
│   ├── android/
│   │   └── app/src/main/
│   │       └── AndroidManifest.xml  # İzinler
│   └── pubspec.yaml        # Flutter bağımlılıkları
│
├── merge_datasets.py       # Veri seti birleştirme aracı
├── requirements.txt        # Python bağımlılıkları
└── README.md               # Bu dosya
```

---

## 🌐 API Dokümantasyonu

### POST /predict

SMS mesajını analiz eder.

**Request:**
```json
{
  "message": "Hesabınız bloke edildi! garanti-dogrula.xyz",
  "sender": "+905551234567"
}
```

**Response:**
```json
{
  "mesaj": "Hesabınız bloke edildi! garanti-dogrula.xyz",
  "gonderen": "+905551234567",
  "gonderen_bilgi": {
    "guven": 0.3,
    "tur": "mobil_tr"
  },
  "url_bilgi": {
    "resmi": 0,
    "taklit": 1,
    "suphe_skoru": 2
  },
  "btk_kodu": false,
  "mersis": false,
  "iys_bilgi": false,
  "sonuc": "ZARALI (Smishing/Spam)",
  "etiket": "spam",
  "guven": "100.0%",
  "ham_guven": "0.0%",
  "tehlike_skoru": 1
}
```

### Swagger UI

API çalışırken interaktif dokümantasyon:
```
http://localhost:8000/docs
```

---

## 🔬 Whitelisted Kaynaklar

### Resmi Gönderici ID'leri (150+)
Bankalar, GSM operatörleri, kargo firmaları, e-ticaret siteleri, devlet kurumları, marketler, kozmetik markaları, havayolları ve daha fazlası.

### Resmi Domain'ler (180+)
`.com.tr`, `.gov.tr`, `.edu.tr` uzantılı resmi kurumlar + kısa URL servisleri (`turkcell.li`, `svr.link`, `madp.tr`).

### Şüpheli TLD'ler (30+)
`.xyz`, `.top`, `.click`, `.site`, `.online`, `.cc`, `.vip`, `.club` ve daha fazlası.

---

## 📄 Lisans

Bu proje Süleyman Demirel Üniversitesi Bilgisayar Mühendisliği bölümü bitirme projesi olarak geliştirilmiştir.

---

## 🙏 Teşekkürler

- SDÜ Bilgisayar Mühendisliği Bölümü
- Scikit-learn, FastAPI, Flutter açık kaynak toplulukları
