from datetime import date

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class RegisterByInviteRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    sex: str = Field(min_length=1, max_length=16)
    birth_year: int = Field(ge=1900, le=2100)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    member_id: str
    household_id: str
    display_name: str
    role: str
    tokens: TokenPair


class InvitationPreviewResponse(BaseModel):
    code: str
    role: str
