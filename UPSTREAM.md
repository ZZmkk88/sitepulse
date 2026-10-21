# 上游溯源（UPSTREAM）

本项目在设计阶段参考了一个开源网站监控项目。按接力规范记录上游信息如下：

- **source_url**: https://github.com/louislam/uptime-kuma
- **source_commit**: 2adb5bc32cb53a93722a7c348364a8290acd74d4
- **license**: MIT
- **attribution**: Copyright (c) 2021 Louis Lam

## 说明

- `source_commit` 是 2026-10-21 通过 GitHub 接口实查的上游默认分支 HEAD 提交
  （提交说明 "chore: Translations Update from Weblate (#7959)"，提交时间
  2026-10-20）；当日做设计调研时通读的上游源码正是这一提交，包括
  `README.md`、`db/knex_init_db.js`（monitor 表结构）与
  `server/model/heartbeat.js`（探测记录模型及其公开侧字段处理）。
- `attribution` 的版权行逐字复制自上游仓库 `LICENSE` 原文，未做任何改动。
- 本项目代码为独立重写，未复制上游源码；借鉴的是监控项、定时探测、
  探测记录与公开状态页这类核心概念，具体取舍记录见 NOTES.md。
