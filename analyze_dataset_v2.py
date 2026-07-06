import os
import json
import time
import pandas as pd
from openai import OpenAI

INPUT_CSV = "onepiece_top209_with_images.csv"
OUTPUT_CSV = "onepiece_ai_final.csv"
CHECKPOINT_CSV = "onepiece_ai_final_checkpoint.csv"

MODEL = "gpt-4o-mini"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def analyze_character(name, image_url):
    prompt = f"""
You are analyzing an anime character image for a face/lookalike matching test.

Character name: {name}

Return ONLY valid JSON.
Do not add markdown.

Use short English keywords.

Schema:
{{
  "gender": "",
  "species": "",
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
  "match_tags": "",
  "match_note": ""
}}

Rules:
- levels are integers from 0 to 10
- match_tags should be comma-separated keywords
- match_note should be one short Korean sentence explaining the visual vibe
- focus on visible appearance only
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


def main():
    if not os.path.exists(INPUT_CSV):
        print(f"파일 없음: {INPUT_CSV}")
        return

    df = pd.read_csv(INPUT_CSV)

    if os.path.exists(CHECKPOINT_CSV):
        print("체크포인트 발견! 이어서 진행합니다.")
        result_df = pd.read_csv(CHECKPOINT_CSV)
        done_names = set(result_df["name"].astype(str).tolist())
        rows = result_df.to_dict(orient="records")
    else:
        done_names = set()
        rows = []

    total = len(df)
    print(f"전체 캐릭터 수: {total}")
    print(f"이미 완료된 수: {len(done_names)}")

    for idx, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        image_url = str(row.get("image_url", "")).strip()

        if not name:
            continue

        if name in done_names:
            continue

        if not image_url or image_url.lower() == "nan":
            print(f"[SKIP] {name} 이미지 없음")
            continue

        print(f"[{idx + 1}/{total}] 분석 중: {name}")

        base = row.to_dict()

        try:
            ai = analyze_character(name, image_url)

            for key, value in ai.items():
                base[key] = value

            rows.append(base)

            pd.DataFrame(rows).to_csv(
                CHECKPOINT_CSV,
                index=False,
                encoding="utf-8-sig"
            )

            print(f"완료: {name}")

            time.sleep(0.8)

        except Exception as e:
            print(f"실패: {name}")
            print(e)
            time.sleep(2)

    final_df = pd.DataFrame(rows)
    final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("전체 분석 완료!")
    print(f"저장 파일: {OUTPUT_CSV}")
    print(f"분석 완료 수: {len(final_df)}")


if __name__ == "__main__":
    main()
