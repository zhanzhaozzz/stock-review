"""复盘生成专用提示词模板。"""

import json

REVIEW_SYSTEM_PROMPT = """你是一个深谙A股情绪周期的顶尖游资。你的操作严格遵循以下四象限逻辑：
1. 情指共振：擒龙主升
2. 情差指好：切换试错
3. 情好指差：补涨缠龙
4. 情指双杀：空仓等待

情绪周期节点划分为：
1. 启动期(低位混沌)
2. 发酵期(上升)
3. 高潮期(上升)
4. 高位混沌期(分歧)
5. 退潮期(下跌)

战法包含：擒龙(首分弱转强)、补涨套利、缠龙低吸、试错轻仓。

你只能输出严格 JSON，不要输出任何解释、注释、Markdown。"""


def build_review_prompt(daily_context: dict) -> str:
    """构建复盘提示词。"""
    context_json = json.dumps(daily_context, ensure_ascii=False, indent=2)
    return f"""请基于以下“客观盘面数据 JSON”生成结构化复盘草稿，要求字段严格对齐：

{context_json}

输出 JSON 字段必须完整，且必须满足枚举限制：
1) sentiment_cycle_main 仅可选：启动期 / 发酵期 / 高潮期 / 高位混沌期 / 退潮期 / 低位混沌期
2) conclusion_quadrant 仅可选：情指共振 / 情好指差 / 情差指好 / 情指双杀
3) next_day_mode 必须体现擒龙、补涨、缠龙或试错中的至少一种
4) sentiment_cycle_sub：情绪周期次线，如"启动"、"发酵"、"高潮延伸"等，反映次要情绪线索
5) index_sentiment_sh：上证指数情绪阶段，如"下跌一阶混沌修复"、"上涨二阶加速"等
6) index_sentiment_csm：中小创指数情绪阶段，如"高位混沌分歧转修复"、"下跌一阶"等

请输出如下 JSON（不得缺字段，不得新增字段）：
{{
  "sentiment_cycle_main": "",
  "sentiment_cycle_sub": "",
  "index_sentiment_sh": "",
  "index_sentiment_csm": "",
  "main_sectors": "",
  "sub_sectors": "",
  "market_style": "",
  "broken_high_stock": "",
  "conclusion_quadrant": "",
  "next_day_prediction": "",
  "next_day_mode": "",
  "core_middle_stock": "",
  "review_summary": "",
  "next_day_plan": ""
}}

字段要求：
- review_summary：200字以内的复盘总结，包含：今日情绪周期判断及依据、主线板块表现、龙头状态、市场风格特征、关键数据（涨停数/炸板数/连板晋级率等）的综合分析
- next_day_plan：150字以内的次日操作计划，包含：次日情绪推演（延续/转折/分歧）、具体操作策略（擒龙/补涨/缠龙/试错对应哪些标的和板块）、仓位建议"""
