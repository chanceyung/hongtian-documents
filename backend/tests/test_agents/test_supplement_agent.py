"""Tests for SupplementAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, ImageItem, MagazineEditPlan, EditAction
from app.agents.supplement_agent import SupplementAgent


@pytest.fixture
def supplement_agent():
    """Create SupplementAgent instance for testing."""
    return SupplementAgent()


@pytest.fixture
def sample_document_missing_images():
    """Create UnifiedDocument with missing image paths."""
    return UnifiedDocument(
        title="Test Document",
        content=[],
        images=[
            ImageItem(
                id="img-1",
                path="",  # Missing path - needs supplement
                page_number=1,
                bbox=[0.6, 0.1, 0.9, 0.4],
                description="Data growth chart showing upward trend"
            ),
            ImageItem(
                id="img-2",
                path="",  # Missing path - needs supplement
                page_number=1,
                bbox=[0.6, 0.5, 0.9, 0.8],
                description="Team collaboration meeting photo"
            )
        ],
        metadata={"format": "pptx"}
    )


@pytest.fixture
def sample_edit_plan_missing_images():
    """Create MagazineEditPlan with missing images."""
    return MagazineEditPlan(
        template="modern",
        actions=[
            EditAction(
                action="replace_image",
                id="img-1",
                content=""  # Empty content - needs supplement
            ),
            EditAction(
                action="replace_image",
                id="img-2",
                content=""  # Empty content - needs supplement
            )
        ]
    )


@pytest.fixture
def sample_edit_plan_complete():
    """Create MagazineEditPlan with complete image paths."""
    return MagazineEditPlan(
        template="modern",
        actions=[
            EditAction(
                action="replace_image",
                id="img-1",
                content="/existing/path/to/image1.png"
            ),
            EditAction(
                action="replace_image",
                id="img-2",
                content="/existing/path/to/image2.png"
            )
        ]
    )


class TestSupplementAgentSearchPexels:
    """Tests for _search_pexels method."""

    @pytest.mark.asyncio
    async def test_search_pexels_api_call(self, supplement_agent):
        """Test that Pexels API is called correctly."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "photos": [
                {
                    "src": {"large": "https://images.pexels.com/photos/test1.jpg"},
                    "photographer": "Test Photographer",
                    "url": "https://www.pexels.com/photo/test1"
                }
            ]
        }

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            results = await supplement_agent._search_pexels("business meeting", 1)

            assert len(results) > 0
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_pexels_returns_image_urls(self, supplement_agent):
        """Test that Pexels search returns valid image URLs."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "photos": [
                {
                    "src": {"large": "https://images.pexels.com/photos/business.jpg"},
                    "photographer": "Photographer 1"
                },
                {
                    "src": {"large": "https://images.pexels.com/photos/meeting.jpg"},
                    "photographer": "Photographer 2"
                }
            ]
        }

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            results = await supplement_agent._search_pexels("business", 2)

            assert len(results) == 2
            assert all(url.startswith("https://") for url in results)

    @pytest.mark.asyncio
    async def test_search_pexels_api_error_handling(self, supplement_agent):
        """Test handling of Pexels API errors."""
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            results = await supplement_agent._search_pexels("test", 1)

            # Should return empty list on error
            assert results == []


class TestSupplementAgentSearchUnsplash:
    """Tests for _search_unsplash method (fallback)."""

    @pytest.mark.asyncio
    async def test_search_unsplash_fallback_call(self, supplement_agent):
        """Test that Unsplash is called as fallback."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "urls": {"full": "https://images.unsplash.com/photo-test1.jpg"},
                    "user": {"name": "User 1"}
                }
            ]
        }

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            results = await supplement_agent._search_unsplash("technology", 1)

            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_unsplash_returns_different_source(self, supplement_agent):
        """Test that Unsplash returns Unsplash URLs, not Pexels."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "urls": {"full": "https://images.unsplash.com/photo-123.jpg"},
                    "user": {"name": "Photographer"}
                }
            ]
        }

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            results = await supplement_agent._search_unsplash("test", 1)

            # Should be Unsplash URLs
            assert any("unsplash" in url for url in results)


class TestSupplementAgentExtractKeywords:
    """Tests for _extract_keywords method."""

    @pytest.mark.asyncio
    async def test_extract_keywords_calls_glm5(self, supplement_agent):
        """Test that keyword extraction calls GLM-5 API."""
        description = "A professional business meeting with diverse team members discussing quarterly results"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='["business", "meeting", "team", "collaboration"]'
            ))]
        ))

        with patch('app.agents.supplement_agent.client', mock_client):
            keywords = await supplement_agent._extract_keywords(description)

            mock_client.chat.completions.create.assert_called_once()
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    @pytest.mark.asyncio
    async def test_extract_keywords_relevant_terms(self, supplement_agent):
        """Test that extracted keywords are relevant to description."""
        description = "Data visualization showing sales growth trends over the last quarter"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='["data", "visualization", "sales", "growth", "trends"]'
            ))]
        ))

        with patch('app.agents.supplement_agent.client', mock_client):
            keywords = await supplement_agent._extract_keywords(description)

            # Should contain relevant keywords
            assert any(kw in description.lower() for kw in keywords)

    @pytest.mark.asyncio
    async def test_extract_keywords_empty_description(self, supplement_agent):
        """Test keyword extraction with empty description."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.supplement_agent.client', mock_client):
            keywords = await supplement_agent._extract_keywords("")

            assert keywords == []

    @pytest.mark.asyncio
    async def test_extract_keywords_limits_count(self, supplement_agent):
        """Test that keyword extraction limits to reasonable number."""
        description = "Complex description with many potential keywords for testing the limit functionality"

        mock_client = MagicMock()
        # Return more keywords than expected limit
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8"]'
            ))]
        ))

        with patch('app.agents.supplement_agent.client', mock_client):
            keywords = await supplement_agent._extract_keywords(description)

            # Should limit to reasonable number (typically 3-5)
            assert len(keywords) <= 8


class TestSupplementAgentSupplement:
    """Tests for supplement method."""

    @pytest.mark.asyncio
    async def test_supplement_missing_images(self, supplement_agent, sample_document_missing_images, sample_edit_plan_missing_images):
        """Test supplementing missing images in edit plan."""
        # Mock image search
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "photos": [{
                "src": {"large": "https://images.pexels.com/photos/test.jpg"}
            }]
        }
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        # Mock keyword extraction
        mock_glm_client = MagicMock()
        mock_glm_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='["data", "chart"]'
            ))]
        ))

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            with patch('app.agents.supplement_agent.client', mock_glm_client):
                result = await supplement_agent.supplement(
                    sample_document_missing_images,
                    sample_edit_plan_missing_images
                )

                # All missing images should be supplemented
                img_actions = [a for a in result.actions if a.action == "replace_image"]
                assert all(a.content for a in img_actions)

    @pytest.mark.asyncio
    async def test_supplement_skips_existing_images(self, supplement_agent, sample_document_missing_images, sample_edit_plan_complete):
        """Test that supplement skips images that already have paths."""
        # Mock image search (should not be called for complete plan)
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            result = await supplement_agent.supplement(
                sample_document_missing_images,
                sample_edit_plan_complete
            )

            # Should not modify existing image paths
            img_actions = [a for a in result.actions if a.action == "replace_image"]
            assert all(a.content.startswith("/existing/") for a in img_actions)

            # API should not have been called
            assert not mock_httpx.AsyncClient.called

    @pytest.mark.asyncio
    async def test_supplement_with_empty_plan(self, supplement_agent, sample_document_missing_images):
        """Test supplement with no image actions."""
        empty_plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Text")
            ]
        )

        result = await supplement_agent.supplement(sample_document_missing_images, empty_plan)

        # Should return same plan (no images to supplement)
        assert result.actions == empty_plan.actions

    @pytest.mark.asyncio
    async def test_supplement_preserves_text_actions(self, supplement_agent, sample_document_missing_images):
        """Test that supplement does not modify text actions."""
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Original text", font_size=18),
                EditAction(action="replace_image", id="img-1", content="")
            ]
        )

        # Mock image search
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"photos": [{"src": {"large": "https://test.jpg"}}]}
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        # Mock keyword extraction
        mock_glm_client = MagicMock()
        mock_glm_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='["test"]'))]
        ))

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            with patch('app.agents.supplement_agent.client', mock_glm_client):
                result = await supplement_agent.supplement(sample_document_missing_images, plan)

                # Text action should be unchanged
                text_action = next((a for a in result.actions if a.action == "replace_span"), None)
                assert text_action is not None
                assert text_action.content == "Original text"
                assert text_action.font_size == 18

    @pytest.mark.asyncio
    async def test_supplement_marks_supplemented_images(self, supplement_agent, sample_document_missing_images, sample_edit_plan_missing_images):
        """Test that supplemented images are marked appropriately."""
        # Mock image search
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock()
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"photos": [{"src": {"large": "https://test.jpg"}}]}
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx.AsyncClient.return_value = mock_client

        # Mock keyword extraction
        mock_glm_client = MagicMock()
        mock_glm_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='["test"]'))]
        ))

        with patch('app.agents.supplement_agent.httpx', mock_httpx):
            with patch('app.agents.supplement_agent.client', mock_glm_client):
                result = await supplement_agent.supplement(
                    sample_document_missing_images,
                    sample_edit_plan_missing_images
                )

                # Supplemented images should have valid content
                img_actions = [a for a in result.actions if a.action == "replace_image"]
                assert all(a.content for a in img_actions)
                assert all(a.content.startswith("http") for a in img_actions)