from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import requests
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = "onepiece_characters_raw.csv"
API_URL = "https://onepiece.fandom.com/api.php"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/1.0"
}

SEED_KEYWORDS = [
    "Monkey", "Roronoa", "Nami", "Usopp", "Sanji", "Tony Tony", "Nico",
    "Franky", "Brook", "Jinbe", "Portgas", "Gol", "Trafalgar", "Eustass",
    "Shanks", "Buggy", "Crocodile", "Doflamingo", "Kaido", "Big Mom",
    "Charlotte", "Vinsmoke", "Donquixote", "Bartholomew", "Boa",
    "Marine", "Pirates", "Kingdom", "Island", "Crew", "Family",
    "Admiral", "Vice Admiral", "Captain", "Officer", "Agent",
    "Luffy", "Zoro", "Robin", "Chopper", "Law", "Ace", "Sabo"
]


@app.get("/")
def home():
    return {
        "message": "One Piece Character Match API is running!",
        "status": "ok",
        "csv_exists": os.path.exists(CSV_PATH)
    }


def search_pages(keyword):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": keyword,
        "srlimit": 50,
        "format": "json",
    }

    res = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    res.raise_for_status()
    data = res.json()

    rows = []

    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")

        if not title:
            continue
        if title.startswith(("File:", "Category:", "Template:", "List of")):
            continue
        if "/" in title:
            continue

        rows.append({
            "name": title,
            "pageid": item.get("pageid"),
            "source_url": f"https://onepiece.fandom.com/wiki/{title.replace(' ', '_')}",
            "image_url": ""
        })

    return rows


@app.get("/collect")
def collect_characters():
    all_rows = []

    for keyword in SEED_KEYWORDS:
        try:
            all_rows.extend(search_pages(keyword))
            time.sleep(0.15)
        except Exception:
            pass

    df = pd.DataFrame(all_rows)

    if df.empty:
        return {
            "message": "collection failed",
            "character_count": 0
        }

    df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)

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
        "sample": df.head(30).to_dict(orient="records")
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
