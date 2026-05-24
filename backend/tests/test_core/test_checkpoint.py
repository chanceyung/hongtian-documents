"""Checkpoint System Tests"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import aiosqlite
import pytest

from app.core.checkpoint import CheckpointDB, CheckpointInfo, checkpoint_db
from app.models.design_spec import ColorScheme, DesignSpec, Typography
from app.models.edit_actions import EditAction, MagazineEditPlan, SlideEditPlan
from app.models.unified_document import (
    BoundingBox,
    ContentFingerprint,
    ImageElement,
    TextElement,
    UnifiedDocument,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create temporary database file"""
    db_path = tmp_path / "test_checkpoints.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
async def checkpoint_db_instance(temp_db_path: str) -> CheckpointDB:
    """Create isolated checkpoint database for testing"""
    db = CheckpointDB()
    db._db_url = temp_db_path
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def cp0_state() -> dict:
    """CP0 checkpoint state (after upload)"""
    return {
        "file_path": "/tmp/test.pptx",
        "output_format": "pdf",
        "template_id": "modern_tech",
    }


@pytest.fixture
def cp1_state() -> dict:
    """CP1 checkpoint state (after parse)"""
    doc = UnifiedDocument(
        source_file="/tmp/test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            TextElement(
                id="t1",
                content="Title",
                page=1,
                bbox=BoundingBox(left=100, top=100, width=800, height=100),
                level=1,
            ),
            TextElement(
                id="t2",
                content="Body text",
                page=1,
                bbox=BoundingBox(left=100, top=220, width=800, height=600),
                level=0,
            ),
        ],
        images=[
            ImageElement(
                id="img1",
                local_path="/tmp/image1.png",
                page=1,
                bbox=BoundingBox(left=500, top=300, width=400, height=300),
            ),
        ],
        parse_warnings=["Warning: font not found"],
    )
    return {
        "document": doc.model_dump(),
        "parse_warnings": doc.parse_warnings,
    }


@pytest.fixture
def cp2_state() -> dict:
    """CP2 checkpoint state (after analyze)"""
    return {
        "analysis": {
            "theme": "technology",
            "tone": "professional",
            "target_audience": "business",
            "key_points": ["point1", "point2"],
        },
        "execution_plan": {
            "slides": [
                {
                    "page_number": 1,
                    "title": "Cover",
                    "template": "cover_page",
                }
            ]
        },
    }


@pytest.fixture
def cp3_state() -> dict:
    """CP3 checkpoint state (after design)"""
    design_spec = DesignSpec(
        colors=ColorScheme(primary="#2E86AB"),
    )
    edit_plan = MagazineEditPlan(
        document_id="test_doc",
        template_id="modern_tech",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="cover",
                actions=[
                    EditAction(
                        type="replace_text",
                        target_selector="title",
                        source_id="t1",
                        content="New Title",
                    )
                ],
            )
        ],
        design_spec=design_spec.model_dump(),
    )
    return {
        "edit_plan": edit_plan.model_dump(),
        "design_spec": design_spec.model_dump(),
        "supplemented": True,
    }


@pytest.fixture
def cp4_state() -> dict:
    """CP4 checkpoint state (after render)"""
    return {
        "output_path": "/tmp/output/test_document.pdf",
        "fidelity_score": 0.98,
        "fidelity_passed": True,
    }


class TestCheckpointSystem:
    """Test checkpoint save and restore operations"""

    @pytest.mark.asyncio
    async def test_save_and_restore_cp0(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
    ):
        """Test saving and restoring CP0 checkpoint"""
        task_id = "task_001"

        # Save CP0
        info = await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)
        assert info.task_id == task_id
        assert info.level == 0
        assert info.phase_name == "upload"

        # Restore CP0
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 0)
        assert restored is not None
        assert restored["file_path"] == cp0_state["file_path"]
        assert restored["output_format"] == cp0_state["output_format"]
        assert restored["template_id"] == cp0_state["template_id"]

    @pytest.mark.asyncio
    async def test_save_and_restore_cp1(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp1_state: dict,
    ):
        """Test saving and restoring CP1 checkpoint with Pydantic model"""
        task_id = "task_001"

        # Save CP1
        info = await checkpoint_db_instance.save_checkpoint(task_id, 1, cp1_state)
        assert info.level == 1
        assert info.phase_name == "parse"

        # Restore CP1
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 1)
        assert restored is not None
        assert "document" in restored
        assert restored["document"]["source_file"] == cp1_state["document"]["source_file"]
        assert len(restored["document"]["texts"]) == 2
        assert len(restored["document"]["images"]) == 1
        assert restored["parse_warnings"] == cp1_state["parse_warnings"]

    @pytest.mark.asyncio
    async def test_save_and_restore_cp2(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp2_state: dict,
    ):
        """Test saving and restoring CP2 checkpoint"""
        task_id = "task_001"

        # Save CP2
        info = await checkpoint_db_instance.save_checkpoint(task_id, 2, cp2_state)
        assert info.level == 2
        assert info.phase_name == "analyze"

        # Restore CP2
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 2)
        assert restored is not None
        assert restored["analysis"]["theme"] == "technology"
        assert restored["execution_plan"]["slides"][0]["title"] == "Cover"

    @pytest.mark.asyncio
    async def test_save_and_restore_cp3(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp3_state: dict,
    ):
        """Test saving and restoring CP3 checkpoint with complex Pydantic models"""
        task_id = "task_001"

        # Save CP3
        info = await checkpoint_db_instance.save_checkpoint(task_id, 3, cp3_state)
        assert info.level == 3
        assert info.phase_name == "design"

        # Restore CP3
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 3)
        assert restored is not None
        assert "edit_plan" in restored
        assert restored["edit_plan"]["document_id"] == "test_doc"
        assert restored["design_spec"]["colors"]["primary"] == "#2E86AB"
        assert restored["supplemented"] is True

    @pytest.mark.asyncio
    async def test_save_and_restore_cp4(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp4_state: dict,
    ):
        """Test saving and restoring CP4 checkpoint"""
        task_id = "task_001"

        # Save CP4
        info = await checkpoint_db_instance.save_checkpoint(task_id, 4, cp4_state)
        assert info.level == 4
        assert info.phase_name == "render"

        # Restore CP4
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 4)
        assert restored is not None
        assert restored["output_path"] == cp4_state["output_path"]
        assert restored["fidelity_score"] == 0.98
        assert restored["fidelity_passed"] is True

    @pytest.mark.asyncio
    async def test_restore_nonexistent_checkpoint(
        self,
        checkpoint_db_instance: CheckpointDB,
    ):
        """Test restoring a checkpoint that doesn't exist"""
        task_id = "nonexistent_task"

        # Try to restore CP1 for nonexistent task
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 1)
        assert restored is None

    @pytest.mark.asyncio
    async def test_list_checkpoints(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
        cp1_state: dict,
        cp2_state: dict,
    ):
        """Test listing all checkpoints for a task"""
        task_id = "task_002"

        # Save multiple checkpoints
        await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 1, cp1_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 2, cp2_state)

        # List checkpoints
        checkpoints = await checkpoint_db_instance.list_checkpoints(task_id)
        assert len(checkpoints) == 3
        assert checkpoints[0].level == 0
        assert checkpoints[1].level == 1
        assert checkpoints[2].level == 2
        assert all(cp.task_id == task_id for cp in checkpoints)

    @pytest.mark.asyncio
    async def test_cleanup_removes_all_checkpoints(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
        cp1_state: dict,
        cp2_state: dict,
    ):
        """Test cleanup removes all checkpoints for a task"""
        task_id = "task_003"

        # Save multiple checkpoints
        await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 1, cp1_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 2, cp2_state)

        # Verify checkpoints exist
        checkpoints = await checkpoint_db_instance.list_checkpoints(task_id)
        assert len(checkpoints) == 3

        # Cleanup
        deleted_count = await checkpoint_db_instance.delete_task_checkpoints(task_id)
        assert deleted_count == 3

        # Verify checkpoints are gone
        checkpoints = await checkpoint_db_instance.list_checkpoints(task_id)
        assert len(checkpoints) == 0

    @pytest.mark.asyncio
    async def test_service_restart_simulation(
        self,
        temp_db_path: str,
        cp0_state: dict,
        cp1_state: dict,
        cp2_state: dict,
    ):
        """Test that checkpoints survive service restart"""
        task_id = "task_004"

        # Phase 1: Save checkpoints with first database instance
        db1 = CheckpointDB()
        db1._db_url = temp_db_path
        await db1.initialize()
        await db1.save_checkpoint(task_id, 0, cp0_state)
        await db1.save_checkpoint(task_id, 1, cp1_state)
        await db1.save_checkpoint(task_id, 2, cp2_state)
        await db1.close()

        # Phase 2: Simulate service restart by creating new instance
        db2 = CheckpointDB()
        db2._db_url = temp_db_path
        await db2.initialize()

        # Verify checkpoints are still accessible
        restored_cp0 = await db2.load_checkpoint(task_id, 0)
        restored_cp1 = await db2.load_checkpoint(task_id, 1)
        restored_cp2 = await db2.load_checkpoint(task_id, 2)

        assert restored_cp0 is not None
        assert restored_cp1 is not None
        assert restored_cp2 is not None
        assert restored_cp0["file_path"] == cp0_state["file_path"]
        assert restored_cp1["document"]["source_file"] == cp1_state["document"]["source_file"]
        assert restored_cp2["analysis"]["theme"] == "technology"

        await db2.close()

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
        cp1_state: dict,
        cp2_state: dict,
    ):
        """Test getting the highest level checkpoint"""
        task_id = "task_005"

        # Save checkpoints in non-sequential order
        await checkpoint_db_instance.save_checkpoint(task_id, 2, cp2_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)
        await checkpoint_db_instance.save_checkpoint(task_id, 1, cp1_state)

        # Get latest checkpoint
        latest = await checkpoint_db_instance.get_latest_checkpoint(task_id)
        assert latest is not None
        level, state = latest
        assert level == 2
        assert state["analysis"]["theme"] == "technology"

    @pytest.mark.asyncio
    async def test_checkpoint_update(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
    ):
        """Test that updating a checkpoint replaces the old one"""
        task_id = "task_006"

        # Save initial CP0
        await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)

        # Update CP0 with new state
        updated_state = {
            "file_path": "/tmp/updated.pptx",
            "output_format": "pptx",
            "template_id": "elegant",
        }
        await checkpoint_db_instance.save_checkpoint(task_id, 0, updated_state)

        # Verify only one checkpoint exists at level 0
        checkpoints = await checkpoint_db_instance.list_checkpoints(task_id)
        assert len(checkpoints) == 1

        # Verify the state is updated
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 0)
        assert restored["file_path"] == "/tmp/updated.pptx"
        assert restored["output_format"] == "pptx"
        assert restored["template_id"] == "elegant"

    @pytest.mark.asyncio
    async def test_concurrent_checkpoint_operations(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
        cp1_state: dict,
    ):
        """Test thread-safe concurrent checkpoint operations"""
        task_id = "task_007"

        # Simulate concurrent saves
        async def save_checkpoint(level: int, state: dict):
            await checkpoint_db_instance.save_checkpoint(task_id, level, state)

        await asyncio.gather(
            save_checkpoint(0, cp0_state),
            save_checkpoint(1, cp1_state),
        )

        # Verify both checkpoints are saved correctly
        checkpoints = await checkpoint_db_instance.list_checkpoints(task_id)
        assert len(checkpoints) == 2

        cp0_restored = await checkpoint_db_instance.load_checkpoint(task_id, 0)
        cp1_restored = await checkpoint_db_instance.load_checkpoint(task_id, 1)

        assert cp0_restored is not None
        assert cp1_restored is not None
        assert cp0_restored["file_path"] == cp0_state["file_path"]
        assert cp1_restored["document"]["source_file"] == cp1_state["document"]["source_file"]

    @pytest.mark.asyncio
    async def test_empty_state_serialization(
        self,
        checkpoint_db_instance: CheckpointDB,
    ):
        """Test serializing empty state dict"""
        task_id = "task_008"

        # Save checkpoint with empty state
        await checkpoint_db_instance.save_checkpoint(task_id, 0, {})

        # Restore and verify
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 0)
        assert restored is not None
        assert restored == {}

    @pytest.mark.asyncio
    async def test_nested_dict_serialization(
        self,
        checkpoint_db_instance: CheckpointDB,
    ):
        """Test serializing deeply nested dictionaries"""
        task_id = "task_009"

        nested_state = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": "deep_value",
                        "numbers": [1, 2, 3],
                    }
                },
                "list_of_dicts": [
                    {"id": 1, "name": "item1"},
                    {"id": 2, "name": "item2"},
                ],
            }
        }

        # Save and restore
        await checkpoint_db_instance.save_checkpoint(task_id, 0, nested_state)
        restored = await checkpoint_db_instance.load_checkpoint(task_id, 0)

        assert restored is not None
        assert restored["level1"]["level2"]["level3"]["data"] == "deep_value"
        assert restored["level1"]["level2"]["level3"]["numbers"] == [1, 2, 3]
        assert len(restored["level1"]["list_of_dicts"]) == 2

    @pytest.mark.asyncio
    async def test_checkpoint_info_model(
        self,
        checkpoint_db_instance: CheckpointDB,
        cp0_state: dict,
    ):
        """Test CheckpointInfo Pydantic model"""
        task_id = "task_010"

        # Save checkpoint
        info = await checkpoint_db_instance.save_checkpoint(task_id, 0, cp0_state)

        # Verify CheckpointInfo fields
        assert isinstance(info, CheckpointInfo)
        assert info.id == f"{task_id}_cp0"
        assert info.task_id == task_id
        assert info.level == 0
        assert info.phase_name == "upload"
        assert isinstance(info.created_at, str)
        # Verify ISO format datetime
        datetime.fromisoformat(info.created_at)