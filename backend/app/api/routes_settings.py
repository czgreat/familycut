from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.runtime_migrations import audit_member_username_state
from app.db.session import get_db
from app.models import AiProviderSetting, Household, Member, NotificationEndpoint
from app.schemas.settings import (
    AdminSettingsResponse,
    AdminSettingsUpdate,
    AiConnectionTestRequest,
    AiConnectionTestResponse,
    AiProviderSettingsResponse,
    AiProviderSettingsUpdate,
    NotificationEndpointCreate,
    NotificationEndpointResponse,
    UsernameAuditResponse,
)
from app.services.ai import ResolvedAiProvider, probe_ai_provider
from app.services.reports import generate_daily_report, push_due_generic_webhooks


router = APIRouter(prefix="/settings", tags=["settings"])


def _serialize_ai_provider(setting: AiProviderSetting) -> AiProviderSettingsResponse:
    return AiProviderSettingsResponse(
        base_url=setting.base_url,
        api_key=setting.api_key,
        vision_model=setting.vision_model,
        timeout_sec=setting.timeout_sec,
        enabled=setting.enabled,
        proxy_enabled=setting.proxy_enabled,
        proxy_url=setting.proxy_url,
    )


def _default_ai_provider() -> AiProviderSettingsResponse:
    settings = get_settings()
    return AiProviderSettingsResponse(
        base_url=settings.newapi_base_url or "",
        api_key=settings.newapi_api_key or "",
        vision_model=settings.newapi_vision_model,
        timeout_sec=60,
        enabled=bool(settings.newapi_base_url and settings.newapi_api_key),
        proxy_enabled=settings.newapi_proxy_enabled,
        proxy_url=settings.newapi_proxy_url,
    )


def _find_endpoint(db: Session, household_id: str, endpoint_type: str) -> NotificationEndpoint | None:
    return db.scalar(
        select(NotificationEndpoint).where(
            NotificationEndpoint.household_id == household_id,
            NotificationEndpoint.endpoint_type == endpoint_type,
        )
    )


def _upsert_generic_webhook(db: Session, household_id: str, enabled: bool, target_url: str) -> NotificationEndpoint | None:
    endpoint = _find_endpoint(db, household_id, "generic_webhook")
    cleaned_url = target_url.strip()
    if endpoint:
        endpoint.enabled = enabled and bool(cleaned_url)
        endpoint.target_url = cleaned_url or endpoint.target_url
        db.add(endpoint)
        return endpoint
    if not cleaned_url:
        return None
    endpoint = NotificationEndpoint(
        household_id=household_id,
        endpoint_type="generic_webhook",
        name="默认 generic webhook",
        target_url=cleaned_url,
        enabled=enabled,
    )
    db.add(endpoint)
    return endpoint


def _upsert_wechatbot_webhook(
    db: Session,
    household_id: str,
    enabled: bool,
    base_url: str,
    token: str,
    target: str,
    is_room: bool,
) -> NotificationEndpoint | None:
    endpoint = _find_endpoint(db, household_id, "wechatbot_webhook")
    cleaned_base_url = base_url.strip().rstrip("/")
    cleaned_token = token.strip()
    cleaned_target = target.strip()
    metadata = {
        "token": cleaned_token,
        "target": cleaned_target,
        "is_room": is_room,
    }
    is_configured = bool(cleaned_base_url and cleaned_token and cleaned_target)

    if endpoint:
        endpoint.enabled = enabled and is_configured
        endpoint.target_url = cleaned_base_url or endpoint.target_url
        endpoint.metadata_json = metadata
        db.add(endpoint)
        return endpoint
    if not is_configured:
        return None
    endpoint = NotificationEndpoint(
        household_id=household_id,
        endpoint_type="wechatbot_webhook",
        name="默认 wechatbot webhook",
        target_url=cleaned_base_url,
        enabled=enabled,
        metadata_json=metadata,
    )
    db.add(endpoint)
    return endpoint


@router.get("/ai-provider", response_model=AiProviderSettingsResponse | None)
def get_ai_provider(admin: Member = Depends(require_admin), db: Session = Depends(get_db)) -> AiProviderSettingsResponse | None:
    setting = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == admin.household_id))
    if not setting:
        return _default_ai_provider()
    return _serialize_ai_provider(setting)


@router.put("/ai-provider", response_model=AiProviderSettingsResponse)
def upsert_ai_provider(
    payload: AiProviderSettingsUpdate,
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AiProviderSettingsResponse:
    setting = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == admin.household_id))
    if setting:
        for key, value in payload.model_dump().items():
            setattr(setting, key, value)
    else:
        setting = AiProviderSetting(household_id=admin.household_id, **payload.model_dump())
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return _serialize_ai_provider(setting)


@router.get("/app-config", response_model=AdminSettingsResponse)
def get_app_config(admin: Member = Depends(require_admin), db: Session = Depends(get_db)) -> AdminSettingsResponse:
    household = db.get(Household, admin.household_id)
    ai_provider = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == admin.household_id))
    generic_webhook = _find_endpoint(db, admin.household_id, "generic_webhook")
    wechatbot_webhook = _find_endpoint(db, admin.household_id, "wechatbot_webhook")
    wechat_metadata = (
        wechatbot_webhook.metadata_json
        if wechatbot_webhook is not None and isinstance(wechatbot_webhook.metadata_json, dict)
        else {}
    )
    resolved_ai = _serialize_ai_provider(ai_provider) if ai_provider else _default_ai_provider()

    return AdminSettingsResponse(
        ai_enabled=resolved_ai.enabled,
        ai_base_url=resolved_ai.base_url,
        ai_api_key=resolved_ai.api_key,
        ai_model_name=resolved_ai.vision_model,
        ai_timeout_sec=resolved_ai.timeout_sec,
        ai_proxy_enabled=resolved_ai.proxy_enabled,
        ai_proxy_url=resolved_ai.proxy_url,
        report_generate_hour=household.report_generate_hour if household else 23,
        report_push_hour=household.report_push_hour if household else 10,
        generic_webhook_enabled=generic_webhook.enabled if generic_webhook else False,
        generic_webhook_url=generic_webhook.target_url if generic_webhook else "",
        wechatbot_webhook_enabled=wechatbot_webhook.enabled if wechatbot_webhook else False,
        wechatbot_base_url=wechatbot_webhook.target_url if wechatbot_webhook else "",
        wechatbot_token=str(wechat_metadata.get("token", "")),
        wechatbot_target=str(wechat_metadata.get("target", "")),
        wechatbot_is_room=bool(wechat_metadata.get("is_room", False)),
    )


@router.get("/username-audit", response_model=UsernameAuditResponse)
def get_username_audit(admin: Member = Depends(require_admin), db: Session = Depends(get_db)) -> UsernameAuditResponse:
    del admin
    settings = get_settings()
    audit = audit_member_username_state(db.get_bind())
    duplicate_usernames = audit["duplicate_usernames"]
    return UsernameAuditResponse(
        table_exists=bool(audit["table_exists"]),
        duplicate_usernames=duplicate_usernames,
        has_global_unique_username_constraint=bool(audit["has_global_unique_username_constraint"]),
        has_household_scoped_unique_username_constraint=bool(audit["has_household_scoped_unique_username_constraint"]),
        guard_enabled=settings.enforce_global_unique_username,
        can_enable_guard=bool(audit["table_exists"]) and not duplicate_usernames and bool(audit["has_global_unique_username_constraint"]),
    )


@router.put("/app-config", response_model=AdminSettingsResponse)
def update_app_config(
    payload: AdminSettingsUpdate,
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSettingsResponse:
    household = db.get(Household, admin.household_id)
    if household:
        household.report_generate_hour = payload.report_generate_hour
        household.report_push_hour = payload.report_push_hour
        db.add(household)

    ai_provider = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == admin.household_id))
    if ai_provider:
        ai_provider.base_url = payload.ai_base_url
        ai_provider.api_key = payload.ai_api_key
        ai_provider.vision_model = payload.ai_model_name
        ai_provider.timeout_sec = payload.ai_timeout_sec
        ai_provider.enabled = payload.ai_enabled
        ai_provider.proxy_enabled = payload.ai_proxy_enabled
        ai_provider.proxy_url = payload.ai_proxy_url
    else:
        ai_provider = AiProviderSetting(
            household_id=admin.household_id,
            base_url=payload.ai_base_url,
            api_key=payload.ai_api_key,
            vision_model=payload.ai_model_name,
            timeout_sec=payload.ai_timeout_sec,
            enabled=payload.ai_enabled,
            proxy_enabled=payload.ai_proxy_enabled,
            proxy_url=payload.ai_proxy_url,
        )
        db.add(ai_provider)

    _upsert_generic_webhook(
        db,
        household_id=admin.household_id,
        enabled=payload.generic_webhook_enabled,
        target_url=payload.generic_webhook_url,
    )
    _upsert_wechatbot_webhook(
        db,
        household_id=admin.household_id,
        enabled=payload.wechatbot_webhook_enabled,
        base_url=payload.wechatbot_base_url,
        token=payload.wechatbot_token,
        target=payload.wechatbot_target,
        is_room=payload.wechatbot_is_room,
    )

    db.commit()
    db.refresh(ai_provider)
    return get_app_config(admin=admin, db=db)


@router.post("/tests/ai-connection", response_model=AiConnectionTestResponse)
def test_ai_connection(
    payload: AiConnectionTestRequest,
    admin: Member = Depends(require_admin),
) -> AiConnectionTestResponse:
    provider = ResolvedAiProvider(
        base_url=payload.ai_base_url,
        api_key=payload.ai_api_key,
        model_name=payload.ai_model_name,
        timeout_sec=payload.ai_timeout_sec,
        enabled=True,
        proxy_enabled=payload.ai_proxy_enabled,
        proxy_url=payload.ai_proxy_url,
    )
    result = probe_ai_provider(provider)
    return AiConnectionTestResponse(
        ok=result.ok,
        transport=result.transport,
        model_name=result.model_name,
        detail=result.detail,
        status_code=result.status_code,
    )


@router.post("/notification-endpoints", response_model=NotificationEndpointResponse)
def create_notification_endpoint(
    payload: NotificationEndpointCreate,
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationEndpointResponse:
    endpoint = NotificationEndpoint(household_id=admin.household_id, **payload.model_dump())
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return NotificationEndpointResponse.model_validate(endpoint, from_attributes=True)


@router.get("/notification-endpoints", response_model=list[NotificationEndpointResponse])
def list_notification_endpoints(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[NotificationEndpointResponse]:
    endpoints = db.scalars(
        select(NotificationEndpoint)
        .where(NotificationEndpoint.household_id == admin.household_id)
        .order_by(NotificationEndpoint.created_at.desc())
    ).all()
    return [NotificationEndpointResponse.model_validate(item, from_attributes=True) for item in endpoints]


@router.post("/tests/generate-today-report")
def generate_today_report_test(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    report = generate_daily_report(db, admin, date.today())
    return {
        "ok": True,
        "report_id": report.id,
        "report_date": report.report_date.isoformat(),
        "status": report.status,
        "image_path": report.image_path,
    }


@router.post("/tests/push-today-report")
def push_today_report_test(
    admin: Member = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    household = db.get(Household, admin.household_id)
    if household is None:
        return {"ok": False, "detail": "家庭不存在"}
    report_date = date.today()
    now = datetime.now().replace(hour=household.report_push_hour, minute=0, second=0, microsecond=0)
    sent_count = push_due_generic_webhooks(db, report_date, now=now)
    return {
        "ok": True,
        "report_date": report_date.isoformat(),
        "sent_count": sent_count,
        "push_hour": household.report_push_hour,
    }
