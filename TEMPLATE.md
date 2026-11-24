# PgBouncer 1.26 with PostgreSQL 18: Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **PgBouncer 1.26 with PostgreSQL 18** |
| Description | Postgres 18 behind a PgBouncer connection pool, private and ready to use. (73 chars) |
| Category | Storage |
| Tags | pgbouncer, postgresql, postgres, connection-pooling, database, pooler |
| Icon | `https://cdn.jsdelivr.net/gh/pgbouncer/pgbouncer.github.io/images/pgbouncer-logo.svg` |
| Repo | `baranberkay96/pgbouncer-railway`, service root `/services/pgbouncer` |

## Base market templates (checked 2026-11-24)

| Code | Name | Total deploys | Stack | Problems |
|---|---|---|---|---|
| `OpUzwe` | PgBouncer | 219 | `railwayapp/pgbouncer:latest` (PgBouncer ≤1.24), public TCP proxy | No database; no healthcheck; session mode (little pooling benefit); `latest` |
| `postgres-pgbouncer` | Postgres + PgBouncer | 83 | same image + Postgres 18 with public TCP proxies on both | Both public without TLS on the pooler; no healthcheck |
| `L09YMd` | PgBouncer for Railway | 23 | third-party repo, `AUTH_TYPE=plain` | Plain-text auth, empty required inputs |

Kept: PgBouncer next to a Railway Postgres, pooled URL exposed as a variable, port 6432.

## Improvements over market templates

1. **Healthcheck** (STANDARD 8.34): private `GET /healthz` on `PORT` 8080, 200 while PgBouncer accepts connections, upstream state in the body.
2. **Real auth for every Postgres user**: `auth_type = scram-sha-256` with `auth_query` against `pg_authid` (SCRAM pass-through); no plain-text password list to sync.
3. **Useful defaults**: transaction pooling with `max_prepared_statements = 200`, `max_db_connections = 80` (below Postgres' 100), reserve pool, wait timeout.
4. **Private by default**; optional client TLS with a generated certificate for TCP-proxy access.
5. **PgBouncer 1.26.1** (current), digest-pinned; Postgres 18.7 digest-pinned.
6. Invalid pool values fall back to defaults with a warning (STANDARD 8.29); the process exits with PgBouncer, so Railway restarts it.

## Pinned versions

| Service | Source | Version | Checked |
|---|---|---|---|
| PgBouncer | `edoburu/pgbouncer:v1.26.1-p0@sha256:488422e3…d624` + Alpine `python3`, `openssl` + `railway-pgbouncer.py` | 1.26.1 | 2026-11-24 |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl:18.7@sha256:0abac5c0…7089` | 18.7 | 2026-11-24 |

`python3` and `openssl` come from the Alpine 3.24 repository of the digest-pinned base (unpinned packages within that branch).

## Services

### PgBouncer

- Repo build (`services/pgbouncer/Dockerfile`), runs as the image's `postgres` user; `railway-pgbouncer.py` writes `pgbouncer.ini`/`userlist.txt`, starts PgBouncer and the health server.
- No public domain, no TCP proxy; `PORT=8080` healthcheck `/healthz` (300 s); restart `ON_FAILURE` ×10. Stateless.

### Postgres

Railway base service (`_railway-base/postgres.json` values), volume `/var/lib/postgresql/data`, private only.

## Resource estimate

RESOURCE_PLACEHOLDER

## Verification checklist

CHECKLIST_PLACEHOLDER

## Open questions

- `AUTH_USER` is the Postgres superuser (simplest working `auth_query`); a dedicated low-privilege lookup role with a `SECURITY DEFINER` function is the hardened alternative, documented upstream.
