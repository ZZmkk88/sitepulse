"""sitepulse live self-test.

Starts the real server (scheduler enabled) against a throwaway DB, then
drives the full flow over HTTP: login -> add a real website and a dead
address -> manual probes -> wait for the background scheduler to fire on
its own -> verify up/down verdicts, uptime and the public status page.

Run:  .venv/bin/python tests/live_selftest.py
Exit code 0 = all checks passed.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def call(base, method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    db = ROOT / "tests" / "_live_sitepulse.db"
    if db.exists():
        db.unlink()
    env = dict(os.environ, SITEPULSE_DB_PATH=str(db), PORT=str(port))
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py")],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    failures = []

    def check(label, cond, extra=""):
        print(("PASS " if cond else "FAIL ") + label + (f" ({extra})" if extra else ""))
        if not cond:
            failures.append(label)

    try:
        # wait for server
        up = False
        for _ in range(50):
            try:
                with urllib.request.urlopen(base + "/status", timeout=2) as r:
                    up = r.status == 200
                    break
            except Exception:
                time.sleep(0.3)
        check("服务器启动且状态页可打开", up)

        _, login = call(base, "POST", "/api/login",
                        {"username": "admin", "password": "admin123"})
        token = login.get("token")
        check("登录成功且提示改密", bool(token) and login.get("must_change_password") is True)

        _, a = call(base, "POST", "/api/monitors",
                    {"name": "真实站点", "url": "https://example.com",
                     "interval_seconds": 5}, token)
        _, b = call(base, "POST", "/api/monitors",
                    {"name": "不存在的地址", "url": f"http://127.0.0.1:{free_port()}/",
                     "interval_seconds": 5}, token)
        check("两个监控项创建成功", bool(a.get("id")) and bool(b.get("id")))

        _, ca = call(base, "POST", f"/api/monitors/{a['id']}/check", token=token)
        check("真实网站判通", ca.get("status") == 1 and ca.get("status_code") == 200,
              f"code={ca.get('status_code')} ms={ca.get('response_ms')}")
        _, cb = call(base, "POST", f"/api/monitors/{b['id']}/check", token=token)
        check("死地址判断且有失败原因", cb.get("status") == 0 and bool(cb.get("error")),
              f"error={cb.get('error')}")

        time.sleep(7)  # let the in-process scheduler run by itself
        _, hist = call(base, "GET", f"/api/monitors/{a['id']}/checks?limit=10", token=token)
        check("后台调度器已自动探测（记录数 >= 2）", isinstance(hist, list) and len(hist) >= 2,
              f"count={len(hist) if isinstance(hist, list) else '?'}")

        _, detail = call(base, "GET", f"/api/monitors/{a['id']}", token=token)
        check("真实站点 24h 可用率 100%", detail.get("uptime_24h") == 100.0,
              f"uptime={detail.get('uptime_24h')}")

        code, pub = call(base, "GET", "/api/public/status")
        names = {m["name"]: m["status"] for m in pub.get("monitors", [])}
        check("公开状态接口免登录且结论正确",
              code == 200 and names.get("真实站点") == "up"
              and names.get("不存在的地址") == "down", f"{names}")
        with urllib.request.urlopen(base + "/api/public/status", timeout=5) as r:
            raw = r.read().decode()
        check("公开接口不泄露网址", "example.com" not in raw and "127.0.0.1" not in raw)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if db.exists():
            db.unlink()

    print("\n结果：", "全部通过" if not failures else f"{len(failures)} 项失败 {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
