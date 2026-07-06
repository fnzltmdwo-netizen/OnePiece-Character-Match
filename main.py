from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from dataset import get_character_count
from analyzer import analyze_user_face
from matcher import match_top20

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MatchRequest(BaseModel):
    image_base64: str


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "status": "ok",
        "csv_exists": os.path.exists("onepiece_ai_clean.csv"),
        "character_count": get_character_count()
    }


def convert_score(raw_score, max_score):
    if max_score <= 0:
        return 85

    percent = int(82 + (raw_score / max_score) * 16)

    if percent > 98:
        percent = 98
    if percent < 82:
        percent = 82

    return percent


@app.post("/match")
def match_character(req: MatchRequest):
    user_dna = analyze_user_face(req.image_base64)

    top20 = match_top20(user_dna)

    top3 = top20[:3]

    max_score = top3[0]["score"] if top3 else 1

    results = []

    for index, item in enumerate(top3):
        character = item["character"]

        score_percent = convert_score(item["score"], max_score)

        reason = character.get("match_note", "")
        if not reason:
            reason = f"{character.get('name')}와 전체적인 분위기와 인상이 비슷합니다."

        results.append({
            "rank": index + 1,
            "name": character.get("name", ""),
            "score": score_percent,
            "image_url": character.get("image_url", ""),
            "source_url": character.get("source_url", ""),
            "reason": reason,
            "tags": character.get("match_tags", ""),
            "raw_score": item["score"]
        })

    return {
        "message": "match complete",
        "user_dna": user_dna,
        "results": results
    }
