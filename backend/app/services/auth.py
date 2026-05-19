from datetime import UTC, date, datetime
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models import AiProviderSetting, Household, Invitation, Member
from app.schemas.auth import AuthResponse, RegisterByInviteRequest, TokenPair


def _members_with_username(db: Session, username: str) -> list[Member]:
    return db.scalars(select(Member).where(Member.username == username).order_by(Member.created_at.asc())).all()


def _members_matching_credentials(db: Session, username: str, password: str) -> list[Member]:
    return [member for member in _members_with_username(db, username) if verify_password(password, member.password_hash)]


def _sync_ai_provider(
    db: Session,
    household_id: str,
    *,
    base_url: str | None,
    api_key: str | None,
    model_name: str,
    proxy_enabled: bool,
    proxy_url: str | None,
) -> bool:
    if not base_url or not api_key:
        return False

    provider = db.scalar(select(AiProviderSetting).where(AiProviderSetting.household_id == household_id))
    if provider is None:
        provider = AiProviderSetting(
            household_id=household_id,
            base_url=base_url,
            api_key=api_key,
            vision_model=model_name,
            timeout_sec=60,
            enabled=True,
            proxy_enabled=proxy_enabled,
            proxy_url=proxy_url,
        )
        db.add(provider)
        return True

    changed = False
    desired_values = {
        "base_url": base_url,
        "api_key": api_key,
        "vision_model": model_name,
        "timeout_sec": 60,
        "enabled": True,
        "proxy_enabled": proxy_enabled,
        "proxy_url": proxy_url,
    }
    for field, value in desired_values.items():
        if getattr(provider, field) != value:
            setattr(provider, field, value)
            changed = True

    if changed:
        db.add(provider)
    return changed


def bootstrap_admin(
    db: Session,
    username: str,
    password: str,
    display_name: str,
    default_report_generate_hour: int,
    default_report_push_hour: int,
) -> None:
    settings = get_settings()
    matches = _members_with_username(db, username)
    existing: Member | None = None
    if len(matches) == 1:
        existing = matches[0]
    elif len(matches) > 1:
        password_matches = _members_matching_credentials(db, username, password)
        if len(password_matches) == 1:
            existing = password_matches[0]
        else:
            # Avoid mutating an ambiguous account if legacy duplicate usernames already exist.
            return

    if existing:
        changed = False
        if existing.display_name != display_name:
            existing.display_name = display_name
            db.add(existing)
            changed = True

        if not verify_password(password, existing.password_hash):
            existing.password_hash = get_password_hash(password)
            db.add(existing)
            changed = True

        household = db.get(Household, existing.household_id)
        desired_household_name = f"{display_name}的家庭"
        if household and household.name != desired_household_name:
            household.name = desired_household_name
            db.add(household)
            changed = True

        if _sync_ai_provider(
            db,
            existing.household_id,
            base_url=settings.newapi_base_url,
            api_key=settings.newapi_api_key,
            model_name=settings.newapi_vision_model,
            proxy_enabled=settings.newapi_proxy_enabled,
            proxy_url=settings.newapi_proxy_url,
        ):
            changed = True

        if changed:
            db.commit()
        return

    household = Household(
        name=f"{display_name}的家庭",
        report_generate_hour=default_report_generate_hour,
        report_push_hour=default_report_push_hour,
    )
    db.add(household)
    db.flush()

    admin = Member(
        household_id=household.id,
        username=username,
        password_hash=get_password_hash(password),
        display_name=display_name,
        role="admin",
    )
    db.add(admin)

    _sync_ai_provider(
        db,
        household.id,
        base_url=settings.newapi_base_url,
        api_key=settings.newapi_api_key,
        model_name=settings.newapi_vision_model,
        proxy_enabled=settings.newapi_proxy_enabled,
        proxy_url=settings.newapi_proxy_url,
    )

    db.commit()


def authenticate(db: Session, username: str, password: str) -> Member:
    matches = _members_matching_credentials(db, username, password)
    if not matches:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if len(matches) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="存在同名且同密码账号，当前无法直接区分，请先联系管理员处理",
        )
    return matches[0]


def issue_auth_response(member: Member) -> AuthResponse:
    return AuthResponse(
        member_id=member.id,
        household_id=member.household_id,
        display_name=member.display_name,
        role=member.role,
        tokens=TokenPair(
            access_token=create_access_token(member.id),
            refresh_token=create_refresh_token(member.id),
        ),
    )


def register_by_invite(db: Session, payload: RegisterByInviteRequest) -> AuthResponse:
    invitation = db.scalar(select(Invitation).where(Invitation.code == payload.code))
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请码不存在")
    if invitation.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已使用")
    if invitation.expires_at and invitation.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已过期")

    existing_member = db.scalar(select(Member).where(Member.username == payload.username))
    if existing_member:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前系统中已存在同名用户")

    member = Member(
        household_id=invitation.household_id,
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
        role=invitation.role,
        sex=payload.sex,
        birthdate=date(payload.birth_year, 1, 1),
    )
    db.add(member)
    db.flush()
    invitation.used_at = datetime.now(UTC)
    invitation.used_by_member_id = member.id
    db.commit()
    db.refresh(member)
    return issue_auth_response(member)


def create_invitation(db: Session, household_id: str, role: str, created_by_member_id: str) -> Invitation:
    invitation = Invitation(
        household_id=household_id,
        role=role,
        code=token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper(),
        created_by_member_id=created_by_member_id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation
