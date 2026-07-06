from dataset import get_all_characters


def norm(v):
    return str(v).lower().strip()


def same(a, b):
    a = norm(a)
    b = norm(b)
    if not a or not b:
        return 0
    if a == b:
        return 1
    if a in b or b in a:
        return 0.5
    return 0


def num_close(a, b):
    try:
        a = float(a)
        b = float(b)
        return max(0, 1 - abs(a - b) / 10)
    except Exception:
        return 0


def tags(value):
    return {
        x.strip().lower()
        for x in str(value).split(",")
        if x.strip()
    }


def tag_similarity(user_tags, char_tags):
    u = tags(user_tags)
    c = tags(char_tags)

    if not u or not c:
        return 0

    common = u.intersection(c)
    return len(common) / max(len(u), 1)


def score_face(user, char):
    score = 0
    score += same(user.get("face_shape"), char.get("face_shape")) * 40
    score += same(user.get("eye_style"), char.get("eye_style")) * 30
    score += same(user.get("eye_size"), char.get("eye_size")) * 15
    score += same(user.get("expression"), char.get("expression")) * 15
    return score


def score_hair(user, char):
    score = 0
    score += same(user.get("hair_color"), char.get("hair_color")) * 35
    score += same(user.get("hair_style"), char.get("hair_style")) * 35
    score += same(user.get("hair_length"), char.get("hair_length")) * 20
    score += same(user.get("beard"), char.get("beard")) * 10
    return score


def score_vibe(user, char):
    score = 0
    score += num_close(user.get("cute_level"), char.get("cute_level")) * 15
    score += num_close(user.get("cool_level"), char.get("cool_level")) * 15
    score += num_close(user.get("energy_level"), char.get("energy_level")) * 15
    score += num_close(user.get("confidence_level"), char.get("confidence_level")) * 15
    score += num_close(user.get("dark_level"), char.get("dark_level")) * 10
    score += num_close(user.get("funny_level"), char.get("funny_level")) * 10
    score += num_close(user.get("power_level"), char.get("power_level")) * 10
    score += same(user.get("age_vibe"), char.get("age_vibe")) * 10
    return score


def score_tags(user, char):
    return tag_similarity(
        user.get("match_tags"),
        char.get("match_tags")
    ) * 100


def total_score(user, char):
    return round(
        score_face(user, char) * 0.42 +
        score_hair(user, char) * 0.18 +
        score_vibe(user, char) * 0.25 +
        score_tags(user, char) * 0.15,
        2
    )


def pick_unique(pool, selected, limit):
    selected_names = {x["character"]["name"] for x in selected}

    for item in pool:
        name = item["character"]["name"]
        if name in selected_names:
            continue

        selected.append(item)
        selected_names.add(name)

        if len(selected) >= limit:
            break


def ranked_by(user_dna, score_func):
    chars = get_all_characters()
    rows = []

    for char in chars:
        rows.append({
            "score": round(score_func(user_dna, char), 2),
            "character": char
        })

    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows


def match_top20(user_dna):
    """
    다양한 후보 TOP20 생성:
    - 얼굴 닮음 TOP
    - 헤어 닮음 TOP
    - 분위기 TOP
    - 태그 TOP
    - 종합 TOP
    """

    face_rank = ranked_by(user_dna, score_face)
    hair_rank = ranked_by(user_dna, score_hair)
    vibe_rank = ranked_by(user_dna, score_vibe)
    tag_rank = ranked_by(user_dna, score_tags)
    total_rank = ranked_by(user_dna, total_score)

    selected = []

    pick_unique(face_rank[:12], selected, 5)
    pick_unique(hair_rank[:12], selected, 9)
    pick_unique(vibe_rank[:12], selected, 13)
    pick_unique(tag_rank[:12], selected, 16)
    pick_unique(total_rank[:30], selected, 20)

    final = []

    for item in selected[:20]:
        char = item["character"]
        final.append({
            "score": total_score(user_dna, char),
            "character": char
        })

    final.sort(key=lambda x: x["score"], reverse=True)
    return final[:20]
