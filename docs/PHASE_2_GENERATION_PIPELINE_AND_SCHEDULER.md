# Phase 2：生成链与调度重排方案

## 文档目的

本阶段承接：

- Phase 0：统一词汇
- Phase 1：V1 四个核心对象完成技术落点

Phase 2 的目标是：

**把 V1 的四个核心对象放进一个真实可运行的交易日时间轴里，让系统开始按日生成稳定产物。**

本阶段关注的是：

- 生成顺序
- 数据来源
- Scheduler 任务重排
- 手动兜底接口
- 对象之间的依赖关系

本阶段不关注前端页面替换。

## 本阶段目标

### 要做

- 定义 V1 四对象的生成时间轴
- 重排现有 APScheduler 任务
- 打通 `MarketStateDaily -> BattleBrief -> CandidatePoolEntry -> PostMarketReview` 产物链
- 为每个生成节点提供手动触发兜底能力
- 明确每个对象由规则、LLM、人工哪一层生成

### 不做

- 不重构首页 UI
- 不切换前端主页面
- 不删除旧接口
- 不引入复杂盘中自动快照
- 不做自动交易
- 不扩展超出 V1 的候选来源

## V1 交易日产物链

### 全局链路

```text
T-1 / T 收盘后
    └── MarketStateDaily

T 日盘前
    └── BattleBrief
            └── CandidatePoolEntry

T 日盘后
    └── CandidatePoolEntry.review_outcome 回填
            └── PostMarketReview
                    └── next_day_seeds 回流到下一日候选池
```

## 对象生成职责

## 1. MarketStateDaily

### 生成时间

- T 日 `15:30` 收盘后

### 输入来源

- 市场收盘后客观行情
- 涨跌停池
- 炸板池
- 成交额
- 梯队结构

### 生成方式

- 客观指标由规则脚本计算
- `market_phase`
- `style_tag`
- `conclusion`
  由规则优先，LLM 辅助生成

### 锁定策略

- 每日生成后默认锁定
- 允许脚本重新生成覆盖
- 不开放给前端自由编辑

## 2. BattleBrief

### 生成时间

- T 日 `08:00`

### 输入来源

- 最近一期 `MarketStateDaily`
- 隔夜外盘
- 隔夜宏观和行业新闻
- 重点主题信息

### 生成方式

- 由 LLM 生成结构化简报
- 允许人工确认或微调

### 产物定位

这是当天的最高指导文件。

后续：

- 首页定调区
- 纪律提醒区
- 候选池门控
- 盘后对账

都以它为基准。

## 3. CandidatePoolEntry

### 生成时间

- 初筛：T-1 `16:00` 到 T 日 `08:15`
- 门控清洗：T 日 `08:15`

### 输入来源

- 梯队来源
- 事件来源
- Watchlist 匹配来源
- BattleBrief 中的风险红线和当日风格

### 生成方式

- 先由来源服务生成候选原料
- 再由 `candidate_pool_service` 融合
- 再由 `discipline_engine` 亮灯并给出行动倾向

### 硬约束

- 同日同票唯一
- 重复来源必须融合
- 输出必须包含：
  - `gate_status`
  - `gate_reason`
  - `action_hint`

## 4. PostMarketReview

### 生成时间

- T 日 `16:00`

### 输入来源

- 当日 `BattleBrief`
- 当日 `MarketStateDaily`
- 当日 `CandidatePoolEntry.review_outcome`

### 生成方式

- LLM 自动生成全局复盘初稿
- 允许人工检查确认

### 产物定位

- 给当天早盘判断打分
- 输出明日承接主题
- 输出明日种子标的

## 现有 Scheduler 的改造原则

当前项目已经有：

- APScheduler
- 工作日定时任务
- 市场同步
- 新闻同步
- 复盘任务

Phase 2 不需要替换调度框架，只需要重排任务和拆分职责。

## 新的任务组

### A. 市场状态任务组

#### 任务 A1：同步收盘市场数据

- 时间：`15:30`
- 职责：拉取当天收盘后的市场客观数据

#### 任务 A2：生成 MarketStateDaily

- 时间：`15:35`
- 职责：根据客观数据生成 `MarketStateDaily`

### B. 盘前简报任务组

#### 任务 B1：抓取隔夜上下文

- 时间：`07:50`
- 职责：准备外盘、宏观、主题新闻上下文

#### 任务 B2：生成 BattleBrief

- 时间：`08:00`
- 职责：生成当天定调、叙事、风险和纪律红线

### C. 候选池任务组

#### 任务 C1：预生成候选原料

- 时间：T-1 `16:00`
- 职责：整理梯队、事件、观察池来源原料

#### 任务 C2：生成 CandidatePoolEntry

- 时间：T 日 `08:15`
- 职责：融合来源、去重、亮灯、写入候选池

### D. 盘后全局复盘任务组

#### 任务 D1：回填候选验证结果

- 时间：`15:35`
- 职责：将候选池对象更新为盘后验证状态

#### 任务 D2：生成 PostMarketReview

- 时间：`16:00`
- 职责：输出全局复盘与明日承接

## 建议的新调度顺序

```text
07:50  准备隔夜上下文
08:00  生成 BattleBrief
08:15  生成 CandidatePoolEntry

15:30  同步收盘市场数据
15:35  生成 MarketStateDaily
15:35  回填 CandidatePoolEntry.review_outcome
16:00  生成 PostMarketReview
16:00  预生成次日候选原料
```

## 手动兜底策略

即使定时任务失败，也必须支持人工触发。

## 必须存在的手动入口

- 手动生成 `MarketStateDaily`
- 手动生成 `BattleBrief`
- 手动生成 `CandidatePoolEntry`
- 手动回填候选验证结果
- 手动生成 `PostMarketReview`

## API 建议

### 1. 市场状态生成

- `POST /api/v1/generate/market-state`

### 2. 作战简报生成

- `POST /api/v1/generate/battle-brief`

### 3. 候选池生成

- `POST /api/v1/generate/candidates`

### 4. 候选池盘后回填

- `POST /api/v1/generate/candidate-review`

### 5. 盘后全局复盘生成

- `POST /api/v1/generate/post-market-review`

这些接口的目标不是给用户直接使用，而是：

- 调试
- 任务兜底
- 本地排障

## 各对象的规则 / LLM / 人工分工

为了避免系统变成“全 AI 黑盒”，必须明确每个对象由谁主导生成。

## MarketStateDaily

- 规则：主
- LLM：辅
- 人工：基本不参与

## BattleBrief

- 规则：提供输入上下文
- LLM：主
- 人工：可检查和微调

## CandidatePoolEntry

- 规则：主导来源融合和门控
- LLM：辅助生成 `source_reason`、`thesis`、部分解释
- 人工：盘中可局部查看和调整复盘结果

## PostMarketReview

- 规则：提供验证输入
- LLM：主
- 人工：检查确认

## 依赖顺序约束

为了避免循环依赖，必须遵守：

### 约束 1

`BattleBrief` 不能依赖当天 `CandidatePoolEntry`

否则盘前定调会被候选池反向污染。

### 约束 2

`CandidatePoolEntry` 必须依赖 `BattleBrief`

否则候选池就失去“今日作战风格”的门控基准。

### 约束 3

`PostMarketReview` 必须依赖当天 `CandidatePoolEntry.review_outcome`

否则盘后全局复盘没有候选池验证闭环。

## 本阶段任务拆解

### Task 1

重构现有 `scheduler.py` 的任务定义，不改调度框架

### Task 2

实现 4 个对象的生成服务入口函数

### Task 3

给每个入口函数补手动触发 API

### Task 4

定义生成日志和错误处理策略

### Task 5

用最小假数据跑通顺序：

- `MarketStateDaily`
- `BattleBrief`
- `CandidatePoolEntry`
- `PostMarketReview`

## 日志与失败处理

Phase 2 必须增加明确日志。

每个任务至少记录：

- 开始执行时间
- 输入来源是否齐备
- 产出对象写入是否成功
- 若失败，失败在哪一步

不允许只记录“任务失败”这种无效日志。

## Phase 2 验证标准

完成后，必须满足：

- Scheduler 里存在新的 V1 任务顺序
- 每个核心对象都可以通过任务或 API 触发生成
- 4 个对象能按顺序写入数据库
- 候选池可以完成去重和门控亮灯
- 盘后复盘可以消费候选池验证结果
- 即使定时任务失败，也可手动补跑

## 当前阶段禁止动作

- 不切换前端到新页面
- 不删除旧复盘逻辑
- 不引入盘中 30 分钟快照
- 不扩展复杂候选来源
- 不做自动交易闭环

## 最终结论

Phase 2 的目标不是“把界面做出来”，而是：

**让 V1 的四个核心对象开始在真实时间轴里自动生产，并形成完整的交易日数据闭环。**
