# NOTICE: PgBouncer template

## Software deployed

| Component | Licence | Source |
|---|---|---|
| PgBouncer 1.26.1 | ISC (© PgBouncer contributors) | https://www.pgbouncer.org, built from the release tarball inside `edoburu/pgbouncer:v1.26.1-p0` |
| edoburu/pgbouncer image (Dockerfile, entrypoint) | MIT (© Diederik van der Boor) | https://github.com/edoburu/docker-pgbouncer, used as base image unmodified; its entrypoint is not used |
| Python 3, OpenSSL | PSF, Apache-2.0 | Alpine Linux packages, installed at build time |
| PostgreSQL 18 | PostgreSQL Licence | Railway's `ghcr.io/railwayapp-templates/postgres-ssl` image |
| PgBouncer logo (listing icon) | from the PgBouncer website repository | https://github.com/pgbouncer/pgbouncer.github.io |

## Written for this template

- `services/pgbouncer/Dockerfile`, `services/pgbouncer/railway-pgbouncer.py` (config generation, health endpoint, process supervision), `template.json`, `README.md`, `TEMPLATE.md`, this file. MIT, © 2026 the template author. The health endpoint follows the same author's GitHub Runner template.

## Upstream sources checked (2026-11-24, read only; nothing was executed locally)

- `edoburu/docker-pgbouncer`: `Dockerfile` (Alpine 3.24, PgBouncer 1.26.1 from pgbouncer.org, `postgres` user owns `/etc/pgbouncer`), `entrypoint.sh`.
- PgBouncer documentation: `config.md` (auth_query default, SCRAM pass-through, `max_prepared_statements`, `listen_addr = *`, TLS settings), `usage.md` (admin console).
- Docker Hub: `edoburu/pgbouncer:v1.26.1-p0` index digest; GHCR: `railwayapp-templates/postgres-ssl:18.7` index digest.

## Market templates reviewed

`OpUzwe` (PgBouncer, `railwayapp/pgbouncer`), `postgres-pgbouncer` (Postgres + PgBouncer), `L09YMd` (PgBouncer for Railway): read for topology and variables only. Nothing was copied.

## Names and affiliation

PostgreSQL is a trademark of the PostgreSQL Community Association. This is a community template, not affiliated with or endorsed by the PgBouncer project or the PostgreSQL Global Development Group.
