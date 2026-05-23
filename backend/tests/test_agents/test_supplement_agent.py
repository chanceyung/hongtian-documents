"""Tests for SupplementAgent."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.unified_document import UnifiedDocument, ImageElement, TextElement, BoundingBox, ContentAssetLink
from app.models.edit_actions import MagazineEditPlan, EditAction, SlideEditPlan
from app.agents.supplement_agent import SupplementAgent
from tests.conftest import _make_mock_llm


@pytest.fixture
def mock_settings():
    """Mock app.core.config.settings."""
    settings = MagicMock()
    settings.PEXELS_API_KEY = "test-pexels-key"
    settings.UNSPLASH_ACCESS_KEY = "test-unsplash-key"
    settings.REPLICATE_API_TOKEN = "test-replicate-token"
    settings.ASSETS_DIR = "/tmp/test_assets"
    return settings


@pytest.fixture
def supplement_agent(mock_settings):
    """Create SupplementAgent instance for testing."""
    llm = _make_mock_llm()
    with patch('app.core.config.settings', mock_settings):
        return SupplementAgent(llm=llm, session_id="test-session")


@pytest.fixture
def sample_document():
    """Create UnifiedDocument with texts and images."""
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            TextElement(
                id="text-1",
                content="Business growth chart showing quarterly revenue increase",
                page=0,
                bbox=BoundingBox(left=10, top=10, width=80, height=20)
            ),
            TextElement(
                id="text-2",
                content="Team collaboration meeting with diverse members",
                page=0,
                bbox=BoundingBox(left=10, top=40, width=80, height=20)
            )
        ],
        images=[
            ImageElement(
                id="img-1",
                local_path="",  # Missing path
                page=0,
                bbox=BoundingBox(left=60, top=10, width=90, height=40),
                alt_text="Data growth chart"
            ),
            ImageElement(
                id="img-2",
                local_path="/existing/path.jpg",  # Existing path
                page=0,
                bbox=BoundingBox(left=60, top=50, width=90, height=80),
                alt_text="Team photo"
            )
        ],
        linkage=[
            ContentAssetLink(
                text_id="text-1",
                asset_id="img-1",
                asset_type="image",
                strategy="semantic",
                confidence=0.9
            )
        ]
    )


@pytest.fixture
def sample_edit_plan():
    """Create MagazineEditPlan with replace_image actions."""
    return MagazineEditPlan(
        document_id="test-doc",
        template_id="modern",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="cover",
                actions=[
                    EditAction(
                        type="replace_image",
                        target_selector="img-1",
                        source_id="img-1",
                        content=""
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="img-2",
                        source_id="img-2",
                        content=""
                    )
                ]
            )
        ]
    )


def _make_async_client_mock(get_side_effect=None, get_return=None):
    """Create a mock for httpx.AsyncClient used as async context manager."""
    mock_client = AsyncMock()
    if get_side_effect:
        mock_client.get.side_effect = get_side_effect
    elif get_return:
        mock_client.get.return_value = get_return
    # Ensure __aenter__ returns the same mock so .get side_effect works
    mock_client.__aenter__.return_value = mock_client
    return mock_client


class TestSupplementAgentSearchPexels:
    """Tests for _search_pexels method."""

    @pytest.mark.asyncio
    async def test_search_pexels_downloads_image(self, supplement_agent, tmp_path):
        """Test that Pexels search downloads and saves image."""
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = {
            "photos": [{"src": {"large2x": "https://example.com/image.jpg"}}]
        }
        mock_search_resp.status_code = 200

        mock_image_resp = MagicMock()
        mock_image_resp.content = b"fake image data"
        mock_image_resp.status_code = 200

        mock_client = _make_async_client_mock(get_side_effect=[mock_search_resp, mock_image_resp])
        supplement_agent.output_dir = tmp_path

        with patch('app.agents.supplement_agent.httpx.AsyncClient', return_value=mock_client):
            with patch.object(supplement_agent, '_extract_keywords', return_value="business chart"):
                result = await supplement_agent._search_pexels("business chart", "img-1")

                assert result is not None
                assert result.name.startswith("img-1_")
                assert result.suffix == ".jpg"

    @pytest.mark.asyncio
    async def test_search_pexels_api_error_returns_none(self, supplement_agent):
        """Test that API error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = _make_async_client_mock(get_return=mock_response)

        with patch('app.agents.supplement_agent.httpx.AsyncClient', return_value=mock_client):
            with patch.object(supplement_agent, '_extract_keywords', return_value="test"):
                result = await supplement_agent._search_pexels("test", "img-1")

                assert result is None


class TestSupplementAgentSearchUnsplash:
    """Tests for _search_unsplash method."""

    @pytest.mark.asyncio
    async def test_search_unsplash_downloads_image(self, supplement_agent, tmp_path):
        """Test that Unsplash search downloads and saves image."""
        mock_search_resp = MagicMock()
        mock_search_resp.json.return_value = {
            "results": [{"urls": {"regular": "https://example.com/image.jpg"}}]
        }
        mock_search_resp.status_code = 200

        mock_image_resp = MagicMock()
        mock_image_resp.content = b"fake image data"
        mock_image_resp.status_code = 200

        mock_client = _make_async_client_mock(get_side_effect=[mock_search_resp, mock_image_resp])
        supplement_agent.output_dir = tmp_path

        with patch('app.agents.supplement_agent.httpx.AsyncClient', return_value=mock_client):
            with patch.object(supplement_agent, '_extract_keywords', return_value="business"):
                result = await supplement_agent._search_unsplash("business", "img-1")

                assert result is not None
                assert result.name.startswith("img-1_")


class TestSupplementAgentExtractKeywords:
    """Tests for _extract_keywords method."""

    @pytest.mark.asyncio
    async def test_extract_keywords_calls_llm(self, supplement_agent):
        """Test that keyword extraction calls LLMClient."""
        supplement_agent.llm.chat_json = AsyncMock(return_value=["business", "chart", "growth"])
        keywords = await supplement_agent._extract_keywords("Business growth chart showing quarterly revenue")

        assert keywords == "business chart growth"

    @pytest.mark.asyncio
    async def test_extract_keywords_fallback_on_error(self, supplement_agent):
        """Test fallback to first 5 words on error."""
        supplement_agent.llm.chat_json = AsyncMock(side_effect=Exception("API Error"))
        keywords = await supplement_agent._extract_keywords("one two three four five six")

        assert keywords == "one two three four five"


class TestSupplementAgentFindTextContext:
    """Tests for _find_text_context method."""

    def test_find_text_context_from_linkage(self, supplement_agent, sample_document, sample_edit_plan):
        """Test finding context from linkage."""
        context = supplement_agent._find_text_context(sample_document, "img-1", sample_edit_plan.pages[0])

        assert "Business growth chart" in context

    def test_find_text_context_from_page_texts(self, supplement_agent, sample_document, sample_edit_plan):
        """Test finding context from page texts when no linkage."""
        context = supplement_agent._find_text_context(sample_document, "img-nonexistent", sample_edit_plan.pages[0])

        assert isinstance(context, str)


class TestSupplementAgentSupplement:
    """Tests for supplement method."""

    @pytest.mark.asyncio
    async def test_supplement_updates_missing_images(self, supplement_agent, tmp_path):
        """Test supplementing missing images updates doc.images."""
        mock_path = tmp_path / "supplemented_img-1.jpg"
        mock_path.write_bytes(b"fake image")

        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            images=[
                ImageElement(id="img-1", local_path="/nonexistent/missing.png", page=0),
            ],
        )
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[EditAction(type="replace_image", target_selector="img-1", source_id="img-1", content="")]
                )
            ]
        )

        with patch.object(supplement_agent, '_try_supplement', return_value=mock_path):
            result = await supplement_agent.supplement(doc, plan)

            assert result is None
            img = next((i for i in doc.images if i.id == "img-1"), None)
            assert img is not None
            assert str(mock_path) == img.local_path

    @pytest.mark.asyncio
    async def test_supplement_skips_existing_images(self, supplement_agent, tmp_path):
        """Test that supplement skips images with existing local files."""
        existing_img = tmp_path / "existing.jpg"
        existing_img.write_bytes(b"real image data")

        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            images=[
                ImageElement(id="img-1", local_path=str(existing_img), page=0),
            ],
        )
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[EditAction(type="replace_image", target_selector="img-1", source_id="img-1", content="")]
                )
            ]
        )

        with patch.object(supplement_agent, '_try_supplement') as mock_try:
            result = await supplement_agent.supplement(doc, plan)

            assert result is None
            mock_try.assert_not_called()

    @pytest.mark.asyncio
    async def test_supplement_with_no_missing_images(self, supplement_agent, tmp_path):
        """Test supplement with no missing images is a no-op."""
        existing = tmp_path / "real_image.jpg"
        existing.write_bytes(b"real image bytes")

        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            images=[
                ImageElement(id="img-1", local_path=str(existing), page=0)
            ]
        )
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[EditAction(type="replace_image", target_selector="img-1", source_id="img-1", content="")]
                )
            ]
        )

        with patch.object(supplement_agent, '_try_supplement') as mock_try:
            result = await supplement_agent.supplement(doc, plan)

            assert result is None
            mock_try.assert_not_called()