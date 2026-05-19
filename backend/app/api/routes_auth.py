from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Invitation
from app.schemas.auth import AuthResponse, InvitationPreviewResponse, LoginRequest, RegisterByInviteRequest
from app.services.auth import authenticate, issue_auth_response, register_by_invite


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    member = authenticate(db, payload.username, payload.password)
    return issue_auth_response(member)


@router.post("/register-by-invite", response_model=AuthResponse)
def register(payload: RegisterByInviteRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return register_by_invite(db, payload)


@router.get("/invite-preview/{code}", response_model=InvitationPreviewResponse)
def invite_preview(code: str, db: Session = Depends(get_db)) -> InvitationPreviewResponse:
    invitation = db.scalar(select(Invitation).where(Invitation.code == code))
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请码不存在")
    if invitation.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已使用")
    return InvitationPreviewResponse(code=invitation.code, role=invitation.role)
