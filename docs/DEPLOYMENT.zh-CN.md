# 部署说明

**语言：** [English](DEPLOYMENT.md) | 中文

本文说明如何在本地、Docker 或手工服务模式下运行 `familycut`。默认你已经 clone 了 GitHub 仓库，并在仓库根目录操作。

## 已经可以使用

- 可通过 Docker Compose 运行后端、PostgreSQL 和 Redis
- 可用 Vite 本地运行管理端和移动端 Web
- 本地开发可使用后端 API 文档
- 配置自己的签名后可继续扩展 Android 壳

## 你需要自己提供

- 自己的 `.env`，包含数据库、JWT、媒体、报表和通知配置
- 用于媒体和报表的私有存储位置
- 如构建 release APK，需要自己的 Android 签名配置
- 只有启用 AI 功能时才需要自己的 AI provider key

## 本地开发

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

如果命令里出现 `. .venv/bin/activate`，Windows PowerShell 下请改用 `.venv\Scripts\Activate.ps1`。

## Docker 部署

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8000/healthz
```

运行 Docker 前，请先检查所有 volume 映射和 `.env`。示例 compose 文件只提供通用起点，需要按你的主机路径和端口修改。

## 手工部署

- 后端：`cd backend && python -m venv .venv && pip install -e ".[dev]" && uvicorn app.main:app --reload`。
- 管理端：`cd admin-web && npm install && npm run dev`。
- 移动端 Web：`cd mobile-web && npm install && npm run dev`。
- Android：先配置本机 SDK 和签名文件再构建。

## 配置检查清单

- `DATABASE_URL`、`REDIS_URL`：后端持久化
- `JWT_SECRET`：真实使用前必须替换
- `MEDIA_ROOT`、`REPORTS_ROOT`：私有可写存储位置
- `OPENAI_API_KEY`、`AI_MODEL`：可选 AI 功能
- `CORS_ORIGINS`：允许调用 API 的前端 origin

## 验证命令

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## 生产检查清单

- 真实使用前替换所有占位密钥。
- 私有配置、生成数据、日志、上传文件和产物不要放进 Git。
- 如果服务会被其他设备访问，请放到启用 HTTPS 的反向代理后面。
- 私有 API 暴露到 localhost 以外前，请先增加鉴权。
- 为数据库、状态目录、上传文件和生成产物配置备份。
- 处理安全问题前先阅读 `SECURITY.md`。

## 排障建议

- 先复查 `.env` 和 volume 路径；多数部署问题来自路径或权限。
- 用 `README.md` 里列出的健康检查接口区分进程启动问题和业务问题。
- 修改部署基础设施前，先跑验证命令。
- 让 AI assistant 帮忙时，提供操作系统、运行时版本、完整命令、去敏日志和部署模式。
