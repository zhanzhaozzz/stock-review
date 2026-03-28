"""评级引擎的 LLM 提示词模板。"""

RATING_SYSTEM_PROMPT = """你是一位资深的中国股票分析师，拥有超过15年A股和港股研究经验。

你的分析必须重点关注以下维度：

【一、行业政策与最新资讯（权重30%）】
1. 最新政策动态：近期发布的相关行业政策、监管变化
2. 政策影响评估：具体政策对该公司所在行业、业务模式的影响
3. 行业周期判断：当前处于行业周期的哪个阶段
4. 市场情绪：最新资讯对市场情绪的带动效应

【二、公司基本面分析（权重30%）】
1. 经营质量：营收增长、盈利能力、现金流
2. 财务健康：负债水平、偿债能力
3. 竞争优势：行业地位、护城河

【三、技术面与资金面（权重25%）】
1. 价格趋势：中长期均线方向和支撑/压力位
2. 资金动向：成交量变化、资金流向
3. 筹码结构：换手率和量价关系

【四、风险评估（权重15%）】
1. 系统性风险
2. 个股风险
3. 市场风险

请给出你独立的评分和判断。严格按照要求的JSON格式输出。"""


def build_rating_prompt(
    name: str,
    code: str,
    market: str,
    price_summary: str,
    quant_summary: str,
    fundamental_summary: str = "",
    news_summary: str = "",
) -> str:
    """构建评级分析的用户提示词。"""
    market_label = {"A": "A股", "HK": "港股"}.get(market, market)

    news_section = ""
    if news_summary:
        news_section = f"\n【相关资讯】\n{news_summary}\n"

    fund_section = ""
    if fundamental_summary:
        fund_section = f"\n【基本面数据】\n{fundamental_summary}\n"

    return f"""请对以下股票进行深度分析，结合行情数据和资讯给出独立的AI评分。

【股票信息】
- 名称: {name}
- 代码: {code}
- 市场: {market_label}
{news_section}{fund_section}
【行情数据摘要】
{price_summary}

【量化技术评分（仅供参考，请给出独立判断）】
{quant_summary}

请输出以下JSON格式（不要输出其他内容）:
{{
  "ai_score": <0-100的整数，你独立给出的AI综合评分>,
  "sentiment_score": <0-100的整数，对该股票当前新闻/政策情绪的评分，50为中性>,
  "analysis": "<200字以内的专业分析，包含：1.行业/政策影响 2.基本面评价 3.风险判断 4.综合操作建议>"
}}"""


RATING_LABELS = [
    (80, "强烈推荐"),
    (65, "推荐"),
    (50, "中性"),
    (35, "谨慎"),
    (0, "回避"),
]


def score_to_label(score: float) -> str:
    for threshold, label in RATING_LABELS:
        if score >= threshold:
            return label
    return "回避"
