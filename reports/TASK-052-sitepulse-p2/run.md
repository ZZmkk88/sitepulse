# TASK-052 sitepulse P2 执行记录

开工：2026-10-21。先只读上一轮 `E:\muse-bridge\out\TASK-033-sitepulse\review.md`，再核对本仓库现状。本文件按步骤追加命令与输出。

## 1. 环境与工作区

仓库根：`E:\muse-bridge\in\TASK-052-sitepulse-p2`。`git status --porcelain` 开工时为空。`git log -1 --oneline`：`a2e615c fix(TASK-033): 复核合并（HOST 默认 127.0.0.1、改密吊销其他会话并保留本次、文档校准、DECISIONS）`。

已有虚拟环境（未新建、未 pip install）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe --version
Python 3.11.9
```

仓库内 `.venv` 不存在。`.gitignore` 已忽略 `data/`、`__pycache__/`、`*.pyc`、`.pytest_cache/`、`*.db`。

## 2. 基线全量 pytest

工作目录切到仓库根后执行（依赖用上一轮已装好的 venv，本轮没有装包）：

```
Set-Location E:\muse-bridge\in\TASK-052-sitepulse-p2
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pip show fastapi uvicorn python-multipart httpx pytest
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

`pip show` 与 `requirements.txt` / `requirements-dev.txt` 一致：fastapi 0.156.4、uvicorn 0.54.0、python-multipart 0.0.32、httpx 0.28.1、pytest 9.1.1。没有重新安装。

pytest 退出码 0。原文：

```
.................                                                        [100%]
============================== warnings summary ===============================
..\..\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-033-sitepulse\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
17 passed, 1 warning in 6.24s
```

警告来自依赖，不是断言失败。17 项比上一轮多 1 项，对应本仓 `tests/test_app.py:266` 的 `test_change_password_revokes_other_sessions_only`。

## 3. 修复前登录路径计时

脚本放在工作目录（不进仓库）：`E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py`。数据库放在同目录 `login_check.db`。命令：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py
```

退出码 0。状态码和耗时（响应体里的 token 不抄）：

```
warmup_ok status=200 ms=123.2
unknown_user status=401 ms=6.1
wrong_password status=401 ms=79.4
ok status=200 ms=87.2
long_4000 status=401 ms=87.1
long_257 status=401 ms=4.1
```

不存在的用户约 4–6 ms，存在用户的错误口令约 79 ms。4000 字口令仍是 401、87 ms，和普通错误口令同一量级，没有测出数量级上的 CPU 放大。

## 4. P2-5 改 README 之后的全量 pytest

只改了 `README.md:19-21`。

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 6.11s
```

退出码 0。

## 5. P2-11 改登录之后

`app.py`：口令上限 256；用户不存在时用等长伪盐做 pbkdf2；改密在哈希前拒绝过长口令。

立刻全量 pytest：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 6.02s
```

退出码 0。

同一工作目录脚本再跑一次（脚本已改成不打印 token）：

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe E:\muse-bridge\work\TASK-052-sitepulse-p2\check_login.py
```

退出码 0。

```
unknown_user status=401 ms=70.4 detail=用户名或密码不正确
wrong_password status=401 ms=68.0 detail=用户名或密码不正确
ok status=200 ms=71.9 has_token=yes must_change=True
long_4000 status=400 ms=2.9 detail=密码过长
long_257_unknown status=400 ms=2.8 detail=密码过长
long_257_admin status=400 ms=3.4 detail=密码过长
change_long status=400 ms=6.3 detail=密码过长
change_short status=400 ms=3.6 detail=新密码至少 6 位
```

（另有 warmup_ok 200、108.3 ms。）修复前不存在用户是 6.1 ms，错误口令是 79.4 ms。

## 6. 全部改完后的全量 pytest 与 git status

```
E:\muse-bridge\work\TASK-033-sitepulse\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

```
17 passed, 1 warning in 5.96s
```

退出码 0。

```
git status --porcelain
```

```
 M README.md
 M app.py
```

没有 commit，没有 push。没有改 `tests/`。
