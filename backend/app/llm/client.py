"""LiteLLM 统一客户端 — 支持 DeepSeek / Zhipu / Moonshot / Qwen 等模型。"""
import os
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_env_configured = False


def _ensure_env():
    """将 .env 中的 API Key 注入环境变量供 LiteLLM 读取。"""
    global _env_configured
    if _env_configured:
        return
    settings = get_settings()
    _mapping = {
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
        "DEEPSEEK_API_BASE": settings.deepseek_api_base,
        "ZHIPUAI_API_KEY": settings.zhipu_api_key,
        "MOONSHOT_API_KEY": settings.moonshot_api_key,
        "DASHSCOPE_API_KEY": settings.dashscope_api_key,
    }
    for k, v in _mapping.items():
        if v:
            os.environ.setdefault(k, v)
    _env_configured = True


async def chat(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.3,
    timeout: int = 120,
) -> Optional[str]:
    """调用单个 LLM 模型，返回文本结果。失败返回 None。"""
    _ensure_env()
    try:
        import litellm
        litellm.set_verbose = False

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )
        content = response.choices[0].message.content
        if content:
            _log_usage(model, response)
        return content or None
    except Exception as e:
        logger.warning("LLM call failed [%s]: %s", model, e)
        return None


def _log_usage(model: str, response):
    """记录 token 用量（异步落库在上层处理）。"""
    usage = getattr(response, "usage", None)
    if usage:
        logger.info(
            "LLM usage [%s]: prompt=%d, completion=%d",
            model,
            getattr(usage, "prompt_tokens", 0),
            getattr(usage, "completion_tokens", 0),
        )
