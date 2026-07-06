import requests
import pandas as pd
import time

API_URL = "https://onepiece.fandom.com/api.php"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/1.0"
}

def get_category_members(category_name, limit=5000):
    rows = []
    cmcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_name,
            "cmlimit": "500",
            "format": "json",
        }

        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        res = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        members = data.get("query", {}).get("categorymembers", [])

        for m in members:
            title = m.get("title", "")
            pageid = m.get("pageid")

            if title.startswith(("Category:", "File:", "Template:")):
                continue

            rows.append({
                "name": title,
                "pageid": pageid,
                "source_url": f"https://onepiece.fandom.com/wiki/{title.replace(' ', '_')}"
            })

            if len(rows) >= limit:
                return rows

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

        time.sleep(0.2)

    return rows


def get_page_images(pageids):
    image_map = {}

    for i in range(0, len(pageids), 50):
        chunk = pageids[i:i+50]

        params = {
            "action": "query",
            "pageids": "|".join(str(x) for x in chunk if x),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": "500",
            "format": "json",
        }

        res = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        pages = data.get("query", {}).get("pages", {})

        for pageid, page in pages.items():
            thumb = page.get("thumbnail", {})
            image_map[int(pageid)] = thumb.get("source", "")

        time.sleep(0.2)

    return image_map


def main():
    print("원피스 캐릭터 수집 시작!")

    categories = [
        "Category:Characters",
        "Category:Canon Characters",
        "Category:Non-Canon Characters",
    ]

    all_rows = []

    for category in categories:
        print(f"수집 중: {category}")
        rows = get_category_members(category)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)

    print(f"캐릭터 수: {len(df)}")
    print("이미지 URL 수집 중...")

    image_map = get_page_images(df["pageid"].tolist())
    df["image_url"] = df["pageid"].map(image_map).fillna("")

    # AI 분석용 빈 컬럼
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

    df.to_csv("onepiece_characters_raw.csv", index=False, encoding="utf-8-sig")

    print("완료!")
    print("저장 파일: onepiece_characters_raw.csv")
    print(df.head(10))


if __name__ == "__main__":
    main()
