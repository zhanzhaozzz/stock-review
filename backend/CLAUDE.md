[根目录](../../CLAUDE.md) > **backend**

# Backend - Python FastAPI 后端服务

> 股票复盘系统的后端 API 服务，提供数据采集、量化评级、情绪周期判断、复盘生成等核心功能。

---

## 模块职责

- REST API 服务：市场数据、评级、自选股、新闻、复盘、策略等端点
- 定时任务：收盘后自动同步数据、执行评级和复盘
- 数据采集：多源数据获取（AKShare/Tushare/efinance）
- LLM 集成：量化评级、情绪判断、复盘总结

---

## 入口与启动

```bash
# 开发模式
cd backend
pip install -r requirements.txt
python main.py  # 启动在 http://localhost:8000

# 或使用 uvicorn
uvicorn main:app --reload --port 8000
```

**启动流程** (`main.py`):
1. 初始化数据库 (`init_db`)
2. 运行种子数据 (`run_seed`)
3. 连接 Redis 缓存
4. 启动定时任务调度器 (`setup_scheduler`)
5. 挂载 API 路由和静态文件

---

## 对外接口

### API 路由 (`api/v1/router.py`)

| 路径 | 模块 | 功能 |
|-----|------|------|
| `/api/v1/market` | market.py | 市场总览、板块排行、涨停梯队 |
| `/api/v1/ratings` | ratings.py | 股票评级查询与历史 |
| `/api/v1/watchlist` | watchlist.py | 自选股管理 |
| `/api/v1/news` | news.py | 新闻聚合与搜索 |
| `/api/v1/review` | review.py | 每日复盘生成与管理 |
| `/api/v1/strategies` | strategy.py | 交易策略管理 |
| `/api/v1/operations` | operations.py | 操作记录管理 |
| `/api/v1/sync` | sync.py | 手动同步触发 |
| `/api/v1/analysis` | analysis.py | AI 分析报告 |

### 核心端点示例

```python
# 复盘 API (review.py)
POST /api/v1/review/run      # 触发当日复盘
GET  /api/v1/review/today    # 获取今日复盘
GET  /api/v1/review/list     # 历史复盘列表
PUT  /api/v1/review/{id}     # 编辑复盘

# 情绪周期
GET  /api/v1/review/sentiment          # 情绪周期日志
GET  /api/v1/review/sentiment/current  # 当前情绪阶段
```

---

## 关键依赖与配置

### 主要依赖 (`requirements.txt`)

| 包名 | 用途 |
|-----|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| sqlalchemy | ORM |
| aiosqlite | 异步 SQLite |
| redis | 缓存客户端 |
| akshare | A 股数据源 (主) |
| tushare | 股票数据源 (辅) |
| efinance | 东方财富数据源 |
| litellm | LLM 统一调用 |
| apscheduler | 定时任务调度 |
| pandas/numpy | 数据处理 |

### 配置项 (`config.py`)

```python
# 数据源
DATA_PROVIDER_PRIORITY = "akshare,tushare,efinance"
TUSHARE_TOKEN = ""

# LLM
DEEPSEEK_API_KEY = ""
ZHIPUAI_API_KEY = ""
RATING_LLM_MODELS = "deepseek/deepseek-chat,zhipu/glm-4-flash"
ANALYSIS_LLM_MODEL = "deepseek/deepseek-chat"

# 定时任务
REFRESH_HOUR = 15    # 收盘后同步
REFRESH_MINUTE = 30
```

---

## 数据模型

### 核心 ORM 模型 (`models/`)

| 模型 | 表名 | 用途 |
|-----|------|------|
| Stock | stocks | 股票基础信息 |
| StockPrice | stock_prices | 日线行情 |
| Rating | ratings | 量化评级结果 |
| DailyReview | daily_reviews | 每日复盘记录 |
| LimitUpBoard | limit_up_boards | 涨停梯队快照 |
| SentimentCycleLog | sentiment_cycle_log | 情绪周期日志 |
| Watchlist | watchlists | 自选股 |
| NewsCache | news_cache | 新闻缓存 |
| Strategy | strategies | 交易策略 |
| OperationRecord | operation_records | 操作记录 |

---

## 核心业务引擎

### 1. 量化评级引擎 (`core/rating_engine.py`)

六维技术因子评分：
- 趋势 (Trend): 均线排列、MA 斜率、ADX
- 动量 (Momentum): RSI、MACD、KDJ
- 波动率 (Volatility): 年化波动率、布林带、ATR
- 成交量 (Volume): 量比、OBV、VWAP
- 价值 (Value): 区间位置、筹码集中度
- 情绪 (Sentiment): 新闻关键词 + LLM 评分

融合权重：
```
量化 35% + 基本面 25% + AI 25% + 情绪 15%
```

### 2. 情绪周期引擎 (`core/sentiment_engine.py`)

情绪周期阶段：
```
冰点 -> 启动 -> 发酵 -> 高潮 -> (高位混沌) -> 分歧 -> 退潮 -> 冰点
```

判断依据：
- 市场高度（连板层数）
- 涨停数量
- 炸板率
- 龙头状态
- 前日周期（用于状态转移）

### 3. 复盘引擎 (`core/review_engine.py`)

工作流：
1. 获取涨停梯队数据
2. 获取市场总览快照
3. 情绪周期判断
4. 识别主线板块
5. LLM 生成复盘总结
6. 写入 daily_reviews 表

### 4. 数据获取管理器 (`data_provider/manager.py`)

多源 failover 机制：
```python
# 按优先级依次尝试
priority = ["akshare", "tushare", "efinance"]
for fetcher in ordered_fetchers:
    result = await fetcher.get_daily(code, days)
    if result:
        return result
```

---

## 定时任务 (`services/scheduler.py`)

| 任务 | 触发时间 | 功能 |
|-----|---------|------|
| sync_market | 15:30 | 同步市场总览 |
| sync_news | 每小时 9-20 | 同步新闻 |
| sync_watchlist | 15:35 | 同步自选股行情 |
| run_rating | 15:40 | 执行自选股评级 |
| run_review | 15:50 | 执行每日复盘 |

---

## 测试与质量

**当前状态**: 无测试文件。

**建议补充**:
- `tests/test_rating_engine.py` - 评级计算单元测试
- `tests/test_sentiment_engine.py` - 情绪周期判断测试
- `tests/test_api/` - API 端点集成测试

---

## 常见问题 (FAQ)

### Q: 如何添加新的数据源？

1. 继承 `BaseFetcher` 类
2. 实现 `get_daily()` 和 `get_realtime_quote()` 方法
3. 在 `manager.py` 中注册到 `_fetchers` 字典
4. 更新 `DATA_PROVIDER_PRIORITY` 配置

### Q: 如何添加新的评级因子？

1. 在 `rating_engine.py` 中添加计算函数（如 `calc_xxx()`）
2. 更新 `QUANT_WEIGHTS` 权重字典
3. 在 `rate_stock()` 中调用并汇总

### Q: 定时任务不执行？

检查：
1. `REFRESH_HOUR`/`REFRESH_MINUTE` 配置是否正确
2. APScheduler 日志是否报错
3. 确保数据库中有股票/自选股数据

---

## 相关文件清单

```
backend/
├── main.py                          # 应用入口
├── requirements.txt                 # 依赖清单
├── app/
│   ├── __init__.py
│   ├── config.py                    # 配置管理
│   ├── database.py                  # 数据库连接
│   ├── cache.py                     # Redis 缓存
│   ├── api/v1/
│   │   ├── router.py                # 路由汇总
│   │   ├── market.py                # 市场 API
│   │   ├── review.py                # 复盘 API
│   │   ├── ratings.py               # 评级 API
│   │   ├── watchlist.py             # 自选股 API
│   │   ├── news.py                  # 新闻 API
│   │   ├── strategy.py              # 策略 API
│   │   ├── operations.py            # 操作记录 API
│   │   ├── sync.py                  # 同步 API
│   │   └── analysis.py              # 分析 API
│   ├── core/
│   │   ├── rating_engine.py         # 量化评级引擎
│   │   ├── sentiment_engine.py      # 情绪周期引擎
│   │   ├── review_engine.py         # 复盘生成引擎
│   │   ├── strategy_matcher.py      # 战法匹配
│   │   ├── limit_up_tracker.py      # 涨停梯队追踪
│   │   ├── stock_analyzer.py        # 股票分析器
│   │   └── analysis_pipeline.py     # 分析流水线
│   ├── data_provider/
│   │   ├── manager.py               # 数据源管理器
│   │   ├── base.py                  # 基类
│   │   ├── akshare_fetcher.py       # AKShare 数据源
│   │   ├── tushare_fetcher.py       # Tushare 数据源
│   │   ├── efinance_fetcher.py      # efinance 数据源
│   │   ├── realtime.py              # 实时行情
│   │   └── fundamental.py           # 基本面数据
│   ├── llm/
│   │   ├── client.py                # LLM 客户端
│   │   ├── multi_model.py           # 多模型融合
│   │   └── prompts/
│   │       ├── rating.py            # 评级 Prompt
│   │       ├── analysis.py          # 分析 Prompt
│   │       └── review.py            # 复盘 Prompt
│   ├── models/
│   │   ├── __init__.py              # 模型导出
│   │   ├── stock.py                 # 股票模型
│   │   ├── rating.py                # 评级模型
│   │   ├── review.py                # 复盘模型
│   │   ├── sentiment.py             # 情绪周期模型
│   │   ├── watchlist.py             # 自选股模型
│   │   ├── news.py                  # 新闻模型
│   │   ├── strategy.py              # 策略模型
│   │   └── ...
│   ├── news/
│   │   ├── aggregator.py            # 新闻聚合器
│   │   ├── base.py                  # 基类
│   │   ├── cls_collector.py         # 财联社采集
│   │   ├── eastmoney_collector.py   # 东方财富采集
│   │   └── sina_collector.py        # 新浪采集
│   ├── schemas/                     # Pydantic 模型
│   └── services/
│       ├── scheduler.py             # 定时任务
│       └── seed.py                  # 种子数据
└── Dockerfile
```

---

## 变更记录 (Changelog)

### 2026-03-31 - 初始化扫描

- 完成后端模块结构梳理
- 识别 9 个核心业务模块
- 记录 74 个 Python 文件
