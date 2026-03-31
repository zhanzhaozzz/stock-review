[根目录](../../CLAUDE.md) > **frontend**

# Frontend - React 前端应用

> 股票复盘系统的前端 SPA，提供市场总览、量化评级、每日复盘、自选股管理等可视化界面。

---

## 模块职责

- 单页应用 (SPA)：基于 React Router 的前端路由
- 数据可视化：Recharts 图表组件
- 状态管理：Zustand 全局状态
- HTTP 客户端：Axios 封装，带 JWT 认证

---

## 入口与启动

```bash
cd frontend
npm install
npm run dev   # 开发模式 http://localhost:5173
npm run build # 生产构建
```

**构建工具**: Vite + TypeScript + Tailwind CSS 4

---

## 对外接口（页面路由）

### 路由配置 (`App.tsx`)

| 路径 | 组件 | 功能 |
|-----|------|------|
| `/` | Dashboard | 市场总览（指数、涨跌面、板块排行） |
| `/ratings` | RatingBoard | 评级看板（雷达图、评级列表） |
| `/watchlist` | Watchlist | 自选股管理 |
| `/news` | News | 新闻聚合 |
| `/review` | DailyReview | 每日复盘（结构化表单） |
| `/review/history` | ReviewHistory | 复盘历史 |
| `/strategies` | Strategies | 策略管理 |
| `/operations` | Operations | 操作记录 |
| `/stock/:code` | StockDetail | 股票详情 |
| `/settings` | Settings | 设置 |

---

## 关键依赖与配置

### 主要依赖 (`package.json`)

| 包名 | 用途 |
|-----|------|
| react | UI 框架 |
| react-router-dom | 路由 |
| axios | HTTP 客户端 |
| zustand | 状态管理 |
| recharts | 图表库 |
| tailwindcss | CSS 框架 |
| vite | 构建工具 |
| typescript | 类型检查 |

### API 客户端 (`api/client.ts`)

```typescript
const api = axios.create({
  baseURL: "/api/v1",
  timeout: 60000,
});

// JWT 认证拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sr_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 组件结构

### 页面组件 (`pages/`)

| 组件 | 功能 |
|-----|------|
| Dashboard | 市场总览：大盘指数卡片、涨跌面统计、板块排行表 |
| RatingBoard | 评级看板：股票搜索、雷达图、评级列表 |
| DailyReview | 每日复盘：情绪周期选择、梯队展示、AI 草稿对比 |
| ReviewHistory | 复盘历史：日期列表、情绪周期趋势图 |
| Watchlist | 自选股管理：添加/删除、行情展示 |
| News | 新闻聚合：新闻列表、LLM 过滤状态 |
| Strategies | 策略管理：战法列表、适用周期 |
| Operations | 操作记录：操作日志、盈亏统计 |
| StockDetail | 股票详情：K 线、评级、分析报告 |
| Settings | 设置：API Key 配置 |

### 通用组件 (`components/`)

| 组件 | 功能 |
|-----|------|
| layout/Shell | 页面外壳：Sidebar + 主内容区 |
| layout/Sidebar | 侧边导航栏 |
| charts/RadarChart | 雷达图（六维评分） |
| charts/MiniKLine | 迷你 K 线图 |
| charts/SentimentTrend | 情绪周期趋势图 |
| charts/WinRatePie | 胜率饼图 |
| StockDrawer | 股票详情抽屉 |

---

## 状态管理 (`stores/`)

### useAppStore

```typescript
// 全局状态（如有）
interface AppState {
  // 待扩展
}
```

---

## 测试与质量

**当前状态**: 无测试文件。

**建议补充**:
- `src/__tests__/` - Vitest 组件测试
- E2E 测试 - Playwright 端到端测试

---

## 常见问题 (FAQ)

### Q: 如何添加新页面？

1. 在 `pages/` 下创建组件
2. 在 `App.tsx` 添加路由
3. 在 `Sidebar.tsx` 添加导航链接

### Q: 如何添加新的图表组件？

1. 使用 Recharts 封装
2. 参考 `components/charts/RadarChart.tsx`

### Q: API 请求跨域问题？

开发模式下 Vite 代理配置：
```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

---

## 相关文件清单

```
frontend/
├── package.json                     # 依赖清单
├── vite.config.ts                   # Vite 配置
├── index.html                       # 入口 HTML
├── public/
│   ├── favicon.svg
│   └── icons.svg
└── src/
    ├── main.tsx                     # 应用入口
    ├── App.tsx                      # 路由配置
    ├── index.css                    # 全局样式
    ├── api/
    │   └── client.ts                # Axios 客户端
    ├── components/
    │   ├── layout/
    │   │   ├── Shell.tsx            # 页面外壳
    │   │   └── Sidebar.tsx          # 侧边导航
    │   ├── charts/
    │   │   ├── RadarChart.tsx       # 雷达图
    │   │   ├── MiniKLine.tsx        # 迷你 K 线
    │   │   ├── SentimentTrend.tsx   # 情绪趋势
    │   │   └── WinRatePie.tsx       # 胜率饼图
    │   └── StockDrawer.tsx          # 股票详情抽屉
    ├── pages/
    │   ├── Dashboard.tsx            # 市场总览
    │   ├── RatingBoard.tsx          # 评级看板
    │   ├── Watchlist.tsx            # 自选股
    │   ├── News.tsx                 # 新闻
    │   ├── DailyReview.tsx          # 每日复盘
    │   ├── ReviewHistory.tsx        # 复盘历史
    │   ├── Strategies.tsx           # 策略管理
    │   ├── Operations.tsx           # 操作记录
    │   ├── StockDetail.tsx          # 股票详情
    │   ├── Settings.tsx             # 设置
    │   └── Placeholder.tsx          # 占位页
    ├── stores/
    │   └── useAppStore.ts           # Zustand 状态
    └── utils/
        └── stockColor.ts            # 涨跌颜色工具
```

---

## 变更记录 (Changelog)

### 2026-03-31 - 初始化扫描

- 完成前端模块结构梳理
- 识别 22 个页面/组件文件
- 记录 React + Vite + Tailwind 技术栈
