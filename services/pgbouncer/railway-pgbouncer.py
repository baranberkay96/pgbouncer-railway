#!/usr/bin/env python3
"""PgBouncer supervisor for Railway (written for this template).

1. Writes /etc/pgbouncer/pgbouncer.ini and userlist.txt from the template
   variables. Deploy-form values never stop the start (STANDARD 8.29): a bad
   number or mode falls back to the default with a warning in the log.
2. Authentication: clients log in with their real Postgres user and password.
   PgBouncer looks the password up in Postgres with auth_query as the
   AUTH_USER (the Postgres superuser by default) and uses SCRAM pass-through,
   so no password list has to be kept in sync.
3. Optional client TLS (PGBOUNCER_CLIENT_TLS=require|allow) with a self-signed
   certificate generated at start, for access through a Railway TCP proxy.
4. Runs PgBouncer as a child and serves GET /healthz on $PORT: 200 while
   PgBouncer accepts connections, with the upstream state in the body.
   The process exits with PgBouncer's exit code, so Railway restarts it.
"""
import http.server
import os
import signal
import socket
import subprocess
import sys
import threading

CONFIG_DIR = "/etc/pgbouncer"
INI = f"{CONFIG_DIR}/pgbouncer.ini"
USERLIST = f"{CONFIG_DIR}/userlist.txt"
TLS_KEY = f"{CONFIG_DIR}/client.key"
TLS_CERT = f"{CONFIG_DIR}/client.crt"
POOL_MODES = ("session", "transaction", "statement")
TLS_MODES = ("disable", "allow", "prefer", "require")
SERVER_TLS_MODES = ("disable", "allow", "prefer", "require", "verify-ca", "verify-full")
AUTH_QUERY = ("SELECT rolname, CASE WHEN rolvaliduntil < now() THEN NULL ELSE rolpassword END "
              "FROM pg_authid WHERE rolname = $1 AND rolcanlogin")


def log(message: str) -> None:
    print(f"railway-pgbouncer: {message}", flush=True)


def env_int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw == "":
        return default
    if raw.isdigit() and low <= int(raw) <= high:
        return int(raw)
    log(f"WARNING: {name}={raw!r} is not a number in {low}..{high}, using {default}")
    return default


def env_choice(name: str, default: str, choices: tuple) -> str:
    raw = os.environ.get(name, "").strip().lower()
    if raw == "":
        return default
    if raw in choices:
        return raw
    log(f"WARNING: {name}={raw!r} is not one of {', '.join(choices)}, using {default}")
    return default


def ini_value(value: str) -> str:
    """Values written to pgbouncer.ini must stay on one line."""
    return value.replace("\n", " ").replace("\r", " ").strip()


def quote_userlist(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def settings() -> dict:
    return {
        "listen_port": env_int("PGBOUNCER_PORT", 6432, 1, 65535),
        "health_port": env_int("PORT", 8080, 1, 65535),
        "db_host": ini_value(os.environ.get("POSTGRES_HOST", "")),
        "db_port": env_int("POSTGRES_PORT", 5432, 1, 65535),
        "auth_user": ini_value(os.environ.get("AUTH_USER", "") or "postgres"),
        "auth_password": os.environ.get("AUTH_PASSWORD", ""),
        "pool_mode": env_choice("PGBOUNCER_POOL_MODE", "transaction", POOL_MODES),
        "max_client_conn": env_int("PGBOUNCER_MAX_CLIENT_CONN", 1000, 1, 100000),
        "default_pool_size": env_int("PGBOUNCER_DEFAULT_POOL_SIZE", 20, 1, 10000),
        "min_pool_size": env_int("PGBOUNCER_MIN_POOL_SIZE", 0, 0, 10000),
        "reserve_pool_size": env_int("PGBOUNCER_RESERVE_POOL_SIZE", 5, 0, 10000),
        "max_db_connections": env_int("PGBOUNCER_MAX_DB_CONNECTIONS", 80, 0, 100000),
        "max_prepared_statements": env_int("PGBOUNCER_MAX_PREPARED_STATEMENTS", 200, 0, 100000),
        "server_idle_timeout": env_int("PGBOUNCER_SERVER_IDLE_TIMEOUT", 600, 0, 86400),
        "query_wait_timeout": env_int("PGBOUNCER_QUERY_WAIT_TIMEOUT", 120, 0, 86400),
        "client_tls": env_choice("PGBOUNCER_CLIENT_TLS", "allow", TLS_MODES),
        "server_tls": env_choice("PGBOUNCER_SERVER_TLS", "disable", SERVER_TLS_MODES),
    }


def write_tls_certificate() -> bool:
    if os.path.exists(TLS_KEY) and os.path.exists(TLS_CERT):
        return True
    result = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
         "-subj", "/CN=pgbouncer", "-keyout", TLS_KEY, "-out", TLS_CERT],
        capture_output=True, text=True)
    if result.returncode != 0:
        log(f"WARNING: could not create a TLS certificate, client TLS disabled: {result.stderr.strip()[:200]}")
        return False
    os.chmod(TLS_KEY, 0o600)
    return True


def write_config(s: dict) -> None:
    if not s["db_host"]:
        log("WARNING: POSTGRES_HOST is empty; PgBouncer starts but cannot reach a database")
    if not s["auth_password"]:
        log("WARNING: AUTH_PASSWORD is empty; logins through PgBouncer will fail until it is set")
    tls = s["client_tls"] != "disable" and write_tls_certificate()
    lines = [
        "[databases]",
        f"* = host={s['db_host'] or '127.0.0.1'} port={s['db_port']}",
        "",
        "[pgbouncer]",
        "listen_addr = *",
        f"listen_port = {s['listen_port']}",
        "unix_socket_dir =",
        "auth_type = scram-sha-256",
        f"auth_file = {USERLIST}",
        f"auth_user = {s['auth_user']}",
        f"auth_query = {AUTH_QUERY}",
        f"admin_users = {s['auth_user']}",
        f"stats_users = {s['auth_user']}",
        f"pool_mode = {s['pool_mode']}",
        f"max_client_conn = {s['max_client_conn']}",
        f"default_pool_size = {s['default_pool_size']}",
        f"min_pool_size = {s['min_pool_size']}",
        f"reserve_pool_size = {s['reserve_pool_size']}",
        "reserve_pool_timeout = 3",
        f"max_db_connections = {s['max_db_connections']}",
        f"max_prepared_statements = {s['max_prepared_statements']}",
        f"server_idle_timeout = {s['server_idle_timeout']}",
        f"query_wait_timeout = {s['query_wait_timeout']}",
        "server_reset_query = DISCARD ALL",
        "ignore_startup_parameters = extra_float_digits",
        "dns_max_ttl = 15",
        f"server_tls_sslmode = {s['server_tls']}",
        "log_connections = 0",
        "log_disconnections = 0",
        "stats_period = 300",
    ]
    if tls:
        lines += [f"client_tls_sslmode = {s['client_tls']}", f"client_tls_key_file = {TLS_KEY}",
                  f"client_tls_cert_file = {TLS_CERT}"]
    with open(INI, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    old = os.umask(0o077)
    try:
        with open(USERLIST, "w", encoding="utf-8") as handle:
            handle.write(f"{quote_userlist(s['auth_user'])} {quote_userlist(s['auth_password'])}\n")
    finally:
        os.umask(old)
    log(f"pool_mode={s['pool_mode']} default_pool_size={s['default_pool_size']} max_client_conn={s['max_client_conn']} "
        f"max_db_connections={s['max_db_connections']} upstream={s['db_host']}:{s['db_port']} "
        f"listen=*:{s['listen_port']} client_tls={'on (' + s['client_tls'] + ')' if tls else 'off'}")


def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def health_server(s: dict) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "railway-pgbouncer-healthz"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] not in ("/healthz", "/"):
                self.send_error(404)
                return
            bouncer = port_open("127.0.0.1", s["listen_port"])
            upstream = bool(s["db_host"]) and port_open(s["db_host"], s["db_port"])
            body = (f"{'ok' if bouncer else 'down'} pgbouncer=" + ("up" if bouncer else "down")
                    + f" upstream={'reachable' if upstream else 'unreachable'}\n").encode()
            self.send_response(200 if bouncer else 503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            return

    class DualStack(http.server.ThreadingHTTPServer):
        address_family = socket.AF_INET6
        daemon_threads = True

        def server_bind(self) -> None:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

    try:
        return DualStack(("::", s["health_port"]), Handler)
    except OSError:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", s["health_port"]), Handler)
        server.daemon_threads = True
        return server


def main() -> int:
    s = settings()
    write_config(s)
    child = subprocess.Popen(["pgbouncer", INI])

    def forward(signum, _frame):
        if child.poll() is None:
            child.send_signal(signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, forward)
    # SIGHUP reloads PgBouncer's config (e.g. after editing the ini by hand).
    signal.signal(signal.SIGHUP, forward)

    server = health_server(s)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"healthcheck on :{s['health_port']}/healthz")
    code = child.wait()
    log(f"pgbouncer exited with code {code}")
    return code if code > 0 else 1 if code < 0 else 0


if __name__ == "__main__":
    sys.exit(main())
