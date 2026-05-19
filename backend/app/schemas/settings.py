from pydantic import BaseModel, Field


class AiProviderSettingsUpdate(BaseModel):
    base_url: str = Field(min_length=1, max_length=255)
    api_key: str = Field(min_length=1, max_length=255)
    vision_model: str = Field(min_length=1, max_length=120)
    timeout_sec: int = Field(default=60, ge=5, le=300)
    enabled: bool = True
    proxy_enabled: bool = False
    proxy_url: str | None = Field(default=None, max_length=255)


class AiProviderSettingsResponse(BaseModel):
    base_url: str
    api_key: str
    vision_model: str
    timeout_sec: int
    enabled: bool
    proxy_enabled: bool
    proxy_url: str | None


class NotificationEndpointCreate(BaseModel):
    endpoint_type: str = Field(pattern="^(app_inbox|generic_webhook|wechatbot_webhook)$")
    name: str = Field(min_length=1, max_length=64)
    target_url: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    metadata_json: dict | None = None


class NotificationEndpointResponse(BaseModel):
    id: str
    endpoint_type: str
    name: str
    target_url: str
    enabled: bool


class UsernameDuplicateItem(BaseModel):
    username: str
    member_count: int


class UsernameAuditResponse(BaseModel):
    table_exists: bool
    duplicate_usernames: list[UsernameDuplicateItem]
    has_global_unique_username_constraint: bool
    has_household_scoped_unique_username_constraint: bool
    guard_enabled: bool
    can_enable_guard: bool


class AdminSettingsResponse(BaseModel):
    ai_enabled: bool
    ai_base_url: str
    ai_api_key: str
    ai_model_name: str
    ai_timeout_sec: int
    ai_proxy_enabled: bool
    ai_proxy_url: str | None
    report_generate_hour: int
    report_push_hour: int
    generic_webhook_enabled: bool
    generic_webhook_url: str
    wechatbot_webhook_enabled: bool
    wechatbot_base_url: str
    wechatbot_token: str
    wechatbot_target: str
    wechatbot_is_room: bool


class AdminSettingsUpdate(BaseModel):
    ai_enabled: bool = True
    ai_base_url: str = Field(min_length=1, max_length=255)
    ai_api_key: str = Field(min_length=1, max_length=255)
    ai_model_name: str = Field(min_length=1, max_length=120)
    ai_timeout_sec: int = Field(default=60, ge=5, le=300)
    ai_proxy_enabled: bool = False
    ai_proxy_url: str | None = Field(default=None, max_length=255)
    report_generate_hour: int = Field(default=23, ge=0, le=23)
    report_push_hour: int = Field(default=10, ge=0, le=23)
    generic_webhook_enabled: bool = False
    generic_webhook_url: str = Field(default="", max_length=255)
    wechatbot_webhook_enabled: bool = False
    wechatbot_base_url: str = Field(default="", max_length=255)
    wechatbot_token: str = Field(default="", max_length=255)
    wechatbot_target: str = Field(default="", max_length=255)
    wechatbot_is_room: bool = False


class AiConnectionTestRequest(BaseModel):
    ai_base_url: str = Field(min_length=1, max_length=255)
    ai_api_key: str = Field(min_length=1, max_length=255)
    ai_model_name: str = Field(min_length=1, max_length=120)
    ai_timeout_sec: int = Field(default=60, ge=5, le=300)
    ai_proxy_enabled: bool = False
    ai_proxy_url: str | None = Field(default=None, max_length=255)


class AiConnectionTestResponse(BaseModel):
    ok: bool
    transport: str
    model_name: str
    detail: str
    status_code: int | None = None
