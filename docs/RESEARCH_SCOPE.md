# Araştırma kapsamı

## Tamamlanan analizler

| Çalışma | Kanıt | Yorum |
|---|---|---|
| Sabit Open Play sürümü ve uygun kohort | `data/source_lock.json`, `results/quality_audit.json` | 730 tam GDT çifti → 723 intake eşleşmesi → 710 uygun kişi; Steam koşullu analizde 543 kişi. |
| İlk altı özellik ve M0–M3 yeniden üretimi | `analysis/data.py`, `results/legacy.json` | Önceki on modelin 30 yuvarlanmış metriği eşleşti. |
| Zaman denetimi ve ayrı duyarlılık analizi | `results/primary_final.json` | Tam yaklaşık kayıt ve kaynak zamanı pencere içinde tutulur; sekiz taşan kayıt çıkarıldı. Aynı kişiler korundu. |
| İç döngüde aile/ayar seçimi | `analysis/train.py`, `results/primary_final_folds.json` | 42 ayar; seçme prosedürü ve her ailenin kendi skoru ayrı. |
| RQ2 sonraki rutin müdahalesi | `results/secondary.json` | 935 kişi, 2.093 geçiş; gerçek aralık ≥14 gün; iç ve dış katlar kişi gruplu. |
| Belirsizlik ve açıklanabilirlik | `results/explanation_summary.json`, `results/*_explanations.json` | Sabit OOF kişi bootstrap, dış kat permutation ve tam doğrusal interventional SHAP. |
| Yerel araştırma arayüzü ve API | `app.py`, `deployment/` | Gerçek model, toplu sonuçlar, üç sentetik senaryo; anahtarlı yerel API. |

## Kapsam sınırları

- Gözlenebilirlik paydası doğrulanmamıştır. Pozitif kayıt oranı gözlem kapsamı değildir; kayıtsız süre gerçek oynamama sayılmaz. %80 kapsam eşiği uygulanmamıştır.
- Steam kayıtları yaklaşık ve sağlayıcı tarafından düzeltilmiştir. Kesin oturum başlangıcı/bitişi veya gerçek aktif oynama olarak yorumlanmaz. Gece payı ve yerel haftasonu özellikleri doğrulanmış bireysel saat dilimi geçmişi olmadan üretilmemiştir.
- Xbox, Nintendo ve mobil verinin birleştirilmesi, oyun çeşitliliği/türler, farklı pencere uzunlukları ve ek model aileleri gelecekte değerlendirilebilir.
- NLP isteğe bağlı kapsamdır. Bağımsız insan etiketleri ve etiketleme güvenilirliği olmadan NLP sonucu üretilmemiştir; ham metin dış API'ye gönderilmemiştir.
- Aynı kohort daha önce incelenmiştir. Sonuçlar keşifsel iç doğrulamadır; harici veya hiç görülmemiş bağımsız test olarak sunulmaz. GDT hatırlama dönemleri örtüşür.
- Kişisel risk sınıflaması, klinik eşik, tanı, tedavi önerisi, bildirim veya gerçek kullanıcı izleme yoktur. RQ2 yalnız araştırma sonucu olarak raporlanır.
- Yeni bir kullanıcı için doğrulanmış kapsam/abstention algoritması, ileriye dönük değerlendirme, HTTPS/bulut, çok kullanıcı ve sürekli çalışma test edilmemiştir. Windows/Linux komutları sunulur; bu ortamlarda çalıştırma iddiası yoktur.

Sonuç: Denenen günlük Steam örüntüleri, başlangıç GDT ve toplam kaydedilen sürenin üzerine belirgin ek tahmin faydası göstermemiştir. Bu sonuç ilk çok platformlu araştırma tasarımının tamamının uygulanmış olduğu anlamına gelmez.
