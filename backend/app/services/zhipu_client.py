"""智谱 GLM-5 调用封装 - 语义理解与结构提取"""
import httpx
import json
from typing import Optional
from cryptography.fernet import Fernet

from app.core.redis import redis_client


class ZhipuClient:
    """智谱 API 调用客户端"""

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._fernet = Fernet(Fernet.generate_key())

    async def _get_api_key(self) -> str:
        redis = redis_client.client
        encrypted = await redis.hget(f"api_keys:{self.session_id}", "zhipu_key")
        if not encrypted:
            raise ValueError("未配置智谱 API Key")
        return self._fernet.decrypt(encrypted.encode()).decode()

    async def _get_model(self) -> str:
        redis = redis_client.client
        model = await redis.hget(f"api_keys:{self.session_id}", "zhipu_model")
        return model or "glm-5-pro"

    async def chat(self, system_prompt: str, user_content: str, temperature: float = 0.1) -> str:
        """调用智谱 GLM-5 对话 API"""
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
        """分析文档逻辑结构 - 语义保真"""
        system_prompt = """你是一位专业的商业文档分析师。你的唯一职责是基于提供的文本进行客观分析。
严格规则：
1. 所有分析必须100%基于提供的文本，不得添加任何原文中没有的信息
2. 不得修改原文中的任何数据、数字、观点或表述
3. 不得进行任何主观评价或推断
4. 输出必须是严格的JSON格式

你需要输出以下结构：
{
  "document_type": "文档类型(product_intro|company_profile|marketing|technical_doc|other)",
  "target_audience": "目标受众",
  "key_sections": [
    {
      "section_id": "章节ID",
      "title": "章节标题（从原文提取）",
      "key_points": ["关键信息点（从原文提取）"],
      "importance": "high|medium|low",
      "suggested_page_allocation": 建议分配页数
    }
  ],
  "highlights": ["需要重点突出的内容（原文引用）"],
  "suggested_total_pages": 建议总页数
}"""

        result = await self.chat(system_prompt, text_content)
        return json.loads(result)

    async def plan_layout(
        self,
        structure: dict,
        available_templates: list[dict],
        asset_summary: dict,
    ) -> dict:
        """排版规划 - 根据内容选择模板和布局"""
        system_prompt = """你是一位杂志级排版设计师。根据文档结构和可用模板，规划最佳排版方案。
规则：
1. 保持原文所有内容，不得删减
2. 图片-文字对应关系必须保持不变
3. 每页选择最合适的布局模板
4. 输出严格的JSON格式

输出结构：
{
  "template_id": "选择的基础模板ID",
  "color_scheme": "颜色方案名称",
  "pages": [
    {
      "page_number": 1,
      "layout_type": "布局类型",
      "sections": [
        {
          "text_id": "原文text_id",
          "image_ids": ["关联的图片ID"],
          "table_ids": ["关联的表格ID"],
          "position": "top|center|bottom|left|right",
          "style": "style_preset_name"
        }
      ]
    }
  ]
}"""

        user_content = json.dumps({
            "structure": structure,
            "templates": available_templates,
            "assets": asset_summary,
        }, ensure_ascii=False)

        result = await self.chat(system_prompt, user_content)
        return json.loads(result)

    async def generate_search_keywords(self, text_content: str) -> list[str]:
        """为缺失素材的内容生成搜索关键词"""
        system_prompt = """根据以下文字内容，生成3-5个精确的图片搜索关键词，用于搜索合适的商业素材图片。
要求关键词简洁、具体、适合图片搜索。输出JSON数组格式。"""

        result = await self.chat(system_prompt, text_content)
        return json.loads(result)

    async def generate_image_prompt(self, text_content: str, style: str = "professional") -> str:
        """为缺失素材的内容生成 AI 绘图提示词"""
        system_prompt = f"""根据以下文字内容，生成一个详细的AI绘图提示词。
风格要求：{style}
要求：英文输出，包含主体、场景、光线、风格等要素，适合Flux.1模型。"""

        result = await self.chat(system_prompt, text_content, temperature=0.7)
        return result
