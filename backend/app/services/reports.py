from __future__ import annotations

from datetime import date, datetime, timedelta
import math
from pathlib import Path
from statistics import mean
from time import sleep
from zoneinfo import ZoneInfo

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DailyReport, Household, MeasurementRecord, Member, MealEntry, MediaAsset, NotificationEndpoint
from app.services.tdee import (
    calculate_bmr,
    calculate_goal_intake_kcal,
    calculate_tdee,
    consumed_totals,
    exercise_totals,
    latest_weight_kg,
    macro_progress,
    macro_percentages,
    macro_targets,
)

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
PUSH_RETRY_ATTEMPTS = 3
DAILY_PUSH_MINUTE = 0
WEEKLY_PUSH_MINUTE = 1
MONTHLY_PUSH_MINUTE = 2
WEEKLY_PUSH_WEEKDAY = 0
MONTHLY_PUSH_DAY = 1
DEFAULT_PUSH_CONTENT = {
    "daily": "请查收减脂日报长图。",
    "weekly": "请查收本周周报长图。",
    "monthly": "请查收本月月报长图。",
}
DEFAULT_PUSH_USER_ID_MAP = {
    "admin": "cz",
    "cz": "cz",
    "wdc": "wdc",
}
DISABLED_PUSH_USER_IDS = {"czg"}


def _as_beijing_datetime(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(BEIJING_TZ)
    if value.tzinfo is None:
        return value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ)


def _notification_base_url() -> str:
    settings = get_settings()
    if settings.cors_origins:
        return settings.cors_origins[0].rstrip("/")
    return "http://127.0.0.1:8000"


def _absolute_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{_notification_base_url()}{url}"


def _periodic_title_date(period_start: date, period_end: date) -> date:
    return period_end + timedelta(days=1)


def _resolve_push_user_id(member: Member, endpoint: NotificationEndpoint) -> str | None:
    metadata = endpoint.metadata_json if isinstance(endpoint.metadata_json, dict) else {}
    mapping = metadata.get("user_id_map") if isinstance(metadata.get("user_id_map"), dict) else {}

    mapped = mapping.get(member.username)
    if isinstance(mapped, str) and mapped.strip() and mapped.strip() not in DISABLED_PUSH_USER_IDS:
        return mapped.strip()

    fallback = DEFAULT_PUSH_USER_ID_MAP.get(member.username, member.username)
    if fallback in DISABLED_PUSH_USER_IDS:
        return None
    return fallback if fallback in {"cz", "wdc"} else None


def _endpoint_delivery_state(endpoint: NotificationEndpoint) -> tuple[dict, dict]:
    metadata = endpoint.metadata_json if isinstance(endpoint.metadata_json, dict) else {}
    delivery_state = metadata.get("_delivery") if isinstance(metadata.get("_delivery"), dict) else {}
    metadata["_delivery"] = delivery_state
    return metadata, delivery_state


def _set_endpoint_delivery_state(
    endpoint: NotificationEndpoint,
    *,
    delivery_key: str,
    current_time: datetime,
    target_url: str,
    response_status: int | None = None,
    response_body: object | None = None,
    error: str | None = None,
) -> None:
    metadata, delivery_state = _endpoint_delivery_state(endpoint)
    payload: dict[str, object] = {
        "target_url": target_url,
        "updated_at": current_time.isoformat(),
    }
    if response_status is not None:
        payload["last_status"] = response_status
    if response_body is not None:
        payload["last_response"] = response_body
    if error is not None:
        payload["last_error"] = error
    delivery_state[delivery_key] = payload
    endpoint.metadata_json = metadata


def _should_skip_delivery(endpoint: NotificationEndpoint, delivery_key: str, target_url: str) -> bool:
    _, delivery_state = _endpoint_delivery_state(endpoint)
    state = delivery_state.get(delivery_key) if isinstance(delivery_state.get(delivery_key), dict) else {}
    return state.get("target_url") == target_url and state.get("last_error") is None


def _period_key(report_type: str, *, report_date: date | None = None, period_start: date | None = None, period_end: date | None = None) -> str:
    if report_type == "daily" and report_date is not None:
        return report_date.isoformat()
    if report_type == "weekly" and period_start is not None and period_end is not None:
        return f"{period_start.isoformat()}_{period_end.isoformat()}"
    if report_type == "monthly" and period_start is not None:
        return period_start.strftime("%Y-%m")
    raise ValueError("invalid period key arguments")


def _daily_title(push_user_id: str, report_date: date) -> str:
    return f"【{push_user_id}】{report_date.isoformat()} 日报"


def _weekly_title(push_user_id: str, period_start: date, period_end: date) -> str:
    return f"【{push_user_id}】{_periodic_title_date(period_start, period_end).isoformat()} 周报"


def _monthly_title(push_user_id: str, period_start: date) -> str:
    return f"【{push_user_id}】{period_start.strftime('%Y-%m')} 月报"


def _post_generic_webhook(target_url: str, payload: dict[str, object]) -> tuple[int, object | None]:
    last_error: Exception | None = None
    for attempt in range(PUSH_RETRY_ATTEMPTS):
        try:
            response = httpx.post(target_url, json=payload, timeout=20)
            status = response.status_code
            try:
                body: object | None = response.json()
            except ValueError:
                body = response.text[:1000]

            if status in {200, 202, 207}:
                return status, body

            last_error = RuntimeError(f"HTTP {status}: {response.text[:1000]}")
        except Exception as error:
            last_error = error

        if attempt < PUSH_RETRY_ATTEMPTS - 1:
            sleep(1)

    if last_error is None:
        raise RuntimeError("unknown webhook delivery error")
    raise last_error


def _send_generic_image_message(
    db: Session,
    endpoint: NotificationEndpoint,
    *,
    member: Member,
    report_type: str,
    title: str,
    content: str,
    image_url: str,
    current_time: datetime,
    report_date: date | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> bool:
    push_user_id = _resolve_push_user_id(member, endpoint)
    if not push_user_id:
        return False

    delivery_key = f"{report_type}:{member.id}:{_period_key(report_type, report_date=report_date, period_start=period_start, period_end=period_end)}"
    if _should_skip_delivery(endpoint, delivery_key, endpoint.target_url):
        return False

    payload = {
        "source": "jianfei",
        "type": f"{report_type}_report",
        "memberId": member.id,
        "memberName": member.display_name,
        "userId": push_user_id,
        "title": title,
        "content": content,
        "imageUrl": image_url,
    }
    if report_date is not None:
        payload["reportDate"] = report_date.isoformat()
    if period_start is not None:
        payload["periodStart"] = period_start.isoformat()
    if period_end is not None:
        payload["periodEnd"] = period_end.isoformat()

    try:
        status, body = _post_generic_webhook(endpoint.target_url, payload)
        _set_endpoint_delivery_state(
            endpoint,
            delivery_key=delivery_key,
            current_time=current_time,
            target_url=endpoint.target_url,
            response_status=status,
            response_body=body,
        )
        db.add(endpoint)
        db.commit()
        return True
    except Exception as error:
        _set_endpoint_delivery_state(
            endpoint,
            delivery_key=delivery_key,
            current_time=current_time,
            target_url=endpoint.target_url,
            error=str(error),
        )
        db.add(endpoint)
        db.commit()
        return False


def _media_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    settings = get_settings()
    try:
        relative = Path(file_path).resolve().relative_to(settings.media_root.resolve())
    except ValueError:
        return None
    return f"/media-files/{relative.as_posix()}"


def _report_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    settings = get_settings()
    try:
        relative = Path(file_path).resolve().relative_to(settings.report_image_root.resolve())
    except ValueError:
        return None
    return f"/report-files/{relative.as_posix()}"


def _report_image_path(member: Member, report_date: date) -> Path:
    settings = get_settings()
    target_dir = settings.report_image_root / member.household_id / member.id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{report_date.isoformat()}.png"


def _periodic_report_image_path(member: Member, report_type: str, period_start: date, period_end: date) -> Path:
    settings = get_settings()
    target_dir = settings.report_image_root / member.household_id / member.id / "periodic"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{report_type}-{period_start.isoformat()}-{period_end.isoformat()}.png"

REPORT_BG = "#F7F3ED"
REPORT_CARD = "#FFFDFC"
REPORT_CARD_ALT = "#FFF7EE"
REPORT_HERO = "#16342D"
REPORT_TEXT = "#1B2522"
REPORT_MUTED = "#6B756F"
REPORT_ORANGE = "#E57A44"
REPORT_GREEN = "#2C8E73"
REPORT_TEAL = "#4EA99B"
REPORT_GOLD = "#F4B64A"
REPORT_RED = "#E06666"
REPORT_BLUE = "#5F7CF5"
REPORT_LAVENDER = "#8A79F0"
REPORT_BORDER = "#E7DED4"
REPORT_SHADOW = "#EDE4D9"

FONT_REGULAR_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)

FONT_BOLD_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for path in candidates:
        candidate = Path(path)
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()


def _value_to_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current.rstrip())
            current = ""
            continue
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current.rstrip())
            current = char
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return [line for line in lines if line] or [""]


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    *,
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    line_height: int,
) -> int:
    x, y = xy
    for line in _wrap_text(draw, text, font, max_width):
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _draw_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str = REPORT_CARD,
    radius: int = 36,
) -> None:
    shadow = (box[0], box[1] + 8, box[2], box[3] + 8)
    draw.rounded_rectangle(shadow, radius=radius, fill=REPORT_SHADOW)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=REPORT_BORDER, width=2)


def _draw_metric_tile(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    label: str,
    value: str,
    subtitle: str | None = None,
    accent: str = REPORT_GREEN,
) -> None:
    label_font = _load_font(34)
    value_font = _load_font(72, bold=True)
    subtitle_font = _load_font(30)

    _draw_card(draw, box)
    x0, y0, x1, _ = box
    label_y = y0 + 22
    _, label_height = _text_size(draw, label, label_font)
    value_y = label_y + label_height + 14
    _, value_height = _text_size(draw, value, value_font)
    draw.text((x0 + 28, label_y), label, font=label_font, fill=REPORT_MUTED)
    draw.text((x0 + 28, value_y), value, font=value_font, fill=accent)
    if subtitle:
        _draw_wrapped_text(
            draw,
            subtitle,
            (x0 + 28, value_y + value_height + 18),
            font=subtitle_font,
            fill=REPORT_TEXT,
            max_width=x1 - x0 - 56,
            line_height=36,
        )


def _draw_big_stat_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    label: str,
    value: str,
    subtitle: str | None = None,
    accent: str = REPORT_GREEN,
    fill: str = REPORT_CARD,
) -> None:
    label_font = _load_font(34)
    subtitle_font = _load_font(30)

    _draw_card(draw, box, fill=fill)
    x0, y0, x1, _ = box
    label_y = y0 + 24
    _, label_height = _text_size(draw, label, label_font)
    value_font_size = 88
    value_area_width = int((x1 - x0) * 0.54)
    max_width = value_area_width - 40
    value_font = _load_font(value_font_size, bold=True)
    value_width, value_height = _text_size(draw, value, value_font)
    while (value_width > max_width or value_height > 90) and value_font_size > 60:
        value_font_size -= 4
        value_font = _load_font(value_font_size, bold=True)
        value_width, value_height = _text_size(draw, value, value_font)
    value_y = label_y + label_height + 18
    draw.text((x0 + 30, label_y), label, font=label_font, fill=REPORT_MUTED)
    draw.text((x0 + 30, value_y), value, font=value_font, fill=accent)
    if subtitle:
        meta_title_font = _load_font(24, bold=True)
        meta_body_font = _load_font(28)
        meta_x = x0 + value_area_width + 12
        meta_y = y0 + 34
        draw.text((meta_x, meta_y), "说明", font=meta_title_font, fill=REPORT_MUTED)
        _draw_wrapped_text(
            draw,
            subtitle,
            (meta_x, meta_y + 34),
            font=meta_body_font,
            fill=REPORT_TEXT,
            max_width=x1 - meta_x - 26,
            line_height=34,
        )


def _draw_info_chip(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    fill: str,
    text_fill: str = "#FFFDF9",
) -> None:
    label_font = _load_font(24)
    value_font = _load_font(40, bold=True)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=24, fill=fill)
    draw.text((x0 + 20, y0 + 14), label, font=label_font, fill=text_fill)
    draw.text((x0 + 20, y0 + 44), value, font=value_font, fill=text_fill)


def _draw_donut_chart(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[int, int],
    radius: int,
    ring_width: int,
    segments: list[tuple[float, str]],
    background: str = "#E6E1D8",
) -> None:
    bbox = (
        center[0] - radius,
        center[1] - radius,
        center[0] + radius,
        center[1] + radius,
    )
    draw.arc(bbox, start=0, end=360, fill=background, width=ring_width)
    start_angle = -90.0
    for ratio, color in segments:
        if ratio <= 0:
            continue
        end_angle = start_angle + ratio * 360.0
        draw.arc(bbox, start=start_angle, end=end_angle, fill=color, width=ring_width)
        start_angle = end_angle


def _draw_ratio_legend(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    items: list[tuple[str, float, str]],
) -> None:
    label_font = _load_font(30)
    value_font = _load_font(36, bold=True)
    x, y = origin
    for label, value, color in items:
        draw.rounded_rectangle((x, y + 8, x + 24, y + 32), radius=10, fill=color)
        draw.text((x + 40, y), label, font=label_font, fill=REPORT_TEXT)
        value_text = f"{int(round(value))}%"
        value_width, _ = _text_size(draw, value_text, value_font)
        draw.text((x + 250 - value_width, y), value_text, font=value_font, fill=color)
        y += 60


def _draw_macro_amounts(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    items: list[tuple[str, float, str]],
) -> None:
    font = _load_font(28)
    x, y = origin
    for label, grams, color in items:
        draw.text((x, y), f"{label} {int(round(grams))} g", font=font, fill=color)
        y += 38


def _draw_line_chart(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    title: str,
    values: list[float | None],
    labels: list[str],
    accent: str,
) -> None:
    title_font = _load_font(36, bold=True)
    axis_font = _load_font(24)
    _draw_card(draw, box, fill=REPORT_CARD_ALT)
    x0, y0, x1, y1 = box
    draw.text((x0 + 28, y0 + 22), title, font=title_font, fill=REPORT_TEXT)

    chart_left = x0 + 42
    chart_top = y0 + 88
    chart_right = x1 - 42
    chart_bottom = y1 - 56
    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill=REPORT_BORDER, width=3)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill=REPORT_BORDER, width=3)

    valid = [(index, value) for index, value in enumerate(values) if value is not None]
    if len(valid) < 2:
        draw.text((chart_left, chart_top + 40), "本周期体重点位不足，暂无法绘制走势。", font=axis_font, fill=REPORT_MUTED)
        return

    value_min = min(value for _, value in valid)
    value_max = max(value for _, value in valid)
    if math.isclose(value_min, value_max):
        value_min -= 1
        value_max += 1

    points: list[tuple[int, int]] = []
    steps = max(len(values) - 1, 1)
    for index, value in valid:
        x = int(chart_left + (chart_right - chart_left) * index / steps)
        normalized = (value - value_min) / (value_max - value_min)
        y = int(chart_bottom - (chart_bottom - chart_top - 18) * normalized)
        points.append((x, y))

    for fraction in (0.0, 0.5, 1.0):
        y = int(chart_bottom - (chart_bottom - chart_top - 18) * fraction)
        draw.line((chart_left, y, chart_right, y), fill=REPORT_BORDER, width=2)

    draw.line(points, fill=accent, width=8, joint="curve")
    for point in points:
        draw.ellipse((point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8), fill=REPORT_CARD, outline=accent, width=4)

    first_label = labels[0] if labels else ""
    last_label = labels[-1] if labels else ""
    draw.text((chart_left, chart_bottom + 14), first_label, font=axis_font, fill=REPORT_MUTED)
    last_width, _ = _text_size(draw, last_label, axis_font)
    draw.text((chart_right - last_width, chart_bottom + 14), last_label, font=axis_font, fill=REPORT_MUTED)
    max_text = f"{value_max:.1f}kg"
    min_text = f"{value_min:.1f}kg"
    draw.text((chart_left, chart_top - 4), max_text, font=axis_font, fill=REPORT_MUTED)
    draw.text((chart_left, chart_bottom - 24), min_text, font=axis_font, fill=REPORT_MUTED)


def _draw_deficit_baseline_chart(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    title: str,
    values: list[float],
    labels: list[str],
    goal_kcal: float,
) -> None:
    title_font = _load_font(36, bold=True)
    axis_font = _load_font(22)
    value_font = _load_font(20, bold=True)
    _draw_card(draw, box, fill=REPORT_CARD_ALT)
    x0, y0, x1, y1 = box
    draw.text((x0 + 28, y0 + 22), title, font=title_font, fill=REPORT_TEXT)

    chart_left = x0 + 36
    chart_top = y0 + 106
    chart_right = x1 - 40
    chart_bottom = y1 - 84

    deltas = [value - goal_kcal for value in values]
    peak = max([abs(delta) for delta in deltas] + [1.0])
    baseline_y = int(chart_top + (chart_bottom - chart_top) * 0.5)
    draw.line((chart_left, baseline_y, chart_right, baseline_y), fill=REPORT_GREEN, width=3)
    goal_text = f"目标线 {int(goal_kcal)} kcal"
    goal_width, _ = _text_size(draw, goal_text, axis_font)
    draw.text((chart_right - goal_width, baseline_y - 30), goal_text, font=axis_font, fill=REPORT_GREEN)

    for ratio in (1.0, 0.5, -0.5, -1.0):
        y = int(baseline_y - (baseline_y - chart_top - 10) * ratio)
        draw.line((chart_left, y, chart_right, y), fill=REPORT_BORDER, width=2)

    bar_width = max(16, int((chart_right - chart_left) / max(len(values), 1) * 0.42))
    step = (chart_right - chart_left) / max(len(values), 1)
    for index, delta in enumerate(deltas):
        center_x = chart_left + step * index + step / 2
        scale = min(abs(delta) / peak, 1.0)
        bar_height = int((baseline_y - chart_top - 10) * scale)
        if delta >= 0:
            top = baseline_y - bar_height
            bottom = baseline_y
            color = REPORT_GREEN
            text_y = max(chart_top + 6, top - 24)
        else:
            top = baseline_y
            bottom = baseline_y + bar_height
            color = REPORT_ORANGE
            text_y = min(chart_bottom - 22, bottom + 8)
        draw.rounded_rectangle(
            (
                int(center_x - bar_width / 2),
                int(top),
                int(center_x + bar_width / 2),
                int(bottom),
            ),
            radius=10,
            fill=color,
        )
        value_text = f"{delta:+.0f}"
        value_width, _ = _text_size(draw, value_text, value_font)
        draw.text((int(center_x - value_width / 2), int(text_y)), value_text, font=value_font, fill=color)

    first_label = labels[0] if labels else ""
    last_label = labels[-1] if labels else ""
    draw.text((chart_left, chart_bottom + 18), first_label, font=axis_font, fill=REPORT_MUTED)
    last_width, _ = _text_size(draw, last_label, axis_font)
    draw.text((chart_right - last_width, chart_bottom + 18), last_label, font=axis_font, fill=REPORT_MUTED)


def _draw_deficit_chart(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    title: str,
    values: list[float],
    labels: list[str],
    goal_kcal: float,
) -> None:
    title_font = _load_font(36, bold=True)
    axis_font = _load_font(22)
    subtitle_font = _load_font(24)
    value_font = _load_font(18, bold=True)
    _draw_card(draw, box, fill=REPORT_CARD_ALT)
    x0, y0, x1, y1 = box
    draw.text((x0 + 28, y0 + 22), title, font=title_font, fill=REPORT_TEXT)
    goal_caption = f"目标 {int(goal_kcal)} kcal / 天"
    goal_width, _ = _text_size(draw, goal_caption, subtitle_font)
    draw.text((x1 - 28 - goal_width, y0 + 28), goal_caption, font=subtitle_font, fill=REPORT_GREEN)

    chart_left = x0 + 42
    chart_top = y0 + 108
    chart_right = x1 - 42
    chart_bottom = y1 - 74

    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill=REPORT_BORDER, width=3)
    peak = max([abs(goal_kcal), *[abs(item) for item in values], 1.0])
    if peak == 0:
        peak = 1.0

    zero_y = int(chart_top + (chart_bottom - chart_top) * 0.72)
    draw.line((chart_left, zero_y, chart_right, zero_y), fill=REPORT_BORDER, width=2)
    if goal_kcal > 0:
        goal_y = int(zero_y - (zero_y - chart_top) * min(goal_kcal / peak, 1.0))
        draw.line((chart_left, goal_y, chart_right, goal_y), fill=REPORT_GREEN, width=3)

    bar_width = max(5, int((chart_right - chart_left) / max(len(values), 1) * 0.34))
    step = (chart_right - chart_left) / max(len(values), 1)
    for index, value in enumerate(values):
        center_x = chart_left + step * index + step / 2
        scale = min(abs(value) / peak, 1.0)
        bar_height = int((zero_y - chart_top - 10) * scale)
        if value >= 0:
            top = zero_y - bar_height
            bottom = zero_y
            color = REPORT_GREEN if value >= goal_kcal else REPORT_GOLD
        else:
            top = zero_y
            bottom = zero_y + max(bar_height, 8)
            color = REPORT_RED
        draw.rounded_rectangle(
            (
                int(center_x - bar_width / 2),
                int(top),
                int(center_x + bar_width / 2),
                int(bottom),
            ),
            radius=10,
            fill=color,
        )
        value_text = f"{value:+.0f}"
        value_width, value_height = _text_size(draw, value_text, value_font)
        text_x = int(center_x - value_width / 2)
        if value >= 0:
            text_y = max(chart_top + 4, int(top) - value_height - 10)
        else:
            text_y = min(chart_bottom - value_height - 6, int(bottom) + 8)
        draw.text((text_x, text_y), value_text, font=value_font, fill=color)

    first_label = labels[0] if labels else ""
    last_label = labels[-1] if labels else ""
    draw.text((chart_left, chart_bottom + 20), first_label, font=axis_font, fill=REPORT_MUTED)
    last_width, _ = _text_size(draw, last_label, axis_font)
    draw.text((chart_right - last_width, chart_bottom + 20), last_label, font=axis_font, fill=REPORT_MUTED)


def _draw_period_highlight_card(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    title: str,
    title_color: str,
    items: list[str],
) -> None:
    title_font = _load_font(36, bold=True)
    body_font = _load_font(30)
    _draw_card(draw, box)
    draw.text((box[0] + 28, box[1] + 22), title, font=title_font, fill=title_color)
    y = box[1] + 74
    if items:
        for item in items:
            draw.rounded_rectangle((box[0] + 28, y + 10, box[0] + 42, y + 24), radius=7, fill=title_color)
            y = _draw_wrapped_text(
                draw,
                item,
                (box[0] + 60, y),
                font=body_font,
                fill=REPORT_TEXT,
                max_width=box[2] - box[0] - 88,
                line_height=36,
            ) + 12
    else:
        draw.text((box[0] + 28, y), "暂无可总结的日报。", font=body_font, fill=REPORT_MUTED)


def _format_cn_day(value: date) -> str:
    return value.strftime("%-m月%-d日")


def _meal_slot_label(value: str) -> str:
    labels = {
        "breakfast": "早餐",
        "lunch": "午餐",
        "dinner": "晚餐",
        "snack": "加餐",
    }
    return labels.get(value, value or "-")


def _period_labels(day_cards: list[dict]) -> list[str]:
    labels: list[str] = []
    for item in day_cards:
        raw = str(item.get("date") or "")
        try:
            labels.append(_format_cn_day(date.fromisoformat(raw)))
        except ValueError:
            labels.append(raw)
    return labels


def _render_daily_report_image(member: Member, report: DailyReport) -> str:
    payload = report.payload if isinstance(report.payload, dict) else {}
    intake = payload.get("intake") if isinstance(payload.get("intake"), dict) else {}
    macro_ratio = payload.get("macro_ratio") if isinstance(payload.get("macro_ratio"), dict) else {}
    meal_cards = payload.get("meal_cards") if isinstance(payload.get("meal_cards"), list) else []

    width = 1080
    margin = 42
    hero_height = 248
    stat_height = 204
    chart_height = 420
    insight_height = 186
    meal_height = max(250, 110 + len(meal_cards[:5]) * 68)
    chip_height = 132
    footer_height = 36
    block_gap = 22
    height = 56 + hero_height + chip_height + stat_height * 3 + chart_height + insight_height + meal_height + footer_height + block_gap * 7

    canvas = Image.new("RGB", (width, height), REPORT_BG)
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(56, bold=True)
    headline_font = _load_font(42, bold=True)
    body_font = _load_font(32)
    small_font = _load_font(28)

    hero_box = (margin, 40, width - margin, 40 + hero_height)
    draw.rounded_rectangle(hero_box, radius=42, fill=REPORT_HERO)
    draw.text((hero_box[0] + 38, hero_box[1] + 28), "今日减脂日报", font=title_font, fill="#FFF7ED")
    draw.text((hero_box[0] + 38, hero_box[1] + 102), member.display_name, font=_load_font(36, bold=True), fill="#FFF7ED")
    draw.text(
        (hero_box[0] + 38, hero_box[1] + 154),
        f"{_format_cn_day(report.report_date)}",
        font=body_font,
        fill="#E8EFE9",
    )
    badge_text = "已达标" if payload.get("deficit_hit") else "继续努力"
    badge_fill = REPORT_GREEN if payload.get("deficit_hit") else REPORT_ORANGE
    badge_box = (hero_box[2] - 220, hero_box[1] + 34, hero_box[2] - 38, hero_box[1] + 94)
    draw.rounded_rectangle(badge_box, radius=30, fill=badge_fill)
    badge_width, badge_height = _text_size(draw, badge_text, body_font)
    draw.text(
        (
            badge_box[0] + (badge_box[2] - badge_box[0] - badge_width) / 2,
            badge_box[1] + (badge_box[3] - badge_box[1] - badge_height) / 2 - 2,
        ),
        badge_text,
        font=body_font,
        fill="#FFFDF9",
    )

    intake_kcal = _value_to_float(intake.get("kcal")) or 0.0
    deficit_kcal = _value_to_float(payload.get("deficit_kcal"))
    tdee = _value_to_float(payload.get("tdee"))
    exercise_kcal = _value_to_float(payload.get("exercise_kcal")) or 0.0
    goal_kcal = _value_to_float(payload.get("goal_deficit_kcal")) or 0.0
    completion_ratio = 0.0 if goal_kcal <= 0 or deficit_kcal is None else min(max(deficit_kcal / goal_kcal, 0.0), 1.0)

    chip_y = hero_box[3] + block_gap
    chip_gap = 18
    chip_width = 286
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38, chip_y, hero_box[0] + 38 + chip_width, chip_y + chip_height),
        label="今日摄入",
        value=f"{int(round(intake_kcal))} kcal",
        fill="#244E44",
    )
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38 + chip_width + chip_gap, chip_y, hero_box[0] + 38 + chip_width * 2 + chip_gap, chip_y + chip_height),
        label="运动消耗",
        value=f"{int(round(exercise_kcal))} kcal",
        fill="#305D52",
    )
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38 + (chip_width + chip_gap) * 2, chip_y, hero_box[2] - 38, chip_y + chip_height),
        label="目标热量差",
        value=f"{int(round(goal_kcal))} kcal",
        fill="#3C6E61",
    )

    card_width = width - margin * 2
    first_row_y = chip_y + chip_height + block_gap
    second_row_y = first_row_y + stat_height + block_gap
    third_row_y = second_row_y + stat_height + block_gap
    _draw_big_stat_card(
        draw,
        (margin, first_row_y, margin + card_width, first_row_y + stat_height),
        label="今日热量差",
        value=f"{int(round(deficit_kcal or 0))} kcal" if deficit_kcal is not None else "待生成",
        subtitle=f"目标 {int(round(goal_kcal))} kcal · {'今天已达标' if payload.get('deficit_hit') else '继续努力'}",
        accent=REPORT_BLUE if deficit_kcal is not None and deficit_kcal >= 0 else REPORT_RED,
    )
    _draw_big_stat_card(
        draw,
        (margin, second_row_y, margin + card_width, second_row_y + stat_height),
        label="今日摄入",
        value=f"{int(round(intake_kcal))} kcal",
        subtitle="来自今天已记录的餐食总和",
        accent=REPORT_ORANGE,
    )
    _draw_big_stat_card(
        draw,
        (margin, third_row_y, margin + card_width, third_row_y + stat_height),
        label="今日 TDEE",
        value=f"{int(round(tdee or 0))} kcal" if tdee is not None else "待生成",
        subtitle=f"运动额外消耗 {int(round(exercise_kcal))} kcal · 完成度 {int(round(completion_ratio * 100))}%",
        accent=REPORT_GREEN,
    )

    chart_top = third_row_y + stat_height + block_gap
    chart_box = (margin, chart_top, width - margin, chart_top + chart_height)
    _draw_card(draw, chart_box, fill=REPORT_CARD_ALT)
    draw.text((chart_box[0] + 28, chart_box[1] + 22), "营养占比与完成度", font=headline_font, fill=REPORT_TEXT)
    center = (chart_box[0] + 220, chart_box[1] + 196)
    carb_pct = _value_to_float(macro_ratio.get("carb_pct")) or 0.0
    protein_pct = _value_to_float(macro_ratio.get("protein_pct")) or 0.0
    fat_pct = _value_to_float(macro_ratio.get("fat_pct")) or 0.0
    carb_g = _value_to_float(intake.get("carb_g")) or 0.0
    protein_g = _value_to_float(intake.get("protein_g")) or 0.0
    fat_g = _value_to_float(intake.get("fat_g")) or 0.0
    macro_segments = [
        (max(carb_pct, 0.0) / 100.0, REPORT_GOLD),
        (max(protein_pct, 0.0) / 100.0, REPORT_TEAL),
        (max(fat_pct, 0.0) / 100.0, REPORT_LAVENDER),
    ]
    _draw_donut_chart(draw, center=center, radius=112, ring_width=36, segments=macro_segments)
    macro_label = "宏量占比"
    macro_label_width, _ = _text_size(draw, macro_label, body_font)
    draw.text((center[0] - macro_label_width / 2, chart_box[3] - 78), macro_label, font=body_font, fill=REPORT_TEXT)
    _draw_ratio_legend(
        draw,
        origin=(chart_box[0] + 392, chart_box[1] + 120),
        items=[
            ("碳水", carb_pct, REPORT_GOLD),
            ("蛋白质", protein_pct, REPORT_TEAL),
            ("脂肪", fat_pct, REPORT_LAVENDER),
        ],
    )
    _draw_macro_amounts(
        draw,
        origin=(chart_box[0] + 392, chart_box[1] + 306),
        items=[
            ("碳水", carb_g, REPORT_GOLD),
            ("蛋白质", protein_g, REPORT_TEAL),
            ("脂肪", fat_g, REPORT_LAVENDER),
        ],
    )
    progress_center = (chart_box[0] + 838, chart_box[1] + 194)
    _draw_donut_chart(
        draw,
        center=progress_center,
        radius=96,
        ring_width=26,
        segments=[(completion_ratio, REPORT_GREEN)],
        background="#DDD8CE",
    )
    pct_text = f"{int(round(completion_ratio * 100))}%"
    pct_font = _load_font(48, bold=True)
    draw.text(progress_center, pct_text, font=pct_font, fill=REPORT_GREEN, anchor="mm")
    progress_label = "目标达成"
    label_width, _ = _text_size(draw, progress_label, small_font)
    draw.text((progress_center[0] - label_width / 2, chart_box[3] - 78), progress_label, font=small_font, fill=REPORT_MUTED)

    insight_top = chart_box[3] + block_gap
    insight_box = (margin, insight_top, width - margin, insight_top + insight_height)
    _draw_card(draw, insight_box)
    draw.text((insight_box[0] + 28, insight_box[1] + 20), "今日结论", font=headline_font, fill=REPORT_TEXT)
    insight_text = (
        f"今天已达到目标热量差，继续保持。"
        if payload.get("deficit_hit")
        else f"距离目标还差 {max(int(round(goal_kcal - (deficit_kcal or 0))), 0)} kcal，可优先控制晚间摄入。"
    )
    _draw_wrapped_text(
        draw,
        insight_text,
        (insight_box[0] + 28, insight_box[1] + 76),
        font=body_font,
        fill=REPORT_TEXT,
        max_width=insight_box[2] - insight_box[0] - 56,
        line_height=38,
    )

    meal_top = insight_box[3] + block_gap
    meal_box = (margin, meal_top, width - margin, meal_top + meal_height)
    _draw_card(draw, meal_box)
    draw.text((meal_box[0] + 28, meal_box[1] + 20), "今日餐食", font=headline_font, fill=REPORT_TEXT)
    meal_y = meal_box[1] + 74
    if meal_cards:
        for meal in meal_cards[:5]:
            meal_slot = str(meal.get("meal_slot") or "-")
            meal_name = str(meal.get("food_name") or "-")
            grams = int(round(_value_to_float(meal.get("actual_grams")) or 0))
            kcal = int(round(_value_to_float(meal.get("kcal")) or 0))
            slot_text = _meal_slot_label(meal_slot)
            pill_left = meal_box[0] + 28
            pill_top = meal_y + 2
            pill_width = 96
            draw.rounded_rectangle((pill_left, pill_top, pill_left + pill_width, pill_top + 34), radius=16, fill="#EEF5F2")
            slot_width, _ = _text_size(draw, slot_text, small_font)
            draw.text((pill_left + (pill_width - slot_width) / 2, pill_top + 4), slot_text, font=small_font, fill=REPORT_GREEN)
            meal_text = f"{meal_name} · {grams}g · {kcal} kcal"
            meal_y = _draw_wrapped_text(
                draw,
                meal_text,
                (meal_box[0] + 140, meal_y),
                font=body_font,
                fill=REPORT_TEXT,
                max_width=meal_box[2] - meal_box[0] - 168,
                line_height=34,
            ) + 12
            if meal_y < meal_box[3] - 26:
                draw.line((meal_box[0] + 28, meal_y - 4, meal_box[2] - 28, meal_y - 4), fill=REPORT_BORDER, width=2)
    else:
        draw.text((meal_box[0] + 28, meal_y), "今天还没有餐食记录。", font=body_font, fill=REPORT_MUTED)

    output_path = _report_image_path(member, report.report_date)
    canvas.save(output_path, format="PNG")
    return str(output_path)


def _render_periodic_report_image(member: Member, report_type: str, payload: dict, period_start: date, period_end: date) -> str:
    day_cards = payload.get("day_cards") if isinstance(payload.get("day_cards"), list) else []
    total_days = int(round(_value_to_float(payload.get("total_days")) or 0))
    hit_days = int(round(_value_to_float(payload.get("hit_days")) or 0))
    hit_rate = (hit_days / total_days) if total_days else 0.0
    labels = _period_labels(day_cards)
    weight_values = [_value_to_float(item.get("weight_kg")) if isinstance(item, dict) else None for item in day_cards]
    deficit_values = [_value_to_float(item.get("deficit_kcal")) or 0.0 for item in day_cards if isinstance(item, dict)]
    goal_kcal = float(member.goal_deficit_kcal or 0)

    title = "本周减脂小结" if report_type == "weekly" else "本月减脂小结"
    width = 1080
    margin = 42
    hero_height = 248
    stat_height = 196
    chart_height = 460 if total_days > 14 else 380
    summary_card_height = 300
    summary_gap = 28
    summary_height = summary_card_height * 2 + summary_gap
    chip_height = 132
    footer_height = 36
    block_gap = 22
    height = 60 + hero_height + chip_height + stat_height * 4 + chart_height * 2 + summary_height + footer_height + block_gap * 9

    canvas = Image.new("RGB", (width, height), REPORT_BG)
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(56, bold=True)
    headline_font = _load_font(40, bold=True)
    body_font = _load_font(32)
    small_font = _load_font(28)

    hero_box = (margin, 40, width - margin, 40 + hero_height)
    draw.rounded_rectangle(hero_box, radius=42, fill=REPORT_HERO)
    draw.text((hero_box[0] + 38, hero_box[1] + 28), title, font=title_font, fill="#FFF7ED")
    draw.text((hero_box[0] + 38, hero_box[1] + 102), member.display_name, font=_load_font(36, bold=True), fill="#FFF7ED")
    draw.text(
        (hero_box[0] + 38, hero_box[1] + 154),
        f"{_format_cn_day(period_start)} ~ {_format_cn_day(period_end)}",
        font=body_font,
        fill="#E8EFE9",
    )
    chip_y = hero_box[3] + block_gap
    chip_gap = 18
    chip_width = 286
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38, chip_y, hero_box[0] + 38 + chip_width, chip_y + chip_height),
        label="达标天数",
        value=f"{hit_days} / {total_days} 天",
        fill="#244E44",
    )
    weight_change_value = (
        f"{(_value_to_float(payload.get('weight_change_kg')) or 0):+.1f} kg"
        if payload.get("weight_change_kg") is not None
        else "暂无"
    )
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38 + chip_width + chip_gap, chip_y, hero_box[0] + 38 + chip_width * 2 + chip_gap, chip_y + chip_height),
        label="体重变化",
        value=weight_change_value,
        fill="#305D52",
    )
    _draw_info_chip(
        draw,
        box=(hero_box[0] + 38 + (chip_width + chip_gap) * 2, chip_y, hero_box[2] - 38, chip_y + chip_height),
        label="平均摄入",
        value=f"{int(round(_value_to_float(payload.get('avg_intake_kcal')) or 0))} kcal",
        fill="#3C6E61",
    )

    card_width = width - margin * 2
    first_row_y = chip_y + chip_height + block_gap
    second_row_y = first_row_y + stat_height + block_gap
    third_row_y = second_row_y + stat_height + block_gap
    fourth_row_y = third_row_y + stat_height + block_gap

    _draw_big_stat_card(
        draw,
        (margin, first_row_y, margin + card_width, first_row_y + stat_height),
        label="达标率",
        value=f"{int(round(hit_rate * 100))}%",
        subtitle=f"{hit_days} / {total_days} 天达标",
        accent=REPORT_GREEN,
    )
    _draw_big_stat_card(
        draw,
        (margin, second_row_y, margin + card_width, second_row_y + stat_height),
        label="平均热量差",
        value=f"{int(round(_value_to_float(payload.get('avg_deficit_kcal')) or 0))} kcal",
        subtitle=f"目标 {int(goal_kcal)} kcal / 天",
        accent=REPORT_GREEN if (_value_to_float(payload.get('avg_deficit_kcal')) or 0) >= goal_kcal else REPORT_GOLD,
    )
    _draw_big_stat_card(
        draw,
        (margin, third_row_y, margin + card_width, third_row_y + stat_height),
        label="体重变化",
        value=weight_change_value,
        subtitle=(
            f"{(_value_to_float(payload.get('start_weight_kg')) or 0):.1f} kg -> "
            f"{(_value_to_float(payload.get('end_weight_kg')) or 0):.1f} kg"
            if payload.get("start_weight_kg") is not None and payload.get("end_weight_kg") is not None
            else "负值代表下降"
        ),
        accent=REPORT_TEAL if (_value_to_float(payload.get("weight_change_kg")) or 0) <= 0 else REPORT_RED,
    )
    _draw_big_stat_card(
        draw,
        (margin, fourth_row_y, margin + card_width, fourth_row_y + stat_height),
        label="平均摄入",
        value=f"{int(round(_value_to_float(payload.get('avg_intake_kcal')) or 0))} kcal",
        subtitle="按这个周期日报均值计算",
        accent=REPORT_ORANGE,
    )

    ring_top = fourth_row_y + stat_height + block_gap
    ring_box = (margin, ring_top, width - margin, ring_top + chart_height)
    _draw_card(draw, ring_box, fill=REPORT_CARD_ALT)
    draw.text((ring_box[0] + 28, ring_box[1] + 22), "周期表现", font=headline_font, fill=REPORT_TEXT)
    center = (ring_box[0] + 190, ring_box[1] + 194)
    _draw_donut_chart(
        draw,
        center=center,
        radius=104,
        ring_width=32,
        segments=[(hit_rate, REPORT_GREEN)],
        background="#DDD8CE",
    )
    pct_text = f"{int(round(hit_rate * 100))}%"
    pct_font = _load_font(44, bold=True)
    draw.text(center, pct_text, font=pct_font, fill=REPORT_GREEN, anchor="mm")
    avg_intake_payload = payload.get("avg_intake") if isinstance(payload.get("avg_intake"), dict) else {}
    summary_lines = [
        f"达标率 {int(round(hit_rate * 100))}% · 共 {total_days} 天，达标 {hit_days} 天",
        f"平均摄入 {int(round(_value_to_float(payload.get('avg_intake_kcal')) or 0))} kcal / 天",
        f"平均热量差 {int(round(_value_to_float(payload.get('avg_deficit_kcal')) or 0))} kcal / 天",
        (
            f"平均宏量 碳水 {int(round(_value_to_float(avg_intake_payload.get('carb_g')) or 0))}g"
            f" · 蛋白质 {int(round(_value_to_float(avg_intake_payload.get('protein_g')) or 0))}g"
            f" · 脂肪 {int(round(_value_to_float(avg_intake_payload.get('fat_g')) or 0))}g / 天"
        ),
    ]
    summary_y = ring_box[1] + 96
    for line in summary_lines:
        summary_y = _draw_wrapped_text(
            draw,
            line,
            (ring_box[0] + 360, summary_y),
            font=body_font,
            fill=REPORT_TEXT,
            max_width=ring_box[2] - ring_box[0] - 400,
            line_height=40,
        ) + 10

    weight_chart_top = ring_box[3] + 24
    _draw_line_chart(
        draw,
        box=(margin, weight_chart_top, width - margin, weight_chart_top + chart_height),
        title="体重走势",
        values=weight_values,
        labels=labels,
        accent=REPORT_BLUE,
    )
    deficit_chart_top = weight_chart_top + chart_height + 24
    _draw_deficit_baseline_chart(
        draw,
        box=(margin, deficit_chart_top, width - margin, deficit_chart_top + chart_height),
        title="每日热量差走势",
        values=deficit_values,
        labels=labels,
        goal_kcal=goal_kcal,
    )

    summary_top = deficit_chart_top + chart_height + 24
    best_days = sorted(
        [item for item in day_cards if isinstance(item, dict)],
        key=lambda item: _value_to_float(item.get("deficit_kcal")) or -10_000,
        reverse=True,
    )[:3]
    tough_days = sorted(
        [item for item in day_cards if isinstance(item, dict)],
        key=lambda item: _value_to_float(item.get("deficit_kcal")) or 10_000,
    )[:3]
    best_items = [
        f"{_format_cn_day(date.fromisoformat(str(item.get('date'))))} · 热量差 {int(round(_value_to_float(item.get('deficit_kcal')) or 0))} kcal"
        for item in best_days
    ]
    tough_items = [
        f"{_format_cn_day(date.fromisoformat(str(item.get('date'))))} · 热量差 {int(round(_value_to_float(item.get('deficit_kcal')) or 0))} kcal"
        for item in tough_days
    ]
    best_box = (margin, summary_top, width - margin, summary_top + summary_card_height)
    focus_top = best_box[3] + summary_gap
    focus_box = (margin, focus_top, width - margin, focus_top + summary_card_height)
    _draw_period_highlight_card(
        draw,
        box=best_box,
        title="周期亮点",
        title_color=REPORT_GREEN,
        items=best_items,
    )
    _draw_period_highlight_card(
        draw,
        box=focus_box,
        title="需要留意",
        title_color=REPORT_ORANGE,
        items=tough_items,
    )

    output_path = _periodic_report_image_path(member, report_type, period_start, period_end)
    canvas.save(output_path, format="PNG")
    return str(output_path)

def generate_daily_report(db: Session, member: Member, report_date: date) -> DailyReport:
    report_end = datetime.combine(report_date + timedelta(days=1), datetime.min.time()) - timedelta(microseconds=1)
    weight = latest_weight_kg(db, member.id, as_of=report_end)
    bmr = calculate_bmr(member, weight)
    base_tdee = calculate_tdee(member, weight)
    exercise_kcal, exercise_cards = exercise_totals(db, member.id, report_date, weight)
    tdee = round(base_tdee + exercise_kcal, 2) if base_tdee is not None else None
    totals = consumed_totals(db, member.id, report_date)
    macros = macro_percentages(totals)
    macro_target = macro_targets(member, weight, tdee)
    macro_status = macro_progress(totals, macro_target)
    goal_intake_kcal = calculate_goal_intake_kcal(member, tdee)

    start = datetime.combine(report_date, datetime.min.time())
    end = start + timedelta(days=1)
    latest_measurement = db.scalar(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member.id, MeasurementRecord.measured_at >= start, MeasurementRecord.measured_at < end)
        .order_by(MeasurementRecord.measured_at.desc())
    )
    shared_media = db.scalars(
        select(MediaAsset)
        .where(
            MediaAsset.member_id == member.id,
            MediaAsset.captured_at >= start,
            MediaAsset.captured_at < end,
            MediaAsset.is_shared.is_(True),
        )
        .order_by(MediaAsset.captured_at.desc())
    ).all()
    meals = db.scalars(
        select(MealEntry)
        .where(MealEntry.member_id == member.id, MealEntry.consumed_at >= start, MealEntry.consumed_at < end)
        .order_by(MealEntry.consumed_at.asc())
    ).all()

    deficit = round((tdee or 0.0) - totals["kcal"], 2) if tdee is not None else None
    payload = {
        "member_name": member.display_name,
        "report_date": report_date.isoformat(),
        "weight_kg": weight,
        "weight_source": "latest_measurement",
        "latest_measurement": {
            "weight_kg": latest_measurement.weight_kg if latest_measurement else None,
            "body_fat_pct": latest_measurement.body_fat_pct if latest_measurement else None,
        },
        "bmr": bmr,
        "base_tdee": base_tdee,
        "exercise_kcal": exercise_kcal,
        "exercise_cards": exercise_cards,
        "tdee": tdee,
        "goal_deficit_kcal": member.goal_deficit_kcal,
        "goal_intake_kcal": goal_intake_kcal,
        "intake": totals,
        "macro_ratio": macros,
        "macro_target": macro_target,
        "macro_status": macro_status,
        "deficit_kcal": deficit,
        "deficit_hit": deficit is not None and deficit >= member.goal_deficit_kcal,
        "shared_media_paths": [asset.preview_path or asset.original_path for asset in shared_media],
        "shared_media_urls": [
            url
            for asset in shared_media
            if (url := _media_url(asset.preview_path or asset.original_path)) is not None
        ],
        "meal_cards": [
            {
                "meal_slot": meal.meal_slot,
                "food_name": meal.food_name,
                "actual_grams": meal.actual_grams,
                "kcal": meal.kcal,
            }
            for meal in meals
        ],
    }

    report = db.scalar(select(DailyReport).where(DailyReport.member_id == member.id, DailyReport.report_date == report_date))
    if report:
        previous_payload = report.payload if isinstance(report.payload, dict) else {}
        if "_delivery" in previous_payload:
            payload["_delivery"] = previous_payload["_delivery"]
        report.payload = payload
        report.status = "generated"
    else:
        report = DailyReport(member_id=member.id, report_date=report_date, status="generated", payload=payload)
        db.add(report)

    image_path = _render_daily_report_image(member, report)
    report.image_path = image_path
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def report_image_url(report: DailyReport) -> str | None:
    return _report_url(report.image_path)


def periodic_report_image_url(image_path: str | None) -> str | None:
    return _report_url(image_path)


def _weight_window(db: Session, member_id: str, start: datetime, end: datetime) -> list[MeasurementRecord]:
    return db.scalars(
        select(MeasurementRecord)
        .where(MeasurementRecord.member_id == member_id, MeasurementRecord.measured_at >= start, MeasurementRecord.measured_at < end)
        .order_by(MeasurementRecord.measured_at.asc())
    ).all()


def generate_periodic_report(
    db: Session,
    member: Member,
    report_type: str,
    period_start: date,
    period_end: date,
) -> dict:
    effective_end = min(period_end, date.today())
    current = period_start
    reports: list[DailyReport] = []
    while current <= effective_end:
        reports.append(generate_daily_report(db, member, current))
        current += timedelta(days=1)

    total_days = len(reports)
    intake_values = [float((item.payload or {}).get("intake", {}).get("kcal", 0) or 0) for item in reports]
    carb_values = [float((item.payload or {}).get("intake", {}).get("carb_g", 0) or 0) for item in reports]
    fat_values = [float((item.payload or {}).get("intake", {}).get("fat_g", 0) or 0) for item in reports]
    protein_values = [float((item.payload or {}).get("intake", {}).get("protein_g", 0) or 0) for item in reports]
    deficit_values = [float((item.payload or {}).get("deficit_kcal", 0) or 0) for item in reports if (item.payload or {}).get("deficit_kcal") is not None]
    exercise_values = [float((item.payload or {}).get("exercise_kcal", 0) or 0) for item in reports]
    hit_days = sum(1 for item in reports if (item.payload or {}).get("deficit_hit"))

    start_dt = datetime.combine(period_start, datetime.min.time())
    end_dt = datetime.combine(effective_end + timedelta(days=1), datetime.min.time())
    measurements = _weight_window(db, member.id, start_dt, end_dt)
    start_weight = measurements[0].weight_kg if measurements else None
    end_weight = measurements[-1].weight_kg if measurements else None
    weight_change = round(end_weight - start_weight, 2) if start_weight is not None and end_weight is not None else None
    avg_intake = {
        "kcal": round(mean(intake_values), 1) if intake_values else 0,
        "carb_g": round(mean(carb_values), 1) if carb_values else 0,
        "fat_g": round(mean(fat_values), 1) if fat_values else 0,
        "protein_g": round(mean(protein_values), 1) if protein_values else 0,
    }

    payload = {
        "report_type": report_type,
        "period_start": period_start.isoformat(),
        "period_end": effective_end.isoformat(),
        "start_weight_kg": start_weight,
        "end_weight_kg": end_weight,
        "weight_change_kg": weight_change,
        "avg_intake_kcal": avg_intake["kcal"],
        "avg_intake": avg_intake,
        "avg_deficit_kcal": round(mean(deficit_values), 1) if deficit_values else 0,
        "total_exercise_kcal": round(sum(exercise_values), 1),
        "hit_days": hit_days,
        "total_days": total_days,
        "avg_macro_ratio": macro_percentages(avg_intake),
        "day_cards": [
            {
                "date": item.report_date.isoformat(),
                "intake_kcal": float((item.payload or {}).get("intake", {}).get("kcal", 0) or 0),
                "deficit_kcal": (item.payload or {}).get("deficit_kcal"),
                "deficit_hit": bool((item.payload or {}).get("deficit_hit")),
                "weight_kg": (item.payload or {}).get("latest_measurement", {}).get("weight_kg"),
            }
            for item in reports
        ],
    }
    image_path = _render_periodic_report_image(member, report_type, payload, period_start, period_end)
    return {
        "report_type": report_type,
        "period_start": period_start,
        "period_end": effective_end,
        "status": "generated",
        "payload": payload,
        "image_path": image_path,
        "image_url": periodic_report_image_url(image_path),
    }


def _push_daily_report(
    db: Session,
    endpoint: NotificationEndpoint,
    member: Member,
    report_date: date,
    current_time: datetime,
) -> bool:
    report = db.scalar(select(DailyReport).where(DailyReport.member_id == member.id, DailyReport.report_date == report_date))
    if report is None:
        report = generate_daily_report(db, member, report_date)

    image_url = _absolute_url(report_image_url(report))
    if not image_url:
        return False

    return _send_generic_image_message(
        db,
        endpoint,
        member=member,
        report_type="daily",
        title=_daily_title(_resolve_push_user_id(member, endpoint) or member.username, report_date),
        content=DEFAULT_PUSH_CONTENT["daily"],
        image_url=image_url,
        current_time=current_time,
        report_date=report_date,
    )


def _push_periodic_report(
    db: Session,
    endpoint: NotificationEndpoint,
    member: Member,
    *,
    report_type: str,
    period_start: date,
    period_end: date,
    current_time: datetime,
) -> bool:
    report = generate_periodic_report(db, member, report_type, period_start, period_end)
    image_url = _absolute_url(periodic_report_image_url(report.get("image_path")))
    if not image_url:
        return False

    push_user_id = _resolve_push_user_id(member, endpoint) or member.username
    if report_type == "weekly":
        title = _weekly_title(push_user_id, period_start, period_end)
    else:
        title = _monthly_title(push_user_id, period_start)

    return _send_generic_image_message(
        db,
        endpoint,
        member=member,
        report_type=report_type,
        title=title,
        content=DEFAULT_PUSH_CONTENT[report_type],
        image_url=image_url,
        current_time=current_time,
        period_start=period_start,
        period_end=period_end,
    )


def _due_periodic_windows(current_time: datetime, push_hour: int) -> list[tuple[str, date, date]]:
    current_date = current_time.date()
    jobs: list[tuple[str, date, date]] = []

    if current_time.hour != push_hour:
        return jobs

    if current_time.minute == WEEKLY_PUSH_MINUTE and current_time.weekday() == WEEKLY_PUSH_WEEKDAY:
        period_end = current_date - timedelta(days=1)
        period_start = period_end - timedelta(days=period_end.weekday())
        jobs.append(("weekly", period_start, period_end))

    if current_time.minute == MONTHLY_PUSH_MINUTE and current_date.day == MONTHLY_PUSH_DAY:
        period_end = current_date - timedelta(days=1)
        period_start = period_end.replace(day=1)
        jobs.append(("monthly", period_start, period_end))

    return jobs


def push_due_generic_webhooks(db: Session, report_date: date | None = None, now: datetime | None = None) -> int:
    current_time = _as_beijing_datetime(now)
    sent_count = 0
    endpoints = db.scalars(
        select(NotificationEndpoint).where(
            NotificationEndpoint.endpoint_type.in_(("generic_webhook", "wechatbot_webhook")),
            NotificationEndpoint.enabled.is_(True),
        )
    ).all()

    for endpoint in endpoints:
        household = db.get(Household, endpoint.household_id)
        if not household:
            continue

        members = db.scalars(
            select(Member).where(Member.household_id == household.id, Member.is_active.is_(True)).order_by(Member.created_at.asc())
        ).all()

        if report_date is not None:
            for member in members:
                if endpoint.endpoint_type != "generic_webhook":
                    continue
                sent_count += int(_push_daily_report(db, endpoint, member, report_date, current_time))
            continue

        if current_time.hour == household.report_push_hour and current_time.minute == DAILY_PUSH_MINUTE:
            target_report_date = current_time.date() - timedelta(days=1)
            for member in members:
                if endpoint.endpoint_type != "generic_webhook":
                    continue
                sent_count += int(_push_daily_report(db, endpoint, member, target_report_date, current_time))

        if endpoint.endpoint_type != "generic_webhook":
            continue

        for report_type, period_start, period_end in _due_periodic_windows(current_time, household.report_push_hour):
            for member in members:
                sent_count += int(
                    _push_periodic_report(
                        db,
                        endpoint,
                        member,
                        report_type=report_type,
                        period_start=period_start,
                        period_end=period_end,
                        current_time=current_time,
                    )
                )

    return sent_count
