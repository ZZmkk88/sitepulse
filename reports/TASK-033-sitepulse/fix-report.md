# sitepulse 修复记录

只修 `review.md` 分级清单里的 P1。P0 无。P2 未改。

## P1-2 改密后吊销全部会话

问题编号：P1-2

文件：`app.py:316`（函数 `change_password`，原 `app.py:303-316` 只更新口令）

改法：口令更新成功后，在同一事务执行 `DELETE FROM sessions WHERE user_id = ?`，该用户已签发的 token 全部失效。错误旧密码的分支在删除之前返回，不会误删会话。

验证 1：全量 pytest（工作目录 `E:\muse-bridge\in\TASK-033-sitepulse`）

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=line
```

```
................                                                         [100%]
16 passed, 1 warning in 4.78s
```

退出码 0。警告仍是 starlette 对 httpx 的弃用提示。

中途曾按「改密测试在前、登录测试在后」单独点了两个用例。`test_change_password_flow` 会把共享测试库的口令改成 `newpass1`，后跑的 `test_login_ok_marks_must_change` 再用 `admin123` 登录得到 401。这是点名顺序和测试库不隔离造成的，不是本次改动引入的失败。按文件默认顺序重跑全量后 16 项通过。

验证 2：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\repro_session.py
```

修复前（见 `run.md` 第 8 节）：`token_used_for_change 200`，`other_session 200`。

修复后：

```
change_bad 400
change_ok 200
token_used_for_change 401
other_session 401
old_password_login 401
new_password_login 200 must_change False
live_sqlite_connections_after_gc 0
```

错误旧密码仍是 400。改密后两枚旧 token 都是 401。新密码可登录，且 `must_change_password` 为 false。

## P1-1 默认只监听本机

问题编号：P1-1

文件：`app.py:546-547`（原 `app.py:545` 为 `host="0.0.0.0"`）；`README.md:52` 环境变量表增加 `HOST` 一行。

改法：未设置 `HOST` 时绑定 `127.0.0.1`。需要从其他机器访问时显式设置 `HOST=0.0.0.0`。空字符串仍回落到 `127.0.0.1`。

验证：再次执行 `E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-033-sitepulse\smoke_server.py`（未设置 `HOST`，`PORT=8000`）。

```
GET / -> 200
GET /status -> 200
GET /api/monitors -> 401
POST /api/login -> 200 must_change_password true
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
stopped returncode 1
```

修复前同一脚本的日志是 `Uvicorn running on http://0.0.0.0:8000`。`returncode 1` 仍是 Windows 上 `terminate()` 的退出码，请求在结束前已返回。

## 修复后全量测试

pytest（两条 P1 都改完之后）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
................                                                         [100%]
============================== warnings summary ===============================
..\..\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 1 warning in 4.81s
```

退出码 0。

`tests/live_selftest.py`（修复后，第二次运行）：

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

退出码 1。失败原因与修复前相同，不是这次改动引入的：9 项功能检查都通过（含本机拉起的服务、example.com 返回 200），异常出在 Windows 上删除 `tests/_live_sitepulse.db`。该文件在测试清单的 P2，且禁止改测试文件，所以没有改。前后各跑一次，都是这个错误，没有第三次重试。

未改的 P0：无。未改的 P1：无。P2 共 11 条，都没有动。

## 收尾 git status

工作目录：`E:\muse-bridge\in\TASK-033-sitepulse`

命令：

```
git status --porcelain
```

输出：

```
 M README.md
 M app.py
```
