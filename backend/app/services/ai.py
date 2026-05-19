from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AiProviderSetting


LABEL_SYSTEM_PROMPT = """
You extract a Chinese nutrition facts panel into JSON.
Return strictly valid JSON with keys:
food_name, raw_text, per_100g_kcal, per_100g_carb_g, per_100g_fat_g, per_100g_protein_g, per_100g_sodium_mg, confidence.
food_name should be the product or dish name visible on the package. Use null when missing.
If energy is shown in kJ or 千焦, convert it to kcal for per_100g_kcal.
Carbohydrate, fat, protein, and sodium are optional. Use null when a value is not clearly visible.
Do not invent missing macro values just to fill the JSON.
""".strip()

DISH_SYSTEM_PROMPT = """
You estimate a photographed ready-to-eat dish into JSON.
Return strictly valid JSON with keys:
food_name, raw_text, estimated_grams, estimated_solid_grams, estimated_liquid_grams, estimated_scope, portion_basis, per_100g_kcal, per_100g_carb_g, per_100g_fat_g, per_100g_protein_g, per_100g_sodium_mg, confidence.
food_name should be a concise Chinese dish name.
raw_text should briefly describe the visible ingredients and estimation assumptions in Chinese.
raw_text must explicitly state whether estimated_grams includes soup / broth / drinkable liquid, or only solid edible parts.
estimated_grams should estimate the edible consumed portion shown in the photo.
estimated_solid_grams should estimate edible solid parts only.
estimated_liquid_grams should estimate soup / broth / drinkable liquid only.
estimated_scope must be one of: solid_only, includes_liquid, liquid_only, unclear.
portion_basis should briefly explain how you got the weight, such as bowl count, plate size, visible portion ratio, or user hint.
Include visible soup / broth / sauce only when it is clearly part of the meal and likely to be consumed.
Exclude bowls, plates, bones, shells, and other inedible parts.
If the size reference is weak or the portion is heavily occluded, lower confidence and use null instead of guessing wildly.
Use common serving-size assumptions such as rice bowl, soup bowl, plate diameter, spoon size, and visible ingredient count when needed.
All nutrition values must be estimated per 100g. Use null when missing.
If only energy in kJ is visible or inferred, convert it to kcal for per_100g_kcal.
""".strip()

KJ_PER_KCAL = 4.184
WEIGHT_SCOPE_VALUES = {"solid_only", "includes_liquid", "liquid_only", "unclear"}


@dataclass(slots=True)
class ResolvedAiProvider:
    base_url: str | None
    api_key: str | None
    model_name: str
    timeout_sec: int
    enabled: bool
    proxy_enabled: bool
    proxy_url: str | None


@dataclass(slots=True)
class AiProbeResult:
    ok: bool
    transport: str
    detail: str
    model_name: str
    status_code: int | None = None


def _image_to_data_uri(image_path: Path) -> str:
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    suffix = image_path.suffix.lower().replace(".", "") or "jpeg"
    mime = "jpeg" if suffix == "jpg" else suffix
    return f"data:image/{mime};base64,{encoded}"


def _image_to_inline_data(image_path: Path) -> dict[str, str]:
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    suffix = image_path.suffix.lower().replace(".", "") or "jpeg"
    mime = "jpeg" if suffix == "jpg" else suffix
    return {"mime_type": f"image/{mime}", "data": encoded}


def _message_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                elif isinstance(item.get("content"), str):
                    chunks.append(item["content"])
        joined = "\n".join(chunk for chunk in chunks if chunk.strip())
        if joined.strip():
            return joined
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        nested = content.get("content")
        if isinstance(nested, str):
            return nested
    raise TypeError("Unsupported AI message content format")


def _strip_code_fence(text: str) -> str:
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, flags=re.IGNORECASE | re.DOTALL)
    return fenced.group(1) if fenced else text


def _json_object_candidates(text: str) -> list[str]:
    cleaned = _strip_code_fence(text).strip()
    candidates = [cleaned] if cleaned else []

    start = None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(cleaned):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(cleaned[start : index + 1])
                start = None
    return candidates


def _parse_ai_json(content: object) -> dict:
    text = _message_content_to_text(content)
    for candidate in _json_object_candidates(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise json.JSONDecodeError("No JSON object found", text, 0)


def _to_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() == "null":
            return None
        normalized = cleaned.replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", normalized)
        if match:
            return float(match.group())
    return None


def _to_text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _normalize_weight_scope(value: object) -> str | None:
    text = _to_text_or_none(value)
    if text is None:
        return None
    normalized = text.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in WEIGHT_SCOPE_VALUES else None


def _resolve_energy_kcal(parsed: dict) -> float | None:
    raw_text = str(parsed.get("raw_text") or "")
    kcal = _to_float_or_none(parsed.get("per_100g_kcal"))
    if kcal is not None:
        if re.search(r"(?:kJ|KJ|千焦)", raw_text) and kcal > 900:
            return round(kcal / KJ_PER_KCAL, 1)
        return round(kcal, 1)

    for key in (
        "per_100g_energy_kj",
        "per_100g_kj",
        "per100g_kj",
        "energy_kj",
        "per_100ml_kj",
    ):
        kj = _to_float_or_none(parsed.get(key))
        if kj is not None:
            return round(kj / KJ_PER_KCAL, 1)

    kj_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kJ|KJ|千焦)", raw_text)
    if kj_match:
        return round(float(kj_match.group(1)) / KJ_PER_KCAL, 1)
    return None


def _normalize_ai_nutrition(parsed: dict) -> dict:
    normalized = dict(parsed)
    normalized["food_name"] = _to_text_or_none(parsed.get("food_name"))
    normalized["raw_text"] = _to_text_or_none(parsed.get("raw_text"))
    normalized["portion_basis"] = _to_text_or_none(parsed.get("portion_basis"))
    normalized["estimated_scope"] = _normalize_weight_scope(
        parsed.get("estimated_scope")
        if parsed.get("estimated_scope") is not None
        else parsed.get("estimated_grams_scope")
    )
    normalized["estimated_solid_grams"] = _to_float_or_none(
        parsed.get("estimated_solid_grams")
        if parsed.get("estimated_solid_grams") is not None
        else parsed.get("solid_grams")
    )
    normalized["estimated_liquid_grams"] = _to_float_or_none(
        parsed.get("estimated_liquid_grams")
        if parsed.get("estimated_liquid_grams") is not None
        else parsed.get("liquid_grams")
    )
    total_grams = _to_float_or_none(
        parsed.get("estimated_grams")
        if parsed.get("estimated_grams") is not None
        else parsed.get("actual_grams")
    )
    solid_grams = normalized["estimated_solid_grams"]
    liquid_grams = normalized["estimated_liquid_grams"]
    if total_grams is None and (solid_grams is not None or liquid_grams is not None):
        total_grams = round((solid_grams or 0.0) + (liquid_grams or 0.0), 1)
    normalized["estimated_grams"] = total_grams
    if normalized["estimated_scope"] is None:
        if solid_grams is not None and liquid_grams is not None and liquid_grams > 0:
            normalized["estimated_scope"] = "includes_liquid"
        elif solid_grams is not None:
            normalized["estimated_scope"] = "solid_only"
        elif liquid_grams is not None and liquid_grams > 0:
            normalized["estimated_scope"] = "liquid_only"
    normalized["per_100g_kcal"] = _resolve_energy_kcal(parsed)
    normalized["per_100g_carb_g"] = _to_float_or_none(parsed.get("per_100g_carb_g"))
    normalized["per_100g_fat_g"] = _to_float_or_none(parsed.get("per_100g_fat_g"))
    normalized["per_100g_protein_g"] = _to_float_or_none(parsed.get("per_100g_protein_g"))
    normalized["per_100g_sodium_mg"] = _to_float_or_none(parsed.get("per_100g_sodium_mg"))
    confidence = _to_float_or_none(parsed.get("confidence"))
    normalized["confidence"] = max(0.0, min(confidence, 1.0)) if confidence is not None else None
    return normalized


def _gemini_api_root(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/v1") or cleaned.endswith("/v1beta"):
        return cleaned.rsplit("/", 1)[0]
    return cleaned


def _client_kwargs(provider: ResolvedAiProvider) -> dict[str, object]:
    client_kwargs: dict[str, object] = {"timeout": provider.timeout_sec}
    if provider.proxy_enabled and provider.proxy_url:
        client_kwargs["proxy"] = provider.proxy_url
    return client_kwargs


def _openai_chat_test(client: httpx.Client, provider: ResolvedAiProvider, prompt_text: str) -> AiProbeResult:
    response = client.post(
        f"{provider.base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {provider.api_key}"},
        json={
            "model": provider.model_name,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0,
        },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"].get("content") or ""
    return AiProbeResult(
        ok=True,
        transport="openai_compat",
        detail=str(content).strip()[:500] or "AI 网关已返回成功响应。",
        model_name=provider.model_name,
        status_code=response.status_code,
    )


def _gemini_generate_content_test(client: httpx.Client, provider: ResolvedAiProvider, prompt_text: str) -> AiProbeResult:
    response = client.post(
        f"{_gemini_api_root(provider.base_url or '')}/v1beta/models/{provider.model_name}:generateContent",
        headers={"x-goog-api-key": provider.api_key or ""},
        json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0},
        },
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text", "")).strip() for part in parts if isinstance(part, dict)).strip()
    return AiProbeResult(
        ok=True,
        transport="gemini_native",
        detail=text[:500] or "Gemini 原生接口已返回成功响应。",
        model_name=provider.model_name,
        status_code=response.status_code,
    )


def probe_ai_provider(provider: ResolvedAiProvider, prompt_text: str = "Reply with exactly OK") -> AiProbeResult:
    if not provider.enabled or not provider.base_url or not provider.api_key:
        return AiProbeResult(
            ok=False,
            transport="disabled",
            detail="AI 提供方未启用或缺少 base_url / api_key。",
            model_name=provider.model_name,
        )

    errors: list[str] = []
    with httpx.Client(**_client_kwargs(provider)) as client:
        try:
            return _openai_chat_test(client, provider, prompt_text)
        except httpx.HTTPStatusError as error:
            errors.append(f"openai_compat HTTP {error.response.status_code}: {error.response.text[:400]}")
        except Exception as error:  # pragma: no cover - defensive
            errors.append(f"openai_compat error: {error}")

        if provider.model_name.startswith("gemini"):
            try:
                return _gemini_generate_content_test(client, provider, prompt_text)
            except httpx.HTTPStatusError as error:
                errors.append(f"gemini_native HTTP {error.response.status_code}: {error.response.text[:400]}")
            except Exception as error:  # pragma: no cover - defensive
                errors.append(f"gemini_native error: {error}")

    return AiProbeResult(
        ok=False,
        transport="fallback_failed",
        detail=" | ".join(errors)[:1000] if errors else "AI 测试连接失败。",
        model_name=provider.model_name,
    )


def _gemini_generate_content_analysis(
    client: httpx.Client,
    image_path: Path,
    provider: ResolvedAiProvider,
    system_prompt: str,
    user_text: str,
) -> dict:
    response = client.post(
        f"{_gemini_api_root(provider.base_url or '')}/v1beta/models/{provider.model_name}:generateContent",
        headers={"x-goog-api-key": provider.api_key or ""},
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": user_text},
                        {"inline_data": _image_to_inline_data(image_path)},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        },
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text", "")).strip() for part in parts if isinstance(part, dict)).strip()
    parsed = _normalize_ai_nutrition(_parse_ai_json(text))
    parsed["provider_trace"] = {
        "provider": "newapi",
        "model": provider.model_name,
        "proxy_enabled": provider.proxy_enabled,
        "proxy_url": provider.proxy_url if provider.proxy_enabled else None,
        "transport": "gemini_native",
    }
    return parsed


def resolve_ai_provider(db: Session, household_id: str) -> ResolvedAiProvider:
    settings = get_settings()
    provider = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == household_id))
    if provider:
        return ResolvedAiProvider(
            base_url=provider.base_url,
            api_key=provider.api_key,
            model_name=provider.vision_model,
            timeout_sec=provider.timeout_sec,
            enabled=provider.enabled,
            proxy_enabled=provider.proxy_enabled,
            proxy_url=provider.proxy_url,
        )
    return ResolvedAiProvider(
        base_url=settings.newapi_base_url,
        api_key=settings.newapi_api_key,
        model_name=settings.newapi_vision_model,
        timeout_sec=60,
        enabled=bool(settings.newapi_base_url and settings.newapi_api_key),
        proxy_enabled=settings.newapi_proxy_enabled,
        proxy_url=settings.newapi_proxy_url,
    )


def analyze_food_image(image_path: Path, provider: ResolvedAiProvider, draft_type: str, hint_text: str | None = None) -> dict:
    if not provider.enabled or not provider.base_url or not provider.api_key:
        return {
            "food_name": None,
            "raw_text": None,
            "portion_basis": None,
            "per_100g_kcal": None,
            "per_100g_carb_g": None,
            "per_100g_fat_g": None,
            "per_100g_protein_g": None,
            "per_100g_sodium_mg": None,
            "estimated_grams": None,
            "estimated_solid_grams": None,
            "estimated_liquid_grams": None,
            "estimated_scope": None,
            "confidence": 0.0,
            "provider_trace": {"provider": "disabled"},
        }

    system_prompt = LABEL_SYSTEM_PROMPT if draft_type == "label" else DISH_SYSTEM_PROMPT
    if draft_type == "label":
        user_text = "Read the nutrition facts from this image."
    else:
        user_text = (
            "Estimate this cooked dish from the image. "
            "Explain the portion-size assumptions in raw_text, and clarify whether estimated_grams includes visible soup or only solids."
        )
        if hint_text:
            user_text += f" User hint: {hint_text.strip()}"

    payload = {
        "model": provider.model_name,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": _image_to_data_uri(image_path)}},
                ],
            },
        ],
        "temperature": 0.1,
    }

    try:
        with httpx.Client(**_client_kwargs(provider)) as client:
            response = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {provider.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = _normalize_ai_nutrition(_parse_ai_json(content))
            parsed["provider_trace"] = {
                "provider": "newapi",
                "model": provider.model_name,
                "proxy_enabled": provider.proxy_enabled,
                "proxy_url": provider.proxy_url if provider.proxy_enabled else None,
                "transport": "openai_compat",
            }
            return parsed
    except httpx.HTTPStatusError as error:
        if provider.model_name.startswith("gemini"):
            try:
                with httpx.Client(**_client_kwargs(provider)) as client:
                    return _gemini_generate_content_analysis(client, image_path, provider, system_prompt, user_text)
            except httpx.HTTPStatusError:
                pass
        detail = f"AI 识别服务暂时不可用：上游返回 {error.response.status_code}"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 识别服务连接失败，请稍后再试。") from error
    except (KeyError, json.JSONDecodeError, TypeError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 识别结果格式异常，请稍后再试。") from error


def extract_nutrition_from_image(image_path: Path, provider: ResolvedAiProvider) -> dict:
    return analyze_food_image(image_path, provider, "label")
