from app.services.ai import _normalize_ai_nutrition, _parse_ai_json


def test_parse_ai_json_accepts_markdown_fenced_json() -> None:
    payload = _parse_ai_json(
        """```json
        {"food_name":"红烧肉","per_100g_kcal":320,"confidence":0.82}
        ```"""
    )

    assert payload["food_name"] == "红烧肉"
    assert payload["per_100g_kcal"] == 320


def test_parse_ai_json_accepts_json_embedded_in_explanation() -> None:
    payload = _parse_ai_json(
        '先给出估算说明。{"food_name":"番茄炒蛋","raw_text":"估算值","per_100g_kcal":110,"confidence":0.7}请你手动确认重量。'
    )

    assert payload["food_name"] == "番茄炒蛋"
    assert payload["raw_text"] == "估算值"


def test_normalize_ai_nutrition_converts_kj_to_kcal() -> None:
    payload = _normalize_ai_nutrition(
        {
            "food_name": "荞麦面",
            "raw_text": "能量 1700 千焦 / 100g",
            "per_100g_kj": 1700,
            "per_100g_carb_g": None,
            "per_100g_fat_g": "",
            "per_100g_protein_g": "12.5",
            "confidence": "0.86",
        }
    )

    assert payload["per_100g_kcal"] == 406.3
    assert payload["per_100g_carb_g"] is None
    assert payload["per_100g_fat_g"] is None
    assert payload["per_100g_protein_g"] == 12.5
    assert payload["confidence"] == 0.86


def test_normalize_ai_nutrition_keeps_estimated_grams() -> None:
    payload = _normalize_ai_nutrition(
        {
            "food_name": "意式肉酱披萨",
            "raw_text": "9 寸披萨，整份估算约 420g",
            "estimated_grams": "420",
            "per_100g_kcal": 265,
            "confidence": 0.78,
        }
    )

    assert payload["estimated_grams"] == 420.0


def test_normalize_ai_nutrition_uses_solid_and_liquid_breakdown() -> None:
    payload = _normalize_ai_nutrition(
        {
            "food_name": "家常餐",
            "raw_text": "一盘炒菜和一碗汤，estimated_grams 包含汤汁",
            "estimated_solid_grams": "360",
            "estimated_liquid_grams": "240",
            "estimated_scope": "includes_liquid",
            "portion_basis": "按 1 盘炒菜约 360g、1 碗汤约 240g 估算",
            "per_100g_kcal": 110,
            "confidence": 0.74,
        }
    )

    assert payload["estimated_grams"] == 600.0
    assert payload["estimated_solid_grams"] == 360.0
    assert payload["estimated_liquid_grams"] == 240.0
    assert payload["estimated_scope"] == "includes_liquid"
    assert payload["portion_basis"] == "按 1 盘炒菜约 360g、1 碗汤约 240g 估算"
