"""复盘生成专用提示词模板。"""

REVIEW_SYSTEM_PROMPT = """你是一位短线交易复盘专家，擅长从涨停梯队数据、情绪周期中提炼有价值的复盘总结。

复盘总结需要涵盖:
1. 今日市场情绪概况（一句话定性）
2. 主线板块的运行状态（发酵/高潮/分歧/退潮）
3. 龙头股状态（加速/一致/分歧/断板）
4. 赚钱效应与亏钱效应的分布
5. 明确的次日操作建议（做什么/不做什么/仓位）

输出严格 JSON 格式，不要输出其他内容。"""


def build_review_prompt(
    cycle_phase: str,
    confidence: int,
    market_height: int,
    total_limit_up: int,
    first_board_count: int,
    broken_count: int,
    main_sectors: str,
    sub_sectors: str,
    leader_info: str,
    prev_phases: str,
    matched_strategies: str,
    market_overview_summary: str = "",
) -> str:
    """构建复盘提示词。"""
    sections = [
        f"日期: 今日",
        f"情绪周期: {cycle_phase} (置信度{confidence}%)",
        f"市场高度: {market_height}板",
        f"涨停数: {total_limit_up}, 首板: {first_board_count}, 炸板: {broken_count}",
        f"主线板块: {main_sectors or '不明确'}",
        f"支线板块: {sub_sectors or '无'}",
        f"龙头: {leader_info or '未识别'}",
    ]

    if prev_phases:
        sections.append(f"近期情绪演变: {prev_phases}")

    if matched_strategies:
        sections.append(f"适用战法: {matched_strategies}")

    if market_overview_summary:
        sections.append(f"大盘概况: {market_overview_summary}")

    return f"""请根据以下数据生成今日复盘总结和次日操作计划。

{chr(10).join(sections)}

请输出 JSON（不要输出其他内容）:
{{
  "summary": "<200字复盘总结，包含: 1.情绪定性 2.主线状态 3.龙头状态 4.赚亏效应>",
  "plan": "<100字次日操作计划，包含: 1.该做什么 2.不该做什么 3.仓位建议>",
  "key_observation": "<一句话最重要的观察>"
}}"""
