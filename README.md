# Stock Review - 个人每日复盘炒股系统

面向个人投资者的每日复盘工具，帮助你在收盘后系统化地完成"看大盘 -> 看板块 -> 看自选 -> 看新闻 -> 做决策"的完整复盘流程。

## 核心功能

- **市场总览**: 大盘指数、板块排行、资金流向、涨跌面统计
- **量化评级**: 六维技术因子 + 基本面 + 多模型 LLM 融合评分
- **AI 分析报告**: 技术面 + 新闻 + LLM 生成决策看板
- **情绪周期复盘**: 涨停梯队追踪、情绪周期判断、战法匹配
- **新闻聚合**: 财联社/东方财富/新浪三路采集 + LLM 过滤
- **自选股管理**: 自选股 + 板块扫描

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy + Redis
- **前端**: React 19 + Vite + Tailwind CSS 4 + Recharts
- **数据源**: AKShare (主) + Tushare (辅) + efinance (兜底)
- **LLM**: LiteLLM 统一路由 (DeepSeek/GLM/Kimi/Qwen)
- **部署**: Docker Compose (Nginx + Backend + Redis)

## 快速启动

```bash
# 1. 复制环境配置
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. Docker 一键启动
cd docker
docker-compose up -d

# 3. 访问
# API: http://localhost:8000/api/health
# 前端: http://localhost (需先构建前端)
```

## 开发模式

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端
cd frontend
npm install
npm run dev
```
