"""sitepulse: a lightweight self-hosted website uptime monitor.

Single-file FastAPI backend + SQLite + two static pages (admin console and
a public status page). Design notes live in NOTES.md.
"""
import asyncio
import hashlib
import logging
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("SITEPULSE_DB_PATH", str(BASE_DIR / "data" / "sitepulse.db"))
TOKEN_TTL_SECONDS = 24 * 60 * 60
INITIAL_USERNAME = os.environ.get("SP_INITIAL_USERNAME", "admin")
INITIAL_PASSWORD = os.environ.get("SP_INITIAL_PASSWORD", "admin123")
PROBE_TIMEOUT_SECONDS = 10.0
MIN_INTERVAL_SECONDS = 5
MAX_INTERVAL_SECONDS = 86400
MAX_NAME_LENGTH = 150
MAX_URL_LENGTH = 2048
UPTIME_WINDOW_HOURS = 24

log = logging.getLogger("sitepulse")


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL DEFAULT 60,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                status INTEGER NOT NULL,
                status_code INTEGER,
                response_ms INTEGER,
                error TEXT,
                checked_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_checks_monitor_time
                ON checks(monitor_id, checked_at);
            """
        )
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (INITIAL_USERNAME,)
        ).fetchone()
        if row is None:
            salt = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt,"
                " must_change_password, created_at) VALUES (?, ?, ?, 1, ?)",
                (
                    INITIAL_USERNAME,
                    hash_password(INITIAL_PASSWORD, salt),
                    salt,
                    iso(utcnow()),
                ),
            )


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def probe(url: str, timeout: float = PROBE_TIMEOUT_SECONDS) -> dict:
    """Run one HTTP probe. Up = status 2xx/3xx; anything else (including
    timeouts and connection failures) is down."""
    start = time.perf_counter()
    code = None
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "sitepulse/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            resp.read(1024)
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # URLError, TimeoutError, ssl errors, ...
        reason = getattr(e, "reason", None) or str(e) or e.__class__.__name__
        return {
            "status": 0,
            "status_code": None,
            "response_ms": None,
            "error": str(reason)[:300],
        }
    ms = int((time.perf_counter() - start) * 1000)
    up = code is not None and 200 <= code < 400
    return {
        "status": 1 if up else 0,
        "status_code": code,
        "response_ms": ms,
        "error": None if up else f"HTTP {code}",
    }


def record_check(monitor_id: int, result: dict) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO checks (monitor_id, status, status_code, response_ms,"
            " error, checked_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                monitor_id,
                result["status"],
                result["status_code"],
                result["response_ms"],
                result["error"],
                iso(utcnow()),
            ),
        )
        row = conn.execute(
            "SELECT * FROM checks WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


async def perform_check(monitor_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ?", (monitor_id,)
        ).fetchone()
    if row is None:
        return None
    result = await asyncio.to_thread(probe, row["url"])
    return record_check(monitor_id, result)


async def run_due_probes() -> None:
    now = utcnow()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT m.*, (SELECT MAX(c.checked_at) FROM checks c"
            " WHERE c.monitor_id = m.id) AS last_at"
            " FROM monitors m WHERE m.active = 1"
        ).fetchall()
    due = []
    for row in rows:
        if row["last_at"] is None:
            due.append(row["id"])
            continue
        last = datetime.fromisoformat(row["last_at"])
        if last + timedelta(seconds=row["interval_seconds"]) <= now:
            due.append(row["id"])
    for monitor_id in due:
        await perform_check(monitor_id)


async def scheduler_loop() -> None:
    while True:
        try:
            await run_due_probes()
        except Exception:
            # 调度循环本身必须存活；异常只记录，不吞得无声无息
            log.exception("scheduler round failed")
        await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# app + auth
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = None
    if os.environ.get("SITEPULSE_DISABLE_SCHEDULER") != "1":
        task = asyncio.create_task(scheduler_loop())
    yield
    if task is not None:
        task.cancel()


app = FastAPI(title="sitepulse", lifespan=lifespan)


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class MonitorIn(BaseModel):
    name: str
    url: str
    interval_seconds: int = 60


class MonitorUpdateIn(BaseModel):
    name: str | None = None
    url: str | None = None
    interval_seconds: int | None = None


class ActiveIn(BaseModel):
    active: bool


def current_user(request: Request) -> sqlite3.Row:
    auth = request.headers.get("Authorization", "")
    token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (token, time.time()),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return row


@app.post("/api/login")
def login(body: LoginIn):
    with get_conn() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username,)
        ).fetchone()
        if user is None or hash_password(body.password, user["salt"]) != user["password_hash"]:
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], time.time() + TOKEN_TTL_SECONDS),
        )
    return {
        "token": token,
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


@app.post("/api/logout")
def logout(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""
    if token:
        with get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"ok": True}


@app.post("/api/change-password")
def change_password(
    body: ChangePasswordIn, request: Request, user: sqlite3.Row = Depends(current_user)
):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if hash_password(body.old_password, user["salt"]) != user["password_hash"]:
        raise HTTPException(status_code=400, detail="旧密码不正确")
    salt = secrets.token_hex(16)
    # 本次请求用的令牌：改密成功后吊销除它之外的全部会话（口径第 2 条）。
    # 取不到时不删，避免把自己踢下线。
    auth = request.headers.get("Authorization", "")
    current_token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?,"
            " must_change_password = 0 WHERE id = ?",
            (hash_password(body.new_password, salt), salt, user["id"]),
        )
        if current_token:
            conn.execute(
                "DELETE FROM sessions WHERE user_id = ? AND token != ?",
                (user["id"], current_token),
            )
    return {"ok": True}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(current_user)):
    return {
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


# ---------------------------------------------------------------------------
# monitors
# ---------------------------------------------------------------------------

def validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=400, detail="名称为空或过长")
    return name


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url or len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=400, detail="网址为空或过长")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="只支持 http/https 网址")
    return url


def validate_interval(value: int) -> int:
    if not isinstance(value, int) or not (MIN_INTERVAL_SECONDS <= value <= MAX_INTERVAL_SECONDS):
        raise HTTPException(
            status_code=400,
            detail=f"探测间隔须在 {MIN_INTERVAL_SECONDS} 到 {MAX_INTERVAL_SECONDS} 秒之间",
        )
    return value


def latest_check(conn: sqlite3.Connection, monitor_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM checks WHERE monitor_id = ? ORDER BY checked_at DESC, id DESC"
        " LIMIT 1",
        (monitor_id,),
    ).fetchone()
    return dict(row) if row else None


def uptime_24h(conn: sqlite3.Connection, monitor_id: int) -> float | None:
    cutoff = iso(utcnow() - timedelta(hours=UPTIME_WINDOW_HOURS))
    row = conn.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(status), 0) AS up FROM checks"
        " WHERE monitor_id = ? AND checked_at >= ?",
        (monitor_id, cutoff),
    ).fetchone()
    if not row or row["total"] == 0:
        return None
    return round(row["up"] * 100.0 / row["total"], 1)


def monitor_json(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "interval_seconds": row["interval_seconds"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "latest": latest_check(conn, row["id"]),
        "uptime_24h": uptime_24h(conn, row["id"]),
    }


def get_monitor_row(monitor_id: int) -> sqlite3.Row:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ?", (monitor_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="监控项不存在")
    return row


@app.get("/api/monitors")
def list_monitors(user: sqlite3.Row = Depends(current_user)):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM monitors ORDER BY id").fetchall()
        return [monitor_json(conn, r) for r in rows]


@app.post("/api/monitors")
def create_monitor(body: MonitorIn, user: sqlite3.Row = Depends(current_user)):
    name = validate_name(body.name)
    url = validate_url(body.url)
    interval = validate_interval(body.interval_seconds)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO monitors (name, url, interval_seconds, active, created_at)"
            " VALUES (?, ?, ?, 1, ?)",
            (name, url, interval, iso(utcnow())),
        )
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return monitor_json(conn, row)


@app.get("/api/monitors/{monitor_id}")
def get_monitor(monitor_id: int, user: sqlite3.Row = Depends(current_user)):
    row = get_monitor_row(monitor_id)
    with get_conn() as conn:
        return monitor_json(conn, row)


@app.put("/api/monitors/{monitor_id}")
def update_monitor(
    monitor_id: int, body: MonitorUpdateIn, user: sqlite3.Row = Depends(current_user)
):
    get_monitor_row(monitor_id)
    fields = {}
    if body.name is not None:
        fields["name"] = validate_name(body.name)
    if body.url is not None:
        fields["url"] = validate_url(body.url)
    if body.interval_seconds is not None:
        fields["interval_seconds"] = validate_interval(body.interval_seconds)
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE monitors SET {sets} WHERE id = ?",
                (*fields.values(), monitor_id),
            )
    row = get_monitor_row(monitor_id)
    with get_conn() as conn:
        return monitor_json(conn, row)


@app.post("/api/monitors/{monitor_id}/active")
def set_active(
    monitor_id: int, body: ActiveIn, user: sqlite3.Row = Depends(current_user)
):
    get_monitor_row(monitor_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE monitors SET active = ? WHERE id = ?",
            (1 if body.active else 0, monitor_id),
        )
        row = conn.execute(
            "SELECT * FROM monitors WHERE id = ?", (monitor_id,)
        ).fetchone()
        return monitor_json(conn, row)


@app.delete("/api/monitors/{monitor_id}")
def delete_monitor(monitor_id: int, user: sqlite3.Row = Depends(current_user)):
    get_monitor_row(monitor_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM checks WHERE monitor_id = ?", (monitor_id,))
        conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
    return {"ok": True}


@app.post("/api/monitors/{monitor_id}/check")
async def check_now(monitor_id: int, user: sqlite3.Row = Depends(current_user)):
    get_monitor_row(monitor_id)
    result = await perform_check(monitor_id)
    return result


@app.get("/api/monitors/{monitor_id}/checks")
def list_checks(
    monitor_id: int, limit: int = 50, user: sqlite3.Row = Depends(current_user)
):
    get_monitor_row(monitor_id)
    limit = max(1, min(limit, 500))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM checks WHERE monitor_id = ?"
            " ORDER BY checked_at DESC, id DESC LIMIT ?",
            (monitor_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# public status + pages
# ---------------------------------------------------------------------------

@app.get("/api/public/status")
def public_status():
    """Public, unauthenticated. Only what a visitor needs: monitor name,
    current up/down, latest response time. Never expose URL or error text."""
    items = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM monitors WHERE active = 1 ORDER BY id"
        ).fetchall()
        for row in rows:
            latest = latest_check(conn, row["id"])
            if latest is None:
                status, ms, at = "unknown", None, None
            else:
                status = "up" if latest["status"] == 1 else "down"
                ms, at = latest["response_ms"], latest["checked_at"]
            items.append(
                {"name": row["name"], "status": status,
                 "response_ms": ms, "checked_at": at}
            )
    return {"monitors": items, "generated_at": iso(utcnow())}


@app.get("/")
def index_page():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/status")
def status_page():
    return FileResponse(BASE_DIR / "static" / "status.html")


init_db()

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    uvicorn.run(app, host=host, port=int(os.environ.get("PORT", "8000")))
