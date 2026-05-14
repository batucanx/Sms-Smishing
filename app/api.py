from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os
import pickle

# Ana dizindeki train_model.py modülüne erişmek için
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from train_model import sms_tahmin_et

app = FastAPI(title="SMS Smishing API")

# Modeli belleğe yükle
model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "smishing_model.pkl")
with open(model_path, "rb") as f:
    model_paketi = pickle.load(f)

from typing import List

class SmsRequest(BaseModel):
    message: str
    sender: str = ""

class BulkSmsRequest(BaseModel):
    messages: List[SmsRequest]

@app.post("/predict")
def predict(req: SmsRequest):
    # Tahmin işlemini yap (train_model'deki fonksiyonu kullanarak)
    sonuc = sms_tahmin_et(req.message, model_paketi, gonderen=req.sender)
    return sonuc

@app.post("/predict_bulk")
def predict_bulk(req: BulkSmsRequest):
    sonuclar = []
    for msg in req.messages:
        sonuc = sms_tahmin_et(msg.message, model_paketi, gonderen=msg.sender)
        sonuclar.append(sonuc)
    return {"results": sonuclar}
