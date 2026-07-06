from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import uuid
from datetime import datetime

from dataset import get_character_count
from analyzer import analyze_user_face, normalize_base64
from matcher_v2 import match_top20

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"
RESULT_STORE = "result_store.json"
FRONTEND_URL = "https://onepiece-character-frontend.onrender.com"


class MatchRequest(BaseModel):
    image_base64: str


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "status": "ok",
        "csv_exists": os.path.exists("onepiece_ai_final.csv"),
        "character_count": get_character_count()
    }


def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def load_result_store():
    if not os.path.exists(RESULT_STORE):
        return {}

    try:
        with open(RESULT_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_result(results, user_dna):
    store = load_result_store()
    share_id = str(uuid.uuid4())[:8]

    store[share_id] = {
        "share_id": share_id,
        "created_at": datetime.now().isoformat(),
        "results": results,
        "user_dna": user_dna
    }

    with open(RESULT_STORE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

    return share_id


def gpt_final_judge(image_base64, user_dna, top20):
    candidates = []

    for item in top20:
        c = item["character"]

        candidates.append({
            "name": c.get("name", ""),
            "raw_score": item.get("score", 0),
            "image_url": c.get("image_url", ""),
            "hair_color": c.get("hair_color", ""),
            "hair_style": c.get("hair_style", ""),
            "hair_length": c.get("hair_length", ""),
            "eye_style": c.get("eye_style", ""),
            "eye_size": c.get("eye_size", ""),
            "face_shape": c.get("face_shape", ""),
            "expression": c.get("expression", ""),
            "body_type": c.get("body_type", ""),
            "age_vibe": c.get("age_vibe", ""),
            "cute_level": c.get("cute_level", ""),
            "cool_level": c.get("cool_level", ""),
            "dark_level": c.get("dark_level", ""),
            "funny_level": c.get("funny_level", ""),
            "power_level": c.get("power_level", ""),
            "energy_level": c.get("energy_level", ""),
            "confidence_level": c.get("confidence_level", ""),
            "match_tags": c.get("match_tags", "")
        })

    prompt = f"""
You are judging a One Piece character lookalike test.

You will see:
1. A real person's photo
2. The person's extracted visual DNA
3. Top 20 candidate One Piece characters

Choose the FINAL TOP 3 characters that visually match the person best.

Important:
- Do not identify the person.
- Focus on visible resemblance: face shape, eyes, expression, hairstyle, and overall vibe.
- Use raw_score as a reference, but do not blindly follow it.
- Prefer the most natural visual resemblance.
- Return ONLY valid JSON array.
- Korean reason must be natural and specific.

User DNA:
{json.dumps(user_dna, ensure_ascii=False)}

Candidates:
{json.dumps(candidates, ensure_ascii=False)}

Return format:
[
  {{
    "name": "Character Name",
    "score": 96,
    "reason": "눈매와 전체적인 분위기가 비슷합니다."
  }}
]
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.4,
        max_tokens=900,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": normalize_base64(image_base64)
                        }
                    }
                ]
            }
        ],
    )

    text = response.choices[0].message.content
    return safe_json_parse(text)


@app.post("/match")
def match_character(req: MatchRequest):
    user_dna = analyze_user_face(req.image_base64)
    top20 = match_top20(user_dna)

    try:
        judged = gpt_final_judge(req.image_base64, user_dna, top20)
    except Exception as e:
        print("GPT final judge failed:", e)
        judged = []

    results = []

    if judged:
        for idx, item in enumerate(judged[:3]):
            name = item.get("name", "")

            matched = None
            for candidate in top20:
                if candidate["character"].get("name") == name:
                    matched = candidate
                    break

            if not matched:
                continue

            character = matched["character"]

            results.append({
                "rank": idx + 1,
                "name": character.get("name", ""),
                "score": int(item.get("score", 95)),
                "image_url": character.get("image_url", ""),
                "source_url": character.get("source_url", ""),
                "reason": item.get("reason", character.get("match_note", "")),
                "tags": character.get("match_tags", ""),
                "raw_score": matched.get("score", 0)
            })

    if len(results) < 3:
        top3 = top20[:3]
        max_score = top3[0]["score"] if top3 else 1

        for index, item in enumerate(top3):
            character = item["character"]
            percent = int(82 + (item["score"] / max_score) * 16)
            percent = min(percent, 98)

            results.append({
                "rank": len(results) + 1,
                "name": character.get("name", ""),
                "score": percent,
                "image_url": character.get("image_url", ""),
                "source_url": character.get("source_url", ""),
                "reason": character.get("match_note", "전체적인 분위기와 인상이 비슷합니다."),
                "tags": character.get("match_tags", ""),
                "raw_score": item["score"]
            })

            if len(results) >= 3:
                break

    final_results = results[:3]
    share_id = save_result(final_results, user_dna)

    return {
        "message": "match complete",
        "share_id": share_id,
        "share_url": f"{FRONTEND_URL}/result.html?id={share_id}",
        "user_dna": user_dna,
        "results": final_results
    }


@app.get("/result/{share_id}")
def get_result(share_id: str):
    store = load_result_store()

    if share_id not in store:
        return {
            "error": "result not found"
        }

    return store[share_id]
