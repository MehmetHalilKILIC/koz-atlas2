# KÖZ Atlas

MODIS ve VIIRS termal anomali gözlemlerinin mekânsal-zamansal karşılaştırması için çalıştırılabilir araştırma MVP'si. Takım: **Kirvecanlar**.

## Hızlı başlangıç — Windows

Python 3.11 veya 3.12 kurulu olmalıdır. ZIP'i bir klasöre çıkarıp `start_windows.bat` dosyasını çalıştırın. İlk açılışta bağımlılıkların indirilmesi için internet gerekir. Tarayıcı otomatik açılmazsa terminalde görünen yerel adresi açın.

Elle kurulum (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

## Paketin kapsamı

- `harmonizer.py`: şema kontrolü, güven sınıfları, UTC ayrıştırma, tam kopya eleme, FIRMS Area API, Haversine kümeleri, kalıcılık adayları ve deneysel FRP ölçekleme.
- `app.py`: koyu temalı Streamlit arayüzü; harita, takvim, sensör analitiği, CSV/JSON indirme.
- `data/synthetic_demo.csv`: sabit tohumla üretilen sentetik veri; NASA gözlemi değildir.
- `docs/SUNUM_7_SLAYT.md`: yedi slaytlık Türkçe içerik ve konuşmacı notları.
- `docs/BILIMSEL_YONTEM.md`: yöntem, varsayımlar ve doğrulama gereksinimleri.
- `tests/`: algoritma ve Streamlit işlev testleri.

## Kullanım

1. Anahtarsız test için **Sentetik demo** seçin. 2023–2025 örnekleri gerçek Türkiye yangınları hakkında çıkarım için kullanılamaz.
2. Gerçek veri için NASA CSV dosyalarını yükleyin veya FIRMS MAP_KEY ile API modunu kullanın. Anahtar diske, URL bağlantısı olarak arayüze veya çıktı dosyalarına yazılmaz.
3. Bölge, tarih, minimum güven, uzaklık ve zaman eşiğini seçin. Özel kutu sırası batı, güney, doğu, kuzeydir; antimeridyen geçen kutular desteklenmez.
4. Harita katmanlarını açın. Kalıcı kaynak adayı işaretini gerektiğinde gizleyin. Bu işaret bir tesis doğrulaması değildir.
5. Küme CSV, üye indekslerini içeren gözlem CSV ve işlem kaydı JSON dosyalarını birlikte indirin. Küme tablosundaki `member_ids`, gözlem tablosundaki `member_id` değerlerini gösterir.

CSV için zorunlu sütunlar: `latitude, longitude, acq_date, acq_time, confidence, frp, instrument`. `satellite` eksikse `unknown` olur; güvenilir geçiş ayrımı için gerçek uydu bilgisi sağlanmalıdır. `instrument` MODIS veya VIIRS olmalıdır. Zaman UTC HHMM'dir. Diğer orijinal sütunlar gözlem çıktısında korunur. Yüklenen dosyaların kaynağı bağımsız doğrulanmaz.

API sorguları en fazla beş günlük parçalara ayrılır. Aralık üst sınırı 366 gündür; API'nin ürün/tarih erişimi ve kotaları ayrıca geçerlidir. Uzun arşiv çalışmaları için arşiv CSV yüklemek daha uygundur. Ürünlerin tarih kapsamını NASA veri uygunluk servisinden kontrol edin. NRT/SP ürünlerini aynı dönem için üst üste yüklemeyin; bu sürüm ürün sürümleri arasında bilimsel uzlaştırma yapmaz.

## Bilimsel sınırlar

Bu sürüm bilimsel olarak doğrulanmış bir sensör harmonizasyon ürünü değildir. **Küme sayısı yangın sayısı değildir.** Küçük piksellerin birleştirilmesi sensörün tespit olasılığını, bulutları, geçiş saatini veya tarihsel trend kırılmasını otomatik düzeltmez. Haritadaki çemberler gerçek piksel geometrisi değildir.

FRP MW cinsinden güçtür. MODIS ve VIIRS değerleri birbirine eklenmez. VIIRS 375 m ürününün FRP türetiminde 750 m bilgisi de kullanıldığı için basit piksel toplamları bağımsız doğrulama gerektirir. Kayıt birleştirme yüzdesi doğruluk, başarı veya giderilmiş sahte yangın oranı değildir.

Kalıcı kaynak adaylığı seçilen yüklenmiş zaman aralığındaki tekrarları kullanır; veri eksikliği ve kısa aralıklar aday tespitini etkiler. `False` değeri biyokütle yangını doğrulaması değildir. Tesis envanteri, arazi örtüsü ve görüntü doğrulaması bu pakette yoktur.

Takvimde boş aylar gözlemsiz gün ile verisi eksik gün ayırt edilemediği için boş kalır. Tarihsel medyan aynı ay için en az üç önceki yıl ve dışarıdan kapsam doğrulama beyanı gerektirir. Bu beyan yazılım tarafından doğrulanmaz.

## Takım ve etkinlik bilgileri

Kullanıcının sağladığı proje bağlamı:

- Mehmet Halil KILIÇ — Takım kaptanı, veri mühendisliği ve harmonizasyon.
- İbrahim Halil BİRLİK — Backend, CBS ve Streamlit.
- Mirze KARA — Analitik, aktivite takvimi ve sunum.
- Batman Üniversitesi, Bilgisayar Mühendisliği.
- NASA Space Apps Challenge, Batman, 14–15 Kasım 2026; Prof. Dr. Narin Nasıroğlu Bilim ve İnovasyon Merkezi.

Etkinlik tarihi, yerel koşullar, görev yılı ve yedi slayt sınırı bu çalışma sırasında resmi sayfadan teyit edilemedi. Yedi slayt kullanıcı kapsamına göre hazırlanmıştır; resmi yarışma kuralı olarak sunulmaz.

Mevcut proje bağlantıları kullanıcı tarafından sağlanmıştır; bu teslimde değiştirilmedi ve canlı durumları doğrulanmadı:
- https://github.com/MehmetHalilKILIC/koz-atlas
- https://koz-atlas-gbqjscepvmqcaygzbjlxhq.streamlit.app/

Bu paket canlıya yayımlanmış değildir. Streamlit, bu ortamın statik/Worker web barındırmasına doğrudan uygun olmadığından çalıştırılabilir Python kaynağı olarak teslim edilmiştir. Streamlit Community Cloud için bu dosyaları deponuza ekleyip giriş dosyasını `app.py` seçebilirsiniz.

## Test

```bash
python -m pytest tests -q
```

Canlı API testi anahtar gerektirir. Otomatik testler API hata temizliğini ve tarih parçalamayı taklit edilmiş HTTP yanıtlarıyla sınar; canlı veri erişimini kanıtlamaz. Streamlit AppTest arayüz akışını sınar, tarayıcı piksel yerleşimini veya harita servisinin erişimini doğrulamaz.

## Doğrulanmış teknik kaynaklar

14 Kasım 2026 tarihinde erişilen NASA sayfaları:

1. FIRMS Area API, ürün adları, koordinat sırası, 1–5 günlük istekler: https://firms.modaps.eosdis.nasa.gov/api/area
2. FIRMS API örnekleri ve CSV şeması: https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html
3. VIIRS ürün açıklaması, güven sınıfları, nominal çözünürlük ve FRP sınırlamaları: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html

Kullanıcının verdiği görev bağlantısı (bu teslimde erişim hatası; teyit edilmedi): https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
