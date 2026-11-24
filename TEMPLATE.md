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

Measured on the test deploy (2026-11-24, idle after 40 parallel clients): PgBouncer 22 MiB (PgBouncer + Python health server), Postgres ~115 MiB, CPU < 0.01 vCPU.

| Service | Idle RAM | Typical RAM | CPU |
|---|---|---|---|
| PgBouncer | 22 MB | 30-80 MB (thousands of clients) | < 0.01 idle, ~0.1-0.5 under heavy load (single-threaded) |
| Postgres | 115 MB | 200 MB-1 GB+ (20-80 pooled server connections) | 0.01-1 |

Estimated cost: idle ≈ $1.5/month (0.14 GB RAM + ~0.3 GB volume); typical ≈ $5-15/month (mostly Postgres). Minimum plan: **Trial** (both far under 1 GB).

## Verification checklist

- [x] Both services SUCCESS; Railway healthcheck `/healthz` on 8080 passed (no public domain).
- [x] Test TCP proxy to 6432 (test only, the template has none): `psql sslmode=require` as `postgres` → PostgreSQL 18.7 through PgBouncer 1.26.1, TLS with the generated certificate.
- [x] Created a new role `handson` in Postgres; it logged in through PgBouncer with its own password (auth_query + SCRAM pass-through) and inserted a row; wrong password → `SASL authentication failed`.
- [x] 40 parallel clients served by 20 server connections (`SHOW POOLS`: `sv_idle 20`, transaction mode); `pg_stat_activity` 21 client backends.
- [x] Admin console `SHOW POOLS` / `SHOW VERSION` as `postgres` on database `pgbouncer`.
- [x] `PGBOUNCER_POOL_MODE=bogus`, `PGBOUNCER_DEFAULT_POOL_SIZE=abc` (STANDARD 8.29): deploy SUCCESS, warnings, defaults used.
- [x] `PGBOUNCER_CLIENT_TLS=require`: `sslmode=disable` refused ("SSL required"), `sslmode=require` works.
- [x] Post-publish deploy by the real template id: PASS (2026-11-24).

## Open questions

- `AUTH_USER` is the Postgres superuser (simplest working `auth_query`); a dedicated low-privilege lookup role with a `SECURITY DEFINER` function is the hardened alternative, documented upstream.
