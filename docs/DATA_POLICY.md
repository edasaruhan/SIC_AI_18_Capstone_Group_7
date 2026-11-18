# Veri kullanımı ve gizlilik

Bu depo araştırmanın kaynak kodunu, sürümlenmiş doğrusal modelini, toplu sonuçlarını ve raporunu yayımlamak için hazırlanmıştır.

## Depoya dahil edilenler

- Araştırma yöntemini uygulayan kaynak kod ve sentetik test örnekleri.
- Model karşılaştırmaları, kat düzeyindeki özetler, bootstrap aralıkları ve toplu açıklanabilirlik çıktıları.
- Özellik şeması, ölçekleme/katsayı parametreleri, dosya hash'leri ve model sürümü.
- Akademik yazar bilgileri olarak Group 7 üyelerinin adları.

## Yerelde tutulacaklar

- Katılımcı kimlikleri ve kişi düzeyindeki anket/oyun kayıtları.
- Kişi düzeyindeki özellikler, hedefler ve out-of-fold tahmin tabloları.
- Ham metinler, oyun takvimleri ve katılımcı ekran görüntüleri.
- API anahtarları, `.env`, özel anahtar dosyaları, günlükler, önbellekler ve sanal ortam.

`data/clean/` ve `data/derived/` yalnız yerel tekrar üretim için kullanılır ve `.gitignore` ile dışlanır. Model ve demo ham veriyi okumadan çalışır. API ve arayüz kişisel veri yükleme veya katılımcı seçimi kabul etmez; örnekler kurgusaldır.

Kayıtlı model iki girdili Ridge'dir; artefakt dönüştürücü istatistikleri ve katsayıları içerir, eğitim satırlarını veya katılımcı kimliklerini içermez. Bununla birlikte model katılımcılardan öğrenmiştir; tamamen anonim veya risksiz olarak nitelendirilmez. Küçük alt grupları veya kişiye ait kayıtları sonradan yayımlamayın.

Open Play verisi ek bir no-reidentification koşuluyla paylaşılmıştır. Veri açıklığı kimlik tespiti veya dış kaynaklarla kişileri eşleştirme izni değildir. Kaynak koşulları `docs/data/OPEN_PLAY_LICENSE.txt` içinde korunmuştur. Bu metin veri kaynağının koşullarıdır; proje yazılımına ayrıca bir açık kaynak lisansı atamaz.
