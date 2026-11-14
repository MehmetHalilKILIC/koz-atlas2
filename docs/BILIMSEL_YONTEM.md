# Yöntem ve doğrulama sınırları

## 1. Girdi standardizasyonu

Geçersiz koordinat, tarih, saat, negatif/eksik FRP ve bilinmeyen güven sınıfı elenir. MODIS güveni düşük <30, nominal 30–79, yüksek ≥80 olarak sınıflanır; VIIRS l/n/h sınıfları korunur. Ortak 0/1/2 sırası yalnızca arayüz filtresidir; olasılık eşitliği veya sensör kalibrasyonu ifade etmez. Tam gözlem kopyaları koordinat, UTC, sensör, uydu ve FRP ile elenir. Aynı gözlemin farklı işlenmiş sürümlerini çözümlemek bu kuralın kapsamı dışındadır.

## 2. Mekânsal-zamansal kümeler

Dünya yarıçapı 6371 km; Haversine uzaklığı kullanılır. Uzamsal aday araması birim küre üzerindeki cKDTree ile yapılır. Varsayılan çift sınırları 1,2 km ve 60 dakikadır. Kayıtlar zaman, sensör, koordinat ve uyduya göre sıralanır. Her yeni küme henüz atanmamış ilk kayıtla başlar. Bir aday ancak kümedeki TÜM kayıtlarla her iki eşiği sağlıyorsa eklenir. Böylece A–B ve B–C yakınken A–C uzaktaysa üçlü tek kümeye zincirlenmez. Bu deterministik açgözlü tam-bağ yaklaşımı, fiziksel yangın sınırını veya küresel optimum bölmeyi garanti etmez. Her gözlem tam bir kümeye atanır.

Merkez, FRP ağırlıklı birim küre vektöründen bulunur; tüm FRP sıfırsa eşit ağırlık kullanılır. Kimlik üye gözlemlerinin SHA-256 özetinden türetilir. Parametreler veya girdi değişirse kümeler ve kimlikler değişebilir. Piksel şekli ve tarama geometrisi eşleştirmeye henüz dahil değildir.

## 3. FRP ve deneysel ölçekleme

Aynı sensör, uydu ve tam UTC zamanındaki üye FRP değerleri toplanır. Birden fazla geçiş varsa sensör bazında geçiş toplamlarının medyanı alınır. Temsili FRP için MODIS varsa MODIS, yoksa VIIRS seçilir; sensörler arası çift sayımdan kaçınmak için birbirine eklenmez. Bu temsil kuralı fiziksel kalibrasyon değildir.

Deneysel seçenek en az 20 MODIS–VIIRS eşleşmesi ve beş farklı gün ister. Günlerin ilk yaklaşık %70'i eğitim, geri kalanı zaman bazlı tutulan test kümesidir. Orijinden geçen ölçek katsayısı `a = Σ(V*M)/Σ(V²)` eğitim kümesinde bulunur. Çıktı `a*V` olur; test MAE'si ve ölçeklemesiz MAE birlikte gösterilir. Coğrafi ayrımlı test, bağımsız yangın gerçekliği ve sensör geçişi düzeltmeleri yoktur. Kötü test sonucu da açıkça gösterilir; model otomatik olarak doğrulanmış kabul edilmez. Varsayılan durumda kalibrasyon uygulanmaz ve çıktı sütunu boştur.

## 4. Kalıcılık

Her kümenin 1 km çevresinde en az beş farklı gün ve üç farklı yıl-ay gözlemi aranır. Koşul sağlanırsa `is_static_candidate=True` olur. Bu bir termal kaynak adayıdır; gaz bacası/orman/anız sınıflandırması değildir. Komşuluklar örtüşebildiği için KPI fiziksel tesis sayısını değil aday küme kayıtlarını sayar.

## 5. Değerlendirme planı

Gerçek, kaynak ve kapsam bilgili arşivle pilot yürütün. Eşleşme mesafesi ve zaman penceresi için duyarlılık tabloları çıkarın. Tek bir yangına ait komşu kayıtları eğitim ve teste rastgele bölmeyin. Bölge/yıl/uydu/geçişe göre ayrılmış test yapın. FRP ölçekleme öncesi/sonrası hata, kümelerin manuel doğruluğu, endüstriyel envanter doğruluğu ve eksik gözlem etkisini ayrı raporlayın. Tarihsel sensör kırılmasının giderildiği iddiası ancak bu testler sonrası kurulabilir.

Büyük ve yoğun arşivlerde tam-bağ karşılaştırması en kötü durumda karesel maliyetlidir. Bu MVP'de çalıştırma süresi garantisi yoktur; bölge ve tarih aralığını daraltın. Gelecek sürümde geçiş bazlı bölümleme, kapsama maskesi ve bağımsız değerlendirme veri seti gerekir.
