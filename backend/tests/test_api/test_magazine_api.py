"""Tests for Magazine API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = MagicMock()
    mock.set = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.delete = MagicMock()
    mock.exists = MagicMock(return_value=False)
    return mock


@pytest.fixture
def mock_background_tasks():
    """Create mock background tasks."""
    mock = MagicMock()
    mock.add_task = MagicMock()
    return mock


class TestMagazineAPIUpload:
    """Tests for POST /upload endpoint."""

    def test_upload_unsupported_format_returns_400(self, mock_redis, mock_background_tasks):
        """Test that uploading unsupported format returns 400 status."""
        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                from app.api.magazine_api import app

                client = TestClient(app)

                # Create a file with unsupported extension
                file_content = b"test content"
                file = BytesIO(file_content)
                file.name = "test.unsupported"

                response = client.post(
                    "/upload",
                    files={"file": ("test.unsupported", file, "application/octet-stream")}
                )

                assert response.status_code == 400
                assert "Unsupported" in response.json()["detail"] or "format" in response.json()["detail"].lower()

    def test_upload_pptx_accepts_and_returns_200_with_task_id(self, mock_redis, mock_background_tasks):
        """Test that uploading PPTX returns 200 with task_id."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-123"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    # Create a mock PPTX file
                    file_content = b"PK\x03\x04"  # ZIP file header (PPTX is a ZIP)
                    file = BytesIO(file_content)

                    response = client.post(
                        "/upload",
                        files={"file": ("test.pptx", file, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                    )

                    assert response.status_code == 200
                    assert "task_id" in response.json()
                    assert response.json()["task_id"] == "test-task-123"

    def test_upload_pdf_accepts_and_returns_200(self, mock_redis, mock_background_tasks):
        """Test that uploading PDF returns 200 with task_id."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-456"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    # Create a mock PDF file
                    file_content = b"%PDF-1.4"
                    file = BytesIO(file_content)

                    response = client.post(
                        "/upload",
                        files={"file": ("test.pdf", file, "application/pdf")}
                    )

                    assert response.status_code == 200
                    assert "task_id" in response.json()

    def test_upload_docx_accepts_and_returns_200(self, mock_redis, mock_background_tasks):
        """Test that uploading DOCX returns 200 with task_id."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-789"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    # Create a mock DOCX file
                    file_content = b"PK\x03\x04"  # ZIP file header
                    file = BytesIO(file_content)

                    response = client.post(
                        "/upload",
                        files={"file": ("test.docx", file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                    )

                    assert response.status_code == 200
                    assert "task_id" in response.json()

    def test_upload_xlsx_accepts_and_returns_200(self, mock_redis, mock_background_tasks):
        """Test that uploading XLSX returns 200 with task_id."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-abc"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    # Create a mock XLSX file
                    file_content = b"PK\x03\x04"  # ZIP file header
                    file = BytesIO(file_content)

                    response = client.post(
                        "/upload",
                        files={"file": ("test.xlsx", file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                    )

                    assert response.status_code == 200
                    assert "task_id" in response.json()

    def test_upload_md_accepts_and_returns_200(self, mock_redis, mock_background_tasks):
        """Test that uploading Markdown returns 200 with task_id."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-def"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    # Create a mock Markdown file
                    file_content = b"# Test Document\n\nSome content here."
                    file = BytesIO(file_content)

                    response = client.post(
                        "/upload",
                        files={"file": ("test.md", file, "text/markdown")}
                    )

                    assert response.status_code == 200
                    assert "task_id" in response.json()

    def test_upload_saves_to_redis(self, mock_redis, mock_background_tasks):
        """Test that upload saves task metadata to Redis."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-123"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    file_content = b"PK\x03\x04"
                    file = BytesIO(file_content)

                    client.post(
                        "/upload",
                        files={"file": ("test.pptx", file, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                    )

                    # Verify Redis was called
                    mock_redis.set.assert_called()

    def test_upload_starts_background_task(self, mock_redis, mock_background_tasks):
        """Test that upload starts background processing task."""
        mock_redis.set.return_value = True

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                with patch('app.api.magazine_api.uuid4', return_value="test-task-123"):
                    from app.api.magazine_api import app

                    client = TestClient(app)

                    file_content = b"PK\x03\x04"
                    file = BytesIO(file_content)

                    client.post(
                        "/upload",
                        files={"file": ("test.pptx", file, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                    )

                    # Verify background task was added
                    mock_background_tasks.add_task.assert_called()


class TestMagazineAPIStatus:
    """Tests for GET /status/{task_id} endpoint."""

    def test_get_status_returns_task_status(self, mock_redis):
        """Test that GET /status/{task_id} returns task status."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "processing",
            "progress": 50
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/status/test-task-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert data["progress"] == 50

    def test_get_status_nonexistent_task_returns_404(self, mock_redis):
        """Test that GET /status/{task_id} returns 404 for nonexistent task."""
        mock_redis.get.return_value = None

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/status/nonexistent-task")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_status_with_completed_task(self, mock_redis):
        """Test that status shows completed task."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "completed",
            "progress": 100
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/status/test-task-123")

            assert response.status_code == 200
            assert response.json()["status"] == "completed"


class TestMagazineAPIFidelity:
    """Tests for GET /fidelity/{task_id} endpoint."""

    def test_get_fidelity_returns_report(self, mock_redis):
        """Test that GET /fidelity/{task_id} returns fidelity report."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "fidelity_report": {
                "overall_score": 0.95,
                "fingerprint_score": 1.0,
                "linkage_score": 0.9,
                "semantic_score": 0.95,
                "passed": True,
                "details": {},
                "repair_suggestions": []
            }
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/fidelity/test-task-123")

            assert response.status_code == 200
            data = response.json()
            assert "fidelity_report" in data
            assert data["fidelity_report"]["overall_score"] == 0.95

    def test_get_fidelity_nonexistent_task_returns_404(self, mock_redis):
        """Test that GET /fidelity/{task_id} returns 404 for nonexistent task."""
        mock_redis.get.return_value = None

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/fidelity/nonexistent-task")

            assert response.status_code == 404

    def test_get_fidelity_incomplete_task(self, mock_redis):
        """Test that GET /fidelity/{task_id} returns error for incomplete task."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "processing",
            "fidelity_report": None
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/fidelity/test-task-123")

            # Should return error or null report
            assert response.status_code in [400, 200]


class TestMagazineAPIExport:
    """Tests for GET /export/{task_id} endpoint."""

    def test_get_export_returns_file(self, mock_redis):
        """Test that GET /export/{task_id} returns exported file."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "completed",
            "output_path": "/exports/test-task-123.pdf"
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.FileResponse') as MockFileResponse:
                MockFileResponse.return_value = MagicMock(status_code=200)

                from app.api.magazine_api import app

                client = TestClient(app)

                response = client.get("/export/test-task-123?format=pdf")

                # FileResponse should be called
                MockFileResponse.assert_called()

    def test_get_export_incomplete_task_returns_400(self, mock_redis):
        """Test that GET /export/{task_id} returns 400 for incomplete task."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "processing",
            "output_path": None
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/export/test-task-123?format=pdf")

            assert response.status_code == 400
            assert "not complete" in response.json()["detail"].lower() or "processing" in response.json()["detail"].lower()

    def test_get_export_nonexistent_task_returns_404(self, mock_redis):
        """Test that GET /export/{task_id} returns 404 for nonexistent task."""
        mock_redis.get.return_value = None

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/export/nonexistent-task?format=pdf")

            assert response.status_code == 404

    def test_get_export_unsupported_format(self, mock_redis):
        """Test that GET /export/{task_id} returns error for unsupported format."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-task-123",
            "status": "completed",
            "output_path": "/exports/test-task-123.pdf"
        }).encode()

        with patch('app.api.magazine_api.redis_client', mock_redis):
            from app.api.magazine_api import app

            client = TestClient(app)

            response = client.get("/export/test-task-123?format=unsupported")

            assert response.status_code == 400 or response.status_code == 422


class TestMagazineAPIErrorHandling:
    """Tests for API error handling."""

    def test_upload_no_file_provided(self, mock_redis, mock_background_tasks):
        """Test that upload without file returns error."""
        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                from app.api.magazine_api import app

                client = TestClient(app)

                response = client.post("/upload")

                # Should return error (422 Unprocessable Entity or 400)
                assert response.status_code in [400, 422]

    def test_upload_empty_file(self, mock_redis, mock_background_tasks):
        """Test that upload with empty file returns error."""
        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                from app.api.magazine_api import app

                client = TestClient(app)

                file_content = b""
                file = BytesIO(file_content)

                response = client.post(
                    "/upload",
                    files={"file": ("empty.pptx", file, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                )

                # Should return error
                assert response.status_code in [400, 422]

    def test_redis_connection_error_handling(self, mock_redis, mock_background_tasks):
        """Test that Redis connection errors are handled gracefully."""
        mock_redis.set.side_effect = Exception("Redis connection error")

        with patch('app.api.magazine_api.redis_client', mock_redis):
            with patch('app.api.magazine_api.BackgroundTasks', return_value=mock_background_tasks):
                from app.api.magazine_api import app

                client = TestClient(app)

                file_content = b"PK\x03\x04"
                file = BytesIO(file_content)

                response = client.post(
                    "/upload",
                    files={"file": ("test.pptx", file, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
                )

                # Should handle error gracefully
                assert response.status_code in [500, 400]