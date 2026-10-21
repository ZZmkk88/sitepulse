"""sitepulse automated tests.

A local fake HTTP server stands in for monitored sites so up / down /
timeout / redirect behaviour is tested deterministically, with no
dependence on the real internet.
"""
import http.server
import os
import socket
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "tests" / "_test_sitepulse.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["SITEPULSE_DB_PATH"] = str(TEST_DB)
os.environ["SITEPULSE_DISABLE_SCHEDULER"] = "1"

import app as sp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(sp.app)


# ---------------------------------------------------------------------------
# fake monitored site
# ---------------------------------------------------------------------------

class FakeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def do_GET(self):
        if self.path == "/ok":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/err":
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/redir":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/slow":
            time.sleep(3)
            try:
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


@pytest.fixture(scope="session")
def fake_site():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def closed_port_url():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}/"


@pytest.fixture(scope="session")
def auth():
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def make_monitor(auth, fake_site, **kw):
    url = kw.get("url") or (fake_site + "/ok")
    body = {"name": kw.get("name", "假站-正常"),
            "url": url,
            "interval_seconds": kw.get("interval_seconds", 60)}
    r = client.post("/api/monitors", json=body, headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

def test_login_wrong_password():
    r = client.post("/api/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_login_ok_marks_must_change(auth):
    r = client.get("/api/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_unauthenticated_rejected():
    assert client.get("/api/monitors").status_code == 401
    assert client.get("/api/monitors", headers={"Authorization": "Bearer bad"}).status_code == 401


# ---------------------------------------------------------------------------
# monitor CRUD + validation
# ---------------------------------------------------------------------------

def test_create_and_list(auth, fake_site):
    m = make_monitor(auth, fake_site, name="官网站点")
    assert m["active"] is True and m["latest"] is None and m["uptime_24h"] is None
    lst = client.get("/api/monitors", headers=auth).json()
    assert any(x["id"] == m["id"] for x in lst)


def test_create_validation(auth, fake_site):
    bad_url = client.post("/api/monitors", headers=auth,
                          json={"name": "x", "url": "ftp://a.com", "interval_seconds": 60})
    assert bad_url.status_code == 400
    bad_interval = client.post("/api/monitors", headers=auth,
                               json={"name": "x", "url": fake_site + "/ok", "interval_seconds": 1})
    assert bad_interval.status_code == 400
    empty_name = client.post("/api/monitors", headers=auth,
                             json={"name": "  ", "url": fake_site + "/ok", "interval_seconds": 60})
    assert empty_name.status_code == 400


def test_update_and_toggle(auth, fake_site):
    m = make_monitor(auth, fake_site, name="待改")
    r = client.put(f"/api/monitors/{m['id']}", headers=auth,
                   json={"name": "改好了", "interval_seconds": 120})
    assert r.status_code == 200 and r.json()["name"] == "改好了"
    assert r.json()["interval_seconds"] == 120
    r = client.post(f"/api/monitors/{m['id']}/active", headers=auth, json={"active": False})
    assert r.json()["active"] is False
    r = client.post(f"/api/monitors/{m['id']}/active", headers=auth, json={"active": True})
    assert r.json()["active"] is True
    assert client.get("/api/monitors/999999", headers=auth).status_code == 404


# ---------------------------------------------------------------------------
# probing against the fake site
# ---------------------------------------------------------------------------

def test_check_up(auth, fake_site):
    m = make_monitor(auth, fake_site, name="通的")
    r = client.post(f"/api/monitors/{m['id']}/check", headers=auth)
    assert r.status_code == 200
    c = r.json()
    assert c["status"] == 1 and c["status_code"] == 200 and c["response_ms"] is not None
    hist = client.get(f"/api/monitors/{m['id']}/checks", headers=auth).json()
    assert len(hist) == 1 and hist[0]["id"] == c["id"]
    detail = client.get(f"/api/monitors/{m['id']}", headers=auth).json()
    assert detail["latest"]["status"] == 1 and detail["uptime_24h"] == 100.0


def test_check_redirect_counts_up(auth, fake_site):
    m = make_monitor(auth, fake_site, name="跳转", url=fake_site + "/redir")
    c = client.post(f"/api/monitors/{m['id']}/check", headers=auth).json()
    assert c["status"] == 1 and c["status_code"] == 200


def test_check_http500_down(auth, fake_site):
    m = make_monitor(auth, fake_site, name="五百", url=fake_site + "/err")
    c = client.post(f"/api/monitors/{m['id']}/check", headers=auth).json()
    assert c["status"] == 0 and c["status_code"] == 500 and c["error"] == "HTTP 500"


def test_check_connection_refused_down(auth):
    m = make_monitor(auth, None, name="拒连", url=closed_port_url())
    c = client.post(f"/api/monitors/{m['id']}/check", headers=auth).json()
    assert c["status"] == 0 and c["status_code"] is None and c["error"]


def test_probe_timeout_down(fake_site):
    result = sp.probe(fake_site + "/slow", timeout=1)
    assert result["status"] == 0 and result["status_code"] is None
    assert result["error"]  # carries a timeout / read error description


# ---------------------------------------------------------------------------
# uptime math (seeded history)
# ---------------------------------------------------------------------------

def test_uptime_24h_math(auth, fake_site):
    m = make_monitor(auth, fake_site, name="算可用率")
    now = sp.utcnow()
    rows = []
    for i, st in enumerate([1, 1, 1, 0]):        # within 24h: 3 up / 1 down
        rows.append((m["id"], st, 200 if st else 500, 10, None if st else "HTTP 500",
                     sp.iso(now - timedelta(hours=1, minutes=i))))
    rows.append((m["id"], 1, 200, 10, None, sp.iso(now - timedelta(hours=30))))  # outside window
    with sp.get_conn() as conn:
        conn.executemany(
            "INSERT INTO checks (monitor_id, status, status_code, response_ms,"
            " error, checked_at) VALUES (?, ?, ?, ?, ?, ?)", rows)
    detail = client.get(f"/api/monitors/{m['id']}", headers=auth).json()
    assert detail["uptime_24h"] == 75.0


# ---------------------------------------------------------------------------
# public status page
# ---------------------------------------------------------------------------

def test_public_status_no_auth_no_leak(auth, fake_site):
    m = make_monitor(auth, fake_site, name="公开演示")
    client.post(f"/api/monitors/{m['id']}/check", headers=auth)
    r = client.get("/api/public/status")  # no Authorization header at all
    assert r.status_code == 200
    items = [x for x in r.json()["monitors"] if x["name"] == "公开演示"]
    assert items and items[0]["status"] == "up"
    assert set(items[0].keys()) == {"name", "status", "response_ms", "checked_at"}
    assert "error" not in r.text and fake_site not in r.text  # no URL / error leak
    page = client.get("/status")
    assert page.status_code == 200 and "服务状态" in page.text


def test_public_status_excludes_paused(auth, fake_site):
    m = make_monitor(auth, fake_site, name="暂停不公开")
    client.post(f"/api/monitors/{m['id']}/active", headers=auth, json={"active": False})
    names = [x["name"] for x in client.get("/api/public/status").json()["monitors"]]
    assert "暂停不公开" not in names


# ---------------------------------------------------------------------------
# delete + password change (password test last: it rotates the admin password)
# ---------------------------------------------------------------------------

def test_delete_monitor(auth, fake_site):
    m = make_monitor(auth, fake_site, name="删我")
    client.post(f"/api/monitors/{m['id']}/check", headers=auth)
    r = client.delete(f"/api/monitors/{m['id']}", headers=auth)
    assert r.status_code == 200
    assert client.get(f"/api/monitors/{m['id']}", headers=auth).status_code == 404
    with sp.get_conn() as conn:
        left = conn.execute("SELECT COUNT(*) c FROM checks WHERE monitor_id = ?",
                            (m["id"],)).fetchone()["c"]
    assert left == 0


def test_change_password_flow():
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    bad = client.post("/api/change-password", headers=h,
                      json={"old_password": "wrong", "new_password": "newpass1"})
    assert bad.status_code == 400
    ok = client.post("/api/change-password", headers=h,
                     json={"old_password": "admin123", "new_password": "newpass1"})
    assert ok.status_code == 200
    assert client.post("/api/login",
                       json={"username": "admin", "password": "admin123"}).status_code == 401
    r2 = client.post("/api/login", json={"username": "admin", "password": "newpass1"})
    assert r2.status_code == 200 and r2.json()["must_change_password"] is False
