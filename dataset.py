import os
import pandas as pd

CSV_PATH = "onepiece_ai_final.csv"

_dataset_cache = None

BAD_NAMES = [
    "coffee monkeys",
    "monster",
    "will of d.",
    "light and darkness",
    "yamamoto luffy",
    "oran",
]

BAD_WORDS = [
    "disambiguation",
    "list of",
    "chapter",
    "episode",
    "volume",
    "arc",
    "saga",
    "soundtrack",
    "gallery",
    "movie",
    "video game",
]

BAD_SPECIES = [
    "monkey",
    "animal",
    "spider-human",
    "object",
    "symbol",
    "logo",
    "place",
    "organization",
    "unknown",
]


def is_valid_character(row):
    name = str(row.get("name", "")).lower().strip()
    species = str(row.get("species", "")).lower().strip()
    image_url = str(row.get("image_url", "")).strip()

    if not name:
        return False

    if not image_url or image_url.lower() == "nan":
        return False

    if name in BAD_NAMES:
        return False

    if any(word in name for word in BAD_WORDS):
        return False

    if species in BAD_SPECIES:
        return False

    return True


def load_dataset(force_reload=False):
    global _dataset_cache

    if _dataset_cache is not None and not force_reload:
        return _dataset_cache

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"{CSV_PATH} 파일을 찾을 수 없습니다.")

    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    before = len(df)
    df = df[df.apply(is_valid_character, axis=1)].reset_index(drop=True)
    after = len(df)

    _dataset_cache = df

    print(f"✅ Dataset Loaded : {after} characters")
    print(f"🧹 Removed : {before - after}")

    return _dataset_cache


def get_all_characters():
    return load_dataset().to_dict(orient="records")


def get_character_count():
    return len(load_dataset())
