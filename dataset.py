import os
import pandas as pd

CSV_PATH = "onepiece_ai_clean.csv"

_dataset_cache = None


def load_dataset(force_reload=False):
    """
    CSV를 읽어 메모리에 캐시한다.
    """
    global _dataset_cache

    if _dataset_cache is not None and not force_reload:
        return _dataset_cache

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"{CSV_PATH} 파일을 찾을 수 없습니다."
        )

    df = pd.read_csv(CSV_PATH)

    df = df.fillna("")

    _dataset_cache = df

    print(f"✅ Dataset Loaded : {len(df)} characters")

    return _dataset_cache


def get_all_characters():
    return load_dataset().to_dict(orient="records")


def get_character_count():
    return len(load_dataset())
