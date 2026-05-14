# BioPreserve-AI

BioPreserve-AI, antimikrobiyal peptit adaylarını gıda koruma amacıyla değerlendirmek için hazırlanmış bir analiz sistemidir. Proje, kullanıcıdan peptit sekanslarını içeren bir CSV dosyası alır, bu sekanslardan biyolojik özellikler çıkarır, makine öğrenmesi modeliyle adaylık tahmini yapar ve sonucu rapor olarak sunar.

Bu proje; gıda mühendisliği, biyokimya ve bilgisayar mühendisliği taraflarını bir araya getiren bir prototiptir. Şu an çalışan sistem, peptit tarama akışını göstermek ve ileride gerçek biyolojik veriyle geliştirilecek yapının temelini oluşturmak için hazırlanmıştır.

## Projenin Amacı

Gıdalarda bozulmaya veya hastalık riskine neden olabilecek mikroorganizmaların kontrolünde antimikrobiyal peptitler potansiyel doğal koruyucu adayları olarak değerlendirilebilir. Bu projede amaç, verilen peptit sekanslarının belirli biyolojik özelliklere göre uygun aday olup olmadığını hızlıca inceleyebilen bir karar destek sistemi oluşturmaktır.

Sistem şu soruya cevap arar:

> Bu peptit, biyolojik özellikleri ve seçilen gıda/patojen bağlamı dikkate alındığında uygun bir aday olabilir mi?

## Genel Çalışma Mantığı

Sistem temel olarak şu akışla çalışır:

```text
CSV dosyası yüklenir
Peptit sekansları okunur
Biyolojik özellikler çıkarılır
Temel biyolojik filtreler uygulanır
Random Forest modeli adaylık tahmini yapar
Gıda ve/veya patojen uyumluluğu kontrol edilir
Sonuçlar raporlanır
```

Kullanıcı arayüzü üzerinden CSV dosyası yüklenir. Backend tarafında peptitler tek tek analiz edilir. Analiz sonunda her peptit için uygunluk durumu, makine öğrenmesi skoru ve açıklama notları oluşturulur.

## Kullanıcıdan Beklenen CSV Formatı

Yüklenecek dosya `.csv` formatında olmalıdır. Dosyada en az şu sütun bulunmalıdır:

```text
sequence
```

Örnek CSV:

```csv
sequence
KWKLFKKIGAVLKVL
LLKKLLKKLLKK
RWKRLKRLKRLK
```

Her satırda bir peptit sekansı yer almalıdır. Sütun adı farklı yazılırsa sistem dosyayı doğru okuyamayabilir.

## Analiz Modları

Arayüzde dört farklı analiz modu vardır.

### Genel Tarama

Bu modda kullanıcı herhangi bir gıda veya patojen seçmeden peptitleri genel olarak tarar. Sistem temel biyolojik filtreleri ve makine öğrenmesi modelini kullanarak adayları değerlendirir.

### Gıda Odaklı Tarama

Bu modda kullanıcı belirli bir gıda matrisi seçer. Sistem peptidin seçilen gıda ortamına uygun olup olmadığını kontrol eder.

Örnek gıda matrisleri:

- Peynir
- Yoğurt
- Taze et
- Fermente et
- Meyve suyu

Gıda ortamının pH, tuz oranı ve yağ içeriği gibi özellikleri peptidin uygunluğunu etkileyebilir.

### Patojen Odaklı Tarama

Bu modda kullanıcı yalnızca hedef patojeni seçebilir. Örneğin kullanıcı sadece Salmonella odaklı bir analiz yapmak isterse gıda seçmeden bu modu kullanabilir.

Örnek hedef patojenler:

- Salmonella
- Listeria monocytogenes
- E. coli

### Gıda + Patojen Odaklı Tarama

Bu modda hem gıda hem de patojen birlikte değerlendirilir. Örneğin peynirde Listeria monocytogenes hedefleniyorsa sistem peptidi bu bağlama göre inceler.

## Kullanılan Biyolojik Özellikler

Sistem her peptit için bazı temel biyolojik özellikler hesaplar.

### Peptit Uzunluğu

Peptitte bulunan amino asit sayısıdır. Çok kısa veya çok uzun peptitler biyolojik etki, stabilite veya üretim açısından uygun olmayabilir.

### Net Yük

Peptidin yaklaşık elektriksel yükünü ifade eder. Antimikrobiyal peptitlerde pozitif yük önemli olabilir çünkü bakteri zarları genellikle negatif yüklü bileşenler içerir. Pozitif yüklü peptitler bakteri zarına daha kolay tutunabilir.

### Hidrofobiklik Oranı

Peptitteki hidrofobik amino asitlerin oranıdır. Hidrofobiklik, peptidin bakteri zarındaki lipid yapılarla etkileşime girmesine yardımcı olabilir. Ancak çok yüksek hidrofobiklik toksisite riskini artırabileceği için dengeli bir aralık önemlidir.

### Kritik Amino Asit Oranı

Antimikrobiyal etkiyle ilişkili bazı amino asitlerin peptit içindeki oranını ifade eder. Bu oran, peptidin biyolojik adaylık potansiyelini yorumlamak için yardımcı bir parametredir.

## Makine Öğrenmesi Kullanımı

Projede makine öğrenmesi modeli olarak Random Forest kullanılmaktadır. Random Forest, birden fazla karar ağacının birlikte çalıştığı bir sınıflandırma algoritmasıdır.

Model, peptitlerden çıkarılan sayısal özellikleri kullanır ve peptidin aday olup olmadığına dair tahmin üretir.

Modelin kullandığı temel girdiler:

```text
length
net_charge
hydrophobic_ratio
key_amino_acid_ratio
```

Model çıktıları:

```text
ml_prediction
ml_probability
```

`ml_prediction`, modelin sınıf tahminidir. Genel olarak `1` aday olabilir, `0` aday değil anlamına gelir.

`ml_probability`, modelin peptidi aday olarak görme olasılığıdır. Bu değer karar destek amacıyla kullanılır; tek başına kesin biyolojik doğruluk anlamına gelmez.

## Random Forest Neden Tercih Edildi?

Random Forest bu proje için uygun bir başlangıç modelidir çünkü biyolojik parametreler gibi sayısal verilerle iyi çalışır. Tek bir karar ağacına göre daha kararlı sonuç verir ve küçük/orta ölçekli veri setlerinde kullanılabilir.

Ayrıca hangi özelliklerin model kararında daha etkili olduğunu incelemeye de uygundur. Bu, biyoloji ve gıda mühendisliği ekibiyle model sonuçlarını yorumlamak açısından önemlidir.

## Gıda Uyumluluğu

Sistem yalnızca makine öğrenmesi sonucuna bakmaz. Peptidin seçilen gıda ortamında uygun olup olmayacağını da basit kurallarla kontrol eder.

Örneğin:

- Tuz oranı yüksek gıdalarda net yük önemli olabilir.
- Asidik gıdalarda peptit uzunluğu etkili olabilir.
- Yağ oranı yüksek gıdalarda hidrofobiklik dengesi önem kazanabilir.

Bu bölüm şu an kural tabanlıdır. İleride yeterli veri oluşursa gıda uyumluluğu da doğrudan makine öğrenmesiyle değerlendirilebilir.

## Patojen Uyumluluğu

Sistem seçilen hedef patojene göre ek kontrol yapabilir. Örneğin Salmonella, E. coli veya Listeria monocytogenes için farklı biyolojik beklentiler olabilir.

Bu kontroller şu an basit biyolojik kurallara dayanmaktadır. Gerçek DBAASP ve literatür verisiyle bu bölüm daha güçlü hale getirilebilir.

## Raporlama

Analiz tamamlandığında sistem kullanıcıya sonuçları tablo halinde gösterir ve indirilebilir CSV raporu oluşturur.

Raporda yer alan başlıca alanlar:

```text
sequence
target_food
target_pathogen
final_status
ml_probability
length
net_charge
hydrophobic_ratio
key_amino_acid_ratio
compatible_foods
rule_notes
food_notes
```

`final_status`, peptidin genel durumunu gösterir:

```text
Approved
Rejected
```

`rule_notes`, biyolojik filtre sonucunu açıklar.

`food_notes`, gıda veya patojen uyumluluğuyla ilgili açıklama verir.

## Mevcut Veri Durumu

Proje şu anda çalışan bir prototiptir. Ancak kullanılan veri seti sınırlı ve örnek amaçlıdır. Bu nedenle mevcut model, gerçek biyolojik karar verme için tek başına yeterli kabul edilmemelidir.

Şu anki yapı şunları gösterir:

- CSV yükleme akışı
- Peptit özellik çıkarımı
- Biyolojik filtreleme
- Random Forest ile sınıflandırma
- Gıda/patojen odaklı değerlendirme
- Sonuç raporlama

Bilimsel doğruluk için daha güçlü, temizlenmiş ve etiketlenmiş gerçek veri setine ihtiyaç vardır.


## Hangi dosya ne işe yarar ve neleri barındırır ?

```

`raw` klasörü ham veriyi saklar. Bu veri doğrudan eğitimde kullanılmaz.

`processed` klasörü temizlenmiş, özellikleri çıkarılmış ve modele hazır hale getirilmiş veriyi içerir.

## Proje Yapısı

Projede temel klasör ve dosyalar şu şekildedir:

```text
backend/
FastAPI backend kodları

frontend/
React arayüz kodları

features/
Peptit özellik çıkarım fonksiyonları

ml/
Eğitilmiş model dosyası

data/
Kural ve veri dosyaları

pipeline.py
Ana analiz akışı

Dockerfile
Render yayını için çalışma ortamı

render.yaml
Render servis ayarı
```

## Frontend

Frontend React ve Vite ile geliştirilmiştir. Kullanıcı arayüzü üzerinden CSV dosyası yüklenir, analiz modu seçilir, tarama başlatılır ve sonuçlar görüntülenir.

## Backend

Backend FastAPI ile geliştirilmiştir. CSV dosyasını alır, peptitleri işler, modeli çalıştırır ve raporu oluşturur.

## Pipeline

`pipeline.py`, projenin analiz çekirdeğidir. Peptitlerin değerlendirilmesi, biyolojik filtreler, model tahmini ve rapor üretimi bu akış üzerinden yürütülür.

## Render Üzerinde Yayınlama

Proje Render üzerinde tek servis olarak yayınlanabilecek şekilde hazırlanmıştır. Bu yapıda frontend ve backend ayrı sitelerde değil, aynı Render servisi üzerinden çalışır.

Render üzerinde sistem şu şekilde çalışır:

```text
Dockerfile çalışır
Python bağımlılıkları kurulur
Frontend bağımlılıkları kurulur
Frontend build alınır
FastAPI başlatılır
React arayüzü FastAPI üzerinden servis edilir
```

Bu sayede kullanıcı tek bir Render linki üzerinden projeye ulaşabilir.

## Local Çalıştırma

Backend ve frontend geliştirme sırasında ayrı ayrı çalıştırılabilir.

Backend:

```bash
start-backend.bat
```

Frontend:

```bash
start-frontend.bat
```

Frontend varsayılan olarak şu adreste çalışır:

```text
http://localhost:5173
```

Backend varsayılan olarak şu adreste çalışır:

```text
http://127.0.0.1:8000
```

Render benzeri tek servis çalıştırmak için önce frontend build alınabilir:

```bash
cd frontend
npm run build
```

Sonra backend başlatılır:

```bash
cd ..
start-backend.bat
```

Bu durumda arayüz backend üzerinden de servis edilebilir.



## Kısa Özet

BioPreserve-AI, peptit adaylarını biyolojik parametreler ve Random Forest modeliyle değerlendiren bir gıda koruma odaklı analiz sistemidir. Kullanıcı CSV dosyası yükler, sistem peptitleri analiz eder ve sonuçları raporlar.




