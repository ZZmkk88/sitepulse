# sitepulse · 网站监控

一句话定位：一个轻量、可自己部署的网站监控工具——定时探测你的网站通不通、记录响应时间和可用率，并提供一个免登录的公开状态页。

本项目的设计学习了开源社区网站监控工具的通行思路——如监控项、定时探测、
探测记录与公开状态页这类核心概念；代码为独立实现。上游溯源与署名见 [UPSTREAM.md](UPSTREAM.md)。

## 功能清单（与代码实现一一对应，测试覆盖见 tests/ 与「测试」一节）

- **登录**：单用户账号，Token 登录（24 小时有效），首次登录强制提示改密
- **监控项管理**：新增 / 编辑 / 删除监控项（名称、网址、探测间隔秒数，
  间隔范围 5–86400 秒），可对单个监控项暂停 / 启用
- **后台自动探测**：进程内调度器按各监控项自己的间隔发 HTTP 请求，
  逐条记录结果（通/断、状态码、响应毫秒、时间点、失败原因）；
  判通规则为状态码 2xx/3xx，其余状态码、超时与连接失败均判为断；
  管理台里也可点「立即探测」手动测一次
- **看板**：顶部总览（监控项数、当前通/断数、平均可用率），
  每个监控项显示当前状态、最近响应时间、最近 24 小时可用率与探测历史列表
- **公开状态页**：`/status` 免登录只读页面，只展示各监控项名称、当前通/断、
  最近响应时间与探测时间，不返回网址和失败原因等内部信息

## 安装与启动

需要 Python 3.10 或更高版本。

**Linux / macOS（bash）:**

```bash
cd sitepulse
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py            # 默认监听 8000 端口
```

**Windows（PowerShell）:**

```powershell
cd sitepulse
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py        # 默认监听 8000 端口
```

启动后打开 http://localhost:8000 ，默认账号 **admin / admin123**，首次登录会要求改密码。
公开状态页在 http://localhost:8000/status 。

可选环境变量：

| 变量 | 说明 | 默认 |
|---|---|---|
| `PORT` | 监听端口（Windows PowerShell 里用 `$env:PORT=8123` 设置） | 8000 |
| `HOST` | 监听地址。默认只监听本机；需要从其他机器访问时再设为 `0.0.0.0`，放开前请先改掉默认密码 | `127.0.0.1` |
| `SITEPULSE_DB_PATH` | SQLite 数据库文件位置 | 与 app.py 同目录的 `data/sitepulse.db` |
| `SITEPULSE_DISABLE_SCHEDULER` | 设为 `1` 时不启动后台探测调度器（仅测试用） | 未设置 |
| `SP_INITIAL_USERNAME` / `SP_INITIAL_PASSWORD` | 首次启动创建的初始账号 | admin / admin123 |

## 测试

先装测试依赖（两个系统的命令只是路径写法不同）：

```bash
# Linux / macOS
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -q

# Windows（PowerShell）
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests/ -q
```

自动化测试用本地假 HTTP 服务模拟网站的正常、报错、跳转与超时，
不依赖真实网络。另有真实流程自测脚本（起真服务器、监控真实网站
与不存在地址、验证后台调度与公开状态页）：

```bash
.venv/bin/python tests/live_selftest.py
```
