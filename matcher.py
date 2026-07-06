from dataset import get_all_characters

# 문자열 특징 가중치
STRING_WEIGHTS = {
    "hair_color": 8,
    "hair_style": 7,
    "hair_length": 5,
    "eye_style": 7,
    "eye_size": 5,
    "face_shape": 8,
    "expression": 8,
    "beard": 3,
    "body_type": 5,
    "age_vibe": 4,
}

# 숫자 특징 가중치
NUMBER_WEIGHTS = {
    "cute_level": 7,
    "cool_level": 7,
    "dark_level": 5,
    "funny_level": 5,
    "power_level": 6,
    "hero_level": 5,
    "evil_level": 4,
    "energy_level": 6,
    "confidence_level": 6,
}


def string_score(user_value, char_value, weight):
    if not user_value or not char_value:
        return 0

    u = str(user_value).lower().strip()
    c = str(char_value).lower().strip()

    if u == c:
        return weight

    if u in c or c in u:
        return weight * 0.5

    return 0


def number_score(user_value, char_value, weight):
    try:
        u = float(user_value)
        c = float(char_value)
    except:
        return 0

    diff = abs(u - c)

    return max(0, weight - diff * (weight / 10))


def tag_score(user_tags, char_tags):
    if not user_tags or not char_tags:
        return 0

    user = {
        x.strip().lower()
        for x in str(user_tags).split(",")
        if x.strip()
    }

    char = {
        x.strip().lower()
        for x in str(char_tags).split(",")
        if x.strip()
    }

    common = user.intersection(char)

    return len(common) * 3


def calculate_score(user, character):

    score = 0

    for field, weight in STRING_WEIGHTS.items():
        score += string_score(
            user.get(field),
            character.get(field),
            weight
        )

    for field, weight in NUMBER_WEIGHTS.items():
        score += number_score(
            user.get(field),
            character.get(field),
            weight
        )

    score += tag_score(
        user.get("match_tags"),
        character.get("match_tags")
    )

    return round(score, 2)


def match_top20(user_dna):

    characters = get_all_characters()

    scored = []

    for char in characters:

        score = calculate_score(user_dna, char)

        scored.append({
            "score": score,
            "character": char
        })

    scored.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return scored[:20]
