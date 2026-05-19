# Deployment Guide

**Language:** English | [中文](DEPLOYMENT.zh-CN.md)

This guide explains how to run `familycut` locally, in Docker, or with a manual service setup. It assumes you cloned the GitHub repository and are working from the repository root.

## What Is Already Usable

- Run backend with PostgreSQL and Redis through Docker Compose
- Run admin and mobile web apps locally with Vite
- Use backend API docs during local development
- Extend Android shell after configuring your own signing setup

## What You Must Provide

- Your own `.env` with database, JWT, media, reports, and notification settings
- Private storage for media and reports
- A real Android signing configuration if building release APKs
- Your own AI provider key only if AI features are enabled

## Local Development

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

If the command uses `. .venv/bin/activate`, use `.venv\Scripts\Activate.ps1` on Windows PowerShell.

## Docker Deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8000/healthz
```

Before running Docker, review every bind mount and every value in `.env`. Example compose files are intentionally generic and should be adjusted to your host paths and ports.

## Manual Deployment

- Backend: `cd backend && python -m venv .venv && pip install -e ".[dev]" && uvicorn app.main:app --reload`.
- Admin web: `cd admin-web && npm install && npm run dev`.
- Mobile web: `cd mobile-web && npm install && npm run dev`.
- Android: configure local SDK and signing files before building.

## Configuration Checklist

- `DATABASE_URL`, `REDIS_URL`: backend persistence
- `JWT_SECRET`: replace before any real use
- `MEDIA_ROOT`, `REPORTS_ROOT`: private writable storage
- `OPENAI_API_KEY`, `AI_MODEL`: optional AI features
- `CORS_ORIGINS`: frontend origins allowed to call the API

## Validation Checks

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## Production Checklist

- Replace all placeholder secrets before real use.
- Keep private config, generated data, logs, uploaded media, and generated artifacts outside Git.
- Put the service behind a reverse proxy with HTTPS if it is reachable from other devices.
- Add authentication before exposing private APIs beyond localhost.
- Configure backups for any database, state directory, uploaded files, and generated artifacts.
- Read `SECURITY.md` before reporting or triaging security issues.

## Troubleshooting

- Re-check `.env` and volume paths first; most deployment failures are path or permission issues.
- Use the health endpoint listed in `README.md` to separate process startup issues from application behavior.
- Run the validation commands before changing deployment infrastructure.
- When asking an AI assistant for help, include OS, runtime versions, exact command, sanitized logs, and deployment mode.
