# sitepulse 验收

pytest 16 项通过。按 README 起的服务首页、`/status`、`/api/public/status`、默认账号登录均返回 200。没有 `/health`（404）。`tests/live_selftest.py` 九项检查都 PASS，但 Windows 上清理数据库时文件仍被占用，脚本退出码 1。许可证三份声明在仓库内自洽；上游 commit 与版权行未外网核实。

## 本地跑通记录

环境：Python 3.11.9，仓库根目录 `E:\muse-bridge\in\TASK-043-sitepulse`，虚拟环境 `.venv`（`.gitignore` 已忽略）。

装依赖（退出码 0）：

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements.txt` 钉死的 fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32 都能装上。测试依赖 httpx==0.28.1、pytest==9.1.1 也能装上。

pytest（退出码 0，5.76s）：

```
.venv\Scripts\python.exe -m pytest tests/ -q
................                                                         [100%]
16 passed, 1 warning in 5.76s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`（`.venv\Lib\site-packages\fastapi\testclient.py:1`）。`tests/live_selftest.py` 没有 `test_` 函数，pytest 没跑它。

起服务（工作目录脚本 `smoke.py`，数据库放在 `E:\muse-bridge\work\TASK-043-sitepulse\smoke.db`，端口 8000）。日志：`Uvicorn running on http://0.0.0.0:8000`。

| 请求 | 结果 |
|---|---|
| GET / | 200，`text/html`，标题「sitepulse · 网站监控台」 |
| GET /status | 200，`text/html`，标题「服务状态 · sitepulse」 |
| GET /api/public/status | 200，`{"monitors":[],"generated_at":"2026-10-21T11:59:55+00:00"}` |
| GET /health | 404 `{"detail":"Not Found"}` |
| GET /healthz | 404 `{"detail":"Not Found"}` |
| POST /api/login admin/admin123 | 200，`must_change_password` true，有 token |

探活后已 `terminate` 该进程。当时 `netstat` 上 8000 只剩 TIME_WAIT。后来 8000 被另一个任务的 `serve_once.py` 占用，与本仓库无关，没有动它。

live_selftest（退出码 1）：

```
.venv\Scripts\python.exe -X utf8 tests\live_selftest.py
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=1059)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址
PermissionError: [WinError 32] ... tests\_live_sitepulse.db
```

堆栈在 `tests/live_selftest.py:119` 的 `db.unlink()`。example.com 返回 200，不是外网限制。

空闲锁库（`repro_idle_lock.py`，服务还在跑、请求已返回）：

```
IDLE_UNLINK PermissionError 13 [WinError 32] 另一个程序正在使用此文件
```

进程退出后同一文件可以删掉。原因是 `app.py:54-58` 的 `get_conn()` 借 `with` 只用了 sqlite3 连接的提交语义，连接本身不关闭，进程活着就把库文件占住。

改密不废止会话（`diag.py`，独立库）：

```
change 200 {"ok":true}
token1 after change 200 {"username":"admin","must_change_password":false}
token2 after change 200 {"username":"admin","must_change_password":false}
old password 401 new password 200 False
```

同一用户两个 token，用 token1 改密后，token2 仍能访问 `/api/me`。

## README 与实际不符处

1. `README.md:7` 写「功能清单与代码实现一一对应，均已测试覆盖」。24 小时过期只在 `app.py:25` 的 `TOKEN_TTL_SECONDS = 24 * 60 * 60`，`tests/test_app.py` 没有过期用例。
2. `README.md:15` 写判通规则是状态码 2xx/3xx，没写跟随重定向。`app.py:130` 的 `urlopen` 会跟到最终响应；`tests/test_app.py:178-181` 期望 302 最终变成 200。`NOTES.md:35` 写了跟随重定向，README 没写。
3. `README.md:19-20` 说公开状态页展示各监控项的名称、通断和最近响应时间。`app.py:514` 是 `WHERE active = 1`，暂停项不出现。`tests/test_app.py:239-243` 把这个当预期。README 没写「只含启用中的项」。
4. `README.md:11-12` 只说探测间隔是秒数。`app.py:29-30` 限制 5 到 86400，`app.py:348-354` 会拒绝越界值。`static/index.html:109` 同样限制了 min/max。README 没写范围。
5. `README.md:44` 写「首次登录会要求改密码」。`static/index.html:97` 只显示一条可忽略的横幅；`app.py:401-402` 等管理接口不看 `must_change_password`。`tests/test_app.py:130-134` 在仍须改密时创建监控项。`README.md:10` 的「强制提示」和横幅一致，第 44 行写重了。
6. `README.md:32` 与 `README.md:41` 只写默认端口 8000。`app.py:545` 绑定 `0.0.0.0`。实测日志是 `Uvicorn running on http://0.0.0.0:8000`。README 没写监听地址。
7. `README.md:74` 自测命令只有 `.venv/bin/python tests/live_selftest.py`。同文件 `README.md:64-66` 的 Windows 小节没有这条命令。
8. `README.md:47-53` 的环境变量表没有 `SITEPULSE_DISABLE_SCHEDULER`。`app.py:221` 在该变量为 `1` 时不启动调度器，测试靠它关掉后台探测。

以下与 README 相符，不单列：默认账号 admin/admin123（`app.py:26-27`）、默认库 `data/sitepulse.db`（`app.py:24`）、pytest 不访问外网（16 passed）、公开页不返回网址和失败原因（`app.py:507-527`，测试通过）。

## 许可证与署名核查

仓库内自洽，上游事实未外网核实。

- `LICENSE:1-3`：MIT，`Copyright (c) 2026 sitepulse contributors`。正文是常见 MIT 条文，没有改过免责声明的结构。
- `UPSTREAM.md:5-8`：上游 `https://github.com/louislam/uptime-kuma`，commit `2adb5bc32cb53a93722a7c348364a8290acd74d4`，许可证 MIT，署名 `Copyright (c) 2021 Louis Lam`。`UPSTREAM.md:12-17` 说该 commit 与版权行是 2026-10-21 从上游抄来的。
- `NOTES.md:5-8` 与 UPSTREAM 的项目、commit、版权行一致。`NOTES.md:25-31` 写明表结构自拟，只借鉴监控项、探测记录、公开状态页。
- `README.md:5-6` 指向 UPSTREAM，并写「代码为独立实现」。

本仓库版权（2026 sitepulse contributors）和上游版权（2021 Louis Lam）分成两个文件，没有互相覆盖。抽查 `app.py` 与 `static/index.html`、`static/status.html`：Python + SQLite + 手写页面，没有 knex、heartbeat、Vue 或 Uptime Kuma 源码片段。字段是 `monitors` / `checks`，不是上游的 monitor / heartbeat。在「未复制源码」的前提下，LICENSE 不收录 Louis Lam 一行，和 MIT 的衍生作品要求不冲突。

未核实：任务禁止抓取外部页面，没有对照 GitHub 上的 commit 和上游 LICENSE 原文。若该 commit 不存在，或版权行不是 `Copyright (c) 2021 Louis Lam`，则 `UPSTREAM.md:12-17` 的「实查」「逐字复制」不成立。仓库里没有相反证据。

`sitepulse contributors` 没有对应的作者名单。仓库内也没有另一套个人版权声明，不算自相矛盾。

## 分级修复清单

### P0

1. **P0-1** `app.py:54-58`。`get_conn()` 不关闭连接，服务空闲时仍锁住 sqlite。Windows 上 `tests/live_selftest.py:119` 因此 `PermissionError [WinError 32]`，脚本退出码 1。修法：改成用完提交并 `close()` 的上下文管理器。

### P1

1. **P1-1** `app.py:303-316`。改密只更新哈希，不删除该用户已有 session。窃取的 token 在改密后 24 小时内仍有效（diag 中 token2 仍 200）。修法：同一事务删除该用户其他 session。
2. **P1-2** `app.py:48-51` 与 `app.py:274-280`。密码没有上限，登录对已知用户名做 20 万次 pbkdf2。超长密码可占满单进程。修法：超过 128 字符直接拒绝，且不要算哈希。

### P2

1. **P2-1** `app.py:545`。默认 `host="0.0.0.0"`，加上 README 里的默认口令 `admin/admin123`（`app.py:26-27`），局域网可直接登录。修法：默认绑 `127.0.0.1`，需要对外时再用环境变量打开。本次不改，避免把「自己部署到别的机器」这条路径弄断。
2. **P2-2** `app.py:130-142`。先读到状态码再读 body，body 超时会走进 `except Exception` 并丢掉状态码，记成 `status_code: null`。`repro_body.py`：先发 200 再拖住 body，1 秒超时结果是 `{'status': 0, 'status_code': None, 'error': 'timed out'}`。README 写超时算断，判通/断与说明一致，所以不升到 P1。修法：已有 2xx/3xx 时保留状态码，或不要为了判通去读 body。
3. **P2-3** `app.py:338-345`。`validate_url` 放行 CR/LF 和 `http://169.254.169.254/...`、带账号密码的 URL。CR/LF 在 `urllib` 发出前被拒绝（`repro_body.py` 对端没收到字节），当前不能注头。修法：校验时拒绝 ASCII 控制字符；内网探测是监控工具本身的功能，不在这里封私网。
4. **P2-4** `app.py:208-209`。调度器 `except Exception: pass`，一轮失败没有任何记录。修法：至少记下异常类型，不要空吞。
5. **P2-5** `app.py:262-267`。过期 session 只在查询时过滤，不删除。修法：登录或定时删除 `expires_at` 已过的行。
6. **P2-6** `app.py:100-114`。换一个 `SP_INITIAL_USERNAME` 会再插入用户，旧账号仍在，且监控项没有用户隔离。和 `README.md:10` 的「单用户」在二次配置时不一致。修法：启动时不要无条件追加第二个管理员，或在 README 写明只在库为空时播种。
7. **P2-7** 应用没有 `/health`。实测 GET `/health` 与 `/healthz` 都是 404。README 没承诺该路径。修法：若需要探活，加一个不访问外网的只读端点；现在可用 `/api/public/status`。
8. **P2-8** `app.py` 未关闭 FastAPI 默认文档。GET `/docs` 与 `/openapi.json` 无登录且返回 200，`/docs` 的 HTML 引用外网 CDN。修法：生产默认关掉 `docs_url` / `openapi_url`。
9. **P2-9** `requirements.txt:3` 的 `python-multipart` 在仓库源码里没有引用。修法：确认无表单上传后从依赖去掉。本次不动版本号。
10. **P2-10** 测试客户端警告：当前 starlette 建议换 `httpx2`，现在 16 项仍通过。修法：等依赖冲突真正出现再改 `requirements-dev.txt`，本次不改钉死版本。
11. **P2-11** `tests/test_app.py:262-275`。`test_change_password_flow` 改掉共享库里的 admin 密码，后面的用例靠收集顺序仍用旧 token。禁止改测试，所以不动。

本次只改 P0-1、P1-1、P1-2，都在 `app.py`。
