# Roadmap

This public release is a cleaned, source-focused baseline. It is intended to be usable by developers, but each deployment still needs local configuration.

## Complete enough to use

- Backend, admin web, mobile web, and Android source are present
- Docker example includes Postgres and Redis
- Example environment file is included
- Backend compile check passes

## Needs local completion

- Strong JWT secret
- Database and Redis configuration
- A decision on AI nutrition provider
- Optional webhook notification provider
- Android signing keys if publishing APKs

## Suggested improvements

- Create seed/demo data that contains no personal information
- Add screenshots for admin and mobile flows
- Harden production auth and rate limits
- Prepare Android release signing docs for a chosen store/channel

## Documentation still worth adding

- Real screenshots or short demo videos.
- A known-good production deployment example for a generic Linux host.
- Troubleshooting notes collected from real user deployments.

