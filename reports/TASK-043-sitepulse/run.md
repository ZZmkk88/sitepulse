# TASK-043-sitepulse 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-043-sitepulse`。先审查再修 P0/P1。

## 1. 环境探测

命令：`python --version`

输出：
```
Python 3.11.9
```
退出码 0。满足 README「Python 3.10 或更高」。

命令：`git -C E:\muse-bridge\in\TASK-043-sitepulse status --porcelain`

输出：（空，工作区干净）

`.gitignore` 已忽略 `.venv/`、`data/`、`*.db`、`.pytest_cache/`。按 README 在仓库内建 `.venv`。

## 2. 建虚拟环境并装运行依赖

命令（仓库根目录）：
```
python -m venv .venv
.venv\Scripts\python.exe -m pip --version
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

pip 版本输出：`pip 24.0 from E:\muse-bridge\in\TASK-043-sitepulse\.venv\Lib\site-packages\pip (python 3.11)`

`pip install -r requirements.txt` 退出码 0。关键行：
```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.4 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```
钉死版本 fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32 均能装上。

## 3. 装测试依赖

命令：`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`

退出码 0。关键行：
```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 4. pytest（README：`.venv\Scripts\python -m pytest tests/ -q`）

命令：`Set-Location E:\muse-bridge\in\TASK-043-sitepulse; .venv\Scripts\python.exe -m pytest tests/ -q`

退出码 0。输出：
```
................                                                         [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\in\TASK-043-sitepulse\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 1 warning in 5.76s
```

`tests/live_selftest.py` 没有 `test_` 函数，pytest 未执行它。随后单独跑。

## 5. 诊断（工作目录脚本，不改仓库）

### 5.1 会话与连接 `E:\muse-bridge\work\TASK-043-sitepulse\diag.py`

命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\diag.py`

退出码 0。关键输出：
```
CONN before 0
CONN after 20 with-blocks 1
CONN after 10 public requests 1
login 200 200 must True
change 200 {"ok":true}
token1 after change 200 {"username":"admin","must_change_password":false}
token2 after change 200 {"username":"admin","must_change_password":false}
old password 401 new password 200 False
HTTPError before 0
probe 500 result {'status': 0, 'status_code': 500, 'response_ms': 18, 'error': 'HTTP 500'}
HTTPError after 15 probes 0
OK  http://169.254.169.254/latest/meta-data/
OK  http://example.com/\r\nX: y
REJ 'javascript:alert(1)' 只支持 http/https 网址
REJ 'file:///C:/Windows/win.ini' 只支持 http/https 网址
```

说明：改密后签发该用户的两个 token 调 `/api/me` 仍都是 200。`with` 之后仍看到 1 个 Connection，是循环变量 `conn` 仍引用最后一次连接，不能当成泄漏。15 次 HTTP 500 探测后 HTTPError 对象数为 0。

### 5.2 慢 body 与 CRLF `repro_body.py`

命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\repro_body.py`

退出码 0。关键输出：
```
SLOW_BODY {'status': 0, 'status_code': None, 'response_ms': None, 'error': 'timed out'} elapsed 1.004
VALIDATE 'http://127.0.0.1:<port>/\r\nX-Injected: pwned'
PROBE_CRLF {'status': 0, 'status_code': None, 'response_ms': None, 'error': "URL can't contain control characters. '/\\r\\nX-Injected: pwned' (found at least '\\r')"}
RAW_BYTES None
```

先发出 200 头再拖住 body 时，1 秒超时被判为断，且状态码被丢掉。含 CR/LF 的 URL 能通过 `validate_url`，但 urllib 在发出请求前拒绝，对端没收到字节。

## 6. 起服务探活（然后关掉）

命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\smoke.py`

数据库放到 `E:\muse-bridge\work\TASK-043-sitepulse\smoke.db`（`SITEPULSE_DB_PATH`），端口 8000。退出码 0（脚本自身）；服务进程 `terminate` 后 `server_exit 1`（Windows 上结束子进程的常见码，日志里没有 traceback）。

```
homepage_ready True
GET / -> 200 | text/html; charset=utf-8 | <!DOCTYPE html> ... <title>sitepulse · 网站监控台</title>
GET /status -> 200 | text/html; charset=utf-8 | ... <title>服务状态 · sitepulse</title>
GET /api/public/status -> 200 | application/json | {"monitors":[],"generated_at":"2026-10-21T11:59:55+00:00"}
GET /health -> 404 | application/json | {"detail":"Not Found"}
GET /healthz -> 404 | application/json | {"detail":"Not Found"}
GET /docs -> 200 | text/html; charset=utf-8 | ... href="https://cdn.j
GET /openapi.json -> 200 | application/json | {"openapi":"3.1.0","info":{"title":"sitepulse","version":"0.1.0"...
LOGIN 200 must_change True has_token True
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

随后 `netstat -ano -p tcp | findstr ":8000"` 只有 TIME_WAIT，没有 LISTENING。服务已停。对 8000 的阻塞连接超时是 TIME_WAIT 残留，不是仍在监听。

之后再次 `netstat` 时 `127.0.0.1:8000` 被 PID 32492 监听。命令行是另一个任务的 `E:\muse-bridge\work\TASK-044-freshfeeds\serve_once.py`，不是 sitepulse。没有动它。

## 7. live_selftest

命令：`Set-Location E:\muse-bridge\in\TASK-043-sitepulse; .venv\Scripts\python.exe -X utf8 tests\live_selftest.py`

退出码 1。功能检查全部 PASS，清理数据库时抛错：

```
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=1059)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。: 'E:\\muse-bridge\\in\\TASK-043-sitepulse\\tests\\_live_sitepulse.db'
```

堆栈停在 `tests/live_selftest.py:119` 的 `db.unlink()`。example.com 探测成功，不是外网限制。

## 8. 空闲锁库

命令：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\repro_idle_lock.py`

退出码 0。关键行：

```
status 200
login 200
IDLE_UNLINK PermissionError 13 [WinError 32] 另一个程序正在使用此文件，进程无法访问。
cleanup removed db
```

请求已经返回、服务仍在跑时，另一个进程删不掉 sqlite 文件。进程结束后可以删掉。

`row_after_close.py`：连接 `close()` 之后 `sqlite3.Row` 仍能读出字段（`username admin`）。后面把连接改成用完即关，不会弄坏现有的 Row 用法。

## 9. 修复后验证

只改了 `app.py` 的 P0-1、P1-1、P1-2。细节在 `fix-report.md`。

P0-1 之后：

- `pytest tests/ -q`：`16 passed, 1 warning in 4.98s`，退出码 0
- `repro_idle_lock.py`：`IDLE_UNLINK ok (server still up)`，退出码 0
- `tests\live_selftest.py`：`结果： 全部通过`，退出码 0（修复前是 WinError 32）

P1-1 之后：

- `pytest tests/test_app.py::test_change_password_flow tests/test_app.py::test_login_wrong_password tests/test_app.py::test_unauthenticated_rejected -q`：`3 passed, 1 warning in 1.30s`
- `diag.py`：`token2 after change 401`，`token1 after change 200`

P1-2 之后：

- `pwlen.py`：`long_login 401 ... sec 0.041`，`change_long 400 {"detail":"密码过长"}`，`still_old 200`
- 上述三条登录/改密测试：`3 passed, 1 warning in 1.42s`

收尾全量：

- `pytest tests/ -q`：`16 passed, 1 warning in 5.69s`，退出码 0
- `tests\live_selftest.py`：`结果： 全部通过`（真实网站 `code=200 ms=726`），退出码 0

`git -C E:\muse-bridge\in\TASK-043-sitepulse status --porcelain`：

```
 M app.py
```
