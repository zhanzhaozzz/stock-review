"""多模型并行调用 + 加权融合 + 降级。"""
import asyncio
import json
import logging
import re
from typing import Optional

from app.config import get_settings
from app.llm.client import chat

logger = logging.getLogger(__name__)


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _parse_json_response(raw: str) -> Optional[dict]:
    """从 LLM 原始文本中提取 JSON 对象。"""
    if not raw:
        return None

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw)
        raw = re.sub(r"```$", "", raw)
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\"ai_score\".*\}", raw, re.DOTALL)
    if match:
        text = match.group()
        depth, end = 0, 0
        for i, ch in enumerate(text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                return json.loads(text[:end])
            except json.JSONDecodeError:
                pass

    score_m = re.search(r'"ai_score"\s*:\s*(\d+)', raw)
    analysis_m = re.search(r'"analysis"\s*:\s*"([^"]*)"', raw)
    if score_m:
        return {
            "ai_score": int(score_m.group(1)),
            "analysis": analysis_m.group(1) if analysis_m else "",
        }
    return None


async def multi_model_rating(
    prompt: str,
    system: str = "",
) -> Optional[dict]:
    """并行调用配置的多个 LLM，返回加权融合结果。

    Returns:
        {"ai_score": float, "sentiment_score": float | None, "analysis": str} or None
    """
    settings = get_settings()
    models = settings.rating_model_list
    weights = settings.rating_weight_list

    if len(weights) < len(models):
        weights += [1.0 / len(models)] * (len(models) - len(weights))

    tasks = [chat(m, prompt, system=system) for m in models]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    parsed_list: list[tuple[dict, float, str]] = []
    for raw, weight, model_name in zip(results, weights, models):
        if isinstance(raw, Exception):
            logger.warning("Model %s failed: %s", model_name, raw)
            continue
        if raw is None:
            continue
        parsed = _parse_json_response(raw)
        if parsed and "ai_score" in parsed:
            parsed_list.append((parsed, weight, model_name))

    if not parsed_list:
        return None

    total_weight = sum(w for _, w, _ in parsed_list)
    norm = [(p, w / total_weight, n) for p, w, n in parsed_list]

    fused_score = round(sum(p["ai_score"] * w for p, w, _ in norm))
    fused_score = _clamp(fused_score)

    fused_sentiment = None
    sent_items = [(p["sentiment_score"], w) for p, w, _ in norm if "sentiment_score" in p]
    if sent_items:
        sw = sum(w for _, w in sent_items)
        fused_sentiment = round(sum(s * w / sw for s, w in sent_items))

    analysis_parts = []
    for p, _, name in norm:
        short_name = name.split("/")[-1]
        analysis_parts.append(f"[{short_name}({p['ai_score']})] {p.get('analysis', '')}")

    logger.info(
        "Multi-model fusion: %s = %d",
        " + ".join(f"{n.split('/')[-1]}({p['ai_score']})×{w:.0%}" for p, w, n in norm),
        fused_score,
    )

    result = {"ai_score": fused_score, "analysis": "\n".join(analysis_parts)}
    if fused_sentiment is not None:
        result["sentiment_score"] = fused_sentiment
    return result
