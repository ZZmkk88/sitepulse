# sitepulse 验收审查

审查对象：`E:\muse-bridge\in\TASK-033-sitepulse`（修复前的交付版本）。下面的文件行号都按修复前的内容。Python 3.11.9。虚拟环境在 `E:\muse-bridge\work\TASK-033-sitepulse\venv`（未写入仓库）。命令与原文见 `run.md`。修复了哪些行见 `fix-report.md`。

## 本地跑通记录

依赖按 README 的两份 requirements 安装成功，版本与文件一致（`requirements.txt:1-3` 的 fastapi 0.156.4、uvicorn 0.54.0、python-multipart 0.0.32；`requirements-dev.txt:2-3` 的 httpx 0.28.1、pytest 9.1.1）。无依赖冲突。

pytest（工作目录为仓库根）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
16 passed, 1 warning in 5.04s
```

退出码 0。警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自依赖，不是断言失败。

`tests/live_selftest.py` 退出码 1。9 项功能检查全部 PASS，其中包括对 `https://example.com` 的真实探测（`code=200 ms=692`），不记为环境限制。失败原文：

```
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。: 'E:\\muse-bridge\\in\\TASK-033-sitepulse\\tests\\_live_sitepulse.db'
```

位置 `tests/live_selftest.py:119` 的 `db.unlink()`。汇总打印没执行到。进程退出后该文件可以打开并删除（`diag_lock.py` 输出 `remove ok`），不是服务没关干净。

服务按 `app.py` 启动，`PORT=8000`，数据库放在工作目录。日志原文：`Uvicorn running on http://0.0.0.0:8000`。

| 请求 | 结果 |
|---|---|
| `GET /` | 200，标题「sitepulse · 网站监控台」 |
| `GET /status` | 200，标题「服务状态 · sitepulse」 |
| `GET /health` | 404 `{"detail":"Not Found"}` |
| `GET /api/health` | 404 `{"detail":"Not Found"}` |
| `GET /api/public/status` | 200 `{"monitors":[],"generated_at":"2026-10-21T11:02:46+00:00"}` |
| `GET /api/monitors` | 401 `{"detail":"未登录"}` |
| `POST /api/login` admin/admin123 | 200，`must_change_password` 为 true |

探测结束后已 `terminate`。`netstat` 里 8000 端口只剩 `TIME_WAIT`，没有 `LISTENING`。

改密复现（`repro_session.py`，修复前）：错误旧密码 400；改密 200；改密所用 token 再访问 `/api/me` 为 200；另一枚 token 也为 200；旧密码登录 401；新密码登录 200 且 `must_change_password` 为 false。

## README 与实际不符处

1. `README.md:44` 写「首次登录会要求改密码」。实际只在 `static/index.html:97` 显示一条可忽略的横幅，服务端不拦截。`app.py:319-324` 的 `/api/me` 只返回标志；`app.py:401` 起的监控接口只依赖已登录（`current_user`）。`tests/test_app.py:90-103` 在 `must_change_password` 仍为 true 时就创建监控项，测试把「可继续操作」当成了约定。同文件 `README.md:10` 的「强制提示改密」与界面一致，和本行的「会要求」不是一回事。

2. `README.md:32` 与 `README.md:44` 只告诉用户打开 localhost。`app.py:545` 为 `host="0.0.0.0"`。启动日志：`Uvicorn running on http://0.0.0.0:8000`。端口 8000 与 README 一致，监听范围不一致。

3. `README.md:52` 把默认库写成 `data/sitepulse.db`。`app.py:23-24` 实际是 `Path(__file__).parent / "data" / "sitepulse.db"`，锚定 app.py 所在目录，不是进程当前目录。按 README 先 `cd` 到仓库再启动时两条路径重合；从别的目录启动 `python <路径>\app.py` 时不会写到当前目录的 `data\`。

4. `README.md:47-53` 的环境变量表没有 `SITEPULSE_DISABLE_SCHEDULER`。`app.py:221` 读这个变量，等于 `1` 时不启动调度器。`tests/test_app.py:25` 依赖它。

5. `README.md:11` 只说「探测间隔秒数」，没有范围。`app.py:29-30` 与 `app.py:348-354` 把间隔限制在 5 到 86400 秒，超出返回 400。`static/index.html:109` 的输入框同样是 min 5、max 86400。

6. `README.md:19-20` 说公开状态页「只展示」名称、通/断、最近响应时间。`app.py:523-527` 的每条记录还有 `checked_at`，响应体还有 `generated_at`。`tests/test_app.py:233` 要求公开字段正好是 `name/status/response_ms/checked_at`。网址和失败原因确实没有出现在公开接口里，这一点与 README 后半句一致。

7. `README.md:8` 写功能「均已测试覆盖」。pytest 覆盖了登录、监控项增删改、暂停、手动探测、2xx/3xx/500/拒连/超时、24 小时可用率和公开页。没有覆盖：`app.py:25` 的 24 小时 token 过期、看板页面本身、调度循环（调度只在 `tests/live_selftest.py` 里跑过，且该脚本在本机退出码为 1）。

## 许可证与署名核查

内部声明对得上，上游事实未外网复核（本任务禁止抓取外部页面）。没有修改 `LICENSE` 或 `UPSTREAM.md`。

- `LICENSE:1-3`：MIT，版权行 `Copyright (c) 2026 sitepulse contributors`。
- `UPSTREAM.md:5-8`：上游标为 uptime-kuma，commit `2adb5bc32cb53a93722a7c348364a8290acd74d4`，许可证 MIT，署名 `Copyright (c) 2021 Louis Lam`。
- `UPSTREAM.md:12-19` 与 `NOTES.md:5-6`、`NOTES.md:25-31` 一致：同一 commit、同一版权行，并写明本仓库是独立重写，字段名自拟，未复制上游源码。
- `README.md:5-6` 指向 `UPSTREAM.md`，并写「代码为独立实现」。与 UPSTREAM 的「未复制上游源码」一致。
- 仓库内容是 Python、两个静态页和 Markdown，没有上游那种 Node 服务端文件。在「只借鉴概念、未复制源码」的前提下，本仓库用自己的 MIT 版权、把上游署名放在 `UPSTREAM.md`，不与 MIT 的「再分发须保留原版权声明」冲突。
- 未核实：该 commit 是否真是 2026-10-20 的上游 HEAD，以及 `Copyright (c) 2021 Louis Lam` 是否与上游 LICENSE 逐字相同。`UPSTREAM.md:17` 声称逐字复制，本次不能外网对照，所以不改这句话。

没有发现两份文件互相否定的句子。

## 分级修复清单

### P0

无。依赖能装上，pytest 16 项通过，服务能在 8000 端口起起来，首页和 `/status` 返回 200。

### P1

1. **默认监听所有网卡，且默认口令写在仓库里。** `app.py:545` 绑定 `0.0.0.0`；`app.py:26-27` 默认账号 `admin` / `admin123`；`README.md:44` 公开了这组口令。同一网段的人可以直接登录。修法：默认改为 `127.0.0.1`，用环境变量 `HOST` 才能改成其他地址，并在 `README.md:47` 的表里补上 `HOST`。
2. **改密不吊销已签发的会话。** `app.py:303-316` 只更新口令哈希，不删 `sessions`。修复前复现：改密后两枚旧 token 访问 `/api/me` 仍为 200。修法：在同一事务中执行 `DELETE FROM sessions WHERE user_id = ?`。

### P2

1. **`tests/live_selftest.py:119` 在 Windows 上清理数据库抛 `WinError 32`，脚本退出码 1。** 9 项检查已通过。修法：`terminate` 后重试删除，或等进程和文件句柄都释放再 `unlink`。本次不改：禁止改测试文件；进程被 `TerminateProcess` 之后应用层无法提前放锁。
2. **`README.md:44`「会要求改密码」强于实现。** 服务端若在未改密时拒绝监控接口，会破坏 `tests/test_app.py:90-118`。本次不改这条行为，也不单改这句文案。
3. **`README.md:47-53` 未记录 `SITEPULSE_DISABLE_SCHEDULER`（`app.py:221`）。** 修法：在环境变量表补一行，说明它只用于测试。
4. **`README.md:11` 未写探测间隔 5–86400 秒（`app.py:29-30`、`app.py:348-354`）。** 修法：在功能清单里补上范围。
5. **`README.md:19-20` 的「只展示」与 `app.py:523-527` 的 `checked_at`、`generated_at` 不一致。** 修法：改 README，写上这两项，并保留「不返回网址和失败原因」。
6. **`README.md:52` 的相对路径与 `app.py:24` 的「相对 app.py 文件」不一致。** 修法：写成「与 app.py 同级的 data/sitepulse.db」。
7. **`README.md:8`「均已测试覆盖」过满。** 24 小时过期（`app.py:25`）没有测试。修法：改成已覆盖的范围，或补测试。本次不补测试、不改测试。
8. **`requirements.txt:3` 的 python-multipart 在 `app.py` 中没有 Form/File 使用。** 修法：从依赖中删除。本次不改：禁止改已钉住的依赖，除非是冲突；现在没有冲突。
9. **`app.py:208-209` 调度循环 `except Exception: pass`，出错时整轮静默跳过。** 修法：至少把异常写进日志。
10. **无 `/health`。** `/health` 与 `/api/health` 均为 404。README 没有承诺该路由。需要的话可以加一个不查库的 200。本次不加。
11. **登录无限速（`app.py:274-280`），且用户不存在时不做 pbkdf2，响应更快。** 修法：限制口令长度并对不存在的用户也做一次等长计算。绑定改为本机后，风险主要留在本机。
