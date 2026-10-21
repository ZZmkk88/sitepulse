# TASK-033-sitepulse 执行记录

开工时间: 2026-10-21
工作目录: E:\muse-bridge\in\TASK-033-sitepulse
执行方: Grok Build（本地验收）

虚拟环境放在工作目录 `E:\muse-bridge\work\TASK-033-sitepulse\venv`，不写进仓库（仓库 .gitignore 只忽略 `.venv/`，写进仓库会污染 git status）。

## 1. Python 版本

命令:

```
python --version
```

输出:

```
Python 3.11.9
```

满足 README「Python 3.10 或更高版本」。

## 2. 创建虚拟环境

命令:

```
python -m venv E:\muse-bridge\work\TASK-033-sitepulse\venv
```

退出码: 0

## 3. 安装运行依赖

命令:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-033-sitepulse\requirements.txt
```

输出摘要（退出码 0）:

```
Collecting fastapi==0.156.4
Collecting uvicorn==0.54.0
Collecting python-multipart==0.0.32
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.4 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

版本钉死的三个包均能装上，无依赖冲突。

## 4. 安装测试依赖

命令:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-033-sitepulse\requirements-dev.txt
```

输出摘要（退出码 0）:

```
Collecting httpx==0.28.1
Collecting pytest==9.1.1
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 5. pytest 全量（首次，修复前）

命令（工作目录 `E:\muse-bridge\in\TASK-033-sitepulse`）:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

输出:

```
................                                                         [100%]
============================== warnings summary ===============================
..\..\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 1 warning in 5.04s
```

退出码: 0。16 项通过。警告来自依赖（starlette TestClient 弃用 httpx），不是断言失败。

## 6. live_selftest.py（首次）

命令（工作目录 `E:\muse-bridge\in\TASK-033-sitepulse`）:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe tests\live_selftest.py
```

输出:

```
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=692)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址
Traceback (most recent call last):
  File "E:\muse-bridge\in\TASK-033-sitepulse\tests\live_selftest.py", line 126, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "E:\muse-bridge\in\TASK-033-sitepulse\tests\live_selftest.py", line 119, in main
    db.unlink()
  File "C:\Users\xzm\AppData\Local\Programs\Python\Python311\Lib\pathlib.py", line 1147, in unlink
    os.unlink(self)
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。: 'E:\\muse-bridge\\in\\TASK-033-sitepulse\\tests\\_live_sitepulse.db'
```

退出码: 1。9 项功能检查全部 PASS。失败发生在 finally 清理数据库文件（Windows 共享冲突），不是探测逻辑失败。example.com 返回 200，不记为环境限制。

随后用工作目录脚本确认该 db 已不再被占用，并删掉这个测试残留文件（`*.db` 已被仓库 .gitignore 忽略）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\diag_lock.py
```

输出:

```
exists True size 36864
-wal False
-shm False
-journal False
sqlite_open ok (2,)
remove ok
```

进程退出后文件可以打开并删除，说明是退出瞬间的占用，不是服务一直没关。

## 7. 按 README 起服务并探测（修复前）

数据库放到工作目录，避免在仓库里生成 `data/sitepulse.db`。脚本：`E:\muse-bridge\work\TASK-033-sitepulse\smoke_server.py`。

命令:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\smoke_server.py
```

输出片段:

```
starting port 8000
pid 5172
homepage_up True
GET / -> 200 type=text/html; charset=utf-8 server=uvicorn
<title>sitepulse · 网站监控台</title>
GET /status -> 200 type=text/html; charset=utf-8 server=uvicorn
<title>服务状态 · sitepulse</title>
GET /health -> 404 {"detail":"Not Found"}
GET /api/health -> 404 {"detail":"Not Found"}
GET /api/public/status -> 200
{"monitors":[],"generated_at":"2026-10-21T11:02:46+00:00"}
GET /api/monitors -> 401 {"detail":"未登录"}
POST /api/login -> 200
{"token":"...","username":"admin","must_change_password":true}
stopped returncode 1
Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

`stopped returncode 1` 是 `proc.terminate()` 在 Windows 上结束进程的退出码，不是启动失败（此前各请求已返回）。随后 `netstat -ano -p tcp | findstr ":8000"` 只有 `127.0.0.1:8000` 的 `TIME_WAIT`，没有 `LISTENING`。服务已关掉。

项目没有 `/health` 或 `/api/health`。首页 `/` 与公开页 `/status` 返回 200。

## 8. 改密后旧会话仍有效（修复前复现）

命令:

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\repro_session.py
```

输出:

```
change_bad 400
change_ok 200
token_used_for_change 200
other_session 200
old_password_login 401
new_password_login 200 must_change False
live_sqlite_connections_after_gc 0
```

改密成功后，用来改密的 token 和另一枚登录 token 访问 `/api/me` 都仍是 200。

## 9. P1-2 验证（改密吊销会话之后）

全量 pytest：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=line
```

```
16 passed, 1 warning in 4.78s
```

退出码 0。

复现脚本再跑一次（每次用新的数据库文件）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\repro_session.py
```

```
change_bad 400
change_ok 200
token_used_for_change 401
other_session 401
old_password_login 401
new_password_login 200 must_change False
```

## 10. P1-1 验证（默认绑定改为 127.0.0.1 之后）

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\smoke_server.py
```

日志原文：

```
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
GET / -> 200
GET /status -> 200
POST /api/login -> 200
stopped returncode 1
```

## 11. 修复后的全量测试

pytest：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
16 passed, 1 warning in 4.81s
```

退出码 0。警告仍是 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

live_selftest（第二次，也是修复后这一次）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe tests\live_selftest.py
```

```
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=734)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。: 'E:\\muse-bridge\\in\\TASK-033-sitepulse\\tests\\_live_sitepulse.db'
```

退出码 1。与修复前相同：9 项功能检查通过，失败只在 `tests/live_selftest.py:119` 删除数据库。未再重试（已跑 2 次，两次都是这个错误）。绑定改成本机后，该脚本仍能连上自己拉起的服务。

## 12. 收尾 git status

```
git status --porcelain
```

```
 M README.md
 M app.py
```

