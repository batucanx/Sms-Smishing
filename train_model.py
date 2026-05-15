"""
SMS Tabanlı Smishing Tespit Sistemi - Model Eğitim Pipeline
Süleyman Demirel Üniversitesi - Bilgisayar Mühendisliği
Öğrenci: Batuhan Can Aracı - 2211012609
"""

import pandas as pd
import numpy as np
import pickle
import os
import re
import sys
from difflib import SequenceMatcher

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (classification_report, confusion_matrix,
                             accuracy_score, f1_score, precision_score, recall_score)
from scipy.sparse import hstack
import scipy.sparse as sp
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 0. DOMAIN / GÖNDERİCİ SABİTLERİ
# ─────────────────────────────────────────────

# Türkiye'de faaliyet gösteren kurumların resmi domain'leri
RESMI_DOMAINLER = {
    # Havayolları
    "thy.com", "turkishairlines.com", "pegasusairlines.com", "flypgs.com",
    "anadolujet.com", "sunexpress.com", "corendonairlines.com",
    # Bankalar
    "garanti.com.tr", "garantibbva.com.tr", "isbank.com.tr",
    "akbank.com", "ziraatbank.com.tr", "vakifbank.com.tr",
    "halkbank.com.tr", "ykb.com", "qnbfinansbank.com", "qnb.com.tr",
    "denizbank.com", "teb.com.tr", "sekerbank.com.tr",
    "ing.com.tr", "albaraka.com.tr", "kuveytturk.com.tr",
    "odeabank.com.tr", "fibabanka.com.tr", "burgan.com.tr",
    "turkiyefinans.com.tr", "enpara.com",
    # E-ticaret
    "trendyol.com", "hepsiburada.com", "n11.com",
    "gittigidiyor.com", "ciceksepeti.com", "boyner.com.tr",
    "lcwaikiki.com", "zara.com", "defacto.com.tr", "koton.com",
    "mavi.com", "amazon.com.tr", "teknosa.com", "vatanbilgisayar.com",
    "mediamarkt.com.tr", "yemeksepeti.com", "getir.com",
    # Kargo / PTT
    "ptt.gov.tr", "mng.com.tr", "yurticikargo.com",
    "arascargo.com", "surat.com.tr", "horoz.com.tr", "ups.com.tr",
    # Telekom & İnternet
    "turkcell.com.tr", "vodafone.com.tr", "turk.net",
    "turktelekom.com.tr", "superonline.net", "ksgames.com", "kablonet.com.tr",
    # Otobüs Firmaları ve Ulaşım
    "kamilkoc.com.tr", "pamukkale.com.tr", "metroturizm.com.tr", "obilet.com",
    "enuygun.com", "turna.com", "biletall.com", "marti.tech",
    # Devlet ve Kamu
    "turkiye.gov.tr", "e-devlet.gov.tr", "sgk.gov.tr",
    "gib.gov.tr", "nvi.gov.tr", "osym.gov.tr", "mhrs.gov.tr",
    "yok.gov.tr", "meb.gov.tr", "saglik.gov.tr",
    "ibb.gov.tr", "ankara.bel.tr", "izmir.bel.tr", "csb.gov.tr",
    "icisleri.gov.tr", "adalet.gov.tr", "iskur.gov.tr",
    # Üniversiteler
    "sdu.edu.tr", "itu.edu.tr", "metu.edu.tr", "boun.edu.tr",
    "hacettepe.edu.tr", "anadolu.edu.tr", "ankara.edu.tr",
    "ege.edu.tr", "deu.edu.tr",
    # Hastane / Sağlık
    "memorial.com.tr", "acibadem.com.tr", "medicalpark.com.tr",
    "florence.com.tr",
    # Sigorta
    "allianz.com.tr", "axa.com.tr", "mapfre.com.tr", "hdisigorta.com.tr",
    # Toplantı / İletişim
    "zoom.us", "meet.google.com", "teams.microsoft.com",
    "drive.google.com", "dropbox.com", "icloud.com",
    # Sosyal Medya
    "youtube.com", "instagram.com", "twitter.com", "x.com",
    "facebook.com", "linkedin.com", "whatsapp.com",
    # Yemek / Market
    "migros.com.tr", "a101.com.tr", "bim.com.tr", "carrefoursa.com.tr",
    "dominos.com.tr", "burgerking.com.tr",
    # Ödeme Sistemleri
    "iyzico.com", "paytr.com", "param.com.tr",
    "papara.com", "tosla.com", "ininal.com",
    "bkmexpress.com.tr", "paypal.com", "wise.com",
    "moka.com", "paribu.com", "btcturk.com",
    # Eğlence / Medya / Bilet
    "puhutv.com", "gain.tv", "mubi.com", "disneyplus.com",
    "biletix.com", "biletinial.com", "passo.com.tr", "passolig.com.tr",
    # Diğer
    "apple.com", "appleid.apple.com", "google.com", "microsoft.com",
    "netflix.com", "amazon.com", "spotify.com", "blutv.com",
    "exxen.com", "sahibinden.com", "arabam.com",
    "tatilsepeti.com", "jollytur.com", "etstur.com", "tatilbudur.com",
    "bonus.com.tr", "cardfinans.com.tr", "maximum.com.tr",
    "iski.istanbul", "igdas.istanbul",
    # Kısa URL domain'leri (resmi şirketlerin kısaltılmış linkleri)
    "turkcell.li", "svr.link", "madp.tr", "fy.fiyuu.com.tr",
    "fiyuu.com.tr", "bip.com", "bip.ai",
    "lfrfrm.com", "hfrfrm.com",  # Hepsiburada kısa link
    "trfrm.com",  # Trendyol kısa link
    # Bankalar (eksik)
    "yapikredi.com.tr", "worldcard.com.tr", "hsbc.com.tr",
    "anadolubank.com.tr", "turkishbank.com.tr",
    # Mağazalar / Perakende / Kozmetik / Parfüm
    "madparfum.com", "gratis.com", "watsons.com.tr", "sephora.com.tr",
    "flormar.com.tr", "colins.com.tr", "uspoloassn.com",
    "pierrecardin.com.tr", "koton.com", "mavi.com",
    "sok.com.tr", "koctas.com.tr", "bauhaus.com.tr", "tekzen.com.tr",
    "decathlon.com.tr", "intersport.com.tr", "nike.com",
    "adidas.com.tr", "arcelik.com.tr", "vestel.com.tr", "beko.com.tr",
    "starbucks.com.tr", "kfc.com.tr", "pizzahut.com.tr",
    "mcdonalds.com.tr", "popeyes.com.tr", "tavukdunyasi.com.tr",
    # Diğer hizmetler
    "scotty.app", "moovit.com", "obilet.com",
    "bedas.com.tr", "tedas.gov.tr", "ayedas.com.tr",
    "aksigorta.com.tr", "somposigorta.com.tr", "zurich.com.tr",
}

# Domain taklit tespiti için marka kelimeleri
# (Bunları içeren ama resmi domain olmayan URL'ler şüpheli)
MARKA_ISIMLERI = [
    "garanti", "akbank", "ziraat", "vakif", "halk", "isbank", "ykb", "qnb",
    "denizbank", "teb", "sekerbank", "ing", "albaraka", "kuveytturk",
    "thy", "thyairlines", "turkishair", "pegasus", "flypgs", "anadolujet", "sunexpress",
    "trendyol", "hepsiburada", "amazon", "n11", "ciceksepeti", "boyner", "lcwaikiki",
    "yemeksepeti", "getir",
    "ptt", "kargo", "mng", "yurtici", "aras", "surat", "ups",
    "turkcell", "vodafone", "telekom", "superonline",
    "kamilkoc", "pamukkale", "metro", "obilet", "enuygun", "turna",
    "netflix", "apple", "whatsapp", "google", "microsoft", "spotify", "exxen", "blutv",
    "edevlet", "e-devlet", "sgk", "vergi", "mhrs", "osym",
]

# Resmi alfanümerik gönderici ID'leri (kısa mesaj başlıkları)
RESMI_GONDERICI_IDLER = {
    "thy", "turkishair", "pegasus", "flypgs", "anadolujet", "sunexpress", "corendon",
    "garanti", "garantibbva", "akbank", "ziraat", "ziraatbank",
    "vakifbank", "halkbank", "isbank", "ykb", "finansbank", "qnb", "teb", "denizbank",
    "ing", "albaraka", "kuveytturk", "odeabank", "fibabanka", "burgan",
    "trendyol", "hepsiburada", "n11", "amazon", "ciceksepeti", "boyner", "lcwaikiki", "defacto",
    "teknosa", "vatan", "mediamarkt", "yemeksepeti", "getir",
    "ptt", "mnkkargo", "mngkargo", "yurtici", "araskargo", "surat", "ups",
    "turkcell", "vodafone", "turktelekom", "superonline", "kablonet",
    "kamilkoc", "pamukkale", "metro", "obilet", "enuygun", "turna", "biletall", "marti",
    "edevlet", "sgk", "gib", "nvi", "mhrs", "osym", "yok", "meb", "saglik",
    "netflix", "apple", "google", "microsoft", "spotify", "exxen", "blutv",
    "sahibinden", "arabam",
    # Bankalar (eksik olanlar)
    "yapikredi", "yapıkredi", "yapkredi", "enpara", "hsbc",
    "turkiyefinans", "anadolubank", "sekerbank", "turkishbank",
    # Mağazalar / Perakende / Kozmetik / Parfüm
    "iyasmarket", "iyas", "iyasavm", "iyas market",
    "madparfum", "mad", "mad parfum",
    "gratis", "watsons", "sephora", "flormar", "koton",
    "mavi", "colins", "uspoloassn", "pierrecardin",
    "migros", "a101", "bim", "sok", "carrefour", "carrefoursa",
    "macrocenter", "metro", "koctas", "bauhaus", "tekzen",
    "mediamarkt", "arcelik", "vestel", "beko",
    "decathlon", "intersport", "sportive", "nike", "adidas",
    "starbucks", "dominos", "burgerking", "mcdonalds", "kfc",
    "pizzahut", "popeyes", "sbarro", "tavukdunyasi",
    # AVM'ler
    "espark", "ozdilek", "forum", "mallofistanbul", "istinyepark",
    "ankamall", "cepavm", "optimum", "gordion",
    # Sigorta
    "allianz", "axasigorta", "mapfre", "hdisigorta",
    "aksigorta", "somposigorta", "zurich",
    # İletişim / Uygulama
    "bip", "sikayetvar", "sikayet var", "fiyuu",
    "scotty", "marti", "trendyol", "getir",
    # Diğer hizmetler
    "iski", "igdas", "bedas", "tedas", "ayedas",
    "biletix", "biletinial", "passo", "passolig",
    "papara", "tosla", "ininal", "param", "iyzico",
    "tatilbudur", "tatilsepeti", "jollytur", "etstur",
    "scotty", "trply", "moovit",
}

# ─────────────────────────────────────────────
# 1. TÜRKÇE NLP ÖN İŞLEME
# ─────────────────────────────────────────────

# Türkçe stop words (yaygın, anlamsız kelimeler)
TURKCE_STOP_WORDS = [
    "bir", "bu", "ve", "ile", "de", "da", "mi", "mu", "mü", "mı",
    "için", "ama", "fakat", "çok", "az", "en", "ne", "ya", "ki",
    "ben", "sen", "o", "biz", "siz", "onlar", "benim", "senin",
    "gibi", "kadar", "daha", "veya", "hem", "ya", "nasıl", "neden",
    "şimdi", "ise", "bile", "her", "hiç", "artık", "çünkü", "ise",
    "diye", "eğer", "ancak", "bütün", "tüm", "bazı", "beraber"
]

def turkce_on_isleme(metin: str) -> str:
    """
    Türkçe SMS metni için temel NLP ön işleme.
    - Küçük harfe çevirme
    - Noktalama kaldırma  
    - Stop word temizleme
    - Fazla boşluk temizleme
    """
    if not isinstance(metin, str):
        return ""
    
    # Küçük harfe çevir (Türkçe karakterler dahil)
    metin = metin.lower()
    metin = metin.replace("İ", "i").replace("I", "ı")
    
    # URL'leri akıllı tokenlara dönüştür (resmi/şüpheli/nötr)
    metin = _url_tokenize(metin)
    
    # Telefon numaralarını token'a dönüştür
    metin = re.sub(r'\b\d{10,11}\b|\b05\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b', ' telefon ', metin)
    
    # IBAN'ları token'a dönüştür
    metin = re.sub(r'\bTR\d{24}\b', ' iban ', metin)
    
    # Noktalama ve özel karakterleri kaldır (! ? gibi tehlike işaretlerini koru)
    metin = re.sub(r'[^\w\sıİüÜöÖçÇşŞğĞ!?]', ' ', metin)
    
    # Stop word'leri kaldır
    kelimeler = metin.split()
    kelimeler = [k for k in kelimeler if k not in TURKCE_STOP_WORDS and len(k) > 1]
    
    return " ".join(kelimeler)


# URL kısaltıcı servisleri
URL_KISALTICILAR = [
    'bit.ly', 't2m.io', 'cutt.ly', 'tinyurl', 'goo.gl',
    'ow.ly', 'is.gd', 'buff.ly', 'dub.is', 't.ly', 't.me',
    'shorturl.at', 'rb.gy', 'tinyurl.com',
    'fstpy.cc', 'pshgit.co', 'clck.ru', 'tinyurl.is',
    '100havale.com', 'havale.co',
]

# Şüpheli TLD'ler (genişletilmiş)
SUPHE_UZANTILARI_SET = {
    '.xyz', '.top', '.click', '.link', '.site', '.online', '.info',
    '.tk', '.ml', '.ga', '.cf', '.gq', '.win', '.loan', '.bid',
    '.stream', '.racing', '.party', '.download', '.review',
    '.icu', '.buzz', '.monster', '.rest', '.beauty',
    '.cc', '.ws', '.pw', '.su', '.work', '.life', '.fun',
    '.vip', '.club', '.space', '.guru', '.cheap',
}


def _url_tokenize(metin: str) -> str:
    """
    URL'leri akıllı tokenlara dönüştürür:
    - url_resmi : RESMI_DOMAINLER listesindeki URL'ler
    - url_suphe : Şüpheli uzantılı URL'ler (.xyz, .top, .click vb.)
    - url       : Diğer URL'ler
    """
    url_regex = re.compile(r'http\S+|www\.\S+|\S+\.(com|net|xyz|org|tr|site|top|click|link|online|info|buzz|monster|rest|beauty|icu)\S*', re.IGNORECASE)

    def replace_url(match):
        url = match.group(0).lower()
        # Resmi domain kontrolü
        for rd in RESMI_DOMAINLER:
            if rd in url:
                return ' url_resmi '
        # Şüpheli uzantı kontrolü
        for sup in SUPHE_UZANTILARI_SET:
            if sup in url:
                return ' url_suphe '
        return ' url '

    return url_regex.sub(replace_url, metin)


# ─────────────────────────────────────────────
# 2. EK ÖZELLİK ÇIKARIMI (Handcrafted Features)
# ─────────────────────────────────────────────

def _url_analiz(metin: str) -> dict:
    """
    Metindeki URL'leri çıkarır, resmi domain ve taklit tespiti yapar.
    Döner: {'resmi': int, 'taklit': int, 'suphe_skoru': int}
    """
    if not isinstance(metin, str):
        return {'resmi': 0, 'taklit': 0, 'suphe_skoru': 0}

    # URL'leri bul
    url_pattern = re.compile(
        r'(?:https?://|www\.)?'
        r'([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*\.[a-zA-Z]{2,})'
        r'(?:/[^\s]*)?'
    )
    urllar = url_pattern.findall(metin.lower())

    resmi = 0
    taklit = 0
    suphe = 0

    suphe_uzantilari = {
        '.xyz', '.top', '.click', '.link', '.site', '.online', '.info',
        '.tk', '.ml', '.ga', '.cf', '.gq', '.win', '.loan', '.bid',
        '.stream', '.racing', '.party', '.download', '.review',
        '.icu', '.buzz', '.monster', '.rest', '.beauty'
    }

    for domain in urllar:
        # Resmi domain mi?
        if any(domain == rd or domain.endswith('.' + rd) for rd in RESMI_DOMAINLER):
            resmi = 1
            continue

        # Şüpheli uzantı?
        for uzanti in suphe_uzantilari:
            if domain.endswith(uzanti):
                suphe += 2
                break

        # Marka taklit tespiti: domain bir marka adı içeriyor ama resmi değil
        ana_domain = domain.split('.')[-2] if '.' in domain else domain
        for marka in MARKA_ISIMLERI:
            if marka in domain:
                # Resmi domainlerden hiçbiriyle eşleşmiyor ama marka adı içeriyor
                if not any(domain == rd or domain.endswith('.' + rd)
                           for rd in RESMI_DOMAINLER):
                    taklit += 1
                    suphe += 3
                break

    return {'resmi': min(resmi, 1), 'taklit': min(taklit, 1),
            'suphe_skoru': min(suphe, 5)}


def gonderen_analiz(gonderen: str) -> dict:
    """
    Gönderici numarası/ID'sinden güven skoru çıkarır.
    Döner: {'guven': float 0-1, 'tur': str}
    """
    if not gonderen or not isinstance(gonderen, str):
        return {'guven': 0.5, 'tur': 'bilinmiyor'}

    g = gonderen.strip().lower()

    # Boşluksuz ve işaretsiz versiyonu ("LC-WAIKIKI" → "lcwaikiki")
    g_clean = g.replace(' ', '').replace('-', '').replace('.', '').replace('_', '')

    # Resmi alfanümerik ID (ör: THY, GARANTI) - tam eşleşme
    if g in RESMI_GONDERICI_IDLER or g_clean in RESMI_GONDERICI_IDLER:
        return {'guven': 0.95, 'tur': 'resmi_id'}

    # Gönderici adı resmi listede kısmi eşleşme ("IYAS MARKET" içinde "iyas" var mı?)
    for resmi_id in RESMI_GONDERICI_IDLER:
        if len(resmi_id) >= 3 and (resmi_id in g or resmi_id in g_clean):
            return {'guven': 0.90, 'tur': 'resmi_id_kismi'}

    # Alfanümerik ama listede yok → orta güven (Tire ve nokta içerebilir)
    if re.fullmatch(r'[a-z][a-z0-9\-\.]{2,20}', g):
        return {'guven': 0.70, 'tur': 'alfanumerik'}

    # Alfanümerik çok kelimeli ("IYAS MARKET" veya "LC-WAIKIKI" gibi) ama listede yok
    if re.fullmatch(r'[a-zğüşıöçİ][a-zğüşıöç0-9 \-\.]{2,30}', g):
        return {'guven': 0.65, 'tur': 'alfanumerik'}

    # Kısa kod (4-6 rakam) → operatör / banka kanalı
    if re.fullmatch(r'\d{4,6}', g):
        return {'guven': 0.80, 'tur': 'kisa_kod'}

    # Türk mobil numarası (05xx...)
    if re.fullmatch(r'(\+90|0090|0)?5\d{9}', g.replace(' ', '').replace('-', '')):
        return {'guven': 0.30, 'tur': 'mobil_tr'}

    # Uluslararası numara
    if g.startswith('+') and not g.startswith('+90'):
        return {'guven': 0.20, 'tur': 'uluslararasi'}

    return {'guven': 0.40, 'tur': 'diger'}


def ozellik_cikar(df: pd.DataFrame) -> np.ndarray:
    """
    Metin istatistiklerinden manuel özellikler çıkar.
    Bu özellikler TF-IDF vektörlerine eklenir (hibrit yaklaşım).
    Yeni: resmi domain, domain taklit, gönderici güveni
    """
    df = df.copy()
    df['message'] = df['message'].fillna('')
    ozellikler = pd.DataFrame()

    # Mesaj uzunluğu
    ozellikler['uzunluk'] = df['message'].str.len()

    # Banka bildirimi deseni (meşru bankalar kullandığı ifadeler)
    banka_pattern = r'\d{4} nolu hesab|\bFAST\b|\bEFT\b|gönderilmiştir|alınmıştır'
    ozellikler['banka_bildirimi'] = df['message'].str.contains(
        banka_pattern, regex=True, case=False).fillna(False).astype(int)

    # URL varlığı
    ozellikler['url_var'] = df['message'].str.contains(
        r'http|www|\.(com|net|xyz|org|tr)/', regex=True).fillna(False).astype(int)

    # Ünlem sayısı
    ozellikler['unlem_sayisi'] = df['message'].str.count('!')

    # Rakam yoğunluğu
    ozellikler['rakam_orani'] = df['message'].apply(
        lambda x: sum(c.isdigit() for c in str(x)) / max(len(str(x)), 1))

    # Büyük harf oranı
    ozellikler['buyuk_harf_orani'] = df['message'].apply(
        lambda x: sum(c.isupper() for c in str(x)) / max(len(str(x)), 1))

    # Tehlikeli anahtar kelimeler
    tehlike_kelimeleri = [
        'tıklayın', 'tiklayin', 'kazandınız', 'kazandiniz',
        'bloke', 'acil', 'kapatılıyor', 'silinecek',
        'dogrulama', 'doğrulama', 'hediye', 'tebrikler',
        'ödül', 'odul', 'virüs', 'virus',
        # Kumarhane / Bahis / Casino dolandırıcılığı
        'freespin', 'free spin', 'deneme bonusu', 'cevrimsiz',
        'çevrimsiz', 'casino', 'bahis', 'slot', 'cark',
        'çark', 'jackpot', 'premium bakiye', 'yatirim bonusu',
        'yatırım bonusu', 'kayip bonusu', 'kayıp bonusu',
        'havale yatır', 'havale yatir', 'cekim yap', 'çekim yap',
        'uye ol sartsiz', 'üye ol şartsız', 'risksiz',
        'lisansli altyapi', 'lisanslı altyapı',
        'minimum havale', 'pronet',
        # Metin2 / PvP Server tanıtımları
        'metin2', 'pvp server', 'mt2', '1-99', '1-105', '55-250',
        'orta emek', 'zor emek', 'kolay emek', 'wslik server'
    ]
    ozellikler['tehlike_skoru'] = df['message'].apply(
        lambda x: sum(1 for k in tehlike_kelimeleri if k in str(x).lower())
        if pd.notna(x) else 0)

    # IBAN varlığı
    ozellikler['iban_var'] = df['message'].str.contains(
        r'TR\d{24}|IBAN', regex=True).fillna(False).astype(int)

    # Soru işareti
    ozellikler['soru_var'] = df['message'].str.contains(
        '?', regex=False).fillna(False).astype(int)

    # ── Resmi domain ve taklit tespiti ──────────────
    url_sonuc = df['message'].apply(_url_analiz)
    ozellikler['resmi_domain_var'] = url_sonuc.apply(lambda x: x['resmi'])
    ozellikler['domain_taklit']    = url_sonuc.apply(lambda x: x['taklit'])
    ozellikler['domain_suphe']     = url_sonuc.apply(lambda x: x['suphe_skoru'])

    # ── URL kısaltıcı tespiti ──────────────
    ozellikler['url_kisaltma'] = df['message'].apply(
        lambda x: int(any(k in str(x).lower() for k in URL_KISALTICILAR)))

    # ── Aciliyet skoru ──────────────
    aciliyet_kelimeleri = [
        'acil', 'hemen', 'derhal', 'son gün', 'son gun',
        'süresi doluyor', 'suresi doluyor', 'kapatılıyor', 'kapatiliyor',
        'silinecek', 'son şans', 'son sans', 'bugün son', 'bugun son',
        '24 saat', '48 saat', 'yarın son', 'yarin son',
        'son tarih bugün', 'son tarih bugun'
    ]
    ozellikler['aciliyet_skoru'] = df['message'].apply(
        lambda x: sum(1 for k in aciliyet_kelimeleri if k in str(x).lower())
        if pd.notna(x) else 0)

    # ── Meşru banka/kurum bildirimi deseni ──────────────
    mesru_banka_desenleri = [
        r'\d{4}\s*nolu\s*hesab', r'EFT.*gönderil', r'EFT.*tamamlan',
        r'bakiyeniz', r'Bakiyeniz', r'ekstreniz\s*hazır',
        r'son\s*odeme\s*tarih', r'fatura.*kesilmiştir', r'fatura.*kesilmistir',
        r'taksit.*ödemeniz', r'havale.*yapıl', r'havale.*gercekles',
        r'FAST.*havale', r'teslim edilmiştir', r'teslim edilmistir',
        r'siparişiniz.*verilmiştir', r'siparissiniz.*verilmistir',
        r'kargoya verilmiştir', r'kargoya verilmistir',
        r'randevunuz.*onaylanmıştır', r'randevunuz.*onaylanmistir',
        r'ödemeniz alınmıştır', r'odemeniz alinmistir',
        r'hesabınıza.*yatırılmıştır', r'hesabiniza.*yatirilmistir',
    ]
    ozellikler['mesru_banka_deseni'] = df['message'].apply(
        lambda x: int(any(re.search(p, str(x), re.IGNORECASE)
                          for p in mesru_banka_desenleri)) if pd.notna(x) else 0)

    # ── BTK B-Kodu tespiti (Türkiye'de ticari SMS zorunluluğu) ──────────────
    # Resmi ticari SMS'lerin sonunda B\d{3} formatında BTK kodu bulunur
    ozellikler['has_btk_code'] = df['message'].apply(
        lambda x: int(bool(re.search(r'\bB\d{3}\b', str(x)))) if pd.notna(x) else 0)

    # ── MERSIS kodu tespiti (şirket kayıt numarası) ──────────────
    # Resmi ticari SMS'lerde Mersis numarası bulunur
    ozellikler['has_mersis'] = df['message'].apply(
        lambda x: int(bool(re.search(r'[Mm]ersis\s*[:.]?\s*\d{10,}', str(x)))) if pd.notna(x) else 0)

    # ── IYS (İleti Yönetim Sistemi) bilgisi tespiti ──────────────
    # Resmi SMS'lerde "SMS iptal", "SMS RED", "IPTAL yazin" gibi ifadeler bulunur
    ozellikler['has_iys_info'] = df['message'].apply(
        lambda x: int(bool(re.search(
            r'SMS\s*(RED|iptal|ret)|[İI]PTAL\s*yaz|[İI]YS\s*yaz|izin.*iptal|IZINIPTAL',
            str(x), re.IGNORECASE))) if pd.notna(x) else 0)

    # Gönderici sütunu varsa güven skoru ekle (eğitim verisinde yoksa 0.5)
    if 'gonderen' in df.columns:
        ozellikler['gonderen_guven'] = df['gonderen'].apply(
            lambda x: gonderen_analiz(x)['guven'])
    else:
        ozellikler['gonderen_guven'] = 0.5

    return ozellikler.values


# ─────────────────────────────────────────────
# 3. ANA EĞİTİM FONKSİYONU
# ─────────────────────────────────────────────

def modeli_egit(veri_yolu: str = "data/turkce_sms_dataset.csv"):
    print("=" * 60)
    print("  TÜRKÇE SMİSHİNG TESPİT MODELİ - EĞİTİM BAŞLIYOR")
    print("=" * 60)
    
    # ── Veri Yükle ──
    df = pd.read_csv(veri_yolu)
    print(f"\n📊 Veri Seti:")
    print(f"   Toplam SMS  : {len(df)}")
    print(f"   Spam (zararlı): {df['label'].value_counts()['spam']}")
    print(f"   Ham (meşru)   : {df['label'].value_counts()['ham']}")
    
    # ── Ön İşleme ──
    print("\n🔧 Türkçe NLP ön işleme yapılıyor...")
    df['temiz_metin'] = df['message'].apply(turkce_on_isleme)
    df['etiket'] = (df['label'] == 'spam').astype(int)  # spam=1, ham=0
    
    # ── Train/Test Split ──
    X_metin = df['temiz_metin']
    X_ham = df['message']
    y = df['etiket']
    
    X_metin_train, X_metin_test, X_ham_train, X_ham_test, y_train, y_test = train_test_split(
        X_metin, X_ham, y, test_size=0.25, random_state=42, stratify=y
    )
    
    print(f"\n📂 Train/Test Ayrımı:")
    print(f"   Eğitim: {len(X_metin_train)} SMS")
    print(f"   Test  : {len(X_metin_test)} SMS")
    
    # ── TF-IDF Vektörleştirme ──
    print("\n📐 TF-IDF vektörleştirme...")
    tfidf = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 2),       # unigram + bigram
        min_df=2,                 # en az 2 kez geçen kelimeler (gürültü azaltma)
        sublinear_tf=True         # log ölçekleme
    )
    X_tfidf_train = tfidf.fit_transform(X_metin_train)
    X_tfidf_test  = tfidf.transform(X_metin_test)
    
    # ── Manuel Özellikler ──
    print("🔍 Manuel özellikler çıkarılıyor...")
    
    df_train = pd.DataFrame({'message': X_ham_train})
    df_test  = pd.DataFrame({'message': X_ham_test})
    
    manuel_train = sp.csr_matrix(ozellik_cikar(df_train))
    manuel_test  = sp.csr_matrix(ozellik_cikar(df_test))
    
    # Hibrit: TF-IDF + Manuel özellikler birleştir
    X_train = hstack([X_tfidf_train, manuel_train])
    X_test  = hstack([X_tfidf_test,  manuel_test])
    
    # ── Model Tanımları ──
    modeller = {
        "Naive Bayes": MultinomialNB(alpha=0.1),
        "SVM (RBF)": SVC(kernel='rbf', C=10, gamma='scale', probability=True,
                        class_weight='balanced', random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, max_depth=None,
            class_weight='balanced', random_state=42)
    }
    
    # ── Eğitim ve Değerlendirme ──
    print("\n" + "=" * 60)
    print("  MODEL EĞİTİMİ VE KARŞILAŞTIRMA")
    print("=" * 60)
    
    sonuclar = {}
    en_iyi_f1 = 0
    en_iyi_model_adi = ""
    en_iyi_model = None
    
    for isim, model in modeller.items():
        print(f"\n🤖 {isim} eğitiliyor...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_pred_train = model.predict(X_train)  # Eğitim seti tahmini (overfitting kontrolü)
        
        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)
        f1   = f1_score(y_test, y_pred, zero_division=0)
        
        # Eğitim seti performansı (overfitting kontrolü)
        train_acc = accuracy_score(y_train, y_pred_train)
        train_f1  = f1_score(y_train, y_pred_train, zero_division=0)
        
        # Cross-validation (5-fold)
        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='f1')
        cv_mean = cv_scores.mean()
        cv_std  = cv_scores.std()
        
        sonuclar[isim] = {
            "Accuracy": acc, "Precision": prec, "Recall": rec, "F1": f1,
            "Train_Acc": train_acc, "Train_F1": train_f1,
            "CV_F1_Mean": cv_mean, "CV_F1_Std": cv_std
        }
        
        print(f"   Accuracy  : {acc:.4f} ({acc*100:.1f}%)")
        print(f"   Precision : {prec:.4f}")
        print(f"   Recall    : {rec:.4f}")
        print(f"   F1 Score  : {f1:.4f} {'✅' if f1 >= 0.95 else '⚠️'}")
        print(f"   Confusion Matrix:\n   {confusion_matrix(y_test, y_pred)}")
        
        # Overfitting analizi
        overfit_gap = train_f1 - f1
        print(f"\n   📊 Overfitting Analizi:")
        print(f"   Train F1    : {train_f1:.4f}")
        print(f"   Test  F1    : {f1:.4f}")
        print(f"   Fark (Gap)  : {overfit_gap:.4f} {'✅ İyi' if overfit_gap < 0.10 else '⚠️ Overfitting riski!' if overfit_gap < 0.20 else '🔴 OVERFITTING!'}")
        print(f"   CV F1 (5-fold): {cv_mean:.4f} ± {cv_std:.4f}")
        
        if f1 > en_iyi_f1:
            en_iyi_f1 = f1
            en_iyi_model_adi = isim
            en_iyi_model = model
    
    # ── Özet Tablo ──
    print("\n" + "=" * 60)
    print("  SONUÇ KARŞILAŞTIRMA TABLOSU")
    print("=" * 60)
    print(f"{'Model':<20} {'Test F1':>10} {'Train F1':>10} {'CV F1':>10} {'Gap':>8} {'Durum':>12}")
    print("-" * 70)
    for isim, m in sonuclar.items():
        iyi = " ⭐" if isim == en_iyi_model_adi else ""
        gap = m['Train_F1'] - m['F1']
        durum = "✅ Sağlıklı" if gap < 0.10 else "⚠️ Riskli" if gap < 0.20 else "🔴 Overfit"
        print(f"{isim:<20} {m['F1']:>10.4f} {m['Train_F1']:>10.4f} {m['CV_F1_Mean']:>10.4f} {gap:>8.4f} {durum:>12}{iyi}")
    
    print(f"\n🏆 En iyi model: {en_iyi_model_adi} (F1: {en_iyi_f1:.4f})")
    if en_iyi_f1 >= 0.95:
        print("   ✅ Hedef F1 >= %95 BAŞARILA ULAŞILDI!")
    else:
        print(f"   ⚠️ F1 hedefine ({en_iyi_f1*100:.1f}% / hedef %95) daha fazla veri gerekli.")
    
    # ── Modeli Kaydet ──
    os.makedirs("models", exist_ok=True)
    model_paketi = {
        "tfidf": tfidf,
        "model": en_iyi_model,
        "model_adi": en_iyi_model_adi,
        "f1_skoru": en_iyi_f1,
        "tum_sonuclar": sonuclar
    }
    with open("models/smishing_model.pkl", "wb") as f:
        pickle.dump(model_paketi, f)
    print("\n💾 Model kaydedildi: models/smishing_model.pkl")
    
    return model_paketi


# ─────────────────────────────────────────────
# 4. TAHMİN FONKSİYONU
# ─────────────────────────────────────────────

def sms_tahmin_et(mesaj: str, model_paketi: dict = None,
                  gonderen: str = "") -> dict:
    """
    Tek bir SMS mesajını analiz eder.

    Parametreler:
        mesaj      : SMS metni
        model_paketi: pickle'dan yüklü model sözlüğü (None ise diskten okur)
        gonderen   : Gönderici numarası/ID (opsiyonel, boş bırakılabilir)
    """
    if model_paketi is None:
        with open("models/smishing_model.pkl", "rb") as f:
            model_paketi = pickle.load(f)

    tfidf = model_paketi["tfidf"]
    model = model_paketi["model"]

    temiz = turkce_on_isleme(mesaj)
    tfidf_vec = tfidf.transform([temiz])

    df_tek = pd.DataFrame({'message': [mesaj], 'gonderen': [gonderen]})
    ozellikler = ozellik_cikar(df_tek)
    manuel_vec = sp.csr_matrix(ozellikler)

    X = hstack([tfidf_vec, manuel_vec])

    tahmin = model.predict(X)[0]
    if hasattr(model, 'predict_proba'):
        olasilik = model.predict_proba(X)[0]
        guven = olasilik[tahmin]
    else:
        guven = 1.0

    # ── Gönderici ve domain analizi (kural tabanlı düzeltme) ──
    url_bilgi  = _url_analiz(mesaj)
    gon_bilgi  = gonderen_analiz(gonderen)

    # BTK B-kodu, MERSIS ve IYS tespiti
    has_btk = bool(re.search(r'\bB\d{3}\b', mesaj))
    has_mersis = bool(re.search(r'[Mm]ersis\s*[:.]?\s*\d{10,}', mesaj))
    has_iys = bool(re.search(
        r'SMS\s*(RED|iptal|ret)|[İI]PTAL\s*yaz|[İI]YS\s*yaz|izin.*iptal|IZINIPTAL',
        mesaj, re.IGNORECASE))

    # Resmi ticari SMS işaretleyicileri sayısı
    resmi_isaret_sayisi = sum([has_btk, has_mersis, has_iys])

    # URL kısaltıcı tespiti (şüpheli sinyal)
    has_url_shortener = any(k in mesaj.lower() for k in URL_KISALTICILAR)

    # ── KUMAR/BAHİS KESİN TESPİTİ (Hard-Rule) ──
    kumar_kelimeleri = [
        'freespin', 'free spin', 'deneme bonusu', 'cevrimsiz', 'çevrimsiz',
        'casino', 'bahis', 'slot', 'cark', 'çark', 'jackpot', 'yatirim bonusu',
        'yatırım bonusu', 'kayip bonusu', 'kayıp bonusu', 'cekim yap', 'çekim yap',
        'ücretsiz deneme bonusu', 'ucretsiz deneme bonusu',
        'kayıt ol ücretsiz kazan', 'kayit ol ucretsiz kazan',
        'hoşgeldin bonusu', 'hosgeldin bonusu', 'üyelik bonusu', 'uyelik bonusu',
        'canlı casino', 'canli casino', 'rulet', 'poker', 'iddaa', 'kumarhane',
        'promosyon kodu', 'telegram kanal', 'haftalık kayıp', 'haftalik kayip',
        'metin2', 'pvp server', 'mt2', '1-99', '1-105', '55-250',
        'orta emek', 'zor emek', 'kolay emek', 'wslik server', 'açılıyor hemen indir',
        'aciliyor hemen indir', 'avantajlı başla', 'avantajli basla',
        'muhteşem çarpan', 'muhtesem carpan', 'gökyüzü imparatorluğu', 'gokyuzu imparatorlugu',
        'şans denizi', 'sans denizi', 'yeni yıl sürprizi', 'yeni yil surprizi',
        'yatırım uzmanı', 'yatirim uzmani', 'kazı kazan', 'kazi kazan',
        'şans oyunları ödemesi', 'sans oyunu odemesi', 'sans oyunlari odemesi',
        'milyon tl kazanma şansı', 'milyon tl kazanma sansi',
        'çılgın sayısal loto', 'cilgin sayisal loto', 'çekiliş heyecanı', 'cekilis heyecani',
        'en yüksek oran', 'en yuksek oran', 'yüksek oranlar', 'yuksek oranlar',
        'kazançlar için', 'kazanclar icin', 'risebet', 'bet tv',
        'akşam buluşuyoruz', 'aksam bulusuyoruz', 'tüm maçlar', 'tum maclar'
    ]
    has_kumar = any(k in mesaj.lower() for k in kumar_kelimeleri)

    # ⚠️ GÜVENLİK KONTROLÜ: BTK/MERSIS/IYS kodları kopyalanmış olabilir!
    # Kişisel mobil numara veya uluslararası numara → bu kodlar sahte olabilir
    gonderici_guvensiz = gon_bilgi['tur'] in ('mobil_tr', 'uluslararasi', 'diger')

    # Resmi domain + resmi gönderici → güvenilir olasılığı yüksek
    # Model spam dedi ama ikisi de resmi → güveni düşür (ham'a yaklaştır)
    duzeltilmis_guven = guven
    
    if has_kumar:
        # Kumar ve bahis mesajları kesinlikle SPAM'dir. BTK koduna veya göndericiye bakılmaz.
        tahmin = 1
        duzeltilmis_guven = 0.99
    elif tahmin == 1:  # Model spam dedi

        # ── GÜVENSİZ GÖNDERİCİ + resmi işaretleyiciler → KOPYALANMIŞ OLABİLİR ──
        # Mobil numara/uluslararası numara + BTK kodu = dolandırıcı taklidi
        if gonderici_guvensiz and has_url_shortener:
            # Kişisel numara + URL kısaltıcı → model kararına güven, override yapma
            pass  # Model spam dedi, spam kalsın

        elif gonderici_guvensiz and resmi_isaret_sayisi >= 2:
            # Kişisel numara ama çok güçlü resmi işaretler → hafif güven düşür
            # (Gerçek kurumlar genelde alfanümerik ID kullanır, numara kullanmaz)
            duzeltilmis_guven = guven * 0.70
            # Spam olarak bırak ama güveni biraz azalt

        # ── GÜVENİLİR GÖNDERİCİ + resmi işaretleyiciler ──
        # BTK kodu + resmi gönderici → kesinlikle meşru ticari SMS
        elif has_btk and gon_bilgi['guven'] >= 0.65:
            tahmin = 0
            duzeltilmis_guven = 0.85

        # MERSIS + IYS bilgisi + güvenilir gönderici → resmi ticari SMS
        elif resmi_isaret_sayisi >= 2 and gon_bilgi['guven'] >= 0.65:
            tahmin = 0
            duzeltilmis_guven = 0.80

        # BTK kodu var + alfanümerik gönderici (kısa kod veya marka adı)
        elif has_btk and gon_bilgi['guven'] >= 0.40:
            duzeltilmis_guven = guven * 0.35
            if duzeltilmis_guven < 0.50:
                tahmin = 0
                duzeltilmis_guven = 1 - duzeltilmis_guven

        # Resmi domain + resmi gönderici
        elif url_bilgi['resmi'] == 1 and gon_bilgi['guven'] >= 0.70:
            duzeltilmis_guven = guven * 0.35
            if duzeltilmis_guven < 0.50:
                tahmin = 0
                duzeltilmis_guven = 1 - duzeltilmis_guven

        # Sadece resmi gönderici (skor >= 0.90) → güçlü sinyal
        elif gon_bilgi['guven'] >= 0.90:
            duzeltilmis_guven = guven * 0.40
            if duzeltilmis_guven < 0.50:
                tahmin = 0
                duzeltilmis_guven = 1 - duzeltilmis_guven

        elif url_bilgi['resmi'] == 1 and not gonderen:
            duzeltilmis_guven = guven * 0.65

        elif url_bilgi['taklit'] == 1:
            duzeltilmis_guven = min(guven * 1.15, 1.0)

    # ── TERS YÖN DÜZELTME: Model "ham" dedi ama şüpheli sinyaller var ──
    # Dolandırıcılar BTK/MERSIS/IYS kodlarını kopyalayarak modeli kandırabilir
    elif tahmin == 0:  # Model ham (meşru) dedi
        # Güvensiz gönderici (mobil numara, uluslararası) + URL kısaltıcı
        # → büyük ihtimalle dolandırıcı meşru mesajdan kodları kopyalamış
        if gonderici_guvensiz and has_url_shortener:
            tahmin = 1  # SPAM'a çevir
            duzeltilmis_guven = 0.90  # Yüksek güvenle spam

        # Güvensiz gönderici + şüpheli domain (suphe_skoru > 0)
        elif gonderici_guvensiz and url_bilgi['suphe_skoru'] > 0:
            tahmin = 1
            duzeltilmis_guven = 0.85

        # Güvensiz gönderici + domain taklit
        elif gonderici_guvensiz and url_bilgi['taklit'] == 1:
            tahmin = 1
            duzeltilmis_guven = 0.95

    return {
        "mesaj"         : mesaj,
        "gonderen"      : gonderen if gonderen else "Belirtilmedi",
        "gonderen_bilgi": gon_bilgi,
        "url_bilgi"     : url_bilgi,
        "btk_kodu"      : has_btk,
        "mersis"        : has_mersis,
        "iys_bilgi"     : has_iys,
        "sonuc"         : "ZARALI (Smishing/Spam)" if tahmin == 1 else "GUVENLI (Mesru)",
        "etiket"        : "spam" if tahmin == 1 else "ham",
        "guven"         : f"{duzeltilmis_guven*100:.1f}%",
        "ham_guven"     : f"{(1-duzeltilmis_guven)*100:.1f}%",
        "tehlike_skoru" : int(ozellikler[0][6]) if ozellikler.shape[1] > 6 else 0,
    }


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    model_paketi = modeli_egit()
    
    # Test örnekleri
    print("\n" + "=" * 60)
    print("  ÖRNEK TAHMİNLER")
    print("=" * 60)
    
    test_mesajlar = [
        "Tebrikler! 5000 TL kazandınız. Hemen tıklayın: bit.ly/odul",
        "Yarın toplantı saat 10:00, katılımın için teşekkürler.",
        "Hesabınız bloke edildi. garanti-dogrula.xyz adresinden işlem yapın.",
        "Akşam yemeğe gelecek misin? Anne sordu.",
    ]
    
    for msg in test_mesajlar:
        sonuc = sms_tahmin_et(msg, model_paketi)
        emoji = "🔴" if sonuc['etiket'] == 'spam' else "🟢"
        print(f"\n{emoji} [{sonuc['sonuc']}] (Güven: {sonuc['guven']})")
        print(f"   Mesaj: {msg[:70]}...")
