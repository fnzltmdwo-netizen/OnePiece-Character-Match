import time
import requests
import pandas as pd

API_URL = "https://onepiece.fandom.com/api.php"
OUTPUT_CSV = "onepiece_core_with_images.csv"

HEADERS = {
    "User-Agent": "OnePieceCharacterMatch/3.0"
}

CORE_NAMES = [
    "Monkey D. Luffy", "Roronoa Zoro", "Nami", "Usopp", "Sanji",
    "Tony Tony Chopper", "Nico Robin", "Franky", "Brook", "Jinbe",
    "Portgas D. Ace", "Sabo", "Monkey D. Dragon", "Monkey D. Garp",
    "Shanks", "Buggy", "Dracule Mihawk", "Crocodile", "Boa Hancock",
    "Donquixote Doflamingo", "Bartholomew Kuma", "Gecko Moria",
    "Trafalgar D. Water Law", "Eustass Kid", "Killer", "Basil Hawkins",
    "Scratchmen Apoo", "Jewelry Bonney", "Capone Bege", "X Drake",
    "Urouge", "Kaido", "Charlotte Linlin", "Marshall D. Teach",
    "Edward Newgate", "Marco", "Jozu", "Vista", "Kozuki Oden",
    "Kozuki Momonosuke", "Kozuki Hiyori", "Kin'emon", "Kanjuro",
    "Raizo", "Kiku", "Inuarashi", "Nekomamushi", "Denjiro",
    "Ashura Doji", "Kawamatsu", "Yamato", "Kurozumi Orochi",
    "King", "Queen", "Jack", "Ulti", "Page One", "Who's-Who",
    "Sasaki", "Black Maria", "X Drake", "Benn Beckman", "Lucky Roux",
    "Yasopp", "Silvers Rayleigh", "Gol D. Roger", "Koby", "Helmeppo",
    "Sengoku", "Sakazuki", "Borsalino", "Kuzan", "Issho", "Aramaki",
    "Smoker", "Tashigi", "Hina", "Tsuru", "Rob Lucci", "Kaku",
    "Kalifa", "Blueno", "Jabra", "Fukuro", "Kumadori", "Spandam",
    "Vivi", "Karoo", "Cobra", "Igaram", "Pell", "Chaka",
    "Cavendish", "Bartolomeo", "Rebecca", "Kyros", "Viola",
    "Riku Doldo III", "Don Sai", "Leo", "Sugar", "Trebol",
    "Diamante", "Pica", "Vergo", "Caesar Clown", "Monet",
    "Shirahoshi", "Fisher Tiger", "Arlong", "Hody Jones", "Hatchan",
    "Camie", "Pappag", "Enel", "Wyper", "Gan Fall", "Perona",
    "Absalom", "Hogback", "Carrot", "Pedro", "Pekoms", "Bepo",
    "Shachi", "Penguin", "Charlotte Katakuri", "Charlotte Pudding",
    "Charlotte Perospero", "Charlotte Smoothie", "Charlotte Cracker",
    "Charlotte Oven", "Charlotte Daifuku", "Vinsmoke Judge",
    "Vinsmoke Reiju", "Vinsmoke Ichiji", "Vinsmoke Niji", "Vinsmoke Yonji"
]


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


def main():
    rows = []

    for idx, name in enumerate(CORE_NAMES):
        image_url, source_url = get_image_url(name)

        rows.append({
            "name": name,
            "source_url": source_url or f"https://onepiece.fandom.com/wiki/{name.replace(' ', '_')}",
            "image_url": image_url,
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

        print(f"[{idx + 1}/{len(CORE_NAMES)}] {name} / image: {bool(image_url)}")
        time.sleep(0.12)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("완료!")
    print(f"저장 파일: {OUTPUT_CSV}")
    print(f"총 캐릭터 수: {len(df)}")
    print(f"이미지 있는 수: {(df['image_url'] != '').sum()}")


if __name__ == "__main__":
    main()
