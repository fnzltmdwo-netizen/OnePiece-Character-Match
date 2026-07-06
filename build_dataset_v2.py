import time
import requests
import pandas as pd

INPUT_CSV = "onepiece.csv"
OUTPUT_CSV = "onepiece_clean_with_images.csv"

API_URL = "https://onepiece.fandom.com/api.php"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/4.0"
}


def get_image(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages|info",
        "piprop": "original|thumbnail",
        "pithumbsize": "800",
        "redirects": 1,
        "inprop": "url",
        "format": "json",
    }

    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()

        pages = r.json()["query"]["pages"]

        for page in pages.values():

            image = ""

            if "original" in page:
                image = page["original"]["source"]

            elif "thumbnail" in page:
                image = page["thumbnail"]["source"]

            source = page.get(
                "fullurl",
                f"https://onepiece.fandom.com/wiki/{title.replace(' ','_')}"
            )

            return image, source

    except Exception:
        pass

    return "", ""


df = pd.read_csv(INPUT_CSV)

rows = []

for idx, row in df.iterrows():

    name = str(row["Name"]).strip()

    image, source = get_image(name)

    if image == "":
        print(f"[{idx+1}/{len(df)}] {name} ❌")
        continue

    rows.append({

        "name": name,

        "source_url": source,

        "image_url": image,

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

        "cute_level": "",
        "cool_level": "",
        "dark_level": "",
        "funny_level": "",
        "power_level": "",

        "hero_level": "",
        "evil_level": "",
        "energy_level": "",
        "confidence_level": "",

        "match_tags": "",
        "match_note": ""

    })

    print(f"[{idx+1}/{len(df)}] {name} ✅")

    time.sleep(0.15)


result = pd.DataFrame(rows)

result.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

print()
print("="*40)
print("완료!")
print("원본 :", len(df))
print("이미지 :", len(result))
print("저장 :", OUTPUT_CSV)
