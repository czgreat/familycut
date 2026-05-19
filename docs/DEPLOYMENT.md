# Deployment Guide

Self-hosted family fitness tracker with FastAPI, React admin web, React mobile PWA, and Android shell.

## What is already usable

- Backend, admin web, mobile web, and Android source are present
- Docker example includes Postgres and Redis
- Example environment file is included
- Backend compile check passes

## What you must provide

- Strong JWT secret
- Database and Redis configuration
- A decision on AI nutrition provider
- Optional webhook notification provider
- Android signing keys if publishing APKs

## Local development

```bash
cp .env.example .env
docker compose -f docker-compose.example.yml up --build
```

## Validation checks

```bash
python -m compileall backend/app backend/tests
cd admin-web && npm install && npm run build
cd mobile-web && npm install && npm run build
```

## Docker deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

## Manual deployment

Run Postgres and Redis first, start the backend with uvicorn, then run `admin-web` and `mobile-web` with Vite or build them and serve them behind a reverse proxy.

## Production checklist

- Keep `.env` private and never commit it.
- Replace all placeholder secrets before exposing the service.
- Mount runtime data outside the repository.
- Put the service behind HTTPS if it is reachable from other machines.
- Back up persistent data before upgrades.
- Review logs after the first startup.

