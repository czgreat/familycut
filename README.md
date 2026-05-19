# FamilyCut

[![CI](https://github.com/czgreat/familycut/actions/workflows/ci.yml/badge.svg)](https://github.com/czgreat/familycut/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Language:** English | [中文](README.zh-CN.md)

Self-hosted family fitness tracker with a FastAPI backend, admin web app, mobile PWA, and Android client shell.

## Overview

FamilyCut is a private household health and fitness tracker for measurements, meals, exercise, media, reports, invitations, settings, and notification workflows.

## Key Features

- FastAPI backend with auth, members, measurements, meals, exercise, media, reports, and settings APIs
- React admin dashboard for household management
- React mobile PWA for daily input
- Android client shell for packaging experiments
- PostgreSQL and Redis example deployment

## Current Public Release

Ready to use:

- Run backend with PostgreSQL and Redis through Docker Compose
- Run admin and mobile web apps locally with Vite
- Use backend API docs during local development
- Extend Android shell after configuring your own signing setup

You must provide locally:

- Your own `.env` with database, JWT, media, reports, and notification settings
- Private storage for media and reports
- A real Android signing configuration if building release APKs
- Your own AI provider key only if AI features are enabled

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

For Python projects on Windows, activate the virtual environment with `.venv\Scripts\Activate.ps1` instead of `. .venv/bin/activate`.

## Docker Deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8000/healthz
```

## Manual Deployment

- Backend: `cd backend && python -m venv .venv && pip install -e ".[dev]" && uvicorn app.main:app --reload`.
- Admin web: `cd admin-web && npm install && npm run dev`.
- Mobile web: `cd mobile-web && npm install && npm run dev`.
- Android: configure local SDK and signing files before building.

## Configuration

- `DATABASE_URL`, `REDIS_URL`: backend persistence
- `JWT_SECRET`: replace before any real use
- `MEDIA_ROOT`, `REPORTS_ROOT`: private writable storage
- `OPENAI_API_KEY`, `AI_MODEL`: optional AI features
- `CORS_ORIGINS`: frontend origins allowed to call the API

## API Surface

- `GET /healthz` for backend health
- `/api/v1/auth/*` for login and invitation flows
- `/api/v1/members/*` for household members
- `/api/v1/measurements`, `/meals`, `/exercises` for daily data
- `/api/v1/reports/*` for daily, weekly, monthly, and dashboard reports

## Validation

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## Repository Layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI service and tests |
| `admin-web/` | React admin dashboard |
| `mobile-web/` | React mobile PWA |
| `android-app/` | Android client shell |
| `docs/` | Architecture and product notes |

## Documentation

| Topic | English | Chinese |
|---|---|---|
| Deployment | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | [docs/DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md) |
| AI handoff | [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) | [docs/AI_HANDOFF.zh-CN.md](docs/AI_HANDOFF.zh-CN.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) | [docs/ROADMAP.zh-CN.md](docs/ROADMAP.zh-CN.md) |

## AI-Assisted Development

This public release was prepared with Codex using GPT-5.4 and GPT-5.5 assistance. The source code, docs, and public-release cleanup were reviewed for public sharing, but this is a community project and not an official OpenAI product.

Good next tasks for an AI coding assistant:

- Add first-run setup wizard
- Add end-to-end tests for member and measurement flows
- Improve mobile PWA offline behavior
- Document backup/restore operations

## Privacy and Secrets

Do not commit real `.env` files, API keys, webhook secrets, cookies, private media, production databases, logs, generated artifacts, or personal data. Start from the example config files and keep private values outside Git.

## License

MIT
