"""Shared fixtures and configuration for all tests."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path


# Configure pytest for async tests
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def _make_mock_llm(chat_json_return=None, chat_json_list_return=None, chat_text_return=None):
    """Create a mock LLMClient for testing."""
    from app.services.llm_client import LLMClient
    from app.services.cost_tracker import CostTracker

    llm = LLMClient.__new__(LLMClient)
    llm.model = "test-model"
    llm.cost_tracker = CostTracker()
    llm.chat_json = AsyncMock(return_value=chat_json_return if chat_json_return is not None else {})
    llm.chat_json_list = AsyncMock(return_value=chat_json_list_return if chat_json_list_return is not None else [])
    llm.chat_text = AsyncMock(return_value=chat_text_return if chat_text_return is not None else "")
    llm.get_usage_summary = MagicMock(return_value={"total_cost": 0, "total_tokens": 0})
    return llm


@pytest.fixture
def mock_glm_client():
    """Create mock GLM-5 API client."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mock response"))]
    ))
    return client


@pytest.fixture
def temp_directory(tmp_path):
    """Create temporary directory for test files."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return [
        {
            "id": "text-1",
            "content": "Introduction to the document topic",
            "page": 1,
            "bbox": {"left": 10, "top": 10, "width": 50, "height": 20}
        },
        {
            "id": "text-2",
            "content": "Main content with detailed information",
            "page": 1,
            "bbox": {"left": 10, "top": 30, "width": 50, "height": 50}
        },
        {
            "id": "text-3",
            "content": "Conclusion and key takeaways",
            "page": 1,
            "bbox": {"left": 10, "top": 60, "width": 50, "height": 70}
        }
    ]


@pytest.fixture
def sample_image_content():
    """Sample image content for testing."""
    return [
        {
            "id": "img-1",
            "local_path": "/path/to/image1.png",
            "page": 1,
            "bbox": {"left": 60, "top": 10, "width": 90, "height": 40},
            "alt_text": "First image showing data"
        },
        {
            "id": "img-2",
            "local_path": "/path/to/image2.png",
            "page": 1,
            "bbox": {"left": 60, "top": 50, "width": 90, "height": 80},
            "alt_text": "Second image showing charts"
        }
    ]


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = MagicMock()
    client.set = MagicMock(return_value=True)
    client.get = MagicMock(return_value=None)
    client.delete = MagicMock(return_value=True)
    client.exists = MagicMock(return_value=False)
    client.expire = MagicMock(return_value=True)
    return client


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx.AsyncClient."""
    client = AsyncMock()
    response = AsyncMock()
    response.json.return_value = {}
    response.status_code = 200
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


# Test configuration
TEST_CONFIG = {
    "MAX_REPAIR_ATTEMPTS": 2,
    "FIDELITY_THRESHOLD": 0.95,
    "API_TIMEOUT": 30,
    "RENDER_OUTPUT_DIR": "/tmp/test_outputs"
}


@pytest.fixture
def test_config():
    """Get test configuration."""
    return TEST_CONFIG.copy()


# Disable actual API calls in tests
@pytest.fixture(autouse=True)
def disable_real_api_calls():
    """Automatically disable real API calls in all tests."""
    import os
    os.environ["TESTING"] = "true"
    yield
    del os.environ["TESTING"]