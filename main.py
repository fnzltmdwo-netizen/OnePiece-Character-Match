from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import pandas as pd
import os
import json
import base64
import re
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CSV_PATH = "onepiece_ai_clean.csv"
MODEL = "gpt-4o-mini"


class MatchRequest(BaseModel):
    image_base64: str


def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])


def normalize_base64(image_base64):
    if "," in image_base64:
        return image_base64
    return "data:image/jpeg;base64," + image_base64


def analyze_user_face(image_base64):
    image_url = normalize_base64(image_base64)

    prompt = """
You are analyzing a real person's face for an anime character lookalike test.

Return ONLY valid JSON.
No markdown.

Use short English keywords.

Schema:
{
  "gender": "",
  "hair_color": "",
  "hair_style": "",
  "hair_length": "",
  "eye_style": "",
  "eye_size": "",
  "face_shape": "",
  "expression": "",
  "skin_tone": "",
  "beard": "",
  "body_type": "",
  "age_vibe": "",
  "cute_level": 0,
  "cool_level": 0,
  "dark_level": 0,
  "funny_level": 0,
  "power_level": 0,
  "hero_level": 0,
  "evil_level": 0,
  "energy_level": 0,
  "confidence_level": 0,
  "match_tags": ""
}

Rules:
- levels are integers from 0 to 10
- focus only on visible appearance and vibe
- do not identify the person
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
    )

    text = response.choices[0].message.content
    return safe_json_parse(text)


def split_tags(value):
    if not value or str(value).lower() == "nan":
        return set()
    return set(
        tag.strip().lower()
        for tag in str(value).split(",")
        if tag.strip()
    )


def str_score(a, b, weight):
    if not a or not b:
        return 0
    a = str(a).lower().strip()
    b = str(b).lower().strip()
    if a == b:
        return weight
    if a in b or b in a:
        return weight * 0.5
    return 0


def num_score(a, b, weight):
    try:
        a = float(a)
        b = float(b)
        diff = abs(a - b)
        return max(0, weight - diff * (weight / 10))
    except Exception:
        return 0


def calculate_score(user, row):
    score = 0

    score += str_score(user.get("hair_color"), row.get("hair_color"), 8)
    score += str_score(user.get("hair_style"), row.get("hair_style"), 7)
    score += str_score(user.get("hair_length"), row.get("hair_length"), 5)
    score += str_score(user.get("eye_style"), row.get("eye_style"), 7)
    score += str_score(user.get("eye_size"), row.get("eye_size"), 5)
    score += str_score(user.get("face_shape"), row.get("face_shape"), 8)
    score += str_score(user.get("expression"), row.get("expression"), 8)
    score += str_score(user.get("beard"), row.get("beard"), 4)
    score += str_score(user.get("body_type"), row.get("body_type"), 5)
    score += str_score(user.get("age_vibe"), row.get("age_vibe"), 4)

    score += num_score(user.get("cute_level"), row.get("cute_level"), 7)
    score += num_score(user.get("cool_level"), row.get("cool_level"), 7)
    score += num_score(user.get("dark_level"), row.get("dark_level"), 5)
    score += num_score(user.get("funny_level"), row.get("funny_level"), 5)
    score += num_score(user.get("power_level"), row.get("power_level"), 6)
    score += num_score(user.get("hero_level"), row.get("hero_level"), 5)
    score += num_score(user.get("evil_level"), row.get("evil_level"), 4)
    score += num_score(user.get("energy_level"), row.get("energy_level"), 6)
    score += num_score(user.get("confidence_level"), row.get("confidence_level"), 6)

    user_tags = split_tags(user.get("match_tags"))
    char_tags = split_tags(row.get("match_tags"))
    common = user_tags.intersection(char_tags)
    score += len(common) * 3

    return score


def make_reason(user, row):
    prompt = f"""
원피스 캐릭터 닮은꼴 테스트 결과 설명을 작성해줘.

사용자 특징:
{json.dumps(user, ensure_ascii=False)}

캐릭터:
이름: {row.get("name")}
특징:
- 머리: {row.get("hair_color")} / {row.get("hair_style")}
- 눈: {row.get("eye_style")} / {row.get("eye_size")}
- 얼굴형: {row.get("face_shape")}
- 표정: {row.get("expression")}
- 분위기 태그: {row.get("match_tags")}

조건:
- 한국어 한 문장
- 너무 과장하지 말기
- 외모 비하 금지
- "눈매", "표정", "분위기", "인상" 위주로 설명
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.5,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response.choices[0].message.content.strip()


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "csv_exists": os.path.exists(CSV_PATH),
        "csv_path": CSV_PATH
    }


@app.post("/match")
def match_character(req: MatchRequest):
    if not os.path.exists(CSV_PATH):
        return {
            "error": "CSV not found",
            "csv_path": CSV_PATH
        }

    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    user_dna = analyze_user_face(req.image_base64)

    scored = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        raw_score = calculate_score(user_dna, row_dict)

        scored.append({
            "row": row_dict,
            "raw_score": raw_score
        })

    scored = sorted(scored, key=lambda x: x["raw_score"], reverse=True)

    top_candidates = scored[:20]

    random.shuffle(top_candidates)
    top_candidates = sorted(top_candidates, key=lambda x: x["raw_score"], reverse=True)

    top3 = top_candidates[:3]

    max_score = max([x["raw_score"] for x in top3]) if top3 else 1

    results = []

    for i, item in enumerate(top3):
        row = item["row"]

        percent = int(82 + (item["raw_score"] / max_score) * 15)
        percent = min(percent, 98)

        try:
            reason = make_reason(user_dna, row)
        except Exception:
            reason = f"{row.get('name')}와 전체적인 분위기와 인상이 비슷합니다."

        results.append({
            "rank": i + 1,
            "name": row.get("name", ""),
            "score": percent,
            "image_url": row.get("image_url", ""),
            "source_url": row.get("source_url", ""),
            "reason": reason,
            "tags": row.get("match_tags", "")
        })

    return {
        "user_dna": user_dna,
        "results": results
    }
