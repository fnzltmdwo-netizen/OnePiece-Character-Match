from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import requests
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = "onepiece_characters_raw.csv"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/1.0"
}

CHARACTER_LIST_URLS = [
    "https://onepiece.fandom.com/wiki/List_of_Canon_Characters",
    "https://onepiece.fandom.com/wiki/List_of_Non-Canon_Characters",
]


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "status": "ok",
        "csv_exists": os.path.exists(CSV_PATH)
    }


def clean_name(name):
    name = str(name).strip()
    name = re.sub(r"\[[^\]]*\]", "", name)
    name = name.replace("\n", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def collect_from_tables():
    rows = []

    for url in CHARACTER_LIST_URLS:
        tables = pd.read_html(url)

        for table in tables:
            columns = [str(c).lower() for c in table.columns]

            possible_name_cols = []
            for col in table.columns:
                col_text = str(col).lower()
                if "name" in col_text or "character" in col_text:
                    possible_name_cols.append(col)

            if not possible_name_cols:
                continue

            name_col = possible_name_cols[0]

            for _, row in table.iterrows():
                name = clean_name(row.get(name_col, ""))

                if not name:
                    continue
                if name.lower() in ["nan", "name", "character"]:
                    continue
                if len(name) > 80:
                    continue

                source_url = f"https://onepiece.fandom.com/wiki/{name.replace(' ', '_')}"

                rows.append({
                    "name": name,
                    "source_url": source_url,
                    "image_url": "",
                })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)

    return df


@app.get("/collect")
def collect_characters():
    df = collect_from_tables()

    if df.empty:
        return {
            "message": "collection failed",
            "character_count": 0
        }

    df["gender"] = ""
    df["hair_color"] = ""
    df["hair_style"] = ""
    df["eye_style"] = ""
    df["face_shape"] = ""
    df["expression"] = ""
    df["skin_tone"] = ""
    df["beard"] = ""
    df["body_type"] = ""
    df["age_vibe"] = ""
    df["cute_level"] = ""
    df["cool_level"] = ""
    df["dark_level"] = ""
    df["funny_level"] = ""
    df["power_level"] = ""
    df["match_tags"] = ""
    df["match_note"] = ""

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    return {
        "message": "collection complete",
        "character_count": len(df),
        "csv_path": CSV_PATH,
        "sample": df.head(20).to_dict(orient="records")
    }


@app.get("/download-csv")
def download_csv():
    if not os.path.exists(CSV_PATH):
        return {"error": "CSV not found. Please run /collect first."}

    return FileResponse(
        CSV_PATH,
        media_type="text/csv",
        filename=CSV_PATH
    )
