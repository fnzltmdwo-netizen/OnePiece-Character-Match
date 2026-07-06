from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import uuid
import sqlite3
import html
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
DB_PATH = "results.db"
FRONTEND_URL = "https://onepiece-character-frontend.onrender.com"
BACKEND_URL = "https://onepiece-character-match.onrender.com"


class MatchRequest(BaseModel):
    image_base64: str
    user_name: str = ""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            share_id TEXT PRIMARY KEY,
            user_name TEXT,
            created_at TEXT,
            results_json TEXT,
            user_dna_json TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "status": "ok",
        "csv_exists": os.path.exists("onepiece_ai_final.csv"),
        "character_count": get_character_count(),
        "db_exists": os.path.exists(DB_PATH)
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


def save_result(results, user_dna, user_name=""):
    share_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO results (
            share_id,
            user_name,
            created_at,
            results_json,
            user_dna_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            share_id,
            user_name,
            created_at,
            json.dumps(results, ensure_ascii=False),
            json.dumps(user_dna, ensure_ascii=False)
        )
    )

    conn.commit()
    conn.close()

    return share_id


def load_result(share_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT share_id, user_name, created_at, results_json, user_dna_json
        FROM results
        WHERE share_id = ?
        """,
        (share_id,)
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "share_id": row[0],
        "user_name": row[1],
        "created_at": row[2],
        "results": json.loads(row[3]),
        "user_dna": json.loads(row[4])
    }


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
    user_name = (req.user_name or "").strip()[:12]

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

        for item in top3:
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
    share_id = save_result(final_results, user_dna, user_name)

    return {
        "message": "match complete",
        "share_id": share_id,
        "share_url": f"{BACKEND_URL}/share/{share_id}",
        "result_url": f"{FRONTEND_URL}/result.html?id={share_id}",
        "user_name": user_name,
        "user_dna": user_dna,
        "results": final_results
    }


@app.get("/result/{share_id}")
def get_result(share_id: str):
    result = load_result(share_id)

    if not result:
        return {
            "error": "result not found"
        }

    return result


@app.get("/share/{share_id}", response_class=HTMLResponse)
def share_page(share_id: str):
    result = load_result(share_id)

    image_url = f"{FRONTEND_URL}/og-image.png"

    if not result:
        title = "원피스 닮은 캐릭터 테스트"
        desc = "사진 한 장으로 나와 닮은 원피스 캐릭터 TOP3를 찾아보세요!"
        target_url = FRONTEND_URL
    else:
        user_name = result.get("user_name") or "친구"
        results = result.get("results", [])
        top1 = results[0] if results else {}

        char_name = top1.get("name", "원피스 캐릭터")
        score = top1.get("score", "")

        title = f"{user_name}님의 원피스 닮은 캐릭터 결과"
        desc = f"1위 {char_name} · {score}% 닮음! TOP3 결과를 확인해보세요."
        target_url = f"{FRONTEND_URL}/result.html?id={share_id}"

    safe_title = html.escape(title)
    safe_desc = html.escape(desc)
    safe_target_url = html.escape(target_url)
    safe_image_url = html.escape(image_url)
    safe_share_url = html.escape(f"{BACKEND_URL}/share/{share_id}")

    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />

      <meta property="og:title" content="{safe_title}" />
      <meta property="og:description" content="{safe_desc}" />
      <meta property="og:image" content="{safe_image_url}" />
      <meta property="og:url" content="{safe_share_url}" />
      <meta property="og:type" content="website" />

      <title>{safe_title}</title>

      <script>
        window.location.href = "{safe_target_url}";
      </script>
    </head>
    <body>
      <p>결과 페이지로 이동 중...</p>
      <a href="{safe_target_url}">결과 보러가기</a>
    </body>
    </html>
    """
