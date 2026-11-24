# syntax=docker/dockerfile:1
#
# PgBouncer for Railway: edoburu/pgbouncer (PgBouncer built from the official
# release tarball on Alpine, with psql), plus
#   - Python 3 from the image's Alpine repository, and
#   - railway-pgbouncer.py (written for this template): writes pgbouncer.ini
#     and userlist.txt from the template variables, runs PgBouncer, and serves
#     a private /healthz on $PORT for Railway's healthcheck (STANDARD 8.34).
#
# Upstream: https://www.pgbouncer.org (ISC licence), image edoburu/pgbouncer
# (MIT), tag v1.26.1-p0 (PgBouncer 1.26.1), pinned by multi-arch index digest
# (checked 2026-11-24).
FROM edoburu/pgbouncer:v1.26.1-p0@sha256:488422e38cff912895d0d65d8963fcd306e6ac589a724398b6eb8e294e94d624

USER root
RUN apk add --no-cache python3 openssl && python3 --version && pgbouncer --version

COPY --chmod=0755 railway-pgbouncer.py /usr/local/bin/railway-pgbouncer.py
RUN python3 -m py_compile /usr/local/bin/railway-pgbouncer.py

# PgBouncer refuses to run as root; the image's postgres user owns /etc/pgbouncer.
USER postgres

ENV PORT=8080
EXPOSE 6432 8080

ENTRYPOINT []
CMD ["python3", "-u", "/usr/local/bin/railway-pgbouncer.py"]
