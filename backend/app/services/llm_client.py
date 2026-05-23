"""统一 LLM 调用客户端 — 封装 AsyncOpenAI + 成本追踪 + JSON 提取 + 模型降级

整合 hongtian-ai-new 技术基座的 LLM 层核心能力。
所有 agent 通过此类调用 LLM，实现统一的成本追踪和错误处理。
"""
from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.core.retry import llm_retry_with_fallback
from app.services.cost_tracker import CostTracker

logger = get_logger(__name__)


class LLMParseError(Exception):
    """LLM 返回了无法解析的 JSON 响应"""


class LLMClient:

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        model: str = "glm-4-flash",
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.cost_tracker = CostTracker()

    @llm_retry_with_fallback(max_attempts=3)
    async def _raw_chat(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        model: str | None = None,
    ) -> tuple[str, dict]:
        model = model or self.model
        resp = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )

        content = resp.choices[0].message.content or ""
        usage = {}
        if resp.usage:
            usage = {
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
            self.cost_tracker.track(model, usage)

        return content, usage

    async def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
    ) -> dict:
        content, _ = await self._raw_chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return _extract_json_object(content)

    async def chat_json_list(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
    ) -> list[dict]:
        content, _ = await self._raw_chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return _extract_json_list(content)

    async def chat_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
    ) -> str:
        content, _ = await self._raw_chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return content

    def get_usage_summary(self) -> dict:
        return self.cost_tracker.get_summary()


def _extract_json_object(text: str) -> dict:
    if not text:
        raise LLMParseError("LLM 返回空响应")
    text = text.strip()
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.warning("Failed to parse JSON object from LLM response", preview=text[:200])
    raise LLMParseError(f"无法从 LLM 响应中提取 JSON 对象: {text[:100]}")


def _extract_json_list(text: str) -> list[dict]:
    if not text:
        return []
    text = text.strip()
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else [result]
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            result = json.loads(match.group())
            return result if isinstance(result, list) else [result]
        except json.JSONDecodeError:
            pass
    logger.warning("Failed to parse JSON list from LLM response", preview=text[:200])
    raise LLMParseError(f"无法从 LLM 响应中提取 JSON 数组: {text[:100]}")
