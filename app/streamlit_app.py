"""
SMS Smishing Tespit Uygulaması - Streamlit Arayüzü
Süleyman Demirel Üniversitesi - Bilgisayar Mühendisliği
"""

import streamlit as st
import pickle
import pandas as pd
import numpy as np
import sys
import os
import re
import scipy.sparse as sp
from scipy.sparse import hstack

# train_model.py'deki fonksiyonlara erişmek için path ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from train_model import (turkce_on_isleme, ozellik_cikar,
                         sms_tahmin_et, gonderen_analiz, _url_analiz,
                         RESMI_GONDERICI_IDLER, RESMI_DOMAINLER)

# ─── Sayfa Ayarları ───────────────────────────────────
st.set_page_config(
    page_title="SMS Smishing Dedektörü",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ─── CSS Stili ────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    .result-zarali {
        background: linear-gradient(135deg, #ff4b4b22, #ff4b4b11);
        border: 2px solid #ff4b4b;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .result-guvenli {
        background: linear-gradient(135deg, #00cc6622, #00cc6611);
        border: 2px solid #00cc66;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .result-uyari {
        background: linear-gradient(135deg, #ffa50022, #ffa50011);
        border: 2px solid #ffa500;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .badge-resmi {
        display: inline-block;
        background: #00cc66;
        color: white;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 2px;
    }
    .badge-suphe {
        display: inline-block;
        background: #ff4b4b;
        color: white;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 2px;
    }
    .badge-belirsiz {
        display: inline-block;
        background: #888;
        color: white;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .stTextArea textarea {
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Yardımcı: gönderici badge ────────────────────────
def gonderen_badge(bilgi: dict) -> str:
    tur = bilgi.get('tur', 'bilinmiyor')
    guven = bilgi.get('guven', 0.5)
    etiketler = {
        'resmi_id'      : ('badge-resmi',   '✅ Resmi Gönderici ID'),
        'kisa_kod'      : ('badge-resmi',   '✅ Kısa Kod (Operatör/Banka)'),
        'alfanumerik'   : ('badge-belirsiz','🔵 Alfanümerik (Bilinmiyor)'),
        'mobil_tr'      : ('badge-suphe',   '⚠️ Bireysel Türk Numarası'),
        'uluslararasi'  : ('badge-suphe',   '🚨 Yabancı Numara'),
        'bilinmiyor'    : ('badge-belirsiz','— Gönderici Belirtilmedi'),
        'diger'         : ('badge-belirsiz','❓ Tanımlanamadı'),
    }
    cls, etiket = etiketler.get(tur, ('badge-belirsiz', tur))
    return f'<span class="{cls}">{etiket}</span>'

# ─── Model Yükle (Cache ile) ──────────────────────────
@st.cache_resource
def model_yukle():
    model_yolu = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "models", "smishing_model.pkl")
    if not os.path.exists(model_yolu):
        st.error("❌ Model bulunamadı! Lütfen önce `train_model.py` çalıştırın.")
        st.stop()
    with open(model_yolu, "rb") as f:
        return pickle.load(f)

model_paketi = model_yukle()

# ─── Header ───────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🔐 SMS Smishing Dedektörü</h1>
    <p>Türkçe SMS mesajlarını yapay zeka ile analiz et</p>
    <small>SDÜ Bilgisayar Mühendisliği - Tasarım-I Projesi</small>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar: Model Bilgileri ─────────────────────────
with st.sidebar:
    st.header("📊 Model Bilgileri")

    st.metric("Aktif Model", model_paketi["model_adi"])
    st.metric("Test F1 Skoru", f"{model_paketi['f1_skoru']*100:.1f}%")

    st.divider()
    st.subheader("Tüm Model Karşılaştırması")

    sonuclar = model_paketi.get("tum_sonuclar", {})
    if sonuclar:
        df_sonuc = pd.DataFrame(sonuclar).T.round(4)
        df_sonuc.columns = ["Accuracy", "Precision", "Recall", "F1"]
        st.dataframe(df_sonuc, use_container_width=True)

    st.divider()
    st.subheader("ℹ️ Hakkında")
    st.write("""
    Bu sistem makine öğrenimi kullanarak Türkçe SMS mesajlarını analiz eder
    ve **Zararlı (Smishing)** veya **Güvenli** olarak sınıflandırır.

    **Kullanılan Teknikler:**
    - TF-IDF Vektörleştirme
    - Türkçe NLP Ön İşleme
    - Resmi Domain Whitelist
    - Domain Taklit Tespiti
    - Gönderici ID Analizi
    - SVM / Random Forest / Naive Bayes
    """)

    st.divider()
    st.subheader("📋 Resmi Gönderici Örnekleri")
    st.caption("Bu ID'lerden gelen mesajlar daha güvenilir sayılır:")
    ornekler = sorted(list(RESMI_GONDERICI_IDLER))[:30] # Show more examples
    st.code(", ".join(o.upper() for o in ornekler))

# ─── Ana Analiz Bölümü ────────────────────────────────
st.subheader("📨 SMS Analiz Et")

col_msg, col_info = st.columns([3, 1])
with col_msg:
    mesaj = st.text_area(
        "Analiz edilecek SMS mesajını buraya yapıştırın:",
        height=120,
        placeholder="Örnek: Tebrikler! 5000 TL kazandınız. Hemen tıklayın: bit.ly/odul",
        help="Türkçe SMS metni girin."
    )

with col_info:
    gonderen = st.text_input(
        "Gönderici (opsiyonel):",
        placeholder="THY, 05551234567...",
        help=(
            "SMS'in geldiği numara veya başlık.\n\n"
            "**Örnekler:**\n"
            "- `THY` → Türk Hava Yolları ✅\n"
            "- `GARANTI` → Garanti Bankası ✅\n"
            "- `05551234567` → Bireysel numara ⚠️\n"
            "- `+44...` → Yabancı numara 🚨\n\n"
            "Gönderici bilgisi, link içeren resmi mesajların\n"
            "yanlış spam algılanmasını önler."
        )
    )
    if gonderen:
        bilgi = gonderen_analiz(gonderen)
        tur_etiket = {
            'resmi_id': '✅ Resmi',
            'kisa_kod': '✅ Kısa Kod',
            'alfanumerik': '🔵 Bilinmiyor',
            'mobil_tr': '⚠️ Bireysel',
            'uluslararasi': '🚨 Yabancı',
            'bilinmiyor': '—',
            'diger': '❓',
        }
        st.caption(f"Tür: **{tur_etiket.get(bilgi['tur'], bilgi['tur'])}**")
        st.progress(bilgi['guven'], text=f"Güven: {bilgi['guven']*100:.0f}%")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    analiz_btn = st.button("🔍 Analiz Et", type="primary", use_container_width=True)

# ─── Sonuç Göster ────────────────────────────────────
if analiz_btn:
    if not mesaj.strip():
        st.warning("⚠️ Lütfen analiz edilecek bir SMS mesajı girin.")
    else:
        with st.spinner("🤔 Analiz ediliyor..."):
            sonuc = sms_tahmin_et(mesaj, model_paketi, gonderen=gonderen)

        st.divider()
        st.subheader("📋 Analiz Sonucu")

        is_spam   = sonuc["etiket"] == "spam"
        guven_val = float(sonuc["guven"].replace("%", ""))
        url_bilgi = sonuc.get("url_bilgi", {})
        gon_bilgi = sonuc.get("gonderen_bilgi", {})

        # ── Sonuç kutusu ──
        if is_spam and guven_val >= 70:
            st.markdown("""
            <div class="result-zarali">
                <h2>🔴 ZARALI MESAJ TESPİT EDİLDİ</h2>
                <h3>Smishing / Spam</h3>
                <p>Bu mesaj muhtemelen bir dolandırıcılık girişimidir.</p>
            </div>""", unsafe_allow_html=True)
        elif is_spam and guven_val < 70:
            st.markdown("""
            <div class="result-uyari">
                <h2>⚠️ ŞÜPHELI MESAJ</h2>
                <h3>Kesin değil — dikkatli olun</h3>
                <p>Mesaj bazı risk göstergeleri içeriyor, ancak resmi kaynak olabilir.</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="result-guvenli">
                <h2>🟢 GÜVENLİ MESAJ</h2>
                <h3>Meşru SMS</h3>
                <p>Bu mesaj normal/güvenli görünüyor.</p>
            </div>""", unsafe_allow_html=True)

        st.write("")

        # ── Metrik kartları ──
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Model Güveni", sonuc["guven"])
        with col_b:
            tehlike = int(sonuc.get("tehlike_skoru", 0))
            st.metric("Tehlike Skoru", f"{tehlike}/10",
                      delta="Yüksek risk" if tehlike > 3 else "Normal",
                      delta_color="inverse" if tehlike > 3 else "normal")
        with col_c:
            st.metric("Kullanılan Model", model_paketi["model_adi"])

        # ── Güven çubuğu ──
        st.write("")
        st.write("**Sınıflandırma güveni:**")
        renk = "🔴" if is_spam else "🟢"
        st.progress(guven_val / 100,
                    text=f"{renk} {sonuc['sonuc']} — {sonuc['guven']} güven")

        # ── Gönderici & Domain Analizi ──
        st.write("")
        with st.expander("🔎 Gönderici & Domain Analizi", expanded=True):
            col_g, col_d = st.columns(2)

            with col_g:
                st.markdown("**Gönderici Analizi**")
                st.markdown(gonderen_badge(gon_bilgi), unsafe_allow_html=True)
                guven_pct = gon_bilgi.get('guven', 0.5)
                st.progress(guven_pct,
                            text=f"Gönderici güven skoru: {guven_pct*100:.0f}%")
                if gon_bilgi.get('tur') == 'mobil_tr':
                    st.warning("Bireysel bir Türk numarasından gelen SMS'lerde "
                               "link tıklamadan önce dikkatli olun!")
                elif gon_bilgi.get('tur') == 'uluslararasi':
                    st.error("Yabancı numara + link kombinasyonu yüksek risk!")
                elif gon_bilgi.get('tur') == 'resmi_id':
                    st.success("Tanınan resmi bir gönderici ID'si.")

            with col_d:
                st.markdown("**Domain / Link Analizi**")
                if url_bilgi.get('resmi') == 1:
                    st.markdown('<span class="badge-resmi">✅ Resmi Domain Tespit Edildi</span>',
                                unsafe_allow_html=True)
                    st.success("Mesajdaki link, bilinen resmi bir domaine ait.")
                elif url_bilgi.get('taklit') == 1:
                    st.markdown('<span class="badge-suphe">🚨 Domain Taklit Şüphesi</span>',
                                unsafe_allow_html=True)
                    st.error("Link, bir kurumun adını taklit eden sahte bir domain içeriyor!")
                elif url_bilgi.get('suphe_skoru', 0) >= 2:
                    st.markdown('<span class="badge-suphe">⚠️ Şüpheli Domain/Uzantı</span>',
                                unsafe_allow_html=True)
                    st.warning("Mesajdaki link şüpheli bir uzantı içeriyor (.xyz, .top vb.)")
                else:
                    st.markdown('<span class="badge-belirsiz">— Link Yok veya Belirsiz</span>',
                                unsafe_allow_html=True)
                    st.info("Mesajda bilinen bir domain bulunamadı.")

        # ── Detaylı özellik analizi (teknik) ──
        with st.expander("🔬 Detaylı Özellik Analizi (Teknik)"):
            df_tek = pd.DataFrame({'message': [mesaj], 'gonderen': [gonderen]})
            ozellikler = ozellik_cikar(df_tek)[0]

            ozellik_isimleri = [
                "Mesaj Uzunluğu", "Banka Bildirimi", "URL Varlığı",
                "Ünlem Sayısı", "Rakam Oranı", "Büyük Harf Oranı",
                "Tehlike Kelime Skoru", "IBAN Varlığı", "Soru İşareti",
                "Resmi Domain", "Domain Taklit", "Domain Şüphe Skoru",
                "Gönderici Güven Skoru"
            ]

            df_oz = pd.DataFrame({
                "Özellik": ozellik_isimleri[:len(ozellikler)],
                "Değer"  : ozellikler[:len(ozellik_isimleri)].round(4),
            })
            st.dataframe(df_oz, use_container_width=True, hide_index=True)

# ─── Örnek Mesajlar ───────────────────────────────────
st.divider()
st.subheader("🧪 Örnek Mesajlarla Test Et")

col_spam, col_ham = st.columns(2)

with col_spam:
    st.markdown("**🔴 Zararlı (Smishing) Örnekleri:**")
    spam_ornekler = [
        ("Tebrikler! 5000 TL kazandınız → bit.ly/kazan", ""),
        ("Hesabınız bloke! garanti-dogrula.xyz", ""),
        ("PTT: Paket bekliyor, 2 TL öde: ptt-xyz.net", ""),
    ]
    for ornek_mesaj, ornek_gon in spam_ornekler:
        if st.button(f"📋 {ornek_mesaj[:40]}...", key=f"spam_{ornek_mesaj[:10]}",
                     use_container_width=True):
            st.session_state['ornek_mesaj']   = ornek_mesaj
            st.session_state['ornek_gonderen'] = ornek_gon

with col_ham:
    st.markdown("**🟢 Güvenli (Meşru) Örnekleri:**")
    ham_ornekler = [
        ("Toplantı saat 15:00'e ertelendi.", ""),
        ("Uçuşunuz onaylandı. Check-in: thy.com/check-in THY6789", "THY"),
        ("Hesabınıza 1500 TL yatırılmıştır.", "GARANTI"),
        ("Kargonuz yola çıkmıştır. Takip: yurticikargo.com/takip", "YURTICI"),
    ]
    for ornek_mesaj, ornek_gon in ham_ornekler:
        etiket = f" [{ornek_gon}]" if ornek_gon else ""
        if st.button(f"📋 {ornek_mesaj[:35]}{etiket}", key=f"ham_{ornek_mesaj[:10]}",
                     use_container_width=True):
            st.session_state['ornek_mesaj']   = ornek_mesaj
            st.session_state['ornek_gonderen'] = ornek_gon

if 'ornek_mesaj' in st.session_state:
    gon = st.session_state.get('ornek_gonderen', '')
    gon_txt = f" | Gönderici: **{gon}**" if gon else ""
    st.info(f"💡 Seçilen örnek: **{st.session_state['ornek_mesaj'][:60]}**{gon_txt}"
            f" — Yukarıya yapıştırıp analiz edin!")

# ─── Footer ───────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.8rem;">
    SDÜ Mühendislik Fakültesi — Bilgisayar Mühendisliği | Tasarım-I Dersi<br>
    Batuhan Can Aracı (2211012609) | Danışman: Doç. Dr. Fatih Ahmet Şenel
</div>
""", unsafe_allow_html=True)
