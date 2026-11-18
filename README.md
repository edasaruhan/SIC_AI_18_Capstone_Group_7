# Problematic Gaming Early Warning

**SIC Capstone · Group 7**

İlk 14 günlük kaydedilen oyun davranışının, başlangıç Gaming Disorder Test (GDT) skoru ve toplam kaydedilen süre üzerine ek tahmin katkısı sağlayıp sağlamadığını araştıran proje.

## Projeye erişim

| İçerik | Konum |
|---|---|
| Çalıştırılabilir kaynak kod ve kurulum | [`problematic-gaming-early-warning` branch'i](https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7/tree/problematic-gaming-early-warning) |
| Güncel final teslim paketi | [Group7_OpenPlay_Final.zip](releases/Group7_OpenPlay_Final.zip) |
| Final araştırma raporu | [İngilizce PDF](https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7/blob/problematic-gaming-early-warning/docs/final/Group7_Final_Report.pdf) |
| Veri kullanımı ve gizlilik | [Veri politikası](https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7/blob/problematic-gaming-early-warning/docs/DATA_POLICY.md) |
| Önceki ödevler ve ilk proje sunumu | `main` kök dizinindeki özgün belgeler |

Bu branch önceki teslimleri ve indirilebilir final paketini korur. Uygulama, model, testler, ayrıntılı README ve otomatik başlatıcılar kaynak branch'indedir. Kaynak branch'inde önceki belgeler `docs/coursework/` altında düzenlenmiştir; içerikleri değiştirilmemiştir.

## Sunum için sıfırdan çalıştırma

Python **3.12** önceden kurulu olmalıdır. İlk kurulum paket indirmek için internet gerektirir.

```bash
git clone --branch problematic-gaming-early-warning https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7.git
cd SIC_AI_18_Capstone_Group_7
```

macOS / Linux:

```bash
bash start_demo.sh
```

Windows:

```powershell
.\start_demo.bat
```

Başlatıcı `.venv` ortamını oluşturur, kilitli bağımlılıkları kurar, model bütünlüğünü ve sentetik senaryoları kontrol eder, ardından `http://127.0.0.1:8501` üzerinde yerel demoyu açar. Sunum öncesinde yalnız kurulum kontrolü için `--setup-only` kullanılabilir. İlk kurulumdan sonra paketler eşleşiyorsa yeniden indirme yapılmaz. ZIP tercih edilirse dosyaları açıp içindeki proje klasöründe aynı başlatıcıyı çalıştırın.

Demo için katılımcı verisi indirme, yeniden eğitim, `.env` veya API anahtarı gerekmez. Ayrı FastAPI servisi için gerekli anahtar oluşturma komutları kaynak branch'inin README'sindedir.

## Temel sonuç

GDT analizi 543 kişi üzerinde iç içe çapraz doğrulama kullanır. Başlangıç GDT ve kaydedilen saatten öğrenilen Ridge modeli MAE **1.8757**, RMSE **2.3853**, R² **0.4261** üretmiştir. Denenen günlük davranış özellikleri belirgin ek tahmin faydası göstermemiştir. Rutin müdahalesi analizi 935 kişi ve 2.093 geçiş üzerinde kişi gruplu doğrulamayla tamamlanmıştır.

Sonuçlar keşifsel iç doğrulamadır; harici test veya klinik kullanım doğrulaması değildir. Arayüz yalnız toplu sonuçları ve gerçek modelden hesaplanan kurgusal örnekleri gösterir. Katılımcı kimlikleri, ham anket/oyun kayıtları, kişi düzeyindeki özellik ve tahminler, anahtarlar, günlükler ve sanal ortam yayımlanmaz. Akademik yazar bilgisi olarak ekip üyelerinin adları korunur.

## Ekip

Yunus Berkay İnci · Deniz Caman · Fatih Yılmaz · İsa Adahan Ünal · Alperen Acar
