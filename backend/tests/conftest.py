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
            "text": "Introduction to the document topic",
            "type": "paragraph",
            "page_number": 1,
            "bbox": [0.1, 0.1, 0.5, 0.2]
        },
        {
            "id": "text-2",
            "text": "Main content with detailed information",
            "type": "paragraph",
            "page_number": 1,
            "bbox": [0.1, 0.3, 0.5, 0.5]
        },
        {
            "id": "text-3",
            "text": "Conclusion and key takeaways",
            "type": "paragraph",
            "page_number": 1,
            "bbox": [0.1, 0.6, 0.5, 0.7]
        }
    ]


@pytest.fixture
def sample_image_content():
    """Sample image content for testing."""
    return [
        {
            "id": "img-1",
            "path": "/path/to/image1.png",
            "page_number": 1,
            "bbox": [0.6, 0.1, 0.9, 0.4],
            "description": "First image showing data"
        },
        {
            "id": "img-2",
            "path": "/path/to/image2.png",
            "page_number": 1,
            "bbox": [0.6, 0.5, 0.9, 0.8],
            "description": "Second image showing charts"
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