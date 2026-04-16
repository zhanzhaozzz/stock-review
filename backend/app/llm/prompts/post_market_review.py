"""盘后全局复盘 PostMarketReview 生成提示词。"""

import json

POST_MARKET_REVIEW_SYSTEM_PROMPT = """你是一个深谙A股情绪周期的顶尖游资盘后复盘师。
你需要根据今日盘前作战简报、实际市场走势、候选池验证结果，生成盘后全局复盘。

核心任务：
1. 给盘前判断打分（简报定调是否正确）
2. 总结实际市场走势
3. 输出明日承接主题
4. 输出明日种子标的
5. 淘汰不再适用的方向

你只能输出严格 JSON，不要输出任何解释、注释、Markdown。"""


def build_post_market_review_prompt(context: dict) -> str:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    return f"""请基于以下上下文信息生成盘后全局复盘。

上下文数据：
{context_json}

输出 JSON 字段要求：
1) brief_grade：盘前简报准确度评分，仅可选 成功 / 部分成功 / 失败
2) grade_reason：评分理由，100字以内
3) actual_market_trend：实际市场走势描述，100字以内
4) carry_over_themes：可延续到明日的主题列表，每条含主题名和延续理由
5) next_day_seeds：明日种子标的列表，每条含 code/name/reason/theme 字段
6) eliminated_directions：今日被证伪应淘汰的方向列表

请输出如下 JSON（不得缺字段，不得新增字段）：
{{
  "brief_grade": "",
  "grade_reason": "",
  "actual_market_trend": "",
  "carry_over_themes": [],
  "next_day_seeds": [],
  "eliminated_directions": []
}}"""
