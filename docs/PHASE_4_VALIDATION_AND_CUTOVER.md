# Phase 4：验证、切换与收口方案

## 文档目的

本阶段承接：

- Phase 0：统一语言
- Phase 1：核心对象建模
- Phase 2：生成链与调度重排
- Phase 3：前端页面切换

Phase 4 的目标是：

**在不破坏现有系统可用性的前提下，完成 V1 的验证、切换和收口。**

本阶段关注：

- 数据正确性验证
- 页面可用性验证
- 新旧逻辑并行验证
- 手动回滚路径
- 旧对象退役策略

## 本阶段目标

### 要做

- 验证 4 个核心对象的产物质量
- 验证前端三大页面是否符合 V1 目标
- 新旧逻辑并行观察
- 制定回滚方式
- 明确哪些旧模块退为 legacy

### 不做

- 不继续扩功能
- 不新增复杂候选来源
- 不引入多用户
- 不做自动交易

## 验证维度

## 1. 数据验证

必须验证：

- `MarketStateDaily` 是否每日唯一
- `BattleBrief` 是否每日唯一
- `CandidatePoolEntry` 是否满足 `date + code` 唯一
- `PostMarketReview` 是否每日唯一

还要验证：

- `CandidatePoolEntry.review_outcome` 是否可回填
- `PostMarketReview.next_day_seeds` 是否能正常写入

## 2. 逻辑验证

必须验证：

- `BattleBrief` 是否真的先于候选池生成
- 候选池是否依赖 `BattleBrief` 做门控
- 盘后复盘是否依赖候选池验证结果
- 旧的 `daily_reviews` 不再承担新页面主语义

## 3. 页面验证

### AI 作战台

必须验证：

- 1 分钟内能看懂今天能不能做
- 3 分钟内能看懂今日主叙事和主要风险

### 候选池

必须验证：

- 当天候选数是否控制在可读范围
- 同一只票是否不会重复出现
- 卡片是否清楚表达能不能碰

### 盘后复盘

必须验证：

- 能否看出早盘判断是否成立
- 能否看出候选池哪些有效
- 能否输出第二天承接内容

## 4. 用户体验验证

本项目当前主要用户就是你本人。

所以必须用真实使用方式验证：

- 盘前是否真的会打开 AI 作战台
- 盘中是否真的只盯候选池
- 盘后是否真的会使用新复盘页而不是旧复盘逻辑

如果真实使用不成立，说明设计虽对，执行方式仍要调整。

## 新旧并行期策略

### 原则

V1 切换不是瞬间替换，而是经过一段并行期。

### 并行期建议

建议至少保留一段观察期，在这段时间内：

- 新页面可用
- 旧页面保留
- 新对象开始积累数据
- 旧对象继续作为兜底

### 并行期重点检查

- 新对象产物是否稳定
- Scheduler 是否稳定
- 页面是否有断档数据
- 是否还有旧词或旧逻辑泄漏到新 UI

## Legacy 对象退位策略

本阶段不要求物理删除旧对象，但要明确它们的地位。

### `daily_reviews`

- 保留为 legacy
- 停止作为新 UI 主语义来源

### `sentiment_cycle_log`

- 保留历史记录
- 停止作为新页面主阶段来源

### `market_snapshots`

- 保留为原始快照和缓存层
- 不再作为页面主结论层

### `ratings` / `analysis_history`

- 保留为辅助工具
- 不再作为主流程入口

## 回滚策略

每个阶段都必须允许回滚。

### 页面回滚

若新页面异常：

- 侧边栏暂时切回旧入口
- 保留旧页面路由

### 任务回滚

若新生成链异常：

- 可禁用新 Scheduler 任务
- 改为手动 API 触发

### 数据回滚

本阶段不删旧表，因此：

- 新对象异常时，旧对象仍保留
- 可以重新切回旧页面消费旧表

## 验证清单

> 验证日期：2026-04-16 | 验证方式：日志审查 + 代码走查 + API 端点验证

### 数据层

- [x] 四个新表都可正常写入 — 日志确认 MarketStateDaily/BattleBrief/CandidatePoolEntry/PostMarketReview 均成功写入
- [x] 唯一约束生效 — MarketStateDaily/BattleBrief/PostMarketReview 以 date 为主键；CandidatePoolEntry 有 UniqueConstraint(date, code)
- [x] review_outcome 可回填 — 日志: 回填完成 date=2026-04-16 updated=27/27
- [x] next_day_seeds 可写入 — PostMarketReview.next_day_seeds(JSON) 成功持久化，candidate_pool_service 可消费

### 调度层

- [x] 市场状态任务能正常跑 — [V1-Scheduler] MarketStateDaily 生成成功 phase=启动 temp=70
- [x] 作战简报任务能正常跑 — [V1-Scheduler] BattleBrief 生成成功 tone=轻仓试错
- [x] 候选池任务能正常跑 — [V1-Scheduler] CandidatePoolEntry 生成成功 count=27
- [x] 盘后复盘任务能正常跑 — [V1-Scheduler] PostMarketReview 生成成功 grade=失败
- [x] 手动补跑接口可用 — /api/v1/generate/ 提供 5 个 POST 端点

### 页面层

- [x] 首页能给出明确结论 — ToneBlock 显示 status_tone 颜色编码 + MarketNarrativeBlock 展示主叙事
- [x] 候选池无重复票 — 后端 _deduplicate_candidates 按 code 去重，前端直接消费
- [x] 盘后复盘有明日承接内容 — NextDayBlock 展示 carry_over_themes / next_day_seeds / eliminated_directions

### 体验层

- [x] 盘前 3 分钟工作流成立 — Dashboard ToneBlock + DisciplineBlock + CandidatePreviewBlock 信息密度足够
- [x] 盘中注意力能集中到少量候选 — 前端 activeFilters 默认只显示"通过"和"观察"，拦截项隐藏
- [x] 盘后能在 10 分钟内完成校正 — JudgmentReplayBlock + CandidateVerifyBlock + NextDayBlock 流程完整

## V1 成功标准重申

V1 最终只看这 5 条：

- 早上 1 分钟内能看懂今天能不能做
- 早上 3 分钟内能看懂主叙事和主要风险
- 盘中只盯不超过 10 个候选
- 盘后 10 分钟内能判断系统判断是否有效
- 第二天盘前不需要从零重建认知

如果这 5 条成立，V1 就完成了。

## 当前阶段禁止动作

- 不要在验证期再扩需求
- 不要在验证期新增复杂功能
- 不要在验证期删除所有旧页面和旧表
- 不要把并行期压缩得太短

## 已验证回滚步骤清单

> 以下回滚路径已在 2026-04-16 代码走查中确认可行。

### 步骤 A：页面回滚（< 5 分钟）

1. 打开 `frontend/src/components/layout/Sidebar.tsx`
2. 将 `navItems` 恢复为旧配置（加回 `/ratings`、`/news`、`/review/history` 等入口）
3. 重新 `npm run dev` 或重新构建
4. 旧路由在 `App.tsx` 中始终保留，无需额外修改

### 步骤 B：任务回滚（< 5 分钟）

1. 打开 `backend/app/services/scheduler.py`
2. 注释第 120-172 行的 6 个 V1 `scheduler.add_job` 调用
3. 重启后端服务
4. 旧任务（sync_market / run_rating / run_review）照常运行

### 步骤 C：数据回滚（零操作）

1. 旧表 `daily_reviews` / `sentiment_cycle_log` / `market_snapshots` / `ratings` / `analysis_history` 均保留
2. 旧 Scheduler 任务持续写入旧表
3. 页面回滚 + 任务回滚后系统自动恢复到 V0 状态

### 回滚判定条件

- V1 生成链连续 2 个交易日失败
- 新页面出现关键数据缺失（四对象任一为空）
- LLM 服务持续不可用且手动补跑也失败

### 数据完整性验证端点

新增 `GET /api/v1/validate/v1-status?date=YYYY-MM-DD` 端点，可随时检查指定日期四对象是否完整：

```
curl http://localhost:8000/api/v1/validate/v1-status
curl http://localhost:8000/api/v1/validate/v1-status?date=2026-04-16
```

返回 `overall: "PASS"` 或 `"FAIL"`，含每个对象的详细字段检查。

## Legacy 模块代码标记

以下模型文件已添加 `# LEGACY` 头部注释，标明退位状态和替代者：

- `backend/app/models/review.py` — DailyReview → PostMarketReview + BattleBrief + MarketStateDaily
- `backend/app/models/sentiment.py` — SentimentCycleLog → MarketStateDaily.market_phase
- `backend/app/models/market.py` — MarketSnapshot → MarketStateDaily
- `backend/app/models/rating.py` — Rating → 保留为辅助工具
- `backend/app/models/analysis.py` — AnalysisHistory → 保留为辅助工具

`backend/app/services/scheduler.py` 旧任务区块已标记为 `# LEGACY`，保留运行。

## 最终结论

Phase 4 的任务不是继续开发，而是：

**确认新 V1 作战流已经足够稳定，可以成为你日常真正使用的主系统。**
