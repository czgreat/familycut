# FamilyCut / 家庭减脂追踪系统

[![CI](https://github.com/czgreat/familycut/actions/workflows/ci.yml/badge.svg)](https://github.com/czgreat/familycut/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**语言：** [English](README.md) | 中文

自托管家庭减脂追踪系统，包含 FastAPI 后端、管理后台、移动端 PWA 和 Android 客户端壳。

## 概览

FamilyCut 是面向家庭私有使用的健康/减脂追踪系统，覆盖体重围度、饮食、运动、照片、报表、邀请、设置和通知流程。

## 主要功能

- FastAPI 后端，包含鉴权、成员、测量、饮食、运动、媒体、报表和设置 API
- React 管理后台用于家庭管理
- React 移动端 PWA 用于日常录入
- Android 客户端壳用于打包实验
- 提供 PostgreSQL 和 Redis 示例部署

## 当前公开版状态

已经可以使用：

- 可通过 Docker Compose 运行后端、PostgreSQL 和 Redis
- 可用 Vite 本地运行管理端和移动端 Web
- 本地开发可使用后端 API 文档
- 配置自己的签名后可继续扩展 Android 壳

需要你在本地补全：

- 自己的 `.env`，包含数据库、JWT、媒体、报表和通知配置
- 用于媒体和报表的私有存储位置
- 如构建 release APK，需要自己的 Android 签名配置
- 只有启用 AI 功能时才需要自己的 AI provider key

## 快速开始

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

如果在 Windows PowerShell 使用 Python 虚拟环境，请用 `.venv\Scripts\Activate.ps1`，不要用 `. .venv/bin/activate`。

## Docker 部署

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8000/healthz
```

## 手工部署

- 后端：`cd backend && python -m venv .venv && pip install -e ".[dev]" && uvicorn app.main:app --reload`。
- 管理端：`cd admin-web && npm install && npm run dev`。
- 移动端 Web：`cd mobile-web && npm install && npm run dev`。
- Android：先配置本机 SDK 和签名文件再构建。

## 配置说明

- `DATABASE_URL`、`REDIS_URL`：后端持久化
- `JWT_SECRET`：真实使用前必须替换
- `MEDIA_ROOT`、`REPORTS_ROOT`：私有可写存储位置
- `OPENAI_API_KEY`、`AI_MODEL`：可选 AI 功能
- `CORS_ORIGINS`：允许调用 API 的前端 origin

## API 概览

- `GET /healthz` 后端健康检查
- `/api/v1/auth/*` 登录和邀请流程
- `/api/v1/members/*` 家庭成员
- `/api/v1/measurements`、`/meals`、`/exercises` 日常数据
- `/api/v1/reports/*` 日报、周报、月报和仪表盘报表

## 验证命令

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## 仓库结构

| 路径 | 说明 |
|---|---|
| `backend/` | FastAPI 服务和测试 |
| `admin-web/` | React 管理后台 |
| `mobile-web/` | React 移动端 PWA |
| `android-app/` | Android 客户端壳 |
| `docs/` | 架构和产品说明 |

## 更多文档

| 主题 | 中文 | English |
|---|---|---|
| 部署 | [docs/DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| AI 接手 | [docs/AI_HANDOFF.zh-CN.md](docs/AI_HANDOFF.zh-CN.md) | [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) |
| 路线图 | [docs/ROADMAP.zh-CN.md](docs/ROADMAP.zh-CN.md) | [docs/ROADMAP.md](docs/ROADMAP.md) |

## AI 辅助开发说明

这个公开版由 Codex 使用 GPT-5.4 和 GPT-5.5 辅助整理完成。源码、文档和公开前清理都经过面向公开分享的复核，但本项目是社区项目，不是 OpenAI 官方产品。

适合继续交给 AI coding assistant 的任务：

- 增加首次运行设置向导
- 增加成员和测量流程端到端测试
- 改进移动端 PWA 离线行为
- 补充备份/恢复操作文档

## 隐私和密钥

不要提交真实 `.env`、API key、webhook secret、cookies、私人媒体、生产数据库、日志、生成产物或个人数据。请从示例配置开始，把私有值保存在 Git 之外。

## License

MIT
