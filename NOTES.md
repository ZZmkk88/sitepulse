# sitepulse 调研笔记（开工记录）

## 参考对象调研（2026-10-21，经 GitHub 接口实查）

参考对象：Uptime Kuma（github.com/louislam/uptime-kuma，MIT）。
当日实查的上游状态：默认分支 HEAD 提交
`2adb5bc32cb53a93722a7c348364a8290acd74d4`（2026-10-20），
LICENSE 版权行为 `Copyright (c) 2021 Louis Lam`。

通读过的上游材料：

- `README.md`：功能清单（HTTP(s)/TCP/关键字等多种探测类型、通知、
  20 秒级间隔、多个公开状态页、响应时间图表、证书信息等）。
- `db/knex_init_db.js` 的 monitor 表：核心字段为 name、active、interval
  （默认 20 秒）、url、type、created_date，另有大量高级字段
  （maxretries、accepted_statuscodes_json 默认 `["200-299"]`、
  retry_interval、method/headers/body、ignore_tls 等）。
- `server/model/heartbeat.js`：每次探测记一条 heartbeat，字段含
  monitor_id、status（0=断 DOWN、1=通 UP、2=待定、3=维护）、time、
  msg（失败原因）、ping（响应毫秒）、duration、retries；
  其 `toPublicJSON()` 对公开侧只给 status / time / ping，
  **特意把 msg 置空隐藏**——公开状态页不泄露内部失败细节，
  这一点本项目照此办理。

## 本项目的取舍（只借核心，自行实现）

- 只做 HTTP(s) 探测一种类型；TCP、关键字、证书、通知、多状态页、
  重试策略等高级功能不进 MVP。
- 数据模型收敛为两张表：monitors（name / url / interval_seconds /
  active / created_at）与 checks（status / status_code / response_ms /
  error / checked_at），字段命名与结构均为自拟。
- 判通规则按任务书：2xx/3xx 为通，其余状态码与超时、连接失败为断
  （比上游默认只认 200-299 略宽，按任务要求执行并在此注明）。
- 可用率口径：最近 24 小时内 checks 中通的占比。
- 探测实现：Python 标准库 urllib（跟随重定向、10 秒超时），
  调度器为进程内 asyncio 循环，不用任何外部队列/缓存服务。
- 界面为自行设计的单页（顶部总览条 + 监控卡片墙 + 历史流水），
  与原版的侧栏布局明显不同。

## 资源核对（开工前）

云端实测：2 核 CPU、内存 7.7G、无 GPU、Python 3.12.3。
本项目栈为 FastAPI + SQLite + 单页前端，后台探测是每分钟量级的
少量 HTTP 请求，CPU/内存占用远低于云端余量。结论：带得动。

## 沿用的既有做法

登录体系沿用本团队 bookmark-manager 已实测的方案：
pbkdf2_hmac(sha256, 200000 次) + 随机盐、sessions 表存 Token
（24 小时过期）、首次登录强制提示改密、默认账号 admin/admin123。
依赖版本与该项目实测钉死的版本保持一致。
