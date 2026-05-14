"""
Turkce SMS Smishing - Veri Seti Genisletme Scripti
===================================================
HuggingFace kaynaklaer indirilir, normalize edilir ve
mevcut turkce_sms_dataset.csv ile birlestirilir.

Kullanim:
    python merge_datasets.py
"""

import os
import shutil
import sys
import warnings
import pandas as pd
warnings.filterwarnings('ignore')

# Windows terminal encoding duzeltme
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEVCUT_CSV = os.path.join(SCRIPT_DIR, "data", "turkce_sms_dataset.csv")
BACKUP_CSV = os.path.join(SCRIPT_DIR, "data", "turkce_sms_dataset_backup.csv")


# ---------------------------------------------------------
# 1. HuggingFace: akuysal/turkishSMS-ds
# ---------------------------------------------------------
def hf_akuysal_yukle() -> pd.DataFrame:
    """
    akuysal/turkishSMS-ds
    Sutunlar: text | label | sms length
    Label degerleri: 'spam', 'legitimate'
    """
    print("[1/2] HuggingFace: akuysal/turkishSMS-ds indiriliyor...")
    from datasets import load_dataset
    raw = load_dataset("akuysal/turkishSMS-ds")

    kareler = []
    for split_adi, split_veri in raw.items():
        df_s = split_veri.to_pandas()
        kareler.append(df_s)
        print(f"    {split_adi}: {len(df_s)} satir")

    df = pd.concat(kareler, ignore_index=True)

    # Normalize: 'text' -> 'message',  'legitimate' -> 'ham'
    df = df[["text", "label"]].copy()
    df.columns = ["message", "label"]
    df["label"] = df["label"].str.strip().str.lower()
    df["label"] = df["label"].replace({"legitimate": "ham", "spam": "spam"})
    df = df[df["label"].isin(["spam", "ham"])]

    print(f"    Normalize sonrasi: {len(df)} satir "
          f"(spam={( df['label']=='spam').sum()}, ham={(df['label']=='ham').sum()})")
    return df[["label", "message"]]


# ---------------------------------------------------------
# 2. HuggingFace: eskfestsecurity/turkish-igaming-spam-detection
# ---------------------------------------------------------
def hf_igaming_yukle() -> pd.DataFrame:
    """
    eskfestsecurity/turkish-igaming-spam-detection
    Yalnizca spam SMS iceren bir dataset.
    """
    print("[2/2] HuggingFace: eskfestsecurity/turkish-igaming-spam-detection indiriliyor...")
    try:
        from datasets import load_dataset
        raw = load_dataset("eskfestsecurity/turkish-igaming-spam-detection")

        kareler = []
        for split_adi, split_veri in raw.items():
            df_s = split_veri.to_pandas()
            kareler.append(df_s)
            print(f"    {split_adi}: {len(df_s)} satir | sutunlar: {list(df_s.columns)}")

        df = pd.concat(kareler, ignore_index=True)

        # Sutun tespiti
        mesaj_adaylari  = ["text", "message", "sms", "Message", "sms_text", "content", "v2"]
        etiket_adaylari = ["label", "v1", "class", "tag", "type", "category"]

        mesaj_kol  = next((c for c in mesaj_adaylari  if c in df.columns), None)
        etiket_kol = next((c for c in etiket_adaylari if c in df.columns), None)

        if mesaj_kol is None:
            mesaj_kol = df.columns[0]

        if etiket_kol:
            df = df[[etiket_kol, mesaj_kol]].copy()
            df.columns = ["label", "message"]
            df["label"] = df["label"].str.strip().str.lower()
            label_map = {
                "spam": "spam", "smishing": "spam", "phishing": "spam",
                "normal": "ham", "ham": "ham", "legitimate": "ham"
            }
            df["label"] = df["label"].map(label_map)
            df = df[df["label"].isin(["spam", "ham"])]
        else:
            df = df[[mesaj_kol]].copy()
            df.columns = ["message"]
            df["label"] = "spam"

        df = df[["label", "message"]]
        print(f"    Normalize sonrasi: {len(df)} satir "
              f"(spam={( df['label']=='spam').sum()}, ham={(df['label']=='ham').sum()})")
        return df

    except Exception as e:
        print(f"    UYARI: Bu dataset atlandi: {e}")
        return pd.DataFrame(columns=["label", "message"])


# ---------------------------------------------------------
# 3. Birlestir ve Kaydet
# ---------------------------------------------------------
def birlestir():
    print("=" * 55)
    print("  TURKCE SMS VERI SETI GENISLETME")
    print("=" * 55)

    # Mevcut CSV
    print(f"\nMevcut veri seti: {MEVCUT_CSV}")
    df_mevcut = pd.read_csv(MEVCUT_CSV)
    df_mevcut["label"]   = df_mevcut["label"].astype(str).str.strip().str.lower()
    df_mevcut["message"] = df_mevcut["message"].astype(str).str.strip()
    df_mevcut = df_mevcut[["label", "message"]].dropna()
    df_mevcut = df_mevcut[df_mevcut["label"].isin(["spam", "ham"])]
    print(f"  Mevcut: {len(df_mevcut)} satir "
          f"(spam={( df_mevcut['label']=='spam').sum()}, ham={(df_mevcut['label']=='ham').sum()})")

    print()
    df_akuysal = hf_akuysal_yukle()
    print()
    df_igaming  = hf_igaming_yukle()
    print()

    # Birlestir
    df_birlesik = pd.concat(
        [df_mevcut, df_akuysal, df_igaming],
        ignore_index=True
    )

    # Duplicate temizle
    onceki = len(df_birlesik)
    df_birlesik = df_birlesik.drop_duplicates(subset=["message"])
    sonraki = len(df_birlesik)

    # Bos satirlari temizle
    df_birlesik = df_birlesik[df_birlesik["message"].str.strip().ne("")]
    df_birlesik = df_birlesik.dropna(subset=["message", "label"])

    # Karistir (shuffle)
    df_birlesik = df_birlesik.sample(frac=1, random_state=42).reset_index(drop=True)

    # Backup
    shutil.copy(MEVCUT_CSV, BACKUP_CSV)
    print(f"Yedek alindi: {BACKUP_CSV}")

    # Kaydet
    df_birlesik.to_csv(MEVCUT_CSV, index=False, encoding="utf-8-sig")

    # Ozet
    print("\n" + "=" * 55)
    print("  SONUC")
    print("=" * 55)
    print(f"  Eski veri seti   : {len(df_mevcut)} satir")
    print(f"  akuysal eklenen  : {len(df_akuysal)} satir")
    print(f"  igaming eklenen  : {len(df_igaming)} satir")
    print(f"  Duplikat silinen : {onceki - sonraki} satir")
    print(f"  -------------------------------------------")
    print(f"  YENI TOPLAM      : {len(df_birlesik)} satir")
    print(f"  Spam             : {(df_birlesik['label']=='spam').sum()}")
    print(f"  Ham              : {(df_birlesik['label']=='ham').sum()}")
    print(f"\n  KAYDEDILDI: {MEVCUT_CSV}")
    print("\n  Modeli yeniden egitmek icin:")
    print("  -> python train_model.py")


if __name__ == "__main__":
    birlestir()
