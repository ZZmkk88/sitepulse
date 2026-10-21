# sitepulse 修复记录

只改了 `review.md` 清单里的 P0-1、P1-1、P1-2，文件都是 `app.py`。

## P0-1 连接不关闭，Windows 上锁住 sqlite

- 问题编号：P0-1
- 文件：`app.py:15`（补 `contextmanager` 导入）、`app.py:54-70`（重写 `get_conn`）
- 改法：`get_conn` 改为上下文管理器，正常路径 `commit()`，异常 `rollback()`，`finally` 里 `close()`。调用处仍是 `with get_conn() as conn`。

验证 1：`Set-Location E:\muse-bridge\in\TASK-043-sitepulse; .venv\Scripts\python.exe -m pytest tests/ -q`

退出码 0：

```
................                                                         [100%]
16 passed, 1 warning in 4.98s
```

警告仍是 starlette 的 `httpx` / `httpx2` DeprecationWarning，与这次改动无关。

验证 2：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\repro_idle_lock.py`

退出码 0。修复前同一脚本是 `IDLE_UNLINK PermissionError 13 [WinError 32]`。修复后：

```
status 200
login 200
IDLE_UNLINK ok (server still up)
```

验证 3：`.venv\Scripts\python.exe -X utf8 tests\live_selftest.py`

退出码 0。修复前退出码 1，堆栈在 `tests/live_selftest.py:119` 的 `db.unlink()`。修复后：

```
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=762)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址

结果： 全部通过
```

## P1-1 改密不废止其他会话

- 问题编号：P1-1
- 文件：`app.py:321-347`（`change_password`；删除其他会话在 `app.py:343-346`）
- 改法：改密时带上当前请求的 Bearer token，在同一事务里 `DELETE FROM sessions WHERE user_id = ? AND token != ?`。正在改密的这次登录保留，其他 token 失效。

验证 1：`.venv\Scripts\python.exe -m pytest tests/test_app.py::test_change_password_flow tests/test_app.py::test_login_wrong_password tests/test_app.py::test_unauthenticated_rejected -q`

退出码 0：

```
...                                                                      [100%]
3 passed, 1 warning in 1.30s
```

验证 2：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\diag.py`

退出码 0。修复前 token1 与 token2 在改密后都是 200。修复后：

```
change 200 {"ok":true}
token1 after change 200 {"username":"admin","must_change_password":false}
token2 after change 401 {"detail":"登录已过期，请重新登录"}
old password 401 new password 200 False
```

## P1-2 超长密码会跑满 pbkdf2

- 问题编号：P1-2
- 文件：`app.py:33`（`MAX_PASSWORD_LENGTH = 128`）、`app.py:292-298`（登录）、`app.py:327-331`（改密）
- 改法：密码长于 128 字符时，登录仍返回 401「用户名或密码不正确」且不算哈希；改密返回 400「密码过长」，同样不算哈希。

验证 1：`.venv\Scripts\python.exe E:\muse-bridge\work\TASK-043-sitepulse\pwlen.py`

退出码 0：

```
long_login 401 {"detail":"用户名或密码不正确"} sec 0.041
short_wrong 401 sec 0.075
normal 200 True
change_long 400 {"detail":"密码过长"}
still_old 200
```

1 万字符的错误密码比普通错误密码还快返回，说明没有进入 20 万次 pbkdf2。129 字符的新密码被拒绝，旧密码仍能登录。

验证 2：`.venv\Scripts\python.exe -m pytest tests/test_app.py::test_login_wrong_password tests/test_app.py::test_login_ok_marks_must_change tests/test_app.py::test_change_password_flow -q`

退出码 0：

```
...                                                                      [100%]
3 passed, 1 warning in 1.42s
```

## 全量重跑

命令：`Set-Location E:\muse-bridge\in\TASK-043-sitepulse; .venv\Scripts\python.exe -m pytest tests/ -q`

退出码 0：

```
................                                                         [100%]
16 passed, 1 warning in 5.69s
```

警告原文未变：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 这是依赖提示，不是失败。

命令：`.venv\Scripts\python.exe -X utf8 tests\live_selftest.py`

退出码 0：

```
PASS 服务器启动且状态页可打开
PASS 登录成功且提示改密
PASS 两个监控项创建成功
PASS 真实网站判通 (code=200 ms=726)
PASS 死地址判断且有失败原因 (error=[WinError 10061] 由于目标计算机积极拒绝，无法连接。)
PASS 后台调度器已自动探测（记录数 >= 2） (count=3)
PASS 真实站点 24h 可用率 100% (uptime=100.0)
PASS 公开状态接口免登录且结论正确 ({'真实站点': 'up', '不存在的地址': 'down'})
PASS 公开接口不泄露网址

结果： 全部通过
```

没有失败项。P2 未改。

## git status

命令：`git -C E:\muse-bridge\in\TASK-043-sitepulse status --porcelain`

输出：

```
 M app.py
```
