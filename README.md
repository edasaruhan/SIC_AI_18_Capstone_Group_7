# Problematic Gaming Early Warning

**SIC Capstone · Group 7**

Bu proje, ilk 14 günlük kaydedilen oyun davranışının başlangıç Gaming Disorder Test (GDT) skoru ve toplam oyun süresinin üzerine ek tahmin katkısı sağlayıp sağlamadığını araştırır. Sabit Open Play verisi üzerinde tekrar üretilebilir analiz, yerel Streamlit arayüzü ve FastAPI servisi içerir.

**Temel bulgu:** Denenen günlük Steam davranış özellikleri, başlangıç skoru ve toplam kaydedilen sürenin üzerine belirgin ek tahmin faydası göstermemiştir. Sonuçlar keşifsel iç doğrulamadır; tanı veya kişisel alarm amacı taşımaz.

## Araştırma sonuçları

| Model / görev | MAE | RMSE | R² |
|---|---:|---:|---:|
| GDT: başlangıç skorunu aynen taşıma | 2.1031 | 2.8304 | 0.1920 |
| GDT: başlangıç skorundan öğrenilmiş Ridge | 1.8846 | 2.4057 | 0.4162 |
| GDT: başlangıç + kaydedilen saat (R M2) | 1.8757 | 2.3853 | 0.4261 |
| GDT: altı özellikli Ridge (R M3) | 1.8782 | 2.3881 | 0.4248 |
| GDT: iç katlarda aile seçimi (R SELECT) | 1.9033 | 2.4210 | 0.4088 |

GDT analizi aynı 543 kişi üzerinde beş dış / üç iç kat kullanır. R M3 − R M2 MAE farkı +0.002466; sabit OOF kişi bootstrap %95 aralığı [−0.015368, 0.020849]. Aileye özgü değerlendirme ve bütün aile seçme prosedürünün skoru birbirinden ayrıdır.

İkincil rutin müdahalesi görevi (RQ2), en az 14 gün aralıklı 2.093 geçişi olan 935 kişi üzerinde çalıştırılmıştır. İç ve dış katlar kişi ile gruplanır. Bütün metrikler, kat özetleri ve sınırlamalar [İngilizce final raporunda](docs/final/Group7_Final_Report.pdf) ve [araştırma kapsamında](docs/RESEARCH_SCOPE.md) açıklanır.

## Branch ve teslim düzeni

- `main`: önceki ödevler ve [güncel final teslim ZIP'i](https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7/blob/main/releases/Group7_OpenPlay_Final.zip).
- `codex/group7-openplay-final`: çalıştırılabilir kaynak kod, model, testler ve final raporu.
- Önceki ödevler ve proje sunumu bu branch'te `docs/coursework/` altında korunur. Final bulgular için `docs/final/Group7_Final_Report.pdf` kullanılır.

Kaynak branch'ini sıfırdan indirmek için:

```bash
git clone --branch codex/group7-openplay-final https://github.com/edasaruhan/SIC_AI_18_Capstone_Group_7.git
cd SIC_AI_18_Capstone_Group_7
```

## Kurulum

Python **3.12** kullanın. Depoyu klonladıktan sonra proje kökünde çalıştırın. macOS ARM64 üzerinde doğrulanmıştır; Windows/Linux için taşınabilir komutlar sağlanır.

### Sunum için otomatik başlatma

Python 3.12 önceden kurulu olmalıdır. macOS/Linux terminalinde:

```bash
bash start_demo.sh
```

macOS'ta `start_demo.command`, Windows'ta `start_demo.bat` dosyası da açılabilir. Windows terminalinde:

```powershell
.\start_demo.bat
```

Başlatıcı ilk çalıştırmada proje içinde `.venv` oluşturur, kilitli paketleri kurar, model bütünlüğünü ve üç sentetik tahmini kontrol ederek demoyu başlatır. Mevcut `.venv` Python 3.12 ile uyumlu değilse üzerine yazmaz ve hata verir. Sonraki çalıştırmalarda bağımlılıklar kilitle eşleşiyorsa indirme yapmaz. Farklı port için `bash start_demo.sh --port 8502` kullanılabilir.

**İlk kurulum internet gerektirir.** Sunumdan önce aynı bilgisayarda yalnız kurulum kontrolünü çalıştırabilirsiniz:

```bash
bash start_demo.sh --setup-only
```

Windows karşılığı `.\start_demo.bat --setup-only` komutudur. Kurulum tamamlandıktan sonra demo katılımcı verisi indirmeden ve yeniden eğitim yapmadan yerelde çalışır. `.venv` makineye özgüdür ve GitHub'a yüklenmez. Streamlit demosu `.env` veya API anahtarı istemez. `.env.example`, ayrı FastAPI servisi için gerekli değişken adını belgeler; anahtar servis başlatılırken ortamda oluşturulur.

### Elle kurulum

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

Sonraki `python` komutları etkin sanal ortam içindir. Windows'ta etkinleştirmeden `.\.venv\Scripts\python.exe` kullanılabilir. `requirements.txt` doğrudan bağımlılıkları, `requirements-lock.txt` doğrulanan çalışma ortamındaki tüm paket sürümlerini listeler.

## Yerel araştırma arayüzü

```bash
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Tarayıcıda `http://127.0.0.1:8501` adresini açın. Ekran gerçek toplu model sonuçlarını, hata karşılaştırma grafiğini ve kayıtlı modelden hesaplanan üç sentetik örneği gösterir. Demo için veri indirme veya yeniden eğitim gerekmez. Streamlit, API ile ortak `deployment/inference.py` modülünü doğrudan kullanır.

| Örnek | Başlangıç GDT | Kaydedilen saat/hafta |
|---|---:|---:|
| example_a | 8 | 12 |
| example_b | 12 | 12 |
| example_c | 8 | 24 |

`gdt-strict-2` modelinde A için sonraki GDT tahmini **7.3437**, değişim **−0.6563**. Bu bir ölçek puanıdır; risk yüzdesi veya kişisel güven aralığı değildir. Örnekler arasındaki fark nedensel etki göstermez.

## Veriyi ve sonuçları yeniden üretme

```bash
python -m analysis.download
python -m analysis.prepare
python -m analysis.train --mode all
python -m analysis.report
```

Kaynak: [Open Play](https://github.com/digital-wellbeing/open-play/tree/eb0a68c1a7ca1fad54e57a1f89b9d5450f8be840), commit `eb0a68c1a7ca1fad54e57a1f89b9d5450f8be840`. Dosya hash'leri `data/source_lock.json` ile kontrol edilir. İndirme kilitli dosyayı değiştirmez; uyuşmazlıkta durur. Gerekli veri yalnız yerelde indirilir. `data/clean/` ve `data/derived/` Git'e dahil edilmez.

`--mode legacy` önceki rapordaki hesaplamayı; `--mode strict` düzeltilmiş zaman sınırlarıyla GDT analizini; `--mode secondary` rutin görevini çalıştırır. Sağlayıcının Steam satırları tek saat kovası değildir. Final hesaplama bütün yaklaşık kayıtları ve kaynak zamanlarını pencere içinde tutar; sekiz taşan kayıt çıkarılırken aynı 543 kişi korunmuştur. Günlük toplamlar geçen 24 saatlik kutulara dağıtılır.

Rapor Markdown ve grafik olarak ölçülmüş JSON sonuçlarından üretilir. PDF'yi yeniden oluşturmak isteğe bağlıdır:

```bash
python -m pip install -r requirements-report.txt
python tools/render_report.py
```

Yeni PDF'nin sayfa düzeni teslimden önce görsel olarak kontrol edilmelidir. Model manifesti sürüm, hash, girdi sırası, eğitim aralıkları ve dönüşüm parametrelerini içerir. Joblib yalnız güvenilir yerel model artefaktları için kullanılmalıdır.

## API

macOS / Linux:

```bash
export OPENPLAY_DEMO_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn deployment.service:app --host 127.0.0.1 --port 8765 --workers 1 --no-access-log
```

Windows PowerShell:

```powershell
$env:OPENPLAY_DEMO_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -m uvicorn deployment.service:app --host 127.0.0.1 --port 8765 --workers 1 --no-access-log
```

`GET /health`, `POST /predict` ve `GET /metrics`, `X-API-Key` başlığı ister. Anahtar en az 24 karakterdir. `.env.example` yalnız değişken adını gösterir; `.env` otomatik yüklenmez. Anahtarları kaynak koda veya rapora yazmayın. `/predict` yalnız `{"example_id":"example_a"}` gibi üç kurgu kimlikten birini kabul eder. Eksik/yanlış anahtar 401; eksik/fazla alan veya bilinmeyen senaryo 422; hazır olmayan model 503 döndürür. Model bütünlüğü başlangıçta denetlenir; API belgeleri kapalıdır.

İstemci örneği, aynı anahtarın bulunduğu ikinci terminalde:

```python
import os
import httpx

response = httpx.post(
    "http://127.0.0.1:8765/predict",
    headers={"X-API-Key": os.environ["OPENPLAY_DEMO_KEY"]},
    json={"example_id": "example_a"},
)
response.raise_for_status()
print(response.json())
```

Servis tek süreçli yerel HTTP prototipidir. Sayaçlar ve son 1.000 isteğin gecikmeleri bellekte tutulur; yeniden başlatmada sıfırlanır. Günlükler yalnız istek kimliği, durum, süre ve model sürümünü içerir. HTTPS, bulut, çok kullanıcı ve 7/24 çalışma doğrulanmamıştır.

## Testler

Veri indirmeden model, şema, zaman sınırı, sentetik örnekler ve arayüz kontrolleri:

```bash
python -m pytest -q -m "not integration"
python -m deployment.verify
```

Veri hazırlama tamamlandıktan sonra bütün araştırma testleri:

```bash
python -m pytest -q
```

Araştırma/arayüz kontrolleri ve gerçek loopback HTTP dahil 25 API kontrolü çalıştırılmıştır. GitHub Actions yapılandırması yalnız katılımcı verisi gerektirmeyen testleri ve yerel API doğrulamasını çalıştırır; ağdan veri indirme veya eğitim yapmaz.

## Depo düzeni

```text
analysis/           Sabit veri, kohort, kalite, özellikler, eğitim ve raporlama
deployment/         Ortak tahmin modülü, FastAPI ve doğrulama
models/             Final model, şema, manifest ve model kartı
results/            Yalnız toplu bilimsel sonuçlar ve kontrol kayıtları
docs/final/         İngilizce final raporu
docs/data/          Veri kaynağının kullanım koşulları
tests/              Sentetik ve veriyle yapılan bütünlük testleri
tools/              İsteğe bağlı PDF üretimi
data/source_lock.json  Kaynak dosyaların commit ve hash kilidi
app.py              Streamlit giriş noktası
```

## Veri kullanımı ve sınırlar

[Veri politikası](docs/DATA_POLICY.md), [model kartı](models/MODEL_CARD.md) ve [araştırma kapsamı](docs/RESEARCH_SCOPE.md) bu deponun bir parçasıdır. Katılımcı kimlikleri, anket/oyun kayıtları, kişi düzeyindeki özellik ve tahminler, günlükler veya erişim anahtarları yayımlanmaz. Model iki girdili Ridge'dir ve eğitim satırlarını saklamaz; katılımcılardan öğrenmiş olması nedeniyle tamamen anonim veya risksiz olarak tanımlanmaz.

Gözlem kapsamı paydası doğrulanmamıştır; kaydı olmayan 167 kişi oynamayan sayılmaz. GDT hatırlama aralıkları örtüşür, örneklem seçilmiştir ve harici test yoktur. Gece/gerçek oturum, çok platform ve isteğe bağlı NLP kapsam sınırları açıkça belgelenmiştir.

## Ekip

Yunus Berkay İnci · Deniz Caman · Fatih Yılmaz · İsa Adahan Ünal · Alperen Acar
