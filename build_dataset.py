import os
import time
import re
import requests
import pandas as pd

RAW_CSV = "onepiece_characters_raw.csv"
OUTPUT_CSV = "onepiece_with_images.csv"

API_URL = "https://onepiece.fandom.com/api.php"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/1.0"
}


def clean_title(name):
    name = str(name).strip()
    name = re.sub(r"\s+", " ", name)
    return name


def get_image_url(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages|info",
        "piprop": "thumbnail|original",
        "pithumbsize": "700",
        "inprop": "url",
        "redirects": 1,
        "format": "json",
    }

    try:
        res = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        pages = data.get("query", {}).get("pages", {})

        for _, page in pages.items():
            image_url = ""

            if "original" in page:
                image_url = page["original"].get("source", "")

            if not image_url and "thumbnail" in page:
                image_url = page["thumbnail"].get("source", "")

            source_url = page.get("fullurl", "")

            return image_url, source_url

    except Exception:
        return "", ""

    return "", ""


def is_bad_name(name):
    bad_words = [
        "disambiguation",
        "list of",
        "chapter",
        "episode",
        "volume",
        "arc",
        "saga",
        "category",
        "template",
        "file:",
        "gallery",
        "world",
        "island",
        "kingdom",
        "pirates",
        "marine",
        "crew",
        "organization",
        "race",
        "species",
        "devil fruit",
        "haki",
        "weapon",
        "ship",
        "location",
        "timeline",
        "soundtrack",
        "merchandise",
        "video game",
        "movie",
    ]

    text = str(name).lower()

    return any(word in text for word in bad_words)


def main():
    if not os.path.exists(RAW_CSV):
        print(f"파일 없음: {RAW_CSV}")
        return

    df = pd.read_csv(RAW_CSV)
    df["name"] = df["name"].apply(clean_title)

    df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)

    rows = []

    total = len(df)
    print(f"전체 후보: {total}")

    for idx, row in df.iterrows():
        name = row["name"]

        if is_bad_name(name):
            continue

        image_url, source_url = get_image_url(name)

        if not source_url:
            source_url = row.get("source_url", "")

        rows.append({
            "name": name,
            "source_url": source_url,
            "image_url": image_url,
            "gender": "",
            "hair_color": "",
            "hair_style": "",
            "eye_style": "",
            "face_shape": "",
            "expression": "",
            "skin_tone": "",
            "beard": "",
            "body_type": "",
            "age_vibe": "",
            "cute_level": "",
            "cool_level": "",
            "dark_level": "",
            "funny_level": "",
            "power_level": "",
            "match_tags": "",
            "match_note": ""
        })

        print(f"[{idx + 1}/{total}] {name} / image: {bool(image_url)}")

        time.sleep(0.12)

    out = pd.DataFrame(rows)

    out = out.drop_duplicates(subset=["name"]).reset_index(drop=True)

    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("완료!")
    print(f"저장 파일: {OUTPUT_CSV}")
    print(f"최종 캐릭터 수: {len(out)}")
    print(f"이미지 있는 수: {(out['image_url'] != '').sum()}")


if __name__ == "__main__":
    main()
