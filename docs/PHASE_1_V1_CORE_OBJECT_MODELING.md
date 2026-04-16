# Phase 1：V1 核心对象建模方案

## 文档目的

本阶段承接 Phase 0 的统一词汇工作。

Phase 1 的目标不是重构前端页面，也不是改 Scheduler 时间轴，而是把 V1 的 4 个一等公民对象正式落成后端可用的技术对象：

- `MarketStateDaily`
- `BattleBrief`
- `CandidatePoolEntry`
- `PostMarketReview`

本阶段完成后，项目需要具备：

- 新对象对应的 SQLAlchemy Model
- 新对象对应的 Pydantic Schema
- 新对象的基础服务层骨架
- 新对象的基础 API 骨架
- 新旧表并行运行的能力

## 本阶段目标

### 要做

- 新建 4 个核心对象的 SQLAlchemy Model
- 新建对应的 Pydantic Schema
- 为 4 个对象建立最小可用的 service 骨架
- 新增服务 V1 页面所需的 API 骨架
- 保留旧表，建立新旧并行关系

### 不做

- 不删除旧表
- 不迁移首页到新 UI
- 不重构候选池页面
- 不重构盘后复盘页面
- 不做 Scheduler 重排
- 不实现复杂 LLM 编排
- 不做自动化全链路联调

## 本阶段交付物

完成后，代码库里至少要新增这些文件。

### Models

- `backend/app/models/market_state.py`
- `backend/app/models/battle_brief.py`
- `backend/app/models/candidate_pool.py`
- `backend/app/models/review_outcome.py`

### Schemas

- `backend/app/schemas/market_state.py`
- `backend/app/schemas/battle_brief.py`
- `backend/app/schemas/candidate_pool.py`
- `backend/app/schemas/review_outcome.py`

### Services

- `backend/app/core/market_state_service.py`
- `backend/app/core/battle_brief_service.py`
- `backend/app/core/candidate_pool_service.py`
- `backend/app/core/post_market_review_service.py`
- `backend/app/core/discipline_engine.py`

### APIs

- `backend/app/api/v1/combat_desk.py`
- `backend/app/api/v1/candidate_pool.py`
- `backend/app/api/v1/post_market_review.py`

## V1 四个核心对象定稿

## 1. MarketStateDaily

### 对象职责

记录每日收盘后的客观市场状态，并给出客观机器定调。

它服务：

- AI 作战台的市场状态区
- 盘后复盘中的市场结果对照

### 建议表名

`market_state_daily`

### 字段定稿

- `date`: `Date`, 主键
- `temperature_score`: `Integer`
- `market_phase`: `String(32)`，值必须来自统一枚举
- `style_tag`: `String(32)`，值必须来自统一枚举
- `limit_up_count`: `Integer`
- `limit_down_count`: `Integer`
- `boom_rate`: `Float`
- `highest_ladder`: `Integer`
- `promotion_rate`: `Float`
- `total_volume`: `Integer`
- `volume_delta`: `Integer`
- `focus_sectors`: `JSON`
- `conclusion`: `Text`
- `created_at`: `DateTime`
- `updated_at`: `DateTime`

### 建模约束

- 每日一条
- 收盘后生成
- 允许脚本重算覆盖，但不允许 UI 随意编辑

## 2. BattleBrief

### 对象职责

记录盘前生成的全局作战简报，是当天最高指导文件。

它服务：

- AI 作战台的全局定调区
- 今日叙事区
- 纪律提醒区
- 盘后复盘中的“今日判断回放”

### 建议表名

`battle_briefs`

### 字段定稿

- `date`: `Date`, 主键
- `status_tone`: `String(32)`
- `suggested_position`: `String(32)`
- `overall_conclusion`: `Text`
- `macro_context`: `JSON`
- `main_narrative`: `JSON`
- `bullish_sectors`: `JSON`
- `bearish_sectors`: `JSON`
- `risk_tips`: `JSON`
- `allowed_actions`: `JSON`
- `forbidden_actions`: `JSON`
- `created_at`: `DateTime`
- `updated_at`: `DateTime`

### 建模约束

- 每日一条
- 盘前生成
- 允许人工确认或微调
- 结构化列表优先，不允许大段自由长文成为主字段

## 3. CandidatePoolEntry

### 对象职责

记录当天真正的作战名单，负责承载：

- 为什么选它
- 它现在能不能碰
- 它属于什么主题
- 盘后逻辑是否兑现

它服务：

- AI 作战台的候选池预览
- 候选池页面主体
- 盘后复盘的逐票验证区

### 建议表名

`candidate_pool_entries`

### 字段定稿

- `id`: `Integer`, 主键
- `date`: `Date`, 索引
- `code`: `String(20)`, 索引
- `name`: `String(64)`
- `source_type`: `String(32)`
- `source_reason`: `Text`
- `theme`: `String(128)`
- `thesis`: `Text`
- `gate_status`: `String(32)`
- `gate_reason`: `Text`
- `action_hint`: `String(32)`
- `risk_flags`: `JSON`
- `review_outcome`: `String(32)`，默认 `待复盘`
- `review_note`: `Text`, nullable
- `created_at`: `DateTime`
- `updated_at`: `DateTime`

### 建模约束

- 增加唯一约束：`date + code`
- 同一交易日同一只股票只允许一条记录
- 多来源命中时必须在 service 层先融合，再落一条主记录

## 4. PostMarketReview

### 对象职责

记录盘后全局复盘，不做逐票复盘，而是对当天判断做对账，并输出明日承接。

它服务：

- 盘后复盘的全局对账区
- 盘后复盘的明日承接区

### 建议表名

`post_market_reviews`

### 字段定稿

- `date`: `Date`, 主键
- `brief_grade`: `String(32)`
- `grade_reason`: `Text`
- `actual_market_trend`: `Text`
- `carry_over_themes`: `JSON`
- `next_day_seeds`: `JSON`
- `eliminated_directions`: `JSON`
- `created_at`: `DateTime`
- `updated_at`: `DateTime`

### 建模约束

- 每日一条
- 收盘后生成
- 允许人工检查确认
- `next_day_seeds` 要能直接喂给次日候选池生成流程

## 对象关系

```text
MarketStateDaily (T-1 / T 收盘后生成)
    └── BattleBrief (T 盘前生成)
            └── CandidatePoolEntry (T 盘前融合并门控)
                    └── PostMarketReview (T 盘后生成)
```

### 关系约定

- `MarketStateDaily.date` 与 `BattleBrief.date` 是同一交易日的市场状态与盘前计划配对
- `CandidatePoolEntry.date` 归属于同一交易日
- `PostMarketReview.date` 对应同一交易日
- `PostMarketReview.next_day_seeds` 为下一交易日候选池提供种子输入

## 与现有系统的并行关系

本阶段不删除旧表，采用“新建 + 并行 + 逐步切换”。

| 现有对象 | Phase 1 定位 |
| --- | --- |
| `market_snapshots` | 原始快照层，继续保留 |
| `sentiment_cycle_log` | legacy 情绪日志，停止作为主页面语义输出 |
| `limit_up_boards` | 原始梯队数据源，继续保留 |
| `daily_reviews` | legacy 大杂烩表，后续逐步退役 |
| `watchlists` | 长期观察池，继续保留 |
| `ratings` | 候选生成辅助组件 |
| `analysis_history` | 候选生成辅助组件 |

## 新对象与旧对象的边界

### `watchlists`

保留为长期观察池，不改定位。

它不是候选池，不直接代表当天可操作名单。

### `daily_reviews`

暂时保留，不再继续扩张字段。

后续：

- 盘前内容由 `BattleBrief` 承接
- 盘后全局内容由 `PostMarketReview` 承接

### `sentiment_cycle_log`

暂时保留，不直接服务新页面。

后续其阶段判断由 `MarketStateDaily.market_phase` 取代。

## Schema 设计要求

每个对象至少需要三类 Schema：

### 读取类

用于页面读取。

例如：

- `MarketStateDailyRead`
- `BattleBriefRead`
- `CandidatePoolEntryRead`
- `PostMarketReviewRead`

### 生成类

用于内部生成任务或 API 触发生成。

例如：

- `MarketStateDailyCreate`
- `BattleBriefCreate`
- `CandidatePoolEntryCreate`
- `PostMarketReviewCreate`

### 更新类

用于局部更新。

特别是：

- `CandidatePoolEntryUpdate`
  - 允许更新 `review_outcome`
  - 允许更新 `review_note`
- `PostMarketReviewUpdate`
  - 允许人工修正部分字段

## Service 设计要求

本阶段 service 不要求全自动跑通，但必须建立清晰职责边界。

## 1. `market_state_service.py`

职责：

- 从现有 `market_snapshots`、`limit_up_boards`、情绪计算逻辑中抽取数据
- 组装成 `MarketStateDaily`

## 2. `battle_brief_service.py`

职责：

- 消费最新市场状态和隔夜上下文
- 生成 `BattleBrief`

## 3. `discipline_engine.py`

职责：

- 给候选池做显式规则门控
- 输出 `gate_status`、`gate_reason`、`action_hint`

注意：

- 本阶段先写死规则
- 不做自动学习

## 4. `candidate_pool_service.py`

职责：

- 融合梯队来源、事件来源、Watchlist 来源
- 去重并生成 `CandidatePoolEntry`
- 确保同日同票只留一条

## 5. `post_market_review_service.py`

职责：

- 消费当天 `BattleBrief + MarketStateDaily + CandidatePoolEntry`
- 生成 `PostMarketReview`

## API 设计要求

本阶段 API 只要求骨架清晰，不要求前端立刻全部接入。

### 1. `combat_desk.py`

建议提供：

- `GET /api/v1/combat-desk/today`

返回：

- `market_state`
- `battle_brief`
- `candidate_preview`

### 2. `candidate_pool.py`

建议提供：

- `GET /api/v1/candidates/today`
- `GET /api/v1/candidates?date=YYYY-MM-DD`
- `PUT /api/v1/candidates/{id}`

### 3. `post_market_review.py`

建议提供：

- `GET /api/v1/post-market-review/today`
- `POST /api/v1/post-market-review/run`

## Phase 1 任务顺序

严格按顺序推进。

### Task 1

新增 4 个 SQLAlchemy Model

### Task 2

新增 4 组 Pydantic Schema

### Task 3

将新 Model 注册到现有模型入口中

### Task 4

新增最小 service 骨架

### Task 5

新增最小 API 骨架

### Task 6

实现 `date + code` 唯一约束

### Task 7

编写最小回填脚本或手动创建脚本

### Task 8

用最小样本验证新对象能够完整保存和读取

## Phase 1 验证标准

完成后，必须满足：

- 数据库中存在 4 个新对象对应的表
- 可以成功创建和读取一条 `MarketStateDaily`
- 可以成功创建和读取一条 `BattleBrief`
- 可以成功创建和读取一条 `PostMarketReview`
- `CandidatePoolEntry` 对同日同票能阻止重复写入
- 新 API 能返回基础结构
- 旧页面和旧表仍然能继续运行

## 当前阶段禁止动作

在 Phase 1 结束前，不要做这些事：

- 不要删除 `daily_reviews`
- 不要删除 `sentiment_cycle_log`
- 不要把首页直接大改成新作战台
- 不要同时做 Scheduler 重排
- 不要直接做全链路自动生成
- 不要引入更多候选来源

## 最终结论

Phase 1 的任务不是“做完整 V1”，而是：

**让 V1 的 4 个核心对象在当前项目里正式拥有可用的技术落点。**

这一步做完后，项目才真正具备进入下一阶段的条件：

- Scheduler 重排
- 生成链打通
- 前端页面切换到新对象
