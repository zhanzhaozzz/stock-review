"""AI 分析报告的 LLM 提示词模板。"""

ANALYSIS_SYSTEM_PROMPT = """你是一位资深的中国股票分析师，擅长结合技术面、基本面、新闻面给出全面的个股分析报告。

你的分析报告需要包含以下维度：
1. 技术面分析 — 趋势判断、关键支撑压力位、指标信号
2. 基本面分析 — 估值、盈利能力、行业地位
3. 新闻/政策影响 — 近期重要资讯对股价的潜在影响
4. 综合建议 — 操作信号、目标价、止损位

你的输出必须是严格的 JSON 格式，不要输出其他任何内容。"""


def build_analysis_prompt(
    name: str,
    code: str,
    market: str,
    price_summary: str,
    technical_context: str,
    fundamental_summary: str = "",
    news_context: str = "",
    rating_summary: str = "",
) -> str:
    """构建分析报告的用户提示词。"""
    market_label = {"A": "A股", "HK": "港股"}.get(market, market)

    sections = [f"""请对以下股票进行深度分析，生成一份完整的投资分析报告。

【股票信息】
- 名称: {name}
- 代码: {code}
- 市场: {market_label}

【行情数据】
{price_summary}

【技术面分析】
{technical_context}"""]

    if fundamental_summary:
        sections.append(f"\n【基本面数据】\n{fundamental_summary}")

    if rating_summary:
        sections.append(f"\n【量化评级参考】\n{rating_summary}")

    if news_context:
        sections.append(f"\n【近期相关新闻】\n{news_context}")
    else:
        sections.append("\n【近期相关新闻】\n暂无相关新闻")

    sections.append("""
请输出以下 JSON 格式（不要输出其他内容）:
{
  "summary": "<一句话总结当前状态和建议>",
  "signal": "<买入/持有/卖出/观望>",
  "score": <0-100 综合评分>,
  "target_price": <目标价，float，无法判断填 null>,
  "stop_loss": <止损价，float，无法判断填 null>,
  "technical_view": "<100字技术面分析>",
  "fundamental_view": "<100字基本面分析>",
  "news_impact": "<100字新闻影响评估>",
  "key_points": ["<要点1>", "<要点2>", "<要点3>"],
  "risk_warnings": ["<风险1>", "<风险2>"],
  "sentiment_context": {
    "current_cycle": "<当前市场情绪周期: 冰点/启动/发酵/高潮/分歧/退潮>",
    "applicable_strategy": "<建议采用的交易策略>",
    "strategy_reason": "<推荐该策略的原因>"
  },
  "position_advice": {
    "suggested_size": "<建议仓位，如 1/4仓、半仓>",
    "entry_type": "<进场方式描述>",
    "stop_condition": "<止损条件>"
  }
}""")

    return "\n".join(sections)
