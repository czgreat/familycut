# FamilyCut / 家庭减脂追踪系统

[English](README.md) | [中文](README.zh-CN.md)

FamilyCut 是一个自托管家庭健康/减脂追踪系统，包含 FastAPI 后端、React 管理后台、React 移动端 PWA 和 Android 客户端壳，用于小范围成员的体重、饮食、运动、媒体和日报流程。


## AI 辅助开发说明

这个公开版由 Codex 在 GPT-5.4 / GPT-5.5 辅助下整理完成。代码、文档和公开前清理已按公开仓库标准处理，但本项目不是 OpenAI 官方产品。


## 组成

- `backend/` - FastAPI 服务，负责登录、成员、体重、餐食、日报、媒体、设置和后台任务
- `admin-web/` - React 管理后台，用于家庭/小组管理
- `mobile-web/` - React PWA，用于日常录入
- `android-app/` - Android 客户端壳
- `docs/` - 可公开的架构和产品说明

## 公开版范围

这个公开版只包含源码和示例配置，不包含个人健康记录、自拍/上传图片、生产 webhook、数据库文件或真实密钥。

## 快速开始

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

仅启动后端：

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

前端开发：

```bash
cd admin-web && npm install && npm run dev
cd ../mobile-web && npm install && npm run dev
```

## 开发检查

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## 隐私说明

不要提交个人记录、图片、导出报告、数据库、生产 `.env` 或通知 webhook 地址。

## License

MIT

