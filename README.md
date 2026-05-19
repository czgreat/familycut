# FamilyCut

FamilyCut is a small self-hosted family fitness tracker with a FastAPI backend, React admin UI, React mobile PWA, and an Android client shell.

## Components

- `backend/` - FastAPI service for members, measurements, meal records, reports, and notifications
- `admin-web/` - React admin dashboard
- `mobile-web/` - React PWA for daily user input
- `android-app/` - Android client shell

## Public Demo Defaults

This public repository contains code and example configuration only. It does not include personal health data, uploaded photos, production webhook URLs, or real secrets.

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

## Development

Backend checks:

```bash
cd backend
python -m compileall app tests
```

Frontend builds:

```bash
cd admin-web && npm install && npm run build
cd ../mobile-web && npm install && npm run build
```
