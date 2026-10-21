# sitepulse P2 修复记录

只处理上一轮 `review.md` 的 P2，按原编号。P0/P1 本仓已有，本轮不重改。没改 `tests/`，没有 skip/xfail。

## P2-1 不改

问题编号：P2-1

文件：`tests/live_selftest.py:118-119`

原因：`proc.wait` 之后立刻 `unlink`。要重试删除只能改测试文件，本任务禁止。`DECISIONS.md:28-33` 已关闭。本轮没有重跑该脚本（会请求 `https://example.com`）。

## P2-2 不改

问题编号：P2-2

文件：改前 `README.md:44`，P2-5 插入一行后为 `README.md:45`

原因：`DECISIONS.md:6-14` 规定「会要求改密码」指可忽略横幅（`static/index.html:97`），不是业务拦截。服务端若拒绝未改密的监控接口，会破坏 `tests/test_app.py:130-134`。不单改这句文案。

## P2-3 已落地，不改

问题编号：P2-3

文件：改前 `README.md:54`，P2-5 插入一行后为 `README.md:55`。读取点改前 `app.py:225`，P2-11 在常量区插入 3 行后为 `app.py:228`。

当前环境变量表已有 `SITEPULSE_DISABLE_SCHEDULER`，说明为测试用途。不再改。

## P2-4 已落地，不改

问题编号：P2-4

文件：`README.md:11-12`。界限改前是 `app.py:30-31` 与 `app.py:363-368`；常量与登录改动在 `validate_interval` 上方插入之后，函数现在位于 `app.py:375`。`app.py:30-31` 未动。

功能清单已写探测间隔 5–86400 秒。不再改。

## P2-5 README 公开字段与页面、接口对齐

问题编号：P2-5

文件：`README.md:19-21`（改前是 `README.md:19-20`）

改法：删掉「页面只展示探测时间」。改成页面展示名称、通/断、最近响应时间，页脚显示本次更新时间；接口每条另含探测时间；仍不返回网址和失败原因。没有改 `static/status.html`，也没有改 `app.py` 的公开字段。

验证：全量 pytest（工作目录 `E:\muse-bridge\in\TASK-052-sitepulse-p2`）

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 6.11s
```

退出码 0。警告仍是 starlette 对 httpx 的弃用提示。

## P2-6 已落地，不改

问题编号：P2-6

文件：`README.md:53`（P2-5 插入一行后变为 `README.md:54`），实现 `app.py:24-25`

库路径已经写成与 app.py 同目录的 `data/sitepulse.db`。不再改。

## P2-7 已落地，不改

问题编号：P2-7

文件：`README.md:8`

「均已测试覆盖」已经不在。24 小时 token 过期仍没有测试。不补测试，不改测试。

## P2-8 不改

问题编号：P2-8

文件：`requirements.txt:3`

python-multipart 仍无 Form/File 使用，也无版本冲突。不改钉死依赖。`DECISIONS.md:39-43`。

## P2-9 已落地，不改

问题编号：P2-9

文件：改前 `app.py:211-213`，常量区插入 3 行后为 `app.py:215-217`。

调度循环已经 `log.exception("scheduler round failed")`。本轮没有注入异常去看日志。

## P2-10 不改

问题编号：P2-10

文件：上一轮记录的 `/health`、`/api/health`；本仓 README 未承诺该路由。

`DECISIONS.md:35-37` 明确不加。不加路由。

## P2-11 登录等长哈希，并限制口令长度

问题编号：P2-11

文件：`app.py:34-36`（上限 256 与伪盐）、`app.py:280-291`（登录）、`app.py:320-324`（改密在哈希前拒绝过长口令）。

改法：口令长于 256 返回 400「密码过长」，存在用户和不存在用户走同一分支，不先做 pbkdf2。长度合格时，用户不存在用 `_LOGIN_DUMMY_SALT`（32 位十六进制，与 `token_hex(16)` 等长）做一次 `hash_password`，再用 `secrets.compare_digest` 比较；失败仍是 401「用户名或密码不正确」。改密同样在计算旧口令哈希之前拒绝过长的旧口令或新口令。没有加登录次数限制。

验证 1：全量 pytest（这条改完立刻跑，工作目录为仓库根）

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 6.02s
```

退出码 0。警告仍是 starlette 对 httpx 的弃用提示。

验证 2：`E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py`（独立库，不进仓库）

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py
```

退出码 0。原文（不含 token）：

```
warmup_ok status=200 ms=108.3 has_token=yes must_change=True
unknown_user status=401 ms=70.4 detail=用户名或密码不正确
wrong_password status=401 ms=68.0 detail=用户名或密码不正确
ok status=200 ms=71.9 has_token=yes must_change=True
long_4000 status=400 ms=2.9 detail=密码过长
long_257_unknown status=400 ms=2.8 detail=密码过长
long_257_admin status=400 ms=3.4 detail=密码过长
change_long status=400 ms=6.3 detail=密码过长
change_short status=400 ms=3.6 detail=新密码至少 6 位
```

修复前同一脚本：不存在用户 6.1 ms，错误口令 79.4 ms。修复后两条都在 68–70 ms。过长口令对「admin」和「nobody」都是 400，约 3 ms。短新口令仍是 400「新密码至少 6 位」。

## 全部改完后的全量 pytest

两条都改完之后再跑一次（与上面 6.02s 那次分开）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 5.96s
```

退出码 0。

## 收尾 git status

工作目录：`E:\muse-bridge\in\TASK-052-sitepulse-p2`

命令：

```
git status --porcelain
```

输出：

```
 M README.md
 M app.py
```
