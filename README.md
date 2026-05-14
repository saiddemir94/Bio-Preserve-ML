# BioPreserve-AI

Gıda endüstrisinde sentetik koruyuculara (sodyum nitrit, sorbik asit vb.) alternatif olabilecek **doğal antimikrobiyal peptitleri (AMP)** hızlı ve düşük maliyetle belirlemek için geliştirilmiş makine öğrenmesi destekli bir karar destek sistemidir.

Sistem; biyolojik kural filtrelemesi, Random Forest sınıflandırıcısı ve gıda matrisi/patojen uyumluluk kontrollerini birleştiren **çok aşamalı bir tarama pipeline'ı** çalıştırır. Kullanıcı arayüzü FastAPI backend + React (Vite) frontend olarak sunulmaktadır.

---

## İçindekiler

1. [Sistem Pipeline'ı](#sistem-pipelineı)
2. [Veri Seti](#veri-seti)
3. [Özellik Çıkarımı](#özellik-çıkarımı)
4. [Biyolojik Filtreleme Kuralları](#biyolojik-filtreleme-kuralları)
5. [Makine Öğrenmesi Modeli](#makine-öğrenmesi-modeli)
6. [Gıda Matrisleri ve Patojenler](#gıda-matrisleri-ve-patojenler)
7. [Pipeline Performansı](#pipeline-performansı)
8. [Proje Yapısı](#proje-yapısı)
9. [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma)
10. [API Referansı](#api-referansı)
11. [CSV Yükleme Formatı](#csv-yükleme-formatı)
12. [Modeli Yeniden Eğitme](#modeli-yeniden-eğitme)
13. [Dağıtım](#dağıtım)

---

## Sistem Pipeline'ı

Her peptit dizisi aşağıdaki aşamalardan sırayla geçer. Herhangi bir aşamada elenen dizi, sonraki aşamaya iletilmez ve **Rejected** (Elendi) olarak raporlanır.

```
Ham Veri (DRAMP veritabanı CSV dosyaları + özel örnekler)
        │
        ▼
[1] Veri Yükleme & Normalleştirme
    build_amp_dataset.py
    • Kodlama düzeltme (UTF-8, latin-1)
    • Sütun adı eşleme (farklı kaynak formatları)
    • DRAMP kimliği tespiti (dramp_id sütunu varlığına göre)
        │
        ▼
[2] Özellik Çıkarımı
    features/feature_extraction.py
    • 4 biyofiziksel özellik hesaplanır
    • Geçersiz amino asit içeren diziler elenir
        │
        ▼
[3] Etiketleme & Tekilleştirme
    • MIC eşiği: ≤ 32 µg/mL → aktif (label=1)
    • Yinelenen diziler kaldırılır (öncelik: aktif > inaktif)
        │
        ▼
[4] Biyolojik Kural Filtrelemesi   ← pipeline.py
    • Uzunluk: 15–30 AA
    • Net yük: +3 ile +9
    • Hidrofobisite oranı: %40–65
    • Anahtar AA oranı: ≥ %25
        │
        ▼ (geçemeyenler Rejected)
[5] ML Tahmini   ← Random Forest
    • predict_proba ile 0–1 arası AMP olasılık skoru
    • prediction ≠ 1 olanlar Rejected
        │
        ▼ (ML'den geçemeyenler Rejected)
[6] Patojen Uyumluluk Kontrolü
    • Seçilen patojen için net yük ve hidrofobisite kontrolü
        │
        ▼
[7] Gıda Matrisi Uyumluluk Kontrolü
    • Tuz, pH, yağ içeriği koşullarına göre değerlendirme
        │
        ▼
[8] Nihai Sonuç: Approved / Rejected
    candidate_report.csv olarak dışa aktarılır
```

---

## Veri Seti

### Ham Veri Kaynakları

Tüm ham veriler `data/raw/` dizininde bulunmaktadır. Gerçekte kullanılan kaynaklar:

| Dosya | Kaynak | İçerik |
|---|---|---|
| `Antibacterial_amps.csv` | DRAMP | Antibakteriyel AMP'ler |
| `general_amps.csv` | DRAMP | Genel AMP veritabanı |
| `plant_amps.csv` | DRAMP | Bitki kaynaklı AMP'ler |
| `custom_sample_amp_data.csv` | Özel | Küçük özel örnek seti |

> **Kaynak tespiti otomatiktir.** `build_amp_dataset.py`, dosyada `dramp_id` sütununu bulduğunda dosyayı otomatik olarak DRAMP formatında işler; dosya adından bağımsızdır.

### Veri Seti İstatistikleri

| Parametre | Değer |
|---|---|
| Toplam benzersiz peptit dizisi | **9.234** |
| DRAMP kayıtları | 9.228 (%99.9) |
| Özel kayıtlar | 6 (%0.1) |
| Eğitim seti (%80) | **7.387 dizi** |
| Test seti (%20) | **1.847 dizi** |
| Bölme yöntemi | Tabakalı rastgele örnekleme (stratify=y) |
| Eğitim/test ayrımı dosyası | `split_and_retrain.py` |

Ana veri seti dosyaları:

- `data/amp_master_dataset.csv` — tüm sütunları içeren tam kayıt (9.234 satır)
- `data/amp_dataset.csv` — yalnızca 4 özellik + etiket (eğitim için, 7.387 satır)
- `data/database_peptides.csv` — test seti dizi listesi (pipeline varsayılan girdisi, 1.847 satır)

---

## Özellik Çıkarımı

`features/feature_extraction.py` her peptit dizisinden 4 biyofiziksel özellik hesaplar:

| Özellik | Açıklama | Hesaplama Yöntemi |
|---|---|---|
| `length` | Dizi uzunluğu | Amino asit sayısı |
| `net_charge` | Net elektrik yükü | K,R,H: +1 / D,E: -1 (pH 7 koşulları) |
| `hydrophobic_ratio` | Hidrofobisite oranı | {A,V,I,L,M,F,W,Y} sayısı / toplam uzunluk |
| `key_amino_acid_ratio` | Anahtar AA oranı | {K,R,L,I,F} sayısı / toplam uzunluk |

Geçersiz amino asit (standart 20 dışında) içeren diziler `ValueError` fırlatarak elenir.

---

## Biyolojik Filtreleme Kuralları

Kurallar `data/biological_rules.json` dosyasında saklanır:

```json
{
  "target_bacteria": "Listeria monocytogenes",
  "length_range": [15, 30],
  "charge_range": [3, 9],
  "hydrophobicity_range": [0.4, 0.65],
  "key_amino_acids": ["K", "R", "L", "I", "F"]
}
```

| Kural | Eşik | Gerekçe |
|---|---|---|
| Uzunluk | 15–30 amino asit | Kısalar zarı delip geçemez; uzunlar toksik risk taşır |
| Net yük | +3 ile +9 | Pozitif yük, negatif yüklü bakteri zarına elektrostatik bağlanır |
| Hidrofobisite oranı | %40–65 | Zar etkileşimi için gerekli; çok yüksek değer sitotoksisite riski |
| Anahtar AA oranı | ≥ %25 | K,R,L,I,F amino asitleri antimikrobiyal aktiviteyle en çok ilişkili |

---

## Makine Öğrenmesi Modeli

### Model Parametreleri

| Parametre | Değer |
|---|---|
| Algoritma | Random Forest Sınıflandırıcı |
| Ağaç sayısı (`n_estimators`) | 120 |
| Maksimum derinlik (`max_depth`) | 7 |
| Minimum yaprak örneği (`min_samples_leaf`) | 1 |
| Bölme stratejisi | Tabakalı (%80 eğitim / %20 test) |
| Rastgele tohum (`random_state`) | 42 |
| Çıktı | AMP olasılık skoru `predict_proba[1]` (0.0–1.0) |

### Test Seti Performansı (1.847 dizi)

| Sınıf | Kesinlik | Duyarlılık | F1 | Destek |
|---|---|---|---|---|
| AMP değil (label=0) | %72.8 | %75.2 | 0.740 | 1.062 |
| AMP (label=1) | %64.9 | %62.0 | 0.635 | 785 |
| **Genel doğruluk** | — | — | — | **%69.6** |
| Makro ortalama | %68.9 | %68.6 | 0.687 | 1.847 |

Model `ml/model.pkl` olarak `joblib` ile serileştirilmiş halde saklanır.

---

## Gıda Matrisleri ve Patojenler

### Desteklenen Gıda Matrisleri (`data/food_context.json`)

| Gıda | pH | Tuz (%) | Sıcaklık (°C) | Yağ İçeriği |
|---|---|---|---|---|
| Peynir | 5.0 | 2.5 | 4 | Yüksek |
| Yoğurt | 4.5 | 0.5 | 4 | Orta |
| Taze Et | 5.6 | 1.2 | 4 | Yüksek |
| Fermente Et (Sucuk) | 4.8 | 3.0 | 8 | Yüksek |
| Meyve Suyu | 3.8 | 0.1 | 10 | Düşük |
| Bitkisel Protein Bazlı Ürün | 6.2 | 0.8 | 5 | Orta |

### Desteklenen Hedef Patojenler (`pipeline.py`)

| Patojen | Min. Net Yük | Hidrofobisite Aralığı | Gram Tipi |
|---|---|---|---|
| Listeria monocytogenes | ≥ 3 | %40–65 | Gram-pozitif |
| Salmonella | ≥ 4 | %35–60 | Gram-negatif |
| E. coli | ≥ 4 | %35–60 | Gram-negatif |

> **Yeni gıda matrisi veya patojen eklemek** için kaynak kodu değiştirmeye gerek yoktur. Web arayüzündeki "Yeni gıda" / "Yeni patojen" formu aracılığıyla eklenen veriler `food_context.json`'a kalıcı olarak yazılır.

---

## Pipeline Performansı

1.847 test dizisi üzerinde gerçekleştirilen genel tarama (hedef gıda/patojen seçilmeksizin):

| Aşama | Eleme Kriteri | Elenen | Kümülatif Oran |
|---|---|---|---|
| 1–4. Biyolojik filtreler | Uzunluk, yük, hidrofobisite, anahtar AA | 1.528 | %82.7 |
| 5. ML filtresi | `ml_prediction ≠ 1` | 113 | %6.1 |
| 6. Gıda/patojen filtresi | Genel taramada uygulanmaz | — | — |
| **Onaylanan aday** | Tüm aşamaları geçti | **206** | **%11.2** |

Ortalama ML olasılık skoru (yalnızca ML'e giren 319 dizi üzerinden): **0.54**

---

## Proje Yapısı

```
Bio-Preserve-ML/
│
├── pipeline.py                    # Uçtan uca tarama pipeline'ı
│                                  # Biyolojik filtre → ML → patojen → gıda kontrolü
│
├── backend/
│   └── main.py                    # FastAPI uygulaması
│                                  # REST API endpoint'leri + frontend sunumu
│
├── frontend/                      # React 18 + Vite uygulaması
│   └── dist/                      # Build çıktısı (backend'den sunulur)
│
├── features/
│   └── feature_extraction.py      # 4 biyofiziksel özellik hesaplama
│
├── data_ingestion/
│   └── build_amp_dataset.py       # Ham CSV'leri ETL ile işler
│                                  # Normalleştirme, etiketleme, tekilleştirme
│
├── ml/
│   ├── train_model.py             # Standart model eğitim scripti (%75/%25)
│   └── model.pkl                  # Eğitilmiş Random Forest modeli (joblib)
│
├── data/
│   ├── raw/                       # Ham DRAMP ve özel CSV dosyaları
│   ├── amp_master_dataset.csv     # Tüm sütunları içeren tam veri seti (9.234 kayıt)
│   ├── amp_dataset.csv            # Eğitim verisi — 4 özellik + etiket (7.387 kayıt)
│   ├── database_peptides.csv      # Test seti dizi listesi (1.847 kayıt, pipeline girdisi)
│   ├── biological_rules.json      # Biyolojik filtreleme eşik değerleri
│   └── food_context.json          # Gıda matrisleri ve patojen listesi
│
├── outputs/                       # Oluşturulan aday raporları (candidate_report.csv)
│
├── split_and_retrain.py           # %80/%20 bölme + yeniden eğitim (mevcut model bu ile üretildi)
├── run_test_stats.py              # Test seti pipeline istatistiklerini yazdırır
├── generate_final_report.py       # Akademik final raporu (.docx) üretir
├── generate_pipeline_diagram.py   # Sistem akış diyagramı PNG üretir
│
├── setup.bat                      # İlk kurulum (venv oluşturma, bağımlılık yükleme)
├── start-backend.bat              # Backend'i başlatır (http://localhost:8000)
├── start-frontend.bat             # Frontend geliştirme sunucusunu başlatır
└── rebuild-amp-dataset.bat        # Ham veriden veri setini yeniden oluşturur
```

---

## Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.12
- Node.js ve npm (yalnızca frontend geliştirme / yeniden build için)

### İlk Kurulum

```bat
setup.bat
```

Bu komut sanal ortamı oluşturur (`venv`) ve tüm bağımlılıkları yükler.

### Backend'i Başlatma

```bat
start-backend.bat
```

Ardından `http://localhost:8000` adresini açın. Frontend, backend tarafından statik dosya olarak sunulur; ayrı bir frontend sunucusuna gerek yoktur.

### Geliştirme Ortamında Frontend

React kaynak kodunu değiştiriyorsanız ayrı geliştirme sunucusunu başlatın:

```bat
start-frontend.bat
```

Frontend geliştirme sunucusu `http://localhost:5173` adresinde çalışır; değişiklikler anlık yansır.

---

## API Referansı

Tüm endpoint'ler `backend/main.py` içinde tanımlıdır. Swagger dokümantasyonu `http://localhost:8000/docs` adresinde mevcuttur.

### Sağlık Kontrolü

```
GET /api/health
```

### Mevcut Seçenekler

```
GET /api/options
```

Desteklenen gıda matrisleri ve patojenlerin listesini döner.

### Sistem Peptit Havuzuyla Tarama

```
GET /api/run-pipeline?selected_food=Peynir&target_pathogen=Listeria monocytogenes
```

`database_peptides.csv` üzerinde pipeline çalıştırır. Her iki parametre de isteğe bağlıdır.

### CSV Yükleme ile Tarama

```
POST /api/run-pipeline
Content-Type: multipart/form-data

sequence_file: <CSV dosyası>
selected_food: Taze Et          (isteğe bağlı)
target_pathogen: E. coli        (isteğe bağlı)
```

### Rapor İndirme

```
GET /api/reports/{filename}
```

### Yeni Gıda Matrisi Ekleme

```
POST /api/food-matrices
Content-Type: application/json

{
  "product": "Zeytin",
  "pH": 4.2,
  "salt_ratio": 5.0,
  "temperature": 15,
  "fat_content": "high"
}
```

`fat_content` için geçerli değerler: `"low"`, `"medium"`, `"high"`

### Yeni Patojen Ekleme

```
POST /api/pathogens
Content-Type: application/json

{
  "name": "Staphylococcus aureus",
  "min_charge": 3,
  "hydrophobicity_min": 0.40,
  "hydrophobicity_max": 0.65,
  "gram_type": "positive"
}
```

---

## CSV Yükleme Formatı

Kendi peptit listenizi yüklemek için CSV dosyasında en az bir `sequence` sütunu bulunmalıdır:

```csv
sequence
KWKLFKKIGAVLKVL
LLKKLLKKLLKK
RWKRLKRLKRLK
FLPLIAAIAASAAKK
```

Her dizi büyük/küçük harf duyarsız işlenir; yalnızca standart 20 amino asit kodu kabul edilir.

---

## Modeli Yeniden Eğitme

### Mevcut Veri Seti Üzerinden Yeniden Eğitim (%80/%20)

Mevcut `amp_master_dataset.csv` üzerinde %80/%20 bölme yaparak modeli ve test setini yeniden oluşturur:

```bash
python split_and_retrain.py
```

Bu script şunları yapar:
1. `amp_master_dataset.csv`'yi %80/%20 oranında böler (stratified)
2. Eğitim kümesini `data/amp_dataset.csv` olarak kaydeder
3. Test kümesini `data/database_peptides.csv` olarak kaydeder (pipeline varsayılan girdisi)
4. Modeli eğitir ve `ml/model.pkl`'i günceller
5. Test doğruluğunu ve sınıflandırma raporunu ekrana yazdırır

### Ham Veriden Baştan Oluşturma

Yeni ham veri eklemek veya veri setini tamamen sıfırlamak istiyorsanız:

```bash
# 1. Yeni CSV dosyalarını data/raw/ dizinine ekleyin
#    (DRAMP formatındaki dosyalar dramp_id sütunu sayesinde otomatik tanınır)

# 2. Veri setini yeniden oluşturun
python -m data_ingestion.build_amp_dataset

# 3. Modeli yeniden eğitin
python split_and_retrain.py
```

Veya toplu çalıştırma için:

```bat
rebuild-amp-dataset.bat
```

### Test Seti İstatistiklerini Görme

```bash
python run_test_stats.py
```

---

## Dağıtım

Uygulama, **Render** üzerinde tek servis olarak dağıtılacak şekilde yapılandırılmıştır. Frontend `frontend/dist/` dizinine build edilir ve backend tarafından statik dosya olarak sunulur; ayrı bir web sunucusuna gerek yoktur.

Ortam değişkeni (isteğe bağlı):

```
FRONTEND_ORIGINS=https://your-domain.com
```

---

## Proje Hakkında

**T.C. İstanbul Sabahattin Zaim Üniversitesi**  
Mühendislik ve Doğa Bilimleri Fakültesi — Tasarım Projesi

**Ekip:** Betül Pınarcı · Sait Taha Demir · Büşra Demir · Beyza Bartin  
**Danışman:** Dr. Öğr. Üyesi Cem Turan  
**Teslim:** Haziran 2026
