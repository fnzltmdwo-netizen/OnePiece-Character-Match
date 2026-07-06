import pandas as pd

TOP_FILE = "onepiece_top300_names.csv"
IMAGE_FILE = "onepiece_clean_with_images.csv"

OUTPUT_FILE = "onepiece_top209_with_images.csv"

top = pd.read_csv(TOP_FILE)
img = pd.read_csv(IMAGE_FILE)

top["name"] = top["name"].astype(str).str.strip()
img["name"] = img["name"].astype(str).str.strip()

merged = pd.merge(
    top,
    img,
    on="name",
    how="left"
)

merged = merged.drop_duplicates(subset=["name"])

merged = merged[merged["image_url"].notna()]
merged = merged[merged["image_url"] != ""]

merged.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 40)
print("Merge 완료!")
print("Top 캐릭터 :", len(top))
print("Image DB :", len(img))
print("최종 :", len(merged))
print("저장 :", OUTPUT_FILE)
