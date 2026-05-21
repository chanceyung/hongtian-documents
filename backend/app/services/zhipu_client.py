"""智谱 GLM-5 调用封装"""
import httpx
import json

from app.api.router import decrypt_key


class ZhipuClient:
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def _get_api_key(self) -> str:
        from app.core.redis import redis_client

        redis = redis_client.client
        encrypted = await redis.hget(f"api_keys:{self.session_id}", "zhipu_key")
        if not encrypted:
            raise ValueError("未配置智谱 API Key")
        return decrypt_key(encrypted)

    async def _get_model(self) -> str:
        from app.core.redis import redis_client

        redis = redis_client.client
        model = await redis.hget(f"api_keys:{self.session_id}", "zhipu_model")
        return model or "glm-5-pro"

    async def chat(self, system_prompt: str, user_content: str, temperature: float = 0.1) -> str:
        api_key = await self._get_api_key()
        model = await self._get_model()

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def analyze_document_structure(self, text_content: str) -> dict:
        system_prompt = """你是专业的文档分析师。基于提供的文本进行客观分析。
规则：
1. 所有分析必须100%基于提供的文本
2. 不得修改原文中的任何数据
3. 输出严格的JSON格式

输出结构：
{
  "document_type": "文档类型",
  "target_audience": "目标受众",
  "key_sections": [{"section_id": "ID", "title": "标题", "key_points": ["关键点"], "importance": "high|medium|low", "suggested_page_allocation": 页数}],
  "highlights": ["需要突出的内容"],
  "suggested_total_pages": 总页数
}"""
        result = await self.chat(system_prompt, text_content)
        return json.loads(result)

    async def generate_search_keywords(self, text_content: str) -> list[str]:
        system_prompt = "根据文字内容，生成3-5个精确的图片搜索关键词。输出JSON数组格式。"
        result = await self.chat(system_prompt, text_content)
        return json.loads(result)

    async def generate_image_prompt(self, text_content: str, style: str = "professional") -> str:
        system_prompt = f"根据文字内容生成AI绘图提示词。风格：{style}。英文输出，适合Flux.1模型。"
        result = await self.chat(system_prompt, text_content, temperature=0.7)
        return result
