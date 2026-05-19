# FamilyCut

[English](README.md) | [中文](README.zh-CN.md)

FamilyCut is a self-hosted family fitness tracker. It combines a FastAPI backend, React admin dashboard, React mobile PWA, and Android client shell for small-group weight, nutrition, exercise, media, and report workflows.


## AI-assisted development

This public release was prepared with Codex using GPT-5.4 and GPT-5.5 assistance. The code, documentation, and release cleanup were reviewed for public sharing, but the project is community-maintained and is not an official OpenAI product.


## Components

- `backend/` - FastAPI service for auth, members, measurements, meals, reports, media, settings, and background jobs
- `admin-web/` - React admin dashboard for household-level management
- `mobile-web/` - React PWA for daily user input
- `android-app/` - Android client shell
- `docs/` - architecture and product notes suitable for public sharing

## Public Repository Scope

This public release contains source code and example configuration only. It intentionally excludes personal health records, uploaded photos, production webhook URLs, database files, and real secrets.

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

Backend only:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Web apps:

```bash
cd admin-web && npm install && npm run dev
cd ../mobile-web && npm install && npm run dev
```

## Development Checks

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm run build
cd ../mobile-web && npm run build
```

## Privacy

Do not commit personal records, images, exported reports, databases, production `.env` files, or notification webhook URLs.

## License

MIT

