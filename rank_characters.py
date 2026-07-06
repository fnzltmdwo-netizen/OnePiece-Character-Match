import os
import json
import time
import pandas as pd
from openai import OpenAI

INPUT_CSV = "onepiece.csv"
OUTPUT_CSV = "onepiece_ranked.csv"
CHECKPOINT_CSV = "onepiece_ranked_checkpoint.csv"

MODEL = "gpt-4o-mini"
BATCH_SIZE = 40

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def rank_batch(names):
    prompt = f"""
You are ranking One Piece characters by importance/popularity for a character lookalike app.

Return ONLY valid JSON array.
No markdown.

For each name, return:
[
  {{
    "name": "Character Name",
    "importance": 0,
    "reason": "short English reason"
  }}
]

Importance scale:
10 = main protagonist or worldwide iconic
9 = very major recurring / legendary / Yonko / main Straw Hat
8 = major arc character or very popular recurring
7 = important supporting character
6 = supporting but recognizable
5 = minor but named
4 or lower = very minor / obscure

Names:
{json.dumps(names, ensure_ascii=False)}
"""

    res = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=3000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    text = res.choices[0].message.content
    return safe_json_parse(text)


def main():
    df = pd.read_csv(INPUT_CSV)
    names = [str(x).strip() for x in df["Name"].tolist() if str(x).strip()]

    if os.path.exists(CHECKPOINT_CSV):
        result_df = pd.read_csv(CHECKPOINT_CSV)
        rows = result_df.to_dict(orient="records")
        done = set(result_df["name"].astype(str).str.lower())
        print(f"체크포인트 발견! 완료된 수: {len(done)}")
    else:
        rows = []
        done = set()

    remain = [n for n in names if n.lower() not in done]

    print(f"전체: {len(names)}")
    print(f"남은 수: {len(remain)}")

    for i in range(0, len(remain), BATCH_SIZE):
        batch = remain[i:i + BATCH_SIZE]
        print(f"배치 처리 중: {i + 1} ~ {i + len(batch)} / {len(remain)}")

        try:
            ranked = rank_batch(batch)

            for item in ranked:
                rows.append({
                    "name": item.get("name", ""),
                    "importance": item.get("importance", 0),
                    "reason": item.get("reason", "")
                })

            pd.DataFrame(rows).to_csv(
                CHECKPOINT_CSV,
                index=False,
                encoding="utf-8-sig"
            )

            print("저장 완료")
            time.sleep(1)

        except Exception as e:
            print("배치 실패:")
            print(e)
            time.sleep(10)

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("완료!")
    print("저장:", OUTPUT_CSV)
    print("총 평가 수:", len(out))

    top = out[out["importance"] >= 8]
    top.to_csv("onepiece_top_importance.csv", index=False, encoding="utf-8-sig")

    print("8점 이상:", len(top))
    print("저장: onepiece_top_importance.csv")


if __name__ == "__main__":
    main()
