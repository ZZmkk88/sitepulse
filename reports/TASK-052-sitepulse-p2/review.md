# sitepulse 第二轮审查（P2）

审查对象：`E:\muse-bridge\in\TASK-052-sitepulse-p2`，提交 `a2e615c`。开工时 `git status --porcelain` 为空。对照上一轮 `E:\muse-bridge\out\TASK-033-sitepulse\review.md` 的 P2 清单。行号按本轮改代码之前。

结论：没有 P0。上一轮两条 P1 已经在这个仓库里，本轮不重改。11 条 P2 里，5 条已经写进当前文件，4 条不该改。还要改 2 条：公开状态页的 README 句子和登录时序。

## 跑通记录

虚拟环境用已有的 `E:\muse-bridge\work\TASK-033-sitepulse\venv`（Python 3.11.9）。`pip show` 与两份 requirements 一致：fastapi 0.156.4、uvicorn 0.54.0、python-multipart 0.0.32、httpx 0.28.1、pytest 9.1.1。本轮没有 pip install。

工作目录为仓库根：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 6.24s
```

退出码 0。警告是 `StarletteDeprecationWarning`（httpx 与 starlette TestClient），来自依赖，不是断言失败。17 项比上一轮多出的是 `tests/test_app.py:266` 的 `test_change_password_revokes_other_sessions_only`。

本轮没有另起 uvicorn，也没有重跑 `tests/live_selftest.py`。前者不涉及这次要动的监听地址；后者会请求 `https://example.com`，失败点在禁止修改的测试文件里。

## 上一轮 P1 在本仓的状态

1. 默认监听。`app.py:560` 为 `os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"`。`README.md:52` 有 `HOST` 一行。本轮没有抓启动日志，只核对源码。
2. 改密吊销其他会话、保留本次。`app.py:326-330` 执行 `DELETE FROM sessions WHERE user_id = ? AND token != ?`。`DECISIONS.md:16-26` 说明这是对上一轮「连本次会话一起删」的修正。`tests/test_app.py:275-280` 断言其他 token 为 401、本次为 200。全量 pytest 已通过。

## P2 逐条

1. **不改。** `tests/live_selftest.py:118-119` 在 `proc.wait` 之后立刻 `db.unlink()`。要消除 Windows 上的 `WinError 32` 就得改这个测试。`DECISIONS.md:28-33` 已关闭。本轮没有重跑该脚本。
2. **不改。** `README.md:44` 仍写「首次登录会要求改密码」。`DECISIONS.md:6-14` 规定这句指可忽略的提示横幅，服务端不拦截；`static/index.html:97` 是横幅，`tests/test_app.py:130-134` 在 `must_change_password` 仍为 true 时创建监控项。改成强制改密会拆掉现有测试。
3. **已落地，不改。** `README.md:54` 已记录 `SITEPULSE_DISABLE_SCHEDULER`。读取点是 `app.py:225`。
4. **已落地，不改。** `README.md:11-12` 已写间隔 5–86400 秒。界限在 `app.py:30-31` 与 `app.py:363-368`，输入框在 `static/index.html:109`。
5. **要改 README。** `README.md:19-20` 写页面「只展示」名称、通/断、最近响应时间与探测时间。`static/status.html:44-51` 每条只渲染名称、通断和响应毫秒，没有 `checked_at`。更新时间在页脚 `static/status.html:30` 与 `static/status.html:53`，对应 `app.py:542` 的 `generated_at`。接口每条字段由 `tests/test_app.py:233` 锁成 `name/status/response_ms/checked_at`。句子把页面没画的「探测时间」说成页面内容，又没写页脚的更新时间。
6. **已落地，不改。** `README.md:53` 写「与 app.py 同目录的 `data/sitepulse.db`」。`app.py:24-25` 是 `Path(__file__).resolve().parent / "data" / "sitepulse.db"`。
7. **已落地，不改。** `README.md:8` 已改成「测试覆盖见 tests/ 与「测试」一节」，不再写「均已测试覆盖」。24 小时过期仍无测试（`app.py:26` 的 `TOKEN_TTL_SECONDS`）。不补测试。
8. **不改。** `requirements.txt:3` 的 python-multipart 在 `app.py` 里没有 Form/File。无版本冲突。`DECISIONS.md:39-43` 要求保留钉死依赖。
9. **已落地，不改。** `app.py:211-213` 调度异常走 `log.exception("scheduler round failed")`，不再是 `pass`。本轮没有人为制造调度异常去看日志行。
10. **不改。** `/health` 与 `/api/health` 上一轮是 404，README 没有承诺。`DECISIONS.md:35-37` 明确不加。
11. **要改登录。** `app.py:283` 在用户不存在时短路，不调用 `hash_password`。修复前脚本 `E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py`：不存在用户 401、6.1 ms 与 4.1 ms；存在用户的错误口令 401、79.4 ms。口令长度没有上限。4000 字错误口令是 401、87.1 ms，和 79.4 ms 同一量级，不能说成 CPU 被放大了一个数量级；仍按清单加上限，避免超大字符串进入 pbkdf2。不另做登录计数器：清单修法没有要求，服务又只听本机。

## 分级修复清单

### P0

无。pytest 17 项通过，应用能被 TestClient 导入并完成登录、监控和公开接口。

### P1

无。监听地址和改密吊销见上一节，本轮不重改。

### P2（本轮改，按原清单编号）

1. **P2-5** `README.md:19-20`。改成与页面和接口一致：页面展示名称、通/断、最近响应时间，页脚为本次更新时间；接口每条另含探测时间；仍不返回网址和失败原因。不改 `static/status.html`。
2. **P2-11** `app.py:277-294`（以及 `app.py:311` 的改密入口）。超过 256 的口令返回 400；用户不存在时用与 `token_hex(16)` 等长的伪盐做一次 pbkdf2，再返回与密码错误相同的 401。改密在计算哈希前同样拒绝过长口令。

### P2（不改）

- P2-1 `tests/live_selftest.py:118-119`：禁止改测试。
- P2-2 `README.md:44`：`DECISIONS.md:6-14` 已规定文案含义，强制拦截会破坏 `tests/test_app.py:130-134`。
- P2-3 `README.md:54`、P2-4 `README.md:11-12`、P2-6 `README.md:53`、P2-7 `README.md:8`、P2-9 `app.py:211-213`：当前文件已经对齐。
- P2-8 `requirements.txt:3`：无依赖冲突，不改钉死版本。
- P2-10：README 未承诺 `/health`，`DECISIONS.md:35-37` 不加。

## 落地

P2-5、P2-11 已按上面的修法改完，命令原文在 `fix-report.md`。最终 pytest：`17 passed, 1 warning in 5.96s`。`git status --porcelain`：

```
 M README.md
 M app.py
```
