# Deploy and Host PgBouncer with Railway

PgBouncer is the lightweight, battle-tested connection pooler for PostgreSQL. This template deploys PgBouncer 1.26 in front of a PostgreSQL 18 database on Railway's private network, so many app instances, workers or serverless functions can share a small number of real database connections. Point your apps at one pooled URL and you are done.

## About Hosting PgBouncer

Every Postgres connection is a server process that costs memory, and Postgres allows only about 100 by default. Apps with many replicas, background workers or short-lived connections exhaust that quickly. PgBouncer sits between the apps and Postgres, accepts thousands of client connections and hands each transaction a pooled server connection. Hosting it means configuring pools and authentication, keeping it close to the database, and monitoring that it is up. This template generates the PgBouncer configuration from variables, authenticates clients against the real Postgres users (no separate password list), exposes a private health endpoint for Railway, and keeps both services off the public internet.

## Common Use Cases

- Many app replicas or workers sharing one Postgres without hitting `max_connections`
- Serverless or short-lived connections (cron jobs, functions, CLIs) that open a connection per request
- Smoothing connection spikes during deploys and autoscaling
- Pooling an existing Railway Postgres without changing the database
- Watching connection and pool statistics from PgBouncer's admin console

## Dependencies for PgBouncer Hosting

- PgBouncer (`edoburu/pgbouncer` image, built from the official release)
- A PostgreSQL server to pool (bundled: PostgreSQL 18)

### Deployment Dependencies

- PgBouncer documentation: https://www.pgbouncer.org/config.html
- PgBouncer usage and admin console: https://www.pgbouncer.org/usage.html
- Docker image source: https://github.com/edoburu/docker-pgbouncer
- Railway private networking: https://docs.railway.com/guides/private-networking

### Implementation Details

| Service | Image | Purpose | Public |
|---|---|---|---|
| PgBouncer | `edoburu/pgbouncer:v1.26.1-p0` (digest-pinned) + config/health script | Pooler on port 6432, health on 8080 | No (private network only) |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl:18.7` (digest-pinned) | Database, volume `/var/lib/postgresql/data` | No |

**Connect your apps**: set your app's database variable to `${{PgBouncer.DATABASE_URL}}`, which is `postgresql://{user}:{password}@pgbouncer.railway.internal:6432/{database}`. Any Postgres user and database works through the pooler with its normal password: PgBouncer looks passwords up in Postgres (`auth_query`, SCRAM pass-through), so new users need no extra setup. Run migrations directly against `${{Postgres.DATABASE_URL}}`: migration tools often rely on session features (advisory locks) that transaction pooling does not keep.

**Pool settings** (variables on the PgBouncer service, applied at the next deploy; invalid values fall back to the default with a log warning):

| Variable | Default | Meaning |
|---|---|---|
| `PGBOUNCER_POOL_MODE` | `transaction` | Server connection is released after each transaction. Use `session` for apps that need session state (LISTEN/NOTIFY, advisory locks, `SET` without `LOCAL`). |
| `PGBOUNCER_DEFAULT_POOL_SIZE` | `20` | Server connections per database/user pair |
| `PGBOUNCER_MAX_DB_CONNECTIONS` | `80` | Cap per database; keep it below Postgres `max_connections` (100) |
| `PGBOUNCER_RESERVE_POOL_SIZE` | `5` | Extra connections for bursts |
| `PGBOUNCER_MAX_CLIENT_CONN` | `1000` | Total client connections accepted |
| `PGBOUNCER_MAX_PREPARED_STATEMENTS` | `200` | Prepared statements work in transaction mode |
| `PGBOUNCER_QUERY_WAIT_TIMEOUT` | `120` | Seconds a client may wait for a free connection |

**Admin console**: from a service in the project, `psql "postgresql://postgres:{password}@pgbouncer.railway.internal:6432/pgbouncer" -c "SHOW POOLS"` (also `SHOW STATS`, `SHOW CLIENTS`).

**Health**: `GET /healthz` on port 8080 (private) answers 200 while PgBouncer accepts connections and reports whether Postgres is reachable.

**Pool an existing Railway Postgres**: set `POSTGRES_HOST` to that service's private domain (`${{OtherPostgres.RAILWAY_PRIVATE_DOMAIN}}`), and `AUTH_USER` / `AUTH_PASSWORD` to its superuser credentials; then delete the bundled Postgres if you do not need it. For a database outside Railway set `PGBOUNCER_SERVER_TLS=require`.

**Access from outside Railway**: add a TCP proxy to the PgBouncer service (port 6432) and set `PGBOUNCER_CLIENT_TLS=require`; clients then connect with `sslmode=require` (the certificate is self-signed).

**Scaling and upgrades**: PgBouncer is single-threaded and handles thousands of clients per instance; raise pool sizes before adding instances. To upgrade, change the image tag and digest in `services/pgbouncer/Dockerfile` of your repo copy.

This is a community template and is not affiliated with the PgBouncer project or the PostgreSQL Global Development Group.

### Why Deploy PgBouncer on Railway?

Railway runs PgBouncer next to your database on a private network, with healthchecks, logs and restarts handled for you. Your apps get a pooled connection string by reference, and you can scale app replicas without running out of Postgres connections.
