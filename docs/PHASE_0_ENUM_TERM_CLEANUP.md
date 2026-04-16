# Phase 0：枚举与旧词汇清理方案

## 文档目的

本阶段不是新增功能，不是新建 V1 四个核心对象，也不是重构前端页面。

本阶段只做一件事：

**统一 `stock-review` 项目里所有与市场阶段、风格判断、策略适用阶段、页面展示阶段相关的词汇。**

做完之后，系统必须只认一套规范语言，为后续 V1 的对象建模、API 和页面替换打地基。

## Phase 0 的唯一目标

把当前项目中的：

- 市场阶段词
- 阶段展示词
- 策略适用阶段词
- 前端页面硬编码阶段词

全部统一成一套规范词。

## 本阶段明确不做什么

### 不做

- 不新增 V1 四张新表
- 不删除旧表
- 不改 Scheduler 时间轴
- 不重构首页
- 不新建候选池页面
- 不新增 BattleBrief、MarketStateDaily、CandidatePoolEntry、PostMarketReview 的实现
- 不做 API 大改
- 不改业务流程

### 只做

- 重构 `backend/app/core/enums.py`
- 修正后端对旧阶段词的引用
- 修正前端硬编码阶段词
- 新增旧数据迁移脚本
- 做最小验证

## 当前问题概述

当前项目中，市场阶段词存在多层混用：

### 1. 内部阶段词

- `冰点`
- `启动`
- `发酵`
- `高潮`
- `高位混沌`
- `分歧`
- `退潮`

### 2. 展示词

- `启动期`
- `发酵期`
- `高潮期`
- `高位混沌期`
- `退潮期`
- `低位混沌期`

### 3. 老旧策略词

- `上升期`

### 4. 现有主要问题

- `冰点` 被映射成 `低位混沌期`
- `分歧` 被映射成 `高位混沌期`
- `DISPLAY_TO_CYCLE_MAP` 不能稳定反推
- 策略初始化和数据库中仍然存在 `上升期`
- 前端页面中仍存在旧阶段词的硬编码

这会直接导致：

- 后端语义漂移
- 前端展示不一致
- 旧数据迁移不稳定
- V1 新对象无法安全建模

## V1 规范词

Phase 0 完成后，全系统只保留以下规范词。

### 市场阶段

- `冰点`
- `启动`
- `发酵`
- `高潮`
- `高位混沌`
- `退潮`

### 风格标签

- `接力优先`
- `趋势优先`
- `轮动试错`
- `防守观察`

### 今日状态

- `可做`
- `轻仓试错`
- `防守观察`
- `不做`

### 候选来源

- `梯队`
- `事件`
- `观察池`

### 门控状态

- `通过`
- `观察`
- `拦截`

### 操作倾向

- `重点跟踪`
- `轻仓试错`
- `观察等待`
- `放弃`

### 盘后逻辑验证结果

- `待复盘`
- `逻辑兑现`
- `时机未到`
- `逻辑证伪`
- `纪律拦截正确`

### 盘后打分

- `成功`
- `部分成功`
- `失败`

## 旧词映射规则

### 单值字段映射

适用于：

- `daily_reviews.market_sentiment`
- `daily_reviews.sentiment_cycle_main`
- `sentiment_cycle_log.cycle_phase`

映射规则如下：

| 旧词 | 规范词 |
| --- | --- |
| `冰点` | `冰点` |
| `低位混沌` | `冰点` |
| `低位混沌期` | `冰点` |
| `启动` | `启动` |
| `启动期` | `启动` |
| `上升期` | `发酵` |
| `发酵` | `发酵` |
| `发酵期` | `发酵` |
| `高潮` | `高潮` |
| `高潮期` | `高潮` |
| `高位混沌` | `高位混沌` |
| `高位混沌期` | `高位混沌` |
| `分歧` | `高位混沌` |
| `高位震荡` | `高位混沌` |
| `退潮` | `退潮` |
| `退潮期` | `退潮` |

### 列表字段映射

适用于：

- `strategies.applicable_cycles`

规则如下：

- 如果元素是 `上升期`，展开成：
  - `启动`
  - `发酵`
  - `高潮`
- `分歧` 映射为 `高位混沌`
- 其余元素按单值映射规则处理
- 最终结果必须：
  - 去空值
  - 去重
  - 保序
  - 只保留规范词

## 需要修改的文件

### 后端

- `backend/app/core/enums.py`
- `backend/app/core/sentiment_engine.py`
- `backend/app/core/review_engine.py`
- `backend/app/core/strategy_matcher.py`
- `backend/app/services/seed.py`
- `backend/app/api/v1/review.py`

### 前端

- `frontend/src/pages/DailyReview.tsx`
- `frontend/src/pages/ReviewHistory.tsx`
- `frontend/src/pages/Strategies.tsx`

### 迁移脚本

- `backend/scripts/migrate_phase_v1_terms.py`

## 任务拆解

### Task 1：重构 `enums.py`

目标文件：

- `backend/app/core/enums.py`

要求：

- 删除不稳定的展示词映射逻辑
- 定义统一常量：
  - `MARKET_PHASES`
  - `STYLE_TAGS`
  - `STATUS_TONES`
  - `SOURCE_TYPES`
  - `GATE_STATUSES`
  - `ACTION_HINTS`
  - `REVIEW_OUTCOMES`
  - `BRIEF_GRADES`
- 增加 helper：
  - `normalize_market_phase(raw: str) -> str`
  - `normalize_market_phase_list(raw_list: list[str]) -> list[str]`

要求：

- `normalize_market_phase` 负责单值规范化
- `normalize_market_phase_list` 负责列表规范化、展开 `上升期`、去重和保序

### Task 2：修正后端引用点

目标文件：

- `backend/app/core/sentiment_engine.py`
- `backend/app/core/review_engine.py`
- `backend/app/core/strategy_matcher.py`
- `backend/app/services/seed.py`
- `backend/app/api/v1/review.py`

要求：

- 所有阶段词输出必须只使用规范词
- 不允许继续返回：
  - `低位混沌期`
  - `分歧`
  - `上升期`
  - `震荡`
- `strategy_matcher` 先做 normalize 再匹配
- `seed.py` 初始化策略时不允许再使用 `上升期`

### Task 3：修正前端页面硬编码词

目标文件：

- `frontend/src/pages/DailyReview.tsx`
- `frontend/src/pages/ReviewHistory.tsx`
- `frontend/src/pages/Strategies.tsx`

要求：

- 所有阶段常量只保留：
  - `冰点`
  - `启动`
  - `发酵`
  - `高潮`
  - `高位混沌`
  - `退潮`
- 删除：
  - `低位混沌期`
  - `分歧`
  - `上升期`

### Task 4：新增迁移脚本

新增文件：

- `backend/scripts/migrate_phase_v1_terms.py`

要求：

- 支持 `--dry-run`
- 默认支持真实执行
- 输出每张表受影响记录数
- 输出每张表最终更新数

覆盖表：

- `daily_reviews`
- `sentiment_cycle_log`
- `strategies`

覆盖字段：

- `daily_reviews.market_sentiment`
- `daily_reviews.sentiment_cycle_main`
- `sentiment_cycle_log.cycle_phase`
- `strategies.applicable_cycles`

### Task 5：最小验证

要求：

- Python 文件通过 `py_compile`
- 数据库不再残留主要旧词
- 页面核心区域仍然可以正常读取阶段词

## 建议实施顺序

严格按照以下顺序执行：

1. 改 `backend/app/core/enums.py`
2. 改后端引用点
3. 改前端常量
4. 写迁移脚本
5. 先用 `--dry-run` 检查影响范围
6. 再执行真实迁移
7. 跑验证命令
8. 手工打开关键页面检查

不要先跑迁移再改代码。

## 推荐验证命令

### Python 语法验证

```bash
cd /Users/zhanzhao/项目/stock-review/backend
python -m py_compile \
  app/core/enums.py \
  app/core/sentiment_engine.py \
  app/core/review_engine.py \
  app/core/strategy_matcher.py \
  app/services/seed.py \
  app/api/v1/review.py
```

### 数据库旧词残留检查

```bash
sqlite3 /Users/zhanzhao/项目/stock-review/backend/data/stock_review.db "
select 'daily_reviews.market_sentiment', count(*) from daily_reviews where market_sentiment in ('低位混沌','低位混沌期','启动期','上升期','发酵期','高潮期','分歧','高位震荡','高位混沌期','退潮期')
union all
select 'daily_reviews.sentiment_cycle_main', count(*) from daily_reviews where sentiment_cycle_main in ('低位混沌','低位混沌期','启动期','上升期','发酵期','高潮期','分歧','高位震荡','高位混沌期','退潮期')
union all
select 'sentiment_cycle_log.cycle_phase', count(*) from sentiment_cycle_log where cycle_phase in ('低位混沌','低位混沌期','启动期','上升期','发酵期','高潮期','分歧','高位震荡','高位混沌期','退潮期');
"
```

### 策略阶段检查

```bash
sqlite3 /Users/zhanzhao/项目/stock-review/backend/data/stock_review.db "
select id, name, applicable_cycles from strategies;
"
```

人工确认 `applicable_cycles` 中只剩规范词。

## 成功标准

Phase 0 完成后，必须满足：

- 后端只认规范阶段词
- 前端只展示规范阶段词
- 策略适用阶段不再出现 `上升期`
- 数据库中不再残留主要旧词
- 当前复盘页、历史页、策略页仍能正常使用

## 风险点

### 风险 1：直接把旧值改成英文 code

当前项目前后端仍大量直接使用中文值，不适合在 Phase 0 直接切英文 code。

Phase 0 只做中文规范化。

### 风险 2：把 `上升期` 粗暴映射成单阶段

在 `strategies.applicable_cycles` 中，`上升期` 不能粗暴映射成单一阶段，必须展开成：

- `启动`
- `发酵`
- `高潮`

### 风险 3：迁移顺序错误

如果先跑数据库迁移，再改代码和前端页面，会造成旧页面读新值失败或逻辑判断漂移。

## 最终结论

Phase 0 不是重构功能，而是统一语言。

这一步完成后，项目才具备安全进入下一阶段的条件：

- 新建 V1 四个核心对象
- 重排 Scheduler 任务
- 重构三大主页面

一句话：

**Phase 0 的任务就是让整个系统只说一种话。**
