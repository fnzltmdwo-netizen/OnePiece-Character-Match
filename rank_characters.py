import os
import json
import time
import pandas as pd
from openai import OpenAI

INPUT_CSV = "onepiece.csv"
OUTPUT_CSV = "onepiece_ranked.csv"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"

df = pd.read_csv(INPUT_CSV)

rows = []

for idx, row in df.iterrows():

    name = str(row["Name"]).strip()

    print(f"[{idx+1}/{len(df)}] {name}")

    prompt = f"""
Character: {name}

Rate how important this One Piece character is.

Return ONLY JSON.

{{
 "importance":0,
 "reason":""
}}

importance:
10 = Main protagonist / iconic worldwide
9 = Very major recurring
8 = Major arc character
7 = Important supporting
6 = Supporting
5 = Minor
4 이하 = Very minor
"""

    try:

        res = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        )

        txt = res.choices[0].message.content

        js = json.loads(txt)

        rows.append({
            "name":name,
            "importance":js["importance"],
            "reason":js["reason"]
        })

        time.sleep(0.2)

    except Exception as e:

        print(e)

pd.DataFrame(rows).to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

print("완료")
