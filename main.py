
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from PIL import Image
import io

app = FastAPI(title="Nutrient AI – Prototype", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOOD_DB = {
    "rice": {"calories": 206, "carbs": 45, "protein": 4, "fat": 0.4, "iron": 0.4, "vitamin_c": 0},
    "dal": {"calories": 150, "carbs": 20, "protein": 10, "fat": 3, "iron": 1.8, "vitamin_c": 0},
    "vegetables": {"calories": 50, "carbs": 10, "protein": 2, "fat": 0.2, "iron": 0.5, "vitamin_c": 30},
    "chapati": {"calories": 120, "carbs": 18, "protein": 3, "fat": 3, "iron": 0.9, "vitamin_c": 0},
    "egg": {"calories": 78, "carbs": 0.6, "protein": 6, "fat": 5, "iron": 0.9, "vitamin_c": 0},
    "milk": {"calories": 103, "carbs": 12, "protein": 8, "fat": 2.4, "iron": 0, "vitamin_c": 0},
    "banana": {"calories": 105, "carbs": 27, "protein": 1.3, "fat": 0.4, "iron": 0.3, "vitamin_c": 10},
    "spinach": {"calories": 23, "carbs": 3.6, "protein": 2.9, "fat": 0.4, "iron": 2.7, "vitamin_c": 28}
}

RDA = {"calories": 2000, "protein": 50, "iron": 18, "vitamin_c": 90}

class TextInput(BaseModel):
    text: str

def guess_food_from_text(text: str) -> List[Dict[str, Any]]:
    text_l = text.lower()
    items = []
    for key in FOOD_DB.keys():
        if key in text_l:
            items.append({"name": key, "portion": "1 serving", "nutrients": FOOD_DB[key]})
    if not items:
        items.append({"name": "vegetables", "portion": "1 bowl", "nutrients": FOOD_DB["vegetables"]})
    return items

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze/text")
def analyze_text(payload: TextInput):
    detected = guess_food_from_text(payload.text)
    totals = sum_nutrients(detected)
    flags = deficiency_flags(totals)
    recs = recommendations(flags)
    return {"mode": "text", "detected": detected, "totals": totals, "flags": flags, "recommendations": recs}

@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    raw = await file.read()
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file")

    candidates = []
    for key in FOOD_DB.keys():
        if key in name:
            candidates.append({"name": key, "portion": "1 serving", "nutrients": FOOD_DB[key]})
    if not candidates:
        candidates = [
            {"name": "rice", "portion": "1 cup", "nutrients": FOOD_DB["rice"]},
            {"name": "dal", "portion": "1/2 cup", "nutrients": FOOD_DB["dal"]},
            {"name": "vegetables", "portion": "1 bowl", "nutrients": FOOD_DB["vegetables"]},
        ]
    totals = sum_nutrients(candidates)
    flags = deficiency_flags(totals)
    recs = recommendations(flags)
    return {"mode": "image", "detected": candidates, "totals": totals, "flags": flags, "recommendations": recs}

def sum_nutrients(items: List[Dict[str, Any]]) -> Dict[str, float]:
    totals = {"calories": 0, "carbs": 0, "protein": 0, "fat": 0, "iron": 0, "vitamin_c": 0}
    for it in items:
        for k in totals.keys():
            totals[k] += float(it["nutrients"].get(k, 0))
    return totals

def deficiency_flags(totals: Dict[str, float]) -> Dict[str, bool]:
    flags = {}
    flags["low_iron"] = totals.get("iron", 0) < 0.25 * RDA["iron"]
    flags["low_vitamin_c"] = totals.get("vitamin_c", 0) < 0.25 * RDA["vitamin_c"]
    flags["low_protein"] = totals.get("protein", 0) < 0.25 * RDA["protein"]
    return flags

def recommendations(flags: Dict[str, bool]):
    recs = []
    if flags.get("low_iron"):
        recs.append("Include spinach, beans, or lean meats; pair with citrus for iron absorption.")
    if flags.get("low_vitamin_c"):
        recs.append("Add fruits like orange, guava, or banana; include bell peppers or tomatoes.")
    if flags.get("low_protein"):
        recs.append("Add eggs, dal, paneer/tofu, or dairy to increase protein intake.")
    if not recs:
        recs.append("Meal looks balanced for this portion. Keep variety across the day.")
    return recs
