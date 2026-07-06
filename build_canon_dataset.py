import time
import re
import requests
import pandas as pd

API_URL = "https://onepiece.fandom.com/api.php"
OUTPUT_CSV = "onepiece_canon_with_images.csv"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/2.0"
}

CANON_LIST_TITLE = "List of Canon Characters"


def clean_name(name):
    name = str(name).strip()
    name = re.sub(r"\[[^\]]*\]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def get_page_wikitext(title):
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    }

    res = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    res.raise_for_status()
    data = res.json()

    pages = data.get("query", {}).get("pages", {})

    for _, page in pages.items():
        revs = page.get("revisions", [])
        if not revs:
            return ""

        return revs[0].get("slots", {}).get("main", {}).get("*", "")

    return ""


def extract_character_links(wikitext):
    links = re.findall(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", wikitext)

    rows = []

    bad_words = [
        "chapter", "episode", "volume", "arc", "saga",
        "category:", "file:", "image:", "template:",
        "list of", "one piece", "manga", "anime",
    ]

    for target, label in links:
        name = clean_name(label if label else target)
        page_title = clean_name(target)

        lower = page_title.lower()

        if any(bad in lower for bad in bad_words):
            continue

        if len(name) < 2 or len(name) > 50:
            continue

        rows.append({
            "name": name,
            "page_title": page_title,
            "source_url": f"https://onepiece.fandom.com/wiki/{page_title.replace(' ', '_')}"
        })

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["page_title"]).reset_index(drop=True)

    return df


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


def is_bad_candidate(row):
    name = str(row.get("name", "")).lower()
    title = str(row.get("page_title", "")).lower()

    bad_exact = [
        "romanized name",
        "official english name",
        "debut",
        "affiliations",
        "occupations",
        "origin",
        "residence",
        "status",
        "age",
        "birthday",
        "height",
        "blood type",
    ]

    bad_words = [
        "disambiguation",
        "gallery",
        "concept",
        "location",
        "weapon",
        "devil fruit",
        "haki",
        "ship",
        "organization",
        "race",
        "species",
        "kingdom",
        "island",
        "pirates",
        "marines",
        "world government",
    ]

    if name in bad_exact:
        return True

    if any(w in title for w in bad_words):
        return True

    if any(w in name for w in bad_words):
        return True

    return False


def main():
    print("Canon 캐릭터 목록 수집 시작...")

    wikitext = get_page_wikitext(CANON_LIST_TITLE)

    if not wikitext:
        print("위키텍스트를 가져오지 못했어.")
        return

    df = extract_character_links(wikitext)

    print(f"1차 후보 수: {len(df)}")

    df = df[~df.apply(is_bad_candidate, axis=1)].reset_index(drop=True)

    print(f"필터 후 후보 수: {len(df)}")

    rows = []

    for idx, row in df.iterrows():
        name = row["name"]
        title = row["page_title"]

        image_url, source_url = get_image_url(title)

        if not source_url:
            source_url = row["source_url"]

        if image_url:
            rows.append({
                "name": name,
                "page_title": title,
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

        print(f"[{idx + 1}/{len(df)}] {name} / image: {bool(image_url)}")

        time.sleep(0.12)

    out = pd.DataFrame(rows)
    out = out.drop_duplicates(subset=["name"]).reset_index(drop=True)

    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("완료!")
    print(f"저장 파일: {OUTPUT_CSV}")
    print(f"최종 캐릭터 수: {len(out)}")
    print(out.head(20))


if __name__ == "__main__":
    main()
