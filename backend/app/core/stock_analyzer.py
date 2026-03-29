"""技术面规则引擎 — 确定性技术面分析（无 LLM），为 AI 分析提供结构化输入。

分析维度:
  - 均线系统: MA5/10/20/60 排列、金叉死叉、乖离率
  - MACD: 金叉死叉、柱状线趋势
  - RSI: 超买超卖、背离
  - 成交量: 量能变化、量价配合
  - 支撑压力位: 近期高低点、布林带
  - 趋势判断: 综合信号给出方向判断
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TechnicalResult:
    """技术面分析结果。"""
    trend: str = "震荡"
    trend_strength: int = 50
    ma_alignment: str = "混乱"
    macd_signal: str = "中性"
    rsi_14: float = 50.0
    rsi_status: str = "中性"
    volume_trend: str = "正常"
    support: float = 0.0
    resistance: float = 0.0
    bollinger_position: str = "中轨附近"
    signals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""

    def to_context(self) -> str:
        """转为 LLM 可读的文本上下文。"""
        lines = [
            f"趋势判断: {self.trend} (强度 {self.trend_strength}/100)",
            f"均线排列: {self.ma_alignment}",
            f"MACD信号: {self.macd_signal}",
            f"RSI(14): {self.rsi_14:.1f} ({self.rsi_status})",
            f"量能趋势: {self.volume_trend}",
            f"支撑位: {self.support:.2f}  |  压力位: {self.resistance:.2f}",
            f"布林带位置: {self.bollinger_position}",
        ]
        if self.signals:
            lines.append(f"技术信号: {'; '.join(self.signals)}")
        if self.warnings:
            lines.append(f"风险提示: {'; '.join(self.warnings)}")
        return "\n".join(lines)


def analyze_technical(df: pd.DataFrame) -> TechnicalResult:
    """对 DataFrame 执行确定性技术面分析。"""
    result = TechnicalResult()
    if df is None or len(df) < 20:
        result.summary = "数据不足，无法进行技术分析"
        return result

    close = pd.Series(df["close"].values, dtype=float)
    volume = pd.Series(df["volume"].values, dtype=float)
    high_s = pd.Series(df.get("high", close * 1.01).values, dtype=float)
    low_s = pd.Series(df.get("low", close * 0.99).values, dtype=float)
    price = close.iloc[-1]

    _analyze_ma(close, price, result)
    _analyze_macd(close, result)
    _analyze_rsi(close, result)
    _analyze_volume(close, volume, result)
    _analyze_support_resistance(close, high_s, low_s, price, result)
    _analyze_bollinger(close, price, result)
    _synthesize(result)

    return result


def _analyze_ma(close: pd.Series, price: float, r: TechnicalResult):
    """均线系统分析。"""
    mas = {}
    for w in [5, 10, 20, 60]:
        if len(close) >= w:
            mas[w] = close.rolling(w).mean().iloc[-1]

    if not mas:
        return

    above_count = sum(1 for v in mas.values() if price > v)
    total = len(mas)

    if total >= 4 and mas.get(5, 0) > mas.get(10, 0) > mas.get(20, 0) > mas.get(60, 0):
        r.ma_alignment = "多头排列"
        r.signals.append("均线多头排列")
    elif total >= 4 and mas.get(5, 0) < mas.get(10, 0) < mas.get(20, 0) < mas.get(60, 0):
        r.ma_alignment = "空头排列"
        r.warnings.append("均线空头排列")
    elif above_count >= 3:
        r.ma_alignment = "偏多"
    elif above_count <= 1:
        r.ma_alignment = "偏空"
    else:
        r.ma_alignment = "交织"

    if 5 in mas and 10 in mas and len(close) > 2:
        ma5_prev = close.rolling(5).mean().iloc[-2]
        ma10_prev = close.rolling(10).mean().iloc[-2]
        if ma5_prev <= ma10_prev and mas[5] > mas[10]:
            r.signals.append("MA5/10 金叉")
        elif ma5_prev >= ma10_prev and mas[5] < mas[10]:
            r.warnings.append("MA5/10 死叉")

    if 20 in mas:
        bias = (price - mas[20]) / (mas[20] + 1e-10) * 100
        if bias > 8:
            r.warnings.append(f"20日乖离率偏高({bias:.1f}%)，有回调风险")
        elif bias < -8:
            r.signals.append(f"20日乖离率偏低({bias:.1f}%)，可能超跌反弹")


def _analyze_macd(close: pd.Series, r: TechnicalResult):
    """MACD 分析。"""
    if len(close) < 35:
        return
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    hist = (dif - dea) * 2

    dif_v, dea_v, hist_v = dif.iloc[-1], dea.iloc[-1], hist.iloc[-1]
    hist_prev = hist.iloc[-2] if len(hist) > 1 else 0

    if dif_v > dea_v and hist_v > 0:
        if hist_v > hist_prev:
            r.macd_signal = "多头加速"
        else:
            r.macd_signal = "多头减弱"
    elif dif_v < dea_v and hist_v < 0:
        if abs(hist_v) > abs(hist_prev):
            r.macd_signal = "空头加速"
        else:
            r.macd_signal = "空头减弱"
    else:
        r.macd_signal = "中性"

    dif_prev = dif.iloc[-2]
    dea_prev = dea.iloc[-2]
    if dif_prev <= dea_prev and dif_v > dea_v:
        r.signals.append("MACD 金叉")
    elif dif_prev >= dea_prev and dif_v < dea_v:
        r.warnings.append("MACD 死叉")

    if dif_v > 0 and dea_v > 0:
        r.signals.append("MACD 零轴之上运行")
    elif dif_v < 0 and dea_v < 0:
        r.warnings.append("MACD 零轴之下运行")


def _analyze_rsi(close: pd.Series, r: TechnicalResult):
    """RSI 分析。"""
    if len(close) < 15:
        return
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(14).mean().iloc[-1]
    avg_loss = loss.rolling(14).mean().iloc[-1]
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - 100 / (1 + rs)
    r.rsi_14 = round(rsi, 1)

    if rsi >= 80:
        r.rsi_status = "严重超买"
        r.warnings.append(f"RSI({rsi:.0f})严重超买")
    elif rsi >= 70:
        r.rsi_status = "超买"
        r.warnings.append(f"RSI({rsi:.0f})超买")
    elif rsi <= 20:
        r.rsi_status = "严重超卖"
        r.signals.append(f"RSI({rsi:.0f})严重超卖")
    elif rsi <= 30:
        r.rsi_status = "超卖"
        r.signals.append(f"RSI({rsi:.0f})超卖")
    else:
        r.rsi_status = "中性"


def _analyze_volume(close: pd.Series, volume: pd.Series, r: TechnicalResult):
    """成交量分析。"""
    if len(volume) < 20:
        return
    vm5 = volume.rolling(5).mean().iloc[-1]
    vm20 = volume.rolling(20).mean().iloc[-1]
    ratio = vm5 / (vm20 + 1e-10)

    pct = close.pct_change()
    last_pct = pct.iloc[-1] if len(pct) > 0 else 0

    if ratio > 2.0:
        r.volume_trend = "放量异动"
        if last_pct > 0:
            r.signals.append("放量上涨")
        else:
            r.warnings.append("放量下跌")
    elif ratio > 1.3:
        r.volume_trend = "温和放量"
    elif ratio < 0.6:
        r.volume_trend = "缩量"
        r.warnings.append("成交缩量，关注量能配合")
    else:
        r.volume_trend = "正常"


def _analyze_support_resistance(close: pd.Series, high_s: pd.Series, low_s: pd.Series, price: float, r: TechnicalResult):
    """支撑压力位分析。"""
    lookback = min(60, len(close))
    recent_high = high_s.tail(lookback)
    recent_low = low_s.tail(lookback)

    r.resistance = round(float(recent_high.max()), 2)
    r.support = round(float(recent_low.min()), 2)

    dist_to_resistance = (r.resistance - price) / (price + 1e-10) * 100
    dist_to_support = (price - r.support) / (price + 1e-10) * 100

    if dist_to_resistance < 2:
        r.warnings.append(f"接近压力位{r.resistance}，上方空间有限")
    if dist_to_support < 3:
        r.signals.append(f"接近支撑位{r.support}，可能获得支撑")


def _analyze_bollinger(close: pd.Series, price: float, r: TechnicalResult):
    """布林带分析。"""
    if len(close) < 20:
        return
    ma20 = close.rolling(20).mean().iloc[-1]
    std20 = close.rolling(20).std().iloc[-1]
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20

    if price > upper:
        r.bollinger_position = "上轨之上"
        r.warnings.append("价格突破布林带上轨，注意回调风险")
    elif price > ma20 + std20:
        r.bollinger_position = "上轨附近"
    elif price > ma20:
        r.bollinger_position = "中上轨之间"
    elif price > lower:
        r.bollinger_position = "中下轨之间"
    elif price > ma20 - std20:
        r.bollinger_position = "下轨附近"
        r.signals.append("价格接近布林带下轨，可能超跌反弹")
    else:
        r.bollinger_position = "下轨之下"
        r.signals.append("价格跌破布林带下轨，关注止跌信号")


def _synthesize(r: TechnicalResult):
    """综合所有信号给出趋势判断。"""
    bull_score = 0
    bear_score = 0

    if "多头" in r.ma_alignment:
        bull_score += 25
    elif "空头" in r.ma_alignment:
        bear_score += 25
    elif "偏多" in r.ma_alignment:
        bull_score += 15
    elif "偏空" in r.ma_alignment:
        bear_score += 15

    if "多头" in r.macd_signal:
        bull_score += 20
    elif "空头" in r.macd_signal:
        bear_score += 20

    if r.rsi_14 > 60:
        bull_score += 10
    elif r.rsi_14 < 40:
        bear_score += 10

    if "放量上涨" in str(r.signals):
        bull_score += 15
    if "放量下跌" in str(r.warnings):
        bear_score += 15

    bull_score += len([s for s in r.signals if "金叉" in s]) * 10
    bear_score += len([w for w in r.warnings if "死叉" in w]) * 10

    total = bull_score - bear_score
    r.trend_strength = max(0, min(100, 50 + total))

    if total >= 30:
        r.trend = "强势上涨"
    elif total >= 15:
        r.trend = "偏多"
    elif total <= -30:
        r.trend = "强势下跌"
    elif total <= -15:
        r.trend = "偏空"
    else:
        r.trend = "震荡"

    r.summary = f"技术面综合判断: {r.trend}(强度{r.trend_strength}/100), {r.ma_alignment}, MACD{r.macd_signal}, RSI {r.rsi_14:.0f}"
