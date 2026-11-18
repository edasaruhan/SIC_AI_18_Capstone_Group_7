"""Aggregate results and fictional scenarios, with no participant data access."""
import json
import pandas as pd
import streamlit as st
from analysis.config import ROOT, RESULTS
from deployment.inference import get_model, SCENARIOS

st.set_page_config(page_title="Open Play | Group 7", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {max-width:1180px;padding-top:2.2rem}
h1 {letter-spacing:-1.5px} [data-testid="stMetric"] {background:#162439;padding:18px;border-radius:12px}
.eyebrow {font-size:.85rem;color:#7ed4c5;letter-spacing:.16em;font-weight:600}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">SIC CAPSTONE · GROUP 7 · OPEN PLAY</div>', unsafe_allow_html=True)
st.title("Oyun davranışı ne kadar bilgi katıyor?")
st.write("İlk 14 günlük kaydedilen Steam davranışı, başlangıç GDT skoru ve toplam sürenin üzerine sonraki GDT ölçümünü tahmin etmede katkı sağlıyor mu?")
st.caption("Yerel araştırma prototipi · Sentetik örnekler · Tanı veya kişisel alarm üretmez")

def load_result(name):
    return json.loads((RESULTS / name).read_text())

try:
    primary = load_result("primary_final.json")
    quality = load_result("quality_audit.json")
    legacy = load_result("legacy.json")
    secondary = load_result("secondary.json")
except FileNotFoundError:
    st.error("Analiz sonuçları bulunamadı. README'deki veri hazırlama ve eğitim komutlarını çalıştırın.")
    st.stop()

cols = st.columns(3)
cols[0].metric("GDT analizi", f"{primary['people']} kişi")
cols[1].metric("RQ2 analizi", f"{secondary['people']} kişi", f"{secondary['rows']} kişi-geçiş", delta_color="off")
cols[2].metric("İç doğrulama", "5 dış / 3 iç kat")

tab1, tab2, tab3 = st.tabs(["Araştırma sonuçları", "Sentetik model demosu", "Yöntem ve sınırlar"])
with tab1:
    st.subheader("Gerçek çalıştırma sonuçları")
    option = st.selectbox("Analiz", ["GDT · düzeltilmiş zaman penceresi", "GDT · önceki raporun tekrarı", "RQ2 · sonraki rutin müdahalesi"])
    current = primary if option.startswith("GDT · düzel") else legacy if option.startswith("GDT · önce") else secondary
    frame = pd.DataFrame(current["metrics"]).T.rename_axis("Model")
    st.dataframe(frame.style.format("{:.4f}"), use_container_width=True)
    st.bar_chart(frame[["MAE"]], horizontal=True, color="#7ed4c5")
    interval = current["paired_uncertainty"]["R_M3_minus_R_M2"]
    lo, hi = interval["CI95"]
    st.info(f"Davranış özelliklerinin hata farkı (R M3 − R M2): {interval['difference_MAE']:+.4f}; kişi bootstrap %95 aralığı [{lo:+.4f}, {hi:+.4f}]. Negatif değer daha düşük hata demektir. Bu aralık kişisel tahmin aralığı değildir.")
    st.caption("Bootstrap sabit dış kat hatalarını kullanır; modelleri yeniden eğitmez. R SELECT, aile ve ayarı iç katlarda seçen prosedürdür. Tablodaki en iyi satırı seçmek bağımsız test oluşturmaz.")
with tab2:
    st.subheader("Kayıtlı modelden hesaplanan tahmin")
    st.write("Bu üç örnek kurgusaldır. Araç gerçek kişi verisi kabul etmez.")
    example = st.selectbox("Sentetik örnek", list(SCENARIOS), format_func=lambda k: f"{k} · başlangıç {SCENARIOS[k]['baseline']} GDT · {SCENARIOS[k]['weekly_hours']} saat/hafta")
    try:
        engine = get_model()
        output = engine.predict(example)
        c1, c2 = st.columns(2)
        c1.metric("Tahmin edilen sonraki GDT toplamı", f"{output['predicted_gdt_total']:.4f}")
        c2.metric("Başlangıca göre tahmin edilen değişim", f"{output['predicted_change']:+.4f}")
        st.caption(f"Model: {output['model_version']} · {engine.bundle['family']} · Sonuçlar kırpılmamış regresyon çıktılarıdır.")
        st.warning("Araştırma örneği; tanı veya alarm değildir. Senaryolar arasındaki fark davranışı değiştirmenin nedensel etkisini göstermez.")
    except (OSError, ValueError) as error:
        st.error(f"Model hazır değil; tahmin üretilmedi: {error}")
with tab3:
    st.subheader("Veri ve doğrulama sınırları")
    st.markdown(f"""
- Open Play sabit commit: `{primary and 'eb0a68c1a7ca1fad54e57a1f89b9d5450f8be840'}`.
- {quality['flow']['eligible_gdt']} uygun anket tamamlayıcısından {primary['people']} kişide erken Steam kaydı var. Kayıt varlığı gözlem kapsamını kanıtlamaz; diğer 167 kişi oynamayan olarak sınıflandırılmaz.
- Final analizinde bütün yaklaşık kayıtlar ve kaynak zaman damgası tahmin anından önce olmalıdır. Eski yöntemden taşan {quality['steam']['legacy_end_after_cutoff']} kayıt çıkarıldı; kişi sayısı değişmedi.
- GDT son üç ayı sorar; hatırlama aralıkları örtüşür. Sonradan ölçülen belirti yükü tahmin edilir.
- RQ2 girdileri mevcut anketten önceki 14 gün; hedef en az 14 gün sonraki ardışık ankettir. Hem iç hem dış katlar kişi ile gruplanır.
- Aynı kohort önceki ödevlerde incelendi. Harici veya hiç görülmemiş bağımsız test yoktur.
- Telemetri eksikliği, yaklaşık zamanlar, gönüllü örneklem ve katılımcı kaybı genellenebilirliği sınırlar.
""")
    st.caption("Ham veriler, kimlikler, kişisel takvimler, klinik eşikler ve otomatik bildirimler bu arayüzde yer almaz.")
