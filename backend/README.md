# Backend

FastAPI 服务端负责：

- 家庭与成员账号
- 体重、体脂、自拍、饮食记录
- AI 营养表识别草稿
- 每日日报汇总与推送计划
- Home Assistant webhook 预留接入

## 本地运行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

## 关键接口

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register-by-invite`
- `GET /api/v1/members/me`
- `PUT /api/v1/members/me`
- `POST /api/v1/measurements`
- `GET /api/v1/measurements`
- `POST /api/v1/nutrition/drafts`
- `POST /api/v1/meals`
- `POST /api/v1/media/selfies`
- `GET /api/v1/reports/daily/{date}`
- `POST /api/v1/integrations/ha/measurements`

## 环境变量

从仓库根目录复制 `.env.example` 为 `.env`，或直接在部署环境中注入同名变量。

- `APP_ENFORCE_GLOBAL_UNIQUE_USERNAME=false`
  - 默认关闭
  - 只有在 live 已清理重复用户名、并且数据库已落好 `members.username` 全局唯一索引后，才改成 `true`

## 用户名审计

用户名 rollout 采用“先审计、后清洗、再开护栏”的顺序：

```bash
python3 scripts/audit_member_usernames.py
python3 scripts/audit_member_usernames.py --require-global-unique --output dist/member-username-audit.json
```

更完整的上线步骤见：

- `docs/global-username-rollout.md`
