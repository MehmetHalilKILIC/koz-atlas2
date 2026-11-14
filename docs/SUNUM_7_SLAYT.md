# KÖZ Atlas — 7 slaytlık jüri sunumu

Bu dosya sunum içeriği ve konuşmacı metnidir; PPTX/PDF değildir. Gerçek deney sonucu verilmediği için sayısal başarı iddiası içermez.

## 1 — Kim ve ne?
**KÖZ Atlas**
MODIS ve VIIRS sıcak nokta gözlemlerini birlikte inceleme platformu.

Kirvecanlar: Mehmet Halil KILIÇ · İbrahim Halil BİRLİK · Mirze KARA
Batman Üniversitesi / Bilgisayar Mühendisliği
NASA Space Apps Challenge — Batman, 14–15 Kasım 2026 (takımın sağladığı etkinlik bilgisi).

Konuşmacı: “Farklı sensörlerin kayıtlarını tek bir yangın sayısı gibi yorumlamadan, karşılaştırılabilir ve izlenebilir bir çalışma alanı sunuyoruz.”

## 2 — Neden ve ne zaman?
- MODIS ile VIIRS'in nominal uzamsal çözünürlükleri farklıdır.
- VIIRS küçük sıcak noktaları daha ayrıntılı gösterebilir.
- Ham kayıt sayısı artışı tek başına yangın artışını göstermez.
- Geçiş zamanı, hassasiyet ve veri kapsamı tarihsel karşılaştırmayı etkiler.

Konuşmacı: “Sorun yalnızca mükerrer kayıt değildir. Sensörlerin tespit davranışı da farklıdır. Bu MVP önce gözlem eşleştirmesini görünür hale getiriyor; tarihsel kırılmayı giderdiğini iddia etmiyor.”

## 3 — Nerede, hangi veri?
- Türkiye, Batman ve Güneydoğu, Akdeniz ve Ege bölge kutuları.
- Gerçek veri: NASA FIRMS API veya kullanıcı CSV dosyaları.
- Anahtarsız gösterim: açıkça etiketlenmiş sentetik veri.
- Her çıktı veri kaynağı ve işlem parametreleriyle dışa aktarılır.

Konuşmacı: “Batman odağında tekrar eden termal kaynakları inceleyebiliriz. Fakat bir kaydın petrol tesisi olduğunu yalnızca tekrar sayısından çıkarmıyoruz.”

## 4 — Nasıl? Dört aşama
1. UTC zaman, şema, güven ve tam kopya kontrolü.
2. Haversine uzaklığı ve zaman penceresiyle aday kümeler.
3. Sensör bazlı FRP özeti; isteğe bağlı deneysel ölçekleme.
4. Gün ve ay tekrarlarından kalıcı kaynak adaylığı.

Varsayılan eşikler: 1,2 km / 60 dakika. Kullanıcı değiştirebilir.

Konuşmacı: “Kümedeki tüm çiftlerin eşikleri sağlamasını istiyoruz. Böylece yakın noktaların uzun zincirler oluşturup uzak gözlemleri tek olay gibi birleştirmesini engelliyoruz.”

## 5 — Ne üretir?
| Girdi/çıktı | Temsil | Sınır |
|---|---|---|
| MODIS | Sensör gözlemi | Yangın sayısı değildir |
| VIIRS | Daha ayrıntılı sıcak nokta gözlemi | Her alt piksel ayrı yangın değildir |
| KÖZ kümesi | Üyeleri izlenebilir gözlem grubu | Fiziksel yangın olayı doğrulanmamıştır |

- Yıl × ay aktivite takvimi ve günlük dağılım.
- Kapsamı doğrulanan yeterli geçmişte aynı ay medyanı.
- Üye kayıtlarıyla birlikte CSV ve işlem günlüğü.

Konuşmacı: “Eksik veri aylarını sessizce sıfır saymıyoruz. Takvim gözlenen kümeleri gösteriyor; yanmış alan ölçümü yapmıyor.”

## 6 — Çalışan MVP ve doğrulama
Canlı gösterim sırası:
1. Sentetik veri etiketini gösterin.
2. MODIS/VIIRS/aday küme katmanlarını açın.
3. Mesafe ve zaman sürgülerini değiştirin.
4. Takvimi ve FRP karşılaştırmasını gösterin.
5. CSV ve işlem kaydını indirin.

Gelecek doğrulama: gerçek arşiv, bağımsız yangın/tesis bilgisi, bölge ve zaman ayrımlı hata değerlendirmesi.

Konuşmacı: “Teslimimiz çalışan araştırma prototipidir. Bilimsel başarı oranı uydurmak yerine varsayımları ve doğrulama gereksinimlerini açıkça raporluyoruz.”

## 7 — Kaynaklar ve erişim
- NASA FIRMS Area API: https://firms.modaps.eosdis.nasa.gov/api/area
- NASA VIIRS veri tanımları: https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html
- NASA FIRMS API örnekleri: https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html
- Takımın sağladığı depo: https://github.com/MehmetHalilKILIC/koz-atlas
- Takımın sağladığı uygulama: https://koz-atlas-gbqjscepvmqcaygzbjlxhq.streamlit.app/

Konuşmacı: “Bu teslim mevcut depoya gönderilmedi veya canlı uygulamaya yayımlanmadı. Sunumdan önce canlı bağlantıyı ve etkinlik bilgilerini ekip olarak kontrol edeceğiz.”
