"""Supplement Agent — 素材补充：Pexels → Unsplash → AI 生图"""
import asyncio
import hashlib
import base64
from pathlib import Path
from typing import Optional

import httpx

from app.models.unified_document import UnifiedDocument, ImageElement
from app.models.edit_actions import MagazineEditPlan


class SupplementAgent:

    def __init__(self, session_id: str):
        self.session_id = session_id
        from app.core.config import settings
        self.unsplash_key = getattr(settings, "UNSPLASH_ACCESS_KEY", "")
        self.pexels_key = getattr(settings, "PEXELS_API_KEY", "")
        self.replicate_token = getattr(settings, "REPLICATE_API_TOKEN", "")
        self.output_dir = Path(settings.ASSETS_DIR) / session_id / "supplemented"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def supplement(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> None:
        for page in plan.pages:
            for action in page.actions:
                if action.type != "replace_image":
                    continue

                img = next(
                    (i for i in doc.images if i.id == action.source_id), None,
                )
                if img and Path(img.local_path).exists() and Path(img.local_path).stat().st_size > 0:
                    continue

                context = self._find_text_context(doc, action.source_id, page)
                supplemented_path = await self._try_supplement(context, action.source_id)
                if supplemented_path:
                    if img:
                        img.local_path = str(supplemented_path)
                    else:
                        new_img = ImageElement(
                            id=action.source_id,
                            local_path=str(supplemented_path),
                            page=0,
                            hash=hashlib.md5(supplemented_path.read_bytes()).hexdigest()[:12],
                        )
                        doc.images.append(new_img)

    def _find_text_context(self, doc: UnifiedDocument, image_id: str, page) -> str:
        for link in doc.linkage:
            if link.asset_id == image_id and link.asset_type == "image":
                text = next((t for t in doc.texts if t.id == link.text_id), None)
                if text:
                    return text.content[:300]

        page_texts = [t.content for t in doc.texts if t.page == page.page_number - 1]
        return " ".join(page_texts)[:300]

    async def _try_supplement(self, context: str, image_id: str) -> Optional[Path]:
        path = await self._search_pexels(context, image_id)
        if path:
            return path

        path = await self._search_unsplash(context, image_id)
        if path:
            return path

        return await self._generate_image(context, image_id)

    async def _search_pexels(self, context: str, image_id: str) -> Optional[Path]:
        if not self.pexels_key:
            return None

        keywords = await self._extract_keywords(context)
        if not keywords:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": self.pexels_key},
                    params={"query": keywords, "per_page": 3, "orientation": "landscape", "size": "large"},
                )
                if resp.status_code != 200:
                    return None

                photos = resp.json().get("photos", [])
                if not photos:
                    return None

                img_url = photos[0]["src"]["large2x"]
                img_resp = await client.get(img_url)
                if img_resp.status_code != 200:
                    return None

                img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                img_path = self.output_dir / f"{image_id}_{img_hash}.jpg"
                img_path.write_bytes(img_resp.content)
                return img_path
            except Exception:
                return None

    async def _search_unsplash(self, context: str, image_id: str) -> Optional[Path]:
        if not self.unsplash_key:
            return None

        keywords = await self._extract_keywords(context)
        if not keywords:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    "https://api.unsplash.com/search/photos",
                    headers={"Authorization": f"Client-ID {self.unsplash_key}"},
                    params={"query": keywords, "per_page": 3, "orientation": "landscape"},
                )
                if resp.status_code != 200:
                    return None

                results = resp.json().get("results", [])
                if not results:
                    return None

                img_url = results[0]["urls"]["regular"]
                img_resp = await client.get(img_url, headers={"Accept-Version": "v1"})
                if img_resp.status_code != 200:
                    return None

                img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                img_path = self.output_dir / f"{image_id}_{img_hash}.jpg"
                img_path.write_bytes(img_resp.content)
                return img_path
            except Exception:
                return None

    async def _generate_image(self, context: str, image_id: str) -> Optional[Path]:
        if not self.replicate_token:
            return None

        prompt = await self._generate_image_prompt(context)

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(
                    "https://api.replicate.com/v1/models/black-forest-labs/flux-1-schnell/predictions",
                    headers={
                        "Authorization": f"Token {self.replicate_token}",
                        "Content-Type": "application/json",
                    },
                    json={"input": {"prompt": prompt, "width": 1344, "height": 768, "num_outputs": 1}},
                )
                if resp.status_code not in (200, 201):
                    return None

                prediction_id = resp.json()["id"]

                for _ in range(30):
                    await asyncio.sleep(2)
                    status_resp = await client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Token {self.replicate_token}"},
                    )
                    status_data = status_resp.json()

                    if status_data["status"] == "succeeded":
                        output_url = status_data["output"][0]
                        img_resp = await client.get(output_url)
                        img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                        img_path = self.output_dir / f"{image_id}_{img_hash}.png"
                        img_path.write_bytes(img_resp.content)
                        return img_path

                    if status_data["status"] == "failed":
                        return None

                return None
            except Exception:
                return None

    async def _extract_keywords(self, context: str) -> str:
        from app.services.zhipu_client import ZhipuClient
        try:
            client = ZhipuClient(self.session_id)
            keywords = await client.generate_search_keywords(context)
            if isinstance(keywords, list):
                return " ".join(keywords[:3])
            return str(keywords)
        except Exception:
            return " ".join(context.split()[:5])

    async def _generate_image_prompt(self, context: str) -> str:
        from app.services.zhipu_client import ZhipuClient
        try:
            client = ZhipuClient(self.session_id)
            return await client.generate_image_prompt(context)
        except Exception:
            return f"professional business presentation illustration, {context[:100]}, high quality"
