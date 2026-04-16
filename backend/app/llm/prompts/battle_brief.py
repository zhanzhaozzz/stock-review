"""盘前作战简报 BattleBrief 生成提示词。"""

import json

BATTLE_BRIEF_SYSTEM_PROMPT = """你是一个深谙A股情绪周期的顶尖游资盘前策略师。
你需要根据昨日市场状态和隔夜消息面，生成今日作战简报。

情绪周期节点：冰点 / 启动 / 发酵 / 高潮 / 高位混沌 / 退潮
定调枚举：可做 / 轻仓试错 / 防守观察 / 不做

你只能输出严格 JSON，不要输出任何解释、注释、Markdown。"""


def build_battle_brief_prompt(context: dict) -> str:
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    return f"""请基于以下上下文信息生成今日盘前作战简报。

上下文数据：
{context_json}

输出 JSON 字段要求：
1) status_tone：仅可选 可做 / 轻仓试错 / 防守观察 / 不做
2) suggested_position：仓位建议，如"5-7成"、"2-3成"、"0-1成"
3) overall_conclusion：50字以内总定调
4) macro_context：宏观与外盘要点列表，每条30字以内，最多5条
5) main_narrative：今日主线叙事列表，每条50字以内，最多3条
6) bullish_sectors：看多板块列表，每条含板块名和理由
7) bearish_sectors：看空/回避板块列表
8) risk_tips：风险提示列表，最多5条
9) allowed_actions：今天允许做的操作列表
10) forbidden_actions：今天禁止做的操作列表

请输出如下 JSON（不得缺字段，不得新增字段）：
{{
  "status_tone": "",
  "suggested_position": "",
  "overall_conclusion": "",
  "macro_context": [],
  "main_narrative": [],
  "bullish_sectors": [],
  "bearish_sectors": [],
  "risk_tips": [],
  "allowed_actions": [],
  "forbidden_actions": []
}}"""
