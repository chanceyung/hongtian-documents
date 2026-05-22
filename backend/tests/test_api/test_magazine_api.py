"""Tests for Magazine API endpoints."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from io import BytesIO
import zipfile
import tempfile
import shutil

# Create minimal valid test files
def create_minimal_pptx() -> bytes:
    """Create a minimal valid PPTX file (ZIP with required structure)."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Required minimal PPTX structure
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>''')
        zf.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>''')
        zf.writestr("ppt/presentation.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:slideIdLst><p:slideId id="256" r:id="r1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></p:slideIdLst>
</p:presentation>''')
        zf.writestr("ppt/_rels/presentation.xml.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slide1.xml"/>
</Relationships>''')
        zf.writestr("ppt/slide1.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:spTree><p:nvGrpSpPr/></p:spTree>
</p:sld>''')
    buffer.seek(0)
    return buffer.getvalue()


def create_minimal_docx() -> bytes:
    """Create a minimal valid DOCX file (ZIP with required structure)."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        zf.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        zf.writestr("word/document.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body>
</w:document>''')
    buffer.seek(0)
    return buffer.getvalue()


def create_minimal_xlsx() -> bytes:
    """Create a minimal valid XLSX file (ZIP with required structure)."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
</Types>''')
        zf.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        zf.writestr("xl/workbook.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheets><sheet name="Sheet1" sheetId="1" r:id="r1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>
</workbook>''')
    buffer.seek(0)
    return buffer.getvalue()


def create_minimal_pdf() -> bytes:
    """Create a minimal valid PDF file."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF"


def create_minimal_md() -> bytes:
    """Create a minimal valid Markdown file."""
    return b"# Test Document\n\nThis is a test content."


def create_minimal_txt() -> bytes:
    """Create a minimal valid text file."""
    return b"This is a plain text file."


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
async def client():
    """Create test client for FastAPI app."""
    from app.main import app
    from app.core.config import settings
    from app.core.database import task_db

    # Use temp directory for outputs
    original_output_dir = settings.OUTPUT_DIR
    temp_dir = Path(tempfile.mkdtemp())
    settings.OUTPUT_DIR = str(temp_dir)

    # Use in-memory database for tests
    original_db_url = settings.DATABASE_URL
    settings.DATABASE_URL = "sqlite:///:memory:"

    # Initialize database
    await task_db.initialize()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Cleanup
        await task_db.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
        settings.OUTPUT_DIR = original_output_dir
        settings.DATABASE_URL = original_db_url


class TestMagazineAPIUpload:
    """Tests for POST /api/magazine/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_unsupported_format_returns_400(self, client):
        """Test that uploading unsupported format returns 400 status."""
        file_content = b"test content"
        response = await client.post(
            "/api/magazine/upload",
            files={"file": ("test.unsupported", BytesIO(file_content), "application/octet-stream")}
        )

        assert response.status_code == 400
        assert "不支持的格式" in response.json()["detail"] or "format" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_pptx_accepts_and_returns_200_with_task_id(self, client):
        """Test that uploading PPTX returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()
            assert response.json()["status"] == "pending"
            assert "session_id" in response.json()

    @pytest.mark.asyncio
    async def test_upload_pdf_accepts_and_returns_200(self, client):
        """Test that uploading PDF returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            pdf_bytes = create_minimal_pdf()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pdf", BytesIO(pdf_bytes), "application/pdf")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()
            assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_upload_docx_accepts_and_returns_200(self, client):
        """Test that uploading DOCX returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            docx_bytes = create_minimal_docx()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.docx", BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()

    @pytest.mark.asyncio
    async def test_upload_xlsx_accepts_and_returns_200(self, client):
        """Test that uploading XLSX returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            xlsx_bytes = create_minimal_xlsx()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.xlsx", BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()

    @pytest.mark.asyncio
    async def test_upload_md_accepts_and_returns_200(self, client):
        """Test that uploading Markdown returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            md_bytes = create_minimal_md()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.md", BytesIO(md_bytes), "text/markdown")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()

    @pytest.mark.asyncio
    async def test_upload_txt_accepts_and_returns_200(self, client):
        """Test that uploading text file returns 200 with task_id."""
        with patch('app.api.v1._run_pipeline'):
            txt_bytes = create_minimal_txt()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.txt", BytesIO(txt_bytes), "text/plain")}
            )

            assert response.status_code == 200
            assert "task_id" in response.json()

    @pytest.mark.asyncio
    async def test_upload_with_session_id_param(self, client):
        """Test that upload accepts session_id query parameter."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            response = await client.post(
                "/api/magazine/upload?session_id=custom-session-123",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )

            assert response.status_code == 200
            assert response.json()["session_id"] == "custom-session-123"

    @pytest.mark.asyncio
    async def test_upload_with_session_id_header(self, client):
        """Test that upload accepts X-Session-ID header."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            response = await client.post(
                "/api/magazine/upload",
                headers={"X-Session-ID": "header-session-456"},
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )

            assert response.status_code == 200
            assert response.json()["session_id"] == "header-session-456"

    @pytest.mark.asyncio
    async def test_upload_starts_background_task(self, client):
        """Test that upload starts background processing task."""
        with patch('app.api.v1._run_pipeline') as mock_pipeline:
            pptx_bytes = create_minimal_pptx()

            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )

            assert response.status_code == 200

            # Wait a bit for background task to be added
            await asyncio.sleep(0.1)

            # The mock should have been called (background task was scheduled)
            # Note: We can't directly verify the background task was called,
            # but we can verify the task was created
            from app.core.database import task_db
            task_id = response.json()["task_id"]
            task = await task_db.get_task(task_id)
            assert task is not None
            assert task["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_upload_invalid_signature_returns_400(self, client):
        """Test that file with invalid magic number returns 400."""
        # Create a file with .pptx extension but invalid content
        invalid_content = b"INVALID_CONTENT_NOT_ZIP"

        response = await client.post(
            "/api/magazine/upload",
            files={"file": ("test.pptx", BytesIO(invalid_content), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
        )

        assert response.status_code == 400
        assert "不匹配" in response.json()["detail"]


class TestMagazineAPIStatus:
    """Tests for GET /api/magazine/status/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_returns_task_status(self, client):
        """Test that GET /status/{task_id} returns task status."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # First upload a file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Get status
            response = await client.get(f"/api/magazine/status/{task_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "pending"
            assert "progress" in data

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_task_returns_404(self, client):
        """Test that GET /status/{task_id} returns 404 for nonexistent task."""
        response = await client.get("/api/magazine/status/nonexistent-task-id")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "不存在" in detail or "404" in detail.lower() or "not found" in detail.lower()


class TestMagazineAPIFidelity:
    """Tests for GET /api/magazine/fidelity/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_fidelity_returns_report(self, client, temp_output_dir):
        """Test that GET /fidelity/{task_id} returns fidelity report."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Create task summary file
            from app.core.config import settings
            task_dir = Path(settings.OUTPUT_DIR) / task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            summary = {
                "task_id": task_id,
                "overall_score": 0.95,
                "fingerprint_score": 1.0,
                "linkage_score": 0.9,
                "semantic_score": 0.95,
                "passed": True,
                "details": {},
                "repair_suggestions": []
            }
            (task_dir / "task_summary.json").write_text(json.dumps(summary), encoding="utf-8")

            # Get fidelity report
            response = await client.get(f"/api/magazine/fidelity/{task_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["overall_score"] == 0.95
            assert data["fingerprint_score"] == 1.0
            assert data["passed"] is True

    @pytest.mark.asyncio
    async def test_get_fidelity_nonexistent_task_returns_404(self, client):
        """Test that GET /fidelity/{task_id} returns 404 for nonexistent task."""
        response = await client.get("/api/magazine/fidelity/nonexistent-task-id")

        assert response.status_code == 404
        # Just verify status code - error message may vary based on implementation

    @pytest.mark.asyncio
    async def test_get_fidelity_no_report_returns_404(self, client):
        """Test that GET /fidelity/{task_id} returns 404 when report not generated."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Get fidelity report without creating summary file
            response = await client.get(f"/api/magazine/fidelity/{task_id}")

            assert response.status_code == 404
            detail = response.json()["detail"]
            assert "尚未生成" in detail or "404" in detail.lower() or "not found" in detail.lower()


class TestMagazineAPIExport:
    """Tests for GET /api/magazine/export/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_export_returns_pdf_file(self, client):
        """Test that GET /export/{task_id} returns PDF file."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Update task status to completed
            from app.core.database import task_db
            await task_db.update_task(
                task_id, status="completed", output_path=f"/output/{task_id}/magazine.pdf"
            )

            # Create output file
            from app.core.config import settings
            task_dir = Path(settings.OUTPUT_DIR) / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "magazine.pdf").write_bytes(create_minimal_pdf())

            # Export file
            response = await client.get(f"/api/magazine/export/{task_id}?format=pdf")

            assert response.status_code == 200
            assert "application/pdf" in response.headers.get("content-type", "")
            assert response.content.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_get_export_returns_pptx_file(self, client):
        """Test that GET /export/{task_id} returns PPTX file."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Update task status to completed
            from app.core.database import task_db
            await task_db.update_task(
                task_id, status="completed", output_path=f"/output/{task_id}/magazine.pptx"
            )

            # Create output file
            from app.core.config import settings
            task_dir = Path(settings.OUTPUT_DIR) / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "magazine.pptx").write_bytes(create_minimal_pptx())

            # Export file
            response = await client.get(f"/api/magazine/export/{task_id}?format=pptx")

            assert response.status_code == 200
            assert "openxmlformats" in response.headers.get("content-type", "")
            assert response.content.startswith(b"PK\x03\x04")

    @pytest.mark.asyncio
    async def test_get_export_incomplete_task_returns_400(self, client):
        """Test that GET /export/{task_id} returns 400 for incomplete task."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Try to export while task is still pending
            response = await client.get(f"/api/magazine/export/{task_id}?format=pdf")

            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "尚未" in detail or "未完成" in detail or "not complete" in detail.lower()

    @pytest.mark.asyncio
    async def test_get_export_nonexistent_task_returns_404(self, client):
        """Test that GET /export/{task_id} returns 404 for nonexistent task."""
        response = await client.get("/api/magazine/export/nonexistent-task-id?format=pdf")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_export_file_not_exists_returns_404(self, client):
        """Test that GET /export/{task_id} returns 404 when file doesn't exist."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Update task status to completed but don't create file
            from app.core.database import task_db
            await task_db.update_task(
                task_id, status="completed", output_path=f"/output/{task_id}/magazine.pdf"
            )

            # Try to export
            response = await client.get(f"/api/magazine/export/{task_id}?format=pdf")

            assert response.status_code == 404
            detail = response.json()["detail"]
            assert "不存在" in detail or "404" in detail.lower() or "not found" in detail.lower()


class TestMagazineAPIGenerate:
    """Tests for POST /api/magazine/generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_magazine_with_existing_task(self, client):
        """Test that generate endpoint works with existing task."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Generate with custom parameters
            generate_req = {
                "task_id": task_id,
                "session_id": "test-session",
                "output_format": "pptx",
                "template_id": "modern_tech"
            }

            response = await client.post("/api/magazine/generate", json=generate_req)

            assert response.status_code == 200
            assert response.json()["task_id"] == task_id
            assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_generate_nonexistent_task_returns_404(self, client):
        """Test that generate returns 404 for nonexistent task."""
        generate_req = {
            "task_id": "nonexistent-task-id",
            "output_format": "pdf"
        }

        response = await client.post("/api/magazine/generate", json=generate_req)

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "不存在" in detail or "404" in detail.lower() or "not found" in detail.lower()

    @pytest.mark.asyncio
    async def test_generate_with_completed_task_returns_400(self, client):
        """Test that generate returns 400 for already completed task."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Mark task as completed
            from app.core.database import task_db
            await task_db.update_task(task_id, status="completed")

            # Try to regenerate
            generate_req = {
                "task_id": task_id,
                "output_format": "pdf"
            }

            response = await client.post("/api/magazine/generate", json=generate_req)

            assert response.status_code == 400
            assert "无法重新生成" in response.json()["detail"]


class TestMagazineAPIErrorHandling:
    """Tests for API error handling."""

    @pytest.mark.asyncio
    async def test_upload_no_file_provided(self, client):
        """Test that upload without file returns error."""
        response = await client.post("/api/magazine/upload")

        # Should return error (422 Unprocessable Entity)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client):
        """Test that upload with empty file is handled."""
        with patch('app.api.v1._run_pipeline'):
            empty_content = b""

            # Empty file with valid extension
            response = await client.post(
                "/api/magazine/upload",
                files={"file": ("empty.pptx", BytesIO(empty_content), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )

            # Should fail signature validation or file size check
            assert response.status_code in [400, 413]


class TestMagazineAPISSE:
    """Tests for GET /api/magazine/events/{task_id} SSE endpoint."""

    @pytest.mark.asyncio
    async def test_sse_endpoint_returns_event_stream(self, client):
        """Test that SSE endpoint returns text/event-stream."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            from app.core.database import task_db
            await task_db.update_task(task_id, status="completed", progress=1.0)

            response = await client.get(f"/api/magazine/events/{task_id}")

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_sse_nonexistent_task_returns_404(self, client):
        """Test that SSE returns 404 for nonexistent task."""
        response = await client.get("/api/magazine/events/nonexistent-task-id")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "不存在" in detail or "404" in detail.lower() or "not found" in detail.lower()


class TestMagazineAPIDelete:
    """Tests for DELETE /api/magazine/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_task_removes_task_and_files(self, client):
        """Test that delete removes task from database and files from disk."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Mark task as completed
            from app.core.database import task_db
            await task_db.update_task(task_id, status="completed")

            # Delete task
            response = await client.delete(f"/api/magazine/tasks/{task_id}")

            assert response.status_code == 200
            assert response.json()["status"] == "deleted"
            assert response.json()["task_id"] == task_id

            # Verify task is gone from database
            task = await task_db.get_task(task_id)
            assert task is None

            # Verify files are gone from disk
            from app.core.config import settings
            task_dir = Path(settings.OUTPUT_DIR) / task_id
            assert not task_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_active_task_returns_400(self, client):
        """Test that delete returns 400 for active task."""
        with patch('app.api.v1._run_pipeline'):
            pptx_bytes = create_minimal_pptx()

            # Upload file
            upload_resp = await client.post(
                "/api/magazine/upload",
                files={"file": ("test.pptx", BytesIO(pptx_bytes), "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            task_id = upload_resp.json()["task_id"]

            # Mark task as processing
            from app.core.database import task_db
            await task_db.update_task(task_id, status="parsing")

            # Try to delete
            response = await client.delete(f"/api/magazine/tasks/{task_id}")

            assert response.status_code == 400
            assert "正在处理中" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task_returns_404(self, client):
        """Test that delete returns 404 for nonexistent task."""
        response = await client.delete("/api/magazine/tasks/nonexistent-task-id")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "不存在" in detail or "404" in detail.lower() or "not found" in detail.lower()