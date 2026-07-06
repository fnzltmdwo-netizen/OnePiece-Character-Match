from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from openai import OpenAI

import os, json, uuid, sqlite3, html, requests
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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

FONT_PATH = "fonts/Pretendard-Bold.otf"


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
        "db_exists": os.path.exists(DB_PATH),
        "font_exists": os.path.exists(FONT_PATH),
    }


def get_font(size):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)

    fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(fallback):
        return ImageFont.truetype(fallback, size)

    return ImageFont.load_default()


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
            share_id, user_name, created_at, results_json, user_dna_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            share_id,
            user_name,
            created_at,
            json.dumps(results, ensure_ascii=False),
            json.dumps(user_dna, ensure_ascii=False),
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
        "user_dna": json.loads(row[4]),
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
            "match_tags": c.get("match_tags", ""),
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
                        "image_url": {"url": normalize_base64(image_base64)}
                    }
                ]
            }
        ],
    )

    return safe_json_parse(response.choices[0].message.content)
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
                "raw_score": matched.get("score", 0),
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
                "raw_score": item["score"],
            })

            if len(results) >= 3:
                break

    final_results = results[:3]

    fixed_scores = [96, 92, 89]
    
    for i, item in enumerate(final_results):
        item["rank"] = i + 1
        item["score"] = fixed_scores[i]
        
    share_id = save_result(final_results, user_dna, user_name)

    return {
        "message": "match complete",
        "share_id": share_id,
        "share_url": f"{BACKEND_URL}/share/{share_id}",
        "result_url": f"{FRONTEND_URL}/result.html?id={share_id}",
        "user_name": user_name,
        "user_dna": user_dna,
        "results": final_results,
    }


@app.get("/result/{share_id}")
def get_result(share_id: str):
    result = load_result(share_id)

    if not result:
        return {"error": "result not found"}

    return result


def draw_center_text(draw, box, text, font, fill):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = left + (right - left - tw) / 2
    y = top + (bottom - top - th) / 2
    draw.text((x, y), text, font=font, fill=fill)


def load_character_image(url, max_size):
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        char_img = Image.open(BytesIO(r.content)).convert("RGBA")
        char_img.thumbnail(max_size)
        return char_img
    except Exception:
        return None


@app.get("/share-image/{share_id}")
def share_image(share_id: str):
    result = load_result(share_id)

    if not result:
        return Response(status_code=404)

    results = result.get("results", [])
    user_name = result.get("user_name") or "친구"

    W, H = 1200, 630
    navy = "#10233f"
    red = "#e63946"
    gold = "#f4b942"
    parchment = "#f2d8a2"
    cream = "#fffaf0"
    brown = "#8b5e34"

    img = Image.new("RGB", (W, H), parchment)
    draw = ImageDraw.Draw(img)

    font_title = get_font(54)
    font_big = get_font(72)
    font_mid = get_font(40)
    font_small = get_font(30)
    font_tiny = get_font(24)

    # background
    draw.rectangle([0, 0, W, H], fill=parchment)
    draw.rectangle([22, 22, W - 22, H - 22], outline=navy, width=8)
    draw.rectangle([0, 0, W, 112], fill=navy)

    draw.text((52, 27), "ONE PIECE MATCH", fill="white", font=font_title)
    draw.text((58, 132), f"{user_name}님의 닮은 캐릭터", fill=navy, font=font_mid)

    # small decorations
    draw.text((990, 32), "⚓", fill=gold, font=font_title)
    draw.text((1070, 32), "☠", fill=gold, font=font_title)

    if not results:
        draw_center_text(draw, (0, 250, W, 380), "NO RESULT", font_big, navy)
    else:
        top1 = results[0]
        top2 = results[1] if len(results) > 1 else None
        top3 = results[2] if len(results) > 2 else None

        # Top1 wanted poster
        px, py = 65, 190
        pw, ph = 510, 370

        draw.rounded_rectangle(
            [px, py, px + pw, py + ph],
            radius=32,
            fill=cream,
            outline=navy,
            width=6,
        )

        draw.rectangle([px + 22, py + 20, px + pw - 22, py + 72], fill=brown)
        draw_center_text(
            draw,
            (px + 22, py + 20, px + pw - 22, py + 72),
            "WANTED",
            font_mid,
            "white",
        )

        draw.ellipse([px + 30, py + 88, px + 105, py + 163], fill=gold, outline=navy, width=4)
        draw_center_text(draw, (px + 30, py + 88, px + 105, py + 163), "1", font_mid, navy)

        char_img = load_character_image(top1.get("image_url", ""), (270, 225))
        if char_img:
            cx = px + (pw - char_img.width) // 2
            cy = py + 90
            img.paste(char_img.convert("RGB"), (cx, cy), char_img)
        else:
            draw.rectangle([px + 145, py + 105, px + 365, py + 300], fill="#e2e8f0")
            draw_center_text(draw, (px + 145, py + 105, px + 365, py + 300), "NO IMAGE", font_small, navy)

        name = str(top1.get("name", "Unknown"))[:18]
        score = top1.get("score", 0)

        draw_center_text(draw, (px + 25, py + 288, px + pw - 25, py + 330), name, font_mid, navy)

        draw.rounded_rectangle(
            [px + 145, py + 330, px + 365, py + 374],
            radius=20,
            fill=red,
            outline=navy,
            width=3,
        )
        draw_center_text(draw, (px + 145, py + 330, px + 365, py + 374), f"{score}% MATCH", font_small, "white")

        # Right side rankings
        rx = 630
        draw.text((rx, 205), "TOP 3 RESULT", fill=navy, font=font_mid)

        def draw_rank(y, number, item, color):
            if not item:
                return

            draw.rounded_rectangle(
                [rx, y, 1125, y + 95],
                radius=24,
                fill="#fffdf4",
                outline=navy,
                width=4,
            )

            draw.ellipse([rx + 20, y + 20, rx + 76, y + 76], fill=color, outline=navy, width=3)
            draw_center_text(draw, (rx + 20, y + 20, rx + 76, y + 76), str(number), font_small, navy)

            name = str(item.get("name", "Unknown"))[:18]
            score = item.get("score", 0)

            draw.text((rx + 98, y + 16), name, fill=navy, font=font_mid)
            draw.text((rx + 98, y + 57), f"{score}% 닮음", fill=red, font=font_small)

        draw_rank(275, 1, top1, gold)
        draw_rank(385, 2, top2, "#cfd8dc")
        draw_rank(495, 3, top3, "#cd7f32")

    draw.text((58, 575), "사진 한 장으로 원피스 캐릭터 TOP3 찾기", fill=navy, font=font_tiny)
    draw.text((805, 575), "onepiece-character-match", fill=navy, font=font_tiny)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(content=buffer.getvalue(), media_type="image/png")


@app.get("/share/{share_id}", response_class=HTMLResponse)
def share_page(share_id: str):
    result = load_result(share_id)

    image_url = f"{BACKEND_URL}/share-image/{share_id}"

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
