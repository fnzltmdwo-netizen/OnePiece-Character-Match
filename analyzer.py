import os
import json
from openai import OpenAI

MODEL = "gpt-4o-mini"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def safe_json_parse(text):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            return json.loads(text[start:end])

        raise ValueError("JSON 파싱 실패")


def normalize_base64(image_base64):
    if "," in image_base64:
        return image_base64

    return "data:image/jpeg;base64," + image_base64


def analyze_user_face(image_base64):
    image_url = normalize_base64(image_base64)

    prompt = """
You are analyzing a real person's visible appearance for an anime character lookalike test.

Return ONLY valid JSON.
No markdown.
Do not identify the person.
Use short English keywords.

Schema:
{
  "gender": "",
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
  "cute_level": 0,
  "cool_level": 0,
  "dark_level": 0,
  "funny_level": 0,
  "power_level": 0,
  "hero_level": 0,
  "evil_level": 0,
  "energy_level": 0,
  "confidence_level": 0,
  "match_tags": ""
}

Rules:
- levels must be integers from 0 to 10
- focus on visible style, face impression, expression, and overall vibe
- match_tags should be comma-separated keywords
- do not mention race or ethnicity
- do not make sensitive guesses
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
    )

    text = response.choices[0].message.content
    return safe_json_parse(text)
