# Stock Review — 项目说明文档 & 技术方案

> 最后更新: 2026-03-31

---

## 一、项目定位

**个人每日复盘炒股系统**，面向 A 股 + 港股个人投资者，覆盖从收盘复盘到次日计划的完整决策链路：

**核心流程：** `看大盘 → 看板块 → 看自选 → 看新闻 → 做决策`

**设计理念：**
- 数据源多路冗余，自动降级，保证非交易时段也能查看数据
- AI 辅助而非 AI 替代，人工确认后才算复盘完成
- 轻量部署，SQLite + Redis，单台机器即可运行

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (端口 80)                          │
│                    反向代理 + 静态资源                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   FastAPI 后端 (端口 8001)                       │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 市场数据  │  │ 量化评级  │  │ AI 分析   │  │  定时任务调度器   │ │
│  │ 采集+缓存 │  │ 六维因子  │  │ LLM 多模型│  │  APScheduler    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 新闻聚合  │  │ 每日复盘  │  │ 自选股    │  │  板块/成分股     │ │
│  │ 三路采集  │  │ 结构化表单│  │ 管理+行情 │  │  下钻查询        │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└──┬──────────────────┬──────────────────┬───────────────────────┘
   │                  │                  │
   ▼                  ▼                  ▼
┌────────┐     ┌────────────┐     ┌────────────┐
│ SQLite │     │   Redis    │     │  外部数据源  │
│ 持久存储│     │   热缓存   │     │ AKShare     │
│        │     │            │     │ Tushare     │
│        │     │            │     │ 东财/腾讯API │
└────────┘     └────────────┘     │ LLM 服务商   │
                                  └────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                React 前端 (Vite, 端口 3000)                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐ │
│  │市场  │ │自选股│ │每日  │ │历史  │ │设置  │ │StockDrawer  │ │
│  │总览  │ │管理  │ │复盘  │ │复盘  │ │主题  │ │侧边详情面板  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────────┘ │
│  Zustand 状态管理 · Tailwind CSS 4 双主题 · Recharts 图表       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、技术栈详情

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **后端框架** | FastAPI | latest | 异步 REST API |
| **ORM** | SQLAlchemy | 2.x | 异步模式 (aiosqlite) |
| **数据库** | SQLite | 3 | 文件级数据库，零运维 |
| **缓存** | Redis | 7+ | 热数据缓存，交易/非交易时段差异 TTL |
| **定时任务** | APScheduler | 3.x | 工作日 Cron 触发 |
| **数据源** | AKShare + Tushare + efinance | — | 多路 fallback + 腾讯/东财直接 API |
| **LLM** | LiteLLM | latest | 统一路由 DeepSeek/GLM/Kimi/Qwen |
| **前端框架** | React | 19 | 函数式组件 + Hooks |
| **构建工具** | Vite | 6.x | HMR + 生产构建 |
| **CSS** | Tailwind CSS | 4.x | CSS-first 配置，`@theme` 扩展 |
| **图表** | Recharts | latest | K 线、雷达图、趋势图 |
| **状态管理** | Zustand | latest | 主题 + 全局状态 |
| **部署** | Docker Compose | — | Nginx + Backend + Redis |

---

## 四、数据库模型 (16 张表)

| 模型 | 表名 | 职责 | 关键字段 |
|------|------|------|----------|
| `Stock` | `stocks` | 股票基础信息 | code, name, market, sector, industry |
| `StockPrice` | `stock_prices` | 日线历史 | code, date, OHLCV, change_pct |
| `StockFundamental` | `stock_fundamentals` | 基本面快照 | PE/PB/ROE/EPS, 资金流, 量比, 多周期涨跌幅 |
| `Rating` | `ratings` | 量化评级结果 | 六维因子分 + AI 分 + 总分 + 评级标签 |
| `AnalysisHistory` | `analysis_history` | AI 分析报告 | raw_result(JSON), score, advice, 目标价/止损 |
| `Watchlist` | `watchlists` | 自选股列表 | user_id, code, group_name, sort_order |
| `NewsCache` | `news_cache` | 新闻缓存 | title, source, summary, related_codes |
| `DailyReview` | `daily_reviews` | 每日复盘记录 | 情绪周期, 梯队数据, AI 草稿, 人工编辑 |
| `LimitUpBoard` | `limit_up_boards` | 涨停板梯队 | board_count, code, sector, is_broken |
| `Strategy` | `strategies` | 战法库 | name, applicable_cycles, 规则描述 |
| `SentimentCycleLog` | `sentiment_cycle_log` | 情绪周期日志 | date, cycle_phase, market_height |
| `OperationRecord` | `operation_records` | 操作记录 | strategy, stock, action, pnl_pct |
| `User` | `users` | 用户 | username, hashed_password, is_admin |
| `LLMUsage` | `llm_usage` | LLM 调用统计 | model, tokens, purpose |
| `MarketSnapshot` | `market_snapshots` | 市场快照 | snapshot_type, data(JSON) |

---

## 五、API 端点总览 (共 45+ 端点)

基础路径: `/api/v1`

### 5.1 市场数据 (`/market`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/overview` | 大盘指数 + 涨跌面 |
| GET | `/breadth` | 涨跌面统计 |
| GET | `/sectors` | 板块排行 (concept/industry) |
| GET | `/sectors/{name}/constituents` | **板块成分股列表** |
| GET | `/money-flow` | 行业资金流向 |
| GET | `/index/{code}/history` | 指数历史 K 线 |
| GET | `/limit-up` | 涨停板梯队 |
| GET | `/quote/{code}` | 单股实时行情 |
| GET | `/stock/{code}/daily` | 个股日线 (SQLite + 外部补齐) |
| GET | `/fundamental/{code}` | 个股基本面快照 |

### 5.2 量化评级 (`/ratings`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/run` | 执行量化评级 |
| GET | `/latest` | 最新评级列表 |
| GET | `/history/{code}` | 单股评级历史 |
| GET | `/scan` | 全市场扫描评级 |

### 5.3 自选股 (`/watchlist`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 自选股列表 |
| POST | `/` | 批量添加 |
| DELETE | `/{code}` | 删除 |
| PUT | `/{code}` | 更新备注/分组 |
| GET | `/groups` | 分组列表 |
| GET | `/search` | 股票搜索 |

### 5.4 数据同步 (`/sync`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/all` | 全量同步 |
| POST | `/market` | 市场数据 |
| POST | `/news` | 新闻 |
| POST | `/watchlist-quotes` | 自选股行情 |
| POST | `/fundamentals` | 基本面数据 |

### 5.5 AI 分析 (`/analysis`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/analyze` | 运行 AI 分析 |
| GET | `/history` | 分析历史 |
| GET | `/{record_id}` | 分析详情 |

### 5.6 每日复盘 (`/review`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate` | 生成复盘草稿 |
| GET | `/today` | 今日复盘 |
| GET | `/list` | 复盘列表 |
| GET | `/date/{date}` | 指定日期复盘 |
| PUT | `/{id}` | 编辑复盘 |
| GET | `/sentiment` | 情绪周期日志 |

### 5.7 战法库 (`/strategies`) / 操作记录 (`/operations`)

| 模块 | 端点数 | 说明 |
|------|--------|------|
| 战法库 | 5 | CRUD + 推荐匹配 |
| 操作记录 | 5 | CRUD + 统计 |

---

## 六、前端页面与组件

### 6.1 当前启用的页面

| 路由 | 页面 | 状态 | 说明 |
|------|------|------|------|
| `/` | Dashboard | ✅ 已完善 | 大盘指数卡片 + 涨跌面 + 板块排行（可展开成分股） |
| `/watchlist` | Watchlist | ✅ 已完善 | 自选股表格 + 搜索添加 + 分组筛选 + StockDrawer |
| `/review` | DailyReview | ✅ 已完善 | 结构化复盘表单 + 梯队数据 + AI 草稿 + 人工编辑 |
| `/review/history` | ReviewHistory | ✅ 已完善 | 日历视图 + 情绪趋势图 + 复盘列表 |
| `/stock/:code` | StockDetail | ✅ 已完善 | 个股全维度分析（K线 + 雷达 + 估值 + 资金 + AI） |
| `/settings` | Settings | ✅ 已完善 | 外观切换 + 系统状态 + 数据同步 + 定时任务 |

### 6.2 暂时隐藏的页面（功能已实现，侧边栏未展示）

| 路由 | 页面 | 说明 |
|------|------|------|
| `/ratings` | RatingBoard | 量化评级看板 |
| `/news` | News | 新闻聚合 |
| `/strategies` | Strategies | 战法库 |
| `/operations` | Operations | 操作记录 |

### 6.3 核心共享组件

| 组件 | 文件 | 说明 |
|------|------|------|
| `Shell` | `layout/Shell.tsx` | 页面骨架 (侧边栏 + 内容区) |
| `Sidebar` | `layout/Sidebar.tsx` | 左侧导航 |
| `StockDrawer` | `StockDrawer.tsx` | 右侧抽屉：总评分卡 + K 线 + 估值 + 资金流 + 微观 + 雷达 + AI 分析 |
| `MiniKLine` | `charts/MiniKLine.tsx` | K 线折线图 |
| `RadarChart` | `charts/RadarChart.tsx` | 六维雷达图 |
| `SentimentTrend` | `charts/SentimentTrend.tsx` | 情绪周期趋势图 |

### 6.4 主题系统

- **双主题**: 浅色 (`:root`) + 深色 (`.dark`)
- **CSS 变量**: 通过 `index.css` 定义 20+ 语义化变量
- **Tailwind v4**: 通过 `@theme` 映射为自定义颜色（`bg-card`, `text-muted`, `border-edge` 等）
- **Zustand**: `useAppStore` 管理 theme 状态，持久化到 localStorage
- **默认**: 深色模式

---

## 七、数据流架构

### 7.1 数据采集链路

```
定时任务 / 手动触发
        │
        ▼
┌─────────────────────────────────────────────┐
│          DataFetcherManager                  │
│  优先级: AKShare → Tushare → efinance       │
│  兜底:   腾讯K线 API (get_daily)             │
│  实时:   腾讯行情 → 新浪行情 → fetchers     │
│  基本面: 东财 push2 → 腾讯 QT (fallback)    │
└─────────────┬───────────────────────────────┘
              │
              ▼
        ┌──────────┐     ┌──────────┐
        │  SQLite  │◄───▶│  Redis   │
        │ 持久存储  │     │ 热缓存   │
        └──────────┘     └──────────┘
```

### 7.2 分析链路

```
个股代码
    │
    ├─► 技术分析 (MA/MACD/RSI/布林/量价/支撑阻力)
    ├─► 基本面采集 (PE/PB/ROE/资金流)
    ├─► 新闻采集 (财联社/东财/新浪 → LLM 过滤)
    │
    ▼
 LLM 多模型融合 (LiteLLM)
    │
    ▼
 结构化分析报告 (信号/评分/目标价/止损/要点/风险)
```

### 7.3 复盘链路

```
收盘后 (15:30 定时)
    │
    ├─► 同步市场数据 (指数 + 涨跌面 + 板块)
    ├─► 同步涨停梯队 (连板层级结构化)
    ├─► 判断情绪周期 (规则 + AI)
    ├─► 匹配适用战法
    │
    ▼
 生成复盘草稿 (AI)
    │
    ▼
 人工审核修改 → 保存确认
```

---

## 八、定时任务调度

时区: `Asia/Shanghai`，仅工作日执行

| 时间 | 任务 | 说明 |
|------|------|------|
| 15:30 | sync_market | 同步大盘 + 板块 + 涨跌面 |
| 每小时 (9-20) | sync_news | 新闻采集 |
| 15:35 | sync_watchlist | 同步自选股行情 |
| 15:40 | run_rating | 自选股量化评级 |
| 15:50 | run_review | 自动生成复盘草稿 |

---

## 九、已完成功能清单

### 后端 ✅

- [x] 多数据源 fallback 体系 (AKShare/Tushare/efinance/腾讯/东财)
- [x] 大盘指数 + 涨跌面统计
- [x] 概念/行业板块排行
- [x] **板块成分股下钻查询**
- [x] 个股日线历史（SQLite 缓存 + 外部补齐）
- [x] 个股基本面采集（东财 push2 + 腾讯 QT fallback）
- [x] 多周期涨跌幅计算
- [x] 实时行情（腾讯 → 新浪 → fetchers）
- [x] 六维量化评级引擎
- [x] AI 分析流水线（技术 + 新闻 + LLM）
- [x] 涨停板梯队追踪
- [x] 情绪周期判断（规则 + AI）
- [x] 每日复盘自动生成
- [x] 新闻三路采集 + LLM 过滤
- [x] 战法库 CRUD + 匹配推荐
- [x] 操作记录 CRUD + 统计
- [x] 自选股管理（搜索、分组、CRUD）
- [x] Redis 热缓存（交易/非交易差异 TTL）
- [x] APScheduler 定时任务
- [x] Docker Compose 部署方案
- [x] 基本面数据同步接口

### 前端 ✅

- [x] 市场总览仪表盘（指数卡片 + 涨跌面 + 板块排行）
- [x] **板块成分股展开（点击板块行展开个股列表）**
- [x] 自选股管理（搜索添加、删除、分组筛选、行情刷新）
- [x] **StockDrawer 右侧抽屉**（总评分卡 + K 线 + 估值 + 资金 + 微观 + 雷达 + AI）
- [x] StockDetail 完整分析页
- [x] 每日复盘表单（梯队 + 情绪 + AI 草稿 + 人工编辑）
- [x] 历史复盘（日历视图 + 趋势图 + 列表）
- [x] **浅色/深色主题切换**
- [x] Settings 系统设置（外观 + 状态 + 同步 + 定时任务说明）
- [x] 新闻聚合页面（已实现，暂隐藏）
- [x] 量化评级看板（已实现，暂隐藏）
- [x] 战法库管理（已实现，暂隐藏）
- [x] 操作记录（已实现，暂隐藏）

---

## 十、后续待实现功能

### 优先级 P0 — 核心体验

| 编号 | 功能 | 说明 | 涉及模块 |
|------|------|------|----------|
| P0-1 | **量化评级看板重构** | 参考 real-estate-stocks-picker 的评级卡片 + 排序筛选 + 评级趋势，放开 `/ratings` 页面 | 前端 RatingBoard |
| P0-2 | **评级结果可视化** | 自选股列表中内嵌评级 badge + 评分趋势 sparkline | 前端 Watchlist |
| P0-3 | **StockDrawer 评级趋势** | 抽屉底部增加近 30 天评分趋势折线图（类似 DetailPanel 的评分趋势图） | 前端 StockDrawer |
| P0-4 | **登录认证** | 后端已有 JWT 配置和 User 模型，但缺少 `/auth/login` 端点和前端登录页 | 后端 auth.py + 前端 Login |
| P0-5 | **自选股同步频率优化** | 交易时段自动轮询行情（30s），非交易时段停止 | 前端 Watchlist + 定时器 |

### 优先级 P1 — 功能完善

| 编号 | 功能 | 说明 | 涉及模块 |
|------|------|------|----------|
| P1-1 | **新闻聚合页面优化** | 重构 UI，增加股票关联标签、重要度过滤、时间线视图，放开 `/news` | 前端 News |
| P1-2 | **操作记录 + 盈亏追踪** | 完善操作记录页，增加盈亏曲线、胜率统计图表，放开 `/operations` | 前端 Operations |
| P1-3 | **战法库完善** | 战法卡片式展示 + 历史匹配记录 + 战法回测，放开 `/strategies` | 前端 Strategies |
| P1-4 | **行业板块排行** | Dashboard 增加 "行业板块" tab（当前只有概念板块），复用 `/sectors` 接口 | 前端 Dashboard |
| P1-5 | **多市场支持** | 港股/美股自选股的数据源适配（当前 fetcher 主要覆盖 A 股） | 后端 data_provider |
| P1-6 | **数据导出** | 复盘记录 / 操作记录导出为 Excel/PDF | 后端 + 前端 |
| P1-7 | **批量 AI 分析** | 自选股一键批量分析 + 结果对比视图 | 后端 analysis + 前端 |

### 优先级 P2 — 体验优化

| 编号 | 功能 | 说明 | 涉及模块 |
|------|------|------|----------|
| P2-1 | **响应式布局** | 移动端/平板适配（当前固定侧边栏 ml-56） | 前端 Shell/Sidebar |
| P2-2 | **图表交互增强** | K 线图增加成交量柱、MA 均线叠加、十字光标 | 前端 MiniKLine |
| P2-3 | **实时推送** | WebSocket 替代轮询，交易时段实时行情推送 | 后端 + 前端 |
| P2-4 | **通知提醒** | 评级变化/异常波动通过浏览器 Notification / 企业微信推送 | 后端 + 前端 |
| P2-5 | **Dashboard 自定义** | 卡片式布局，用户可拖拽调整模块顺序/隐藏 | 前端 Dashboard |
| P2-6 | **离线模式** | PWA + Service Worker，弱网环境下展示缓存数据 | 前端 |
| P2-7 | **多用户支持** | 完善用户管理，不同用户独立自选股/操作记录 | 后端 + 前端 |
| P2-8 | **复盘模板** | 自定义复盘表单字段（当前固定结构） | 后端 + 前端 |

### 优先级 P3 — 高级功能

| 编号 | 功能 | 说明 |
|------|------|------|
| P3-1 | **回测引擎** | 基于历史数据回测战法有效性 |
| P3-2 | **智能选股** | 根据当前情绪周期 + 板块动量自动推荐标的 |
| P3-3 | **组合管理** | 持仓组合收益追踪 + 风险分析 |
| P3-4 | **多 Agent 协作** | 技术 Agent + 基本面 Agent + 新闻 Agent 协作生成综合报告 |
| P3-5 | **知识库** | 个人投资笔记 + 复盘经验沉淀 + RAG 检索 |

---

## 十一、已知问题 & 待修复

| 编号 | 问题 | 影响 | 建议 |
|------|------|------|------|
| BUG-1 | README 中 health 地址为 `/api/health`，实际为 `/api/v1/health` | 文档误导 | 更新 README |
| BUG-2 | Docker 默认 Redis host 为 `redis`，本地开发需改为 `localhost` | 本地启动报错 | `.env.example` 注释说明 |
| BUG-3 | 后端 JWT 配置完整但缺少 login/register 端点 | 认证不可用 | 待 P0-4 实现 |
| BUG-4 | Scheduler `run_review` 未调用 `_save_limit_up_boards` | 定时生成的复盘缺少梯队持久化 | 对齐 API 逻辑 |
| BUG-5 | Vite 构建 chunk 超过 500KB | 性能警告 | 配置 code-splitting |

---

## 十二、开发环境搭建

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env: DEEPSEEK_API_KEY, REDIS_HOST=localhost 等

# 启动
python main.py
# API: http://localhost:8001/api/v1/health
# Swagger: http://localhost:8001/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 开发服务器: http://localhost:3000
# 自动代理 /api → localhost:8001
```

### Docker 部署

```bash
cd docker
docker-compose up -d
# Nginx: http://localhost (端口 80)
# 后端: http://localhost:8000
# Redis: localhost:6379
```

---

## 十三、目录结构

```
stock-review/
├── backend/
│   ├── main.py                    # FastAPI 入口 + SPA fallback
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env / .env.example
│   ├── data/                      # SQLite 数据文件
│   ├── static/                    # Vite 构建产物
│   └── app/
│       ├── config.py              # Pydantic Settings
│       ├── database.py            # SQLAlchemy 异步引擎
│       ├── cache.py               # Redis 缓存
│       ├── api/v1/
│       │   ├── router.py          # 路由聚合
│       │   ├── market.py          # 市场数据 API
│       │   ├── ratings.py         # 量化评级 API
│       │   ├── watchlist.py       # 自选股 API
│       │   ├── sync.py            # 数据同步 API
│       │   ├── analysis.py        # AI 分析 API
│       │   ├── review.py          # 每日复盘 API
│       │   ├── news.py            # 新闻 API
│       │   ├── strategy.py        # 战法库 API
│       │   └── operations.py      # 操作记录 API
│       ├── models/                # SQLAlchemy 模型 (16 张表)
│       ├── schemas/               # Pydantic 请求/响应
│       ├── core/                  # 业务引擎
│       │   ├── rating_engine.py   # 六维量化评级
│       │   ├── stock_analyzer.py  # 技术分析
│       │   ├── sentiment_engine.py# 情绪周期判断
│       │   ├── review_engine.py   # 复盘生成
│       │   ├── analysis_pipeline.py# AI 分析流水线
│       │   ├── market_review.py   # 市场数据采集
│       │   ├── limit_up_tracker.py# 涨停梯队
│       │   └── strategy_matcher.py# 战法匹配
│       ├── data_provider/         # 多数据源适配
│       │   ├── manager.py         # DataFetcherManager (调度)
│       │   ├── base.py            # BaseFetcher 抽象
│       │   ├── akshare_fetcher.py
│       │   ├── tushare_fetcher.py
│       │   ├── efinance_fetcher.py
│       │   ├── realtime.py        # 腾讯/新浪实时行情
│       │   └── fundamental.py     # 基本面(东财+腾讯)
│       ├── llm/                   # LLM 客户端
│       ├── news/                  # 新闻采集器
│       └── services/
│           ├── scheduler.py       # APScheduler 定时任务
│           └── seed.py            # 初始数据种子
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx               # React 入口
│       ├── App.tsx                # 路由定义
│       ├── index.css              # 双主题 CSS 变量 + Tailwind
│       ├── api/client.ts          # Axios 实例
│       ├── stores/useAppStore.ts  # Zustand (theme + recommend)
│       ├── utils/stockColor.ts    # 颜色/格式化工具
│       ├── pages/                 # 页面组件 (11 个)
│       └── components/
│           ├── layout/Shell.tsx
│           ├── layout/Sidebar.tsx
│           ├── StockDrawer.tsx    # 右侧抽屉详情
│           └── charts/            # MiniKLine, RadarChart, SentimentTrend, WinRatePie
├── docker/
│   ├── docker-compose.yml
│   └── nginx.conf
└── docs/
    └── PROJECT_SPEC.md            # 本文档
```

---

## 十四、前端重构建议（供设计参考）

### 整体风格方向

当前系统已实现浅色/深色双主题，CSS 变量体系完整。后续前端重构建议：

1. **卡片化布局**: 所有数据区块使用统一的 `bg-card rounded-xl border border-edge` 容器
2. **信息密度**: 参考 real-estate-stocks-picker 的 DetailPanel，在有限空间内通过 grid 布局展示更多指标
3. **色彩语义**: 涨跌色统一 (红涨绿跌)，数据源标签用 accent 色，警告用 amber/yellow
4. **交互反馈**: 加载态用骨架屏替代文字，操作按钮增加 loading spinner
5. **动效**: 抽屉滑入已有，可增加页面切换过渡、数据更新高亮闪烁

### 各页面重构要点

| 页面 | 重构方向 |
|------|----------|
| Dashboard | 增加行业板块 tab、板块热力图、资金流向可视化 |
| Watchlist | 评级 badge + sparkline、批量操作、自定义列 |
| RatingBoard | 评级卡片 + 排序筛选 + 评级分布图 + 历史趋势 |
| DailyReview | 时间线视图、梯队可视化优化、情绪周期轮盘 |
| StockDrawer | 增加评分趋势图、历史评级表格、公告列表 |
| News | 时间线视图、重要度标签、股票关联过滤 |
| Operations | 盈亏曲线、月度统计、战法胜率分析 |
| Settings | 数据源状态监控、LLM 配额统计 |

---

> 本文档是项目的单一真源参考，后续功能迭代请同步更新对应章节。
