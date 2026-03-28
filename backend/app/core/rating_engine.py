"""
通用股票量化评级引擎（六维技术因子 + 基本面 + LLM 融合评级）

移植自 real-estate-stocks-picker 的 rating_engine.py，去除地产行业硬编码，
改为通用化评级，支持 A 股 + 港股。

评级架构:
  量化技术评分 (35%) + 基本面评分 (25%) + AI 大模型评分 (25%) + 情绪评分 (15%)

六维技术因子 (各 0-100):
  1. 趋势 (Trend)     — 均线排列、MA 斜率、ADX
  2. 动量 (Momentum)   — RSI、MACD、KDJ、多周期涨跌幅
  3. 波动率 (Volatility)— 年化波动率、布林带、ATR
  4. 成交量 (Volume)   — 量比、OBV、VWAP、量价配合
  5. 价值 (Value)      — 区间位置、筹码集中度、支撑压力
  6. 情绪 (Sentiment)  — 新闻关键词 + LLM 情绪评分

评级标签: 强烈推荐 / 推荐 / 中性 / 谨慎 / 回避
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from app.llm.multi_model import multi_model_rating
from app.llm.prompts.rating import (
    RATING_SYSTEM_PROMPT,
    build_rating_prompt,
    score_to_label,
)
from app.data_provider.manager import get_data_manager

logger = logging.getLogger(__name__)

QUANT_WEIGHTS = {
    "trend": 0.22,
    "momentum": 0.18,
    "volatility": 0.12,
    "volume": 0.18,
    "value": 0.18,
    "sentiment": 0.12,
}

QUANT_RATIO = 0.35
FUNDAMENTAL_RATIO = 0.25
AI_RATIO = 0.25
SENTIMENT_RATIO = 0.15

QUANT_RATIO_NO_FUND = 0.40
AI_RATIO_NO_FUND = 0.35
SENTIMENT_RATIO_NO_FUND = 0.25


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _linear(value: float, low: float, high: float, s_lo: float = 0, s_hi: float = 100) -> float:
    if high == low:
        return (s_lo + s_hi) / 2
    ratio = max(0.0, min(1.0, (value - low) / (high - low)))
    return s_lo + ratio * (s_hi - s_lo)


# ────────────────── 六维技术因子 ──────────────────

def calc_trend(df: pd.DataFrame) -> float:
    if len(df) < 60:
        return 50.0
    close = pd.Series(df["close"].values, dtype=float)
    price = close.iloc[-1]
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    m5, m10, m20, m60 = ma5.iloc[-1], ma10.iloc[-1], ma20.iloc[-1], ma60.iloc[-1]

    score = 0.0
    bull = sum([m5 > m10, m10 > m20, m20 > m60])
    bear = sum([m5 < m10, m10 < m20, m20 < m60])
    score += (bull - bear) * 10

    dev = (price - m20) / (m20 + 1e-10) * 100
    score += _linear(dev, -10, 10, 0, 20)

    ma20_clean = ma20.dropna()
    if len(ma20_clean) >= 10:
        slope = (ma20_clean.iloc[-1] - ma20_clean.iloc[-10]) / (ma20_clean.iloc[-10] + 1e-10) * 100
        score += _linear(slope, -5, 5, 0, 15)

    spread = np.std([m5, m10, m20, m60]) / (m20 + 1e-10) * 100
    if spread < 2:
        score += 12
    elif spread < 4:
        score += 8
    elif spread < 6:
        score += 5
    else:
        score += 2

    high_s = pd.Series(df["high"].values, dtype=float) if "high" in df.columns else close * 1.01
    low_s = pd.Series(df["low"].values, dtype=float) if "low" in df.columns else close * 0.99
    tr = pd.concat([high_s - low_s, (high_s - close.shift(1)).abs(), (low_s - close.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    plus_dm = (high_s - high_s.shift(1)).clip(lower=0)
    minus_dm = (low_s.shift(1) - low_s).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    plus_di = 100 * plus_dm.rolling(14).mean() / (atr14 + 1e-10)
    minus_di = 100 * minus_dm.rolling(14).mean() / (atr14 + 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    adx = dx.rolling(14).mean()
    if not adx.dropna().empty:
        adx_v = adx.iloc[-1]
        if adx_v > 25 and plus_di.iloc[-1] > minus_di.iloc[-1]:
            score += _linear(adx_v, 25, 50, 12, 20)
        elif adx_v > 25:
            score += _linear(adx_v, 25, 50, 0, 5)
        else:
            score += 8

    return _clamp(score)


def calc_momentum(df: pd.DataFrame) -> float:
    if len(df) < 30:
        return 50.0
    close = pd.Series(df["close"].values, dtype=float)
    high_s = pd.Series(df["high"].values, dtype=float) if "high" in df.columns else close * 1.01
    low_s = pd.Series(df["low"].values, dtype=float) if "low" in df.columns else close * 0.99
    price = close.iloc[-1]
    score = 0.0

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss_s = (-delta.where(delta < 0, 0.0))
    rsi_14 = 100 - 100 / (1 + gain.rolling(14).mean().iloc[-1] / (loss_s.rolling(14).mean().iloc[-1] + 1e-10))
    rsi_6 = 100 - 100 / (1 + gain.rolling(6).mean().iloc[-1] / (loss_s.rolling(6).mean().iloc[-1] + 1e-10))
    score += _linear(rsi_14, 20, 80, 0, 12)
    score += _linear(rsi_6, 20, 80, 0, 8)

    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    hist = (dif - dea) * 2
    dif_v, dea_v, hist_v = dif.iloc[-1], dea.iloc[-1], hist.iloc[-1]
    hist_prev = hist.iloc[-2] if len(hist) > 1 else 0
    score += 8 if dif_v > 0 else 2
    score += 7 if dif_v > dea_v else 2
    if hist_v > 0 and hist_v > hist_prev:
        score += 10
    elif hist_v > 0:
        score += 6
    elif hist_v < 0 and abs(hist_v) < abs(hist_prev):
        score += 5
    else:
        score += 1

    low14 = low_s.rolling(14).min()
    high14 = high_s.rolling(14).max()
    rsv = (price - low14.iloc[-1]) / (high14.iloc[-1] - low14.iloc[-1] + 1e-10) * 100
    rsv_series = ((close - low14) / (high14 - low14 + 1e-10) * 100).dropna()
    k_vals = [50.0]
    for rv in rsv_series.values:
        k_vals.append(2 / 3 * k_vals[-1] + 1 / 3 * rv)
    k_val = k_vals[-1]
    d_vals = [50.0]
    for kv in k_vals[1:]:
        d_vals.append(2 / 3 * d_vals[-1] + 1 / 3 * kv)
    d_val = d_vals[-1]
    j_val = 3 * k_val - 2 * d_val
    if k_val > d_val and j_val > 0:
        score += _linear(j_val, 0, 100, 10, 18)
    elif k_val < d_val and j_val < 0:
        score += _linear(j_val, -100, 0, 2, 8)
    else:
        score += 10
    if k_val > 80 and d_val > 80:
        score -= 3
    elif k_val < 20 and d_val < 20:
        score += 2

    wr = (high14.iloc[-1] - price) / (high14.iloc[-1] - low14.iloc[-1] + 1e-10) * (-100)
    score += _linear(wr, -80, -20, 2, 10)

    for offset, span, w in [(6, 5, 5), (11, 10, 5), (21, 20, 5)]:
        if len(close) > offset:
            ret = (price / close.iloc[-offset] - 1) * 100
            bound = span * 1.0
            score += _linear(ret, -bound, bound, 0, w)

    return _clamp(score)


def calc_volatility(df: pd.DataFrame) -> float:
    if len(df) < 20:
        return 50.0
    close = pd.Series(df["close"].values, dtype=float)
    high_s = pd.Series(df["high"].values, dtype=float) if "high" in df.columns else close * 1.01
    low_s = pd.Series(df["low"].values, dtype=float) if "low" in df.columns else close * 0.99
    returns = close.pct_change().dropna()
    price = close.iloc[-1]
    score = 0.0

    vol20 = returns.tail(20).std() * np.sqrt(252) * 100
    score += _linear(vol20, 60, 15, 0, 25)

    ma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20
    bb_w = (upper - lower) / (ma20 + 1e-10) * 100
    score += _linear(bb_w, 25, 3, 0, 12)
    bb_pos = (price - lower) / (upper - lower + 1e-10)
    if 0.3 <= bb_pos <= 0.7:
        score += 13
    elif 0.2 <= bb_pos < 0.3 or 0.7 < bb_pos <= 0.8:
        score += 9
    elif bb_pos < 0.2:
        score += 5
    else:
        score += 4

    tr = pd.concat([high_s - low_s, (high_s - close.shift(1)).abs(), (low_s - close.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean().iloc[-1]
    atr_r = atr14 / (price + 1e-10) * 100
    score += _linear(atr_r, 6, 1, 0, 25)

    if len(returns) >= 30:
        vr = returns.tail(10).std() * np.sqrt(252) * 100
        ve = returns.iloc[-30:-10].std() * np.sqrt(252) * 100
        vc = vr - ve
        if vc < -5:
            score += 22
        elif vc < 0:
            score += 16
        elif vc < 5:
            score += 10
        else:
            score += 4
    else:
        score += 12

    return _clamp(score)


def calc_volume(df: pd.DataFrame) -> float:
    if len(df) < 20:
        return 50.0
    volume = pd.Series(df["volume"].values, dtype=float)
    close = pd.Series(df["close"].values, dtype=float)
    high_s = pd.Series(df["high"].values, dtype=float) if "high" in df.columns else close * 1.01
    low_s = pd.Series(df["low"].values, dtype=float) if "low" in df.columns else close * 0.99
    price = close.iloc[-1]
    score = 0.0

    vm5 = volume.rolling(5).mean().iloc[-1]
    vm20 = volume.rolling(20).mean().iloc[-1]
    r520 = vm5 / (vm20 + 1e-10)
    if 1.0 < r520 < 1.5:
        score += 12
    elif 1.5 <= r520 < 2.5:
        score += 8
    elif r520 >= 2.5:
        score += 3
    elif 0.7 < r520 <= 1.0:
        score += 6
    else:
        score += 2
    vm10 = volume.rolling(10).mean().iloc[-1]
    score += 8 if vm10 / (vm20 + 1e-10) > 1.0 else 3

    obv = (volume * np.sign(close.diff().fillna(0))).cumsum()
    obv5 = obv.rolling(5).mean()
    obv20 = obv.rolling(20).mean()
    if not obv5.dropna().empty and not obv20.dropna().empty:
        o5, o20, oc = obv5.iloc[-1], obv20.iloc[-1], obv.iloc[-1]
        if oc > o5 > o20:
            score += 18
        elif oc > o20:
            score += 12
        elif oc < o5 < o20:
            score += 3
        else:
            score += 8
    else:
        score += 10

    tp = (high_s + low_s + close) / 3
    vwap = (tp * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-10)
    if not vwap.dropna().empty:
        dev = (price - vwap.iloc[-1]) / (vwap.iloc[-1] + 1e-10) * 100
        if 0 < dev < 3:
            score += 15
        elif 3 <= dev < 6:
            score += 10
        elif dev >= 6:
            score += 5
        elif -3 < dev <= 0:
            score += 8
        else:
            score += 3
    else:
        score += 7

    n = min(10, len(close) - 1)
    if n >= 5:
        pc = close.diff().tail(n)
        vc = volume.tail(n)
        up = pc > 0
        dn = pc < 0
        vm = vc.mean()
        uv = vc[up].mean() if up.sum() > 0 else vm
        dv = vc[dn].mean() if dn.sum() > 0 else vm
        if uv > dv * 1.3:
            score += 18
        elif uv > dv:
            score += 13
        elif uv > dv * 0.7:
            score += 8
        else:
            score += 3
    else:
        score += 10

    if len(volume) >= 30:
        vt = (volume.tail(10).mean() / (volume.tail(30).mean() + 1e-10) - 1) * 100
        score += _linear(vt, -30, 30, 2, 10)
    else:
        score += 5

    return _clamp(score)


def calc_value(df: pd.DataFrame) -> float:
    if len(df) < 20:
        return 50.0
    close = pd.Series(df["close"].values, dtype=float)
    volume = pd.Series(df["volume"].values, dtype=float)
    price = close.iloc[-1]
    score = 0.0

    hi, lo = close.max(), close.min()
    rng = hi - lo
    if rng > 0:
        pos = (price - lo) / rng
        if 0.2 <= pos <= 0.5:
            score += 25
        elif 0.1 <= pos < 0.2:
            score += 20
        elif pos < 0.1:
            score += 12
        elif 0.5 < pos <= 0.7:
            score += 18
        elif 0.7 < pos <= 0.85:
            score += 10
        else:
            score += 5
    else:
        score += 12

    if len(close) >= 30:
        rc = close.tail(30)
        rv = volume.tail(30)
        tv = rv.sum()
        if tv > 0:
            vw = (rc * rv).sum() / tv
            cc = np.sqrt(((rc - vw) ** 2 * rv).sum() / tv) / (vw + 1e-10) * 100
            score += _linear(cc, 15, 2, 0, 20)
        else:
            score += 10
    else:
        score += 10

    sp = 0
    for w, wt in [(10, 3), (20, 5), (60, 7)]:
        if len(close) >= w:
            r = close.tail(w)
            rl, rh = r.min(), r.max()
            s = rh - rl
            if s > 0:
                ds = (price - rl) / s
                dr = (rh - price) / s
                if ds < 0.3 and dr > 0.5:
                    sp += wt
                elif ds < 0.5:
                    sp += wt * 0.7
                else:
                    sp += wt * 0.3
    score += _clamp(sp, 0, 25)

    if len(close) >= 10:
        cv = close.tail(10).std() / (close.tail(10).mean() + 1e-10) * 100
        if cv < 2:
            score += 18
        elif cv < 4:
            score += 14
        elif cv < 6:
            score += 10
        else:
            score += 5

    if len(close) >= 6:
        r5 = (price / close.iloc[-6] - 1) * 100
        score += _linear(r5, -8, 8, 2, 10)

    return _clamp(score)


# ────────────────── 基本面评分 ──────────────────

def calc_fundamental(fund: Optional[dict]) -> Optional[float]:
    """通用基本面评分: PE/PB/ROE/负债率/资金流。"""
    if not fund:
        return None
    pe = fund.get("pe")
    pb = fund.get("pb")
    roe = fund.get("roe")
    if pe is None and pb is None:
        return None

    score, mx = 0.0, 0.0

    if pe is not None:
        mx += 20
        if pe < 0:
            score += 3
        elif pe < 10:
            score += 20
        elif pe <= 20:
            score += 15
        elif pe <= 40:
            score += 8
        elif pe <= 60:
            score += 4
        else:
            score += 1

    if pb is not None:
        mx += 20
        if pb < 0:
            score += 2
        elif pb < 1.0:
            score += 18
        elif pb < 2.0:
            score += 14
        elif pb < 3.0:
            score += 8
        else:
            score += 3

    if roe is not None:
        mx += 15
        if roe < 0:
            score += 2
        elif roe < 5:
            score += 5
        elif roe < 10:
            score += 9
        elif roe < 20:
            score += 13
        else:
            score += 15

    cap = fund.get("market_cap")
    if cap is not None:
        mx += 10
        if cap > 100_000_000_000:
            score += 10
        elif cap > 50_000_000_000:
            score += 8
        elif cap > 10_000_000_000:
            score += 6
        elif cap > 3_000_000_000:
            score += 4
        else:
            score += 2

    nf = fund.get("net_flow")
    if nf is not None:
        mx += 10
        if nf and nf > 50_000_000:
            score += 10
        elif nf and nf > 10_000_000:
            score += 8
        elif nf and nf > 0:
            score += 6
        elif nf and nf > -10_000_000:
            score += 4
        else:
            score += 2

    return _clamp(score / mx * 100) if mx > 0 else None


# ────────────────── 综合评级 ──────────────────

def _build_price_summary(df: pd.DataFrame) -> str:
    close = pd.Series(df["close"].values, dtype=float)
    price = close.iloc[-1]
    hi, lo = close.max(), close.min()
    lines = [f"- 最新价: {price:.2f}"]
    for offset, label in [(6, "5日"), (11, "10日"), (21, "20日"), (61, "60日")]:
        if len(close) > offset:
            ret = (price / close.iloc[-offset] - 1) * 100
            lines.append(f"- {label}涨跌幅: {ret:+.2f}%")
    dd = (hi - price) / (hi + 1e-10) * 100
    rb = (price - lo) / (lo + 1e-10) * 100
    lines.append(f"- 区间高点: {hi:.2f} (回撤 {dd:.1f}%)")
    lines.append(f"- 区间低点: {lo:.2f} (反弹 {rb:.1f}%)")
    return "\n".join(lines)


def _build_quant_summary(scores: dict) -> str:
    return "\n".join(
        f"- {k}: {v:.1f}/100" for k, v in scores.items() if k != "quant_total"
    )


def _build_fund_summary(fund: dict) -> str:
    parts = []
    if fund.get("pe") is not None:
        parts.append(f"PE: {fund['pe']:.2f}")
    if fund.get("pb") is not None:
        parts.append(f"PB: {fund['pb']:.2f}")
    if fund.get("roe") is not None:
        parts.append(f"ROE: {fund['roe']:.2f}")
    if fund.get("market_cap") is not None:
        mc_yi = fund["market_cap"] / 100_000_000
        parts.append(f"市值: {mc_yi:.0f}亿")
    if fund.get("industry"):
        parts.append(f"行业: {fund['industry']}")
    return "  |  ".join(parts) if parts else ""


async def rate_stock(
    code: str,
    name: str = "",
    market: str = "A",
    days: int = 120,
) -> Optional[dict]:
    """对单只股票执行完整评级，返回评级结果 dict。"""
    mgr = get_data_manager()

    df = await mgr.get_daily(code, days)
    if df is None or len(df) < 20:
        logger.warning("Insufficient data for %s (%s)", code, name)
        return None

    quant = {
        "trend": round(calc_trend(df), 2),
        "momentum": round(calc_momentum(df), 2),
        "volatility": round(calc_volatility(df), 2),
        "volume": round(calc_volume(df), 2),
        "value": round(calc_value(df), 2),
        "sentiment": 50.0,
    }
    quant_total = round(sum(quant[k] * QUANT_WEIGHTS[k] for k in QUANT_WEIGHTS), 2)
    quant["quant_total"] = quant_total

    fund_data = await mgr.get_fundamental(code)
    fund_score = calc_fundamental(fund_data)

    price_summary = _build_price_summary(df)
    quant_summary = _build_quant_summary(quant)
    fund_summary = _build_fund_summary(fund_data) if fund_data else ""

    ai_result = await multi_model_rating(
        prompt=build_rating_prompt(name, code, market, price_summary, quant_summary, fund_summary),
        system=RATING_SYSTEM_PROMPT,
    )

    ai_score = 0.0
    reason = ""
    sentiment = quant["sentiment"]

    if ai_result:
        ai_score = ai_result["ai_score"]
        reason = ai_result.get("analysis", "")
        if "sentiment_score" in ai_result:
            sentiment = ai_result["sentiment_score"]
            quant["sentiment"] = sentiment
            quant_total = round(sum(quant[k] * QUANT_WEIGHTS[k] for k in QUANT_WEIGHTS), 2)

    has_fund = fund_score is not None
    if ai_result:
        if has_fund:
            total = round(
                quant_total * QUANT_RATIO
                + fund_score * FUNDAMENTAL_RATIO
                + ai_score * AI_RATIO
                + sentiment * SENTIMENT_RATIO, 2
            )
        else:
            total = round(
                quant_total * QUANT_RATIO_NO_FUND
                + ai_score * AI_RATIO_NO_FUND
                + sentiment * SENTIMENT_RATIO_NO_FUND, 2
            )
    else:
        if has_fund:
            total = round(quant_total * 0.55 + fund_score * 0.45, 2)
        else:
            total = round(quant_total, 2)

    label = score_to_label(total)

    if not reason:
        reason = _fallback_reason(name, quant, total, label)

    result = {
        "code": code,
        "name": name,
        "market": market,
        "model_type": "quant_ai",
        "trend_score": quant["trend"],
        "momentum_score": quant["momentum"],
        "volatility_score": quant["volatility"],
        "volume_score": quant["volume"],
        "value_score": quant["value"],
        "sentiment_score": sentiment,
        "fundamental_score": round(fund_score, 2) if fund_score is not None else None,
        "ai_score": round(ai_score, 2),
        "total_score": total,
        "rating": label,
        "reason": reason,
    }

    if fund_data:
        result["pe"] = fund_data.get("pe")
        result["pb"] = fund_data.get("pb")
        result["roe"] = fund_data.get("roe")
        result["market_cap"] = fund_data.get("market_cap")
        result["net_flow"] = fund_data.get("net_flow")

    return result


def _fallback_reason(name: str, scores: dict, total: float, label: str) -> str:
    parts = []
    if scores["trend"] >= 70:
        parts.append("均线多头排列，趋势向好")
    elif scores["trend"] <= 35:
        parts.append("均线空头排列，趋势偏弱")
    if scores["momentum"] >= 70:
        parts.append("技术动量强劲")
    elif scores["momentum"] <= 35:
        parts.append("动量不足")
    if scores["volume"] >= 70:
        parts.append("量价配合良好")
    elif scores["volume"] <= 35:
        parts.append("成交低迷")
    if not parts:
        parts.append("各项指标表现平稳")
    return f"{name}当前评级【{label}】(综合{total:.0f}分): {'；'.join(parts)}。"
