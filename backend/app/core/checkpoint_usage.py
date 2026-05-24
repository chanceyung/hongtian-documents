"""Checkpoint System Usage Examples"""
from __future__ import annotations

from app.core.checkpoint import checkpoint_db
from app.models.edit_actions import MagazineEditPlan
from app.models.unified_document import UnifiedDocument


async def example_pipeline_with_checkpoints(task_id: str):
    """Example: Using checkpoints throughout the pipeline"""

    # CP0: After file upload
    await checkpoint_db.initialize()
    await checkpoint_db.save_checkpoint(
        task_id,
        0,
        {
            "file_path": "/path/to/document.pptx",
            "output_format": "pdf",
            "template_id": "modern_tech",
        },
    )

    # CP1: After parsing
    document = UnifiedDocument(...)  # From parser
    await checkpoint_db.save_checkpoint(
        task_id,
        1,
        {
            "document": document.model_dump(),
            "parse_warnings": [],
        },
    )

    # CP2: After analysis
    await checkpoint_db.save_checkpoint(
        task_id,
        2,
        {
            "analysis": {"theme": "technology", "tone": "professional"},
            "execution_plan": {...},
        },
    )

    # CP3: After design
    edit_plan = MagazineEditPlan(...)  # From designer
    await checkpoint_db.save_checkpoint(
        task_id,
        3,
        {
            "edit_plan": edit_plan.model_dump(),
            "design_spec": edit_plan.design_spec.model_dump(),
            "supplemented": True,
        },
    )

    # CP4: After rendering
    await checkpoint_db.save_checkpoint(
        task_id,
        4,
        {
            "output_path": "/path/to/output.pdf",
            "fidelity_score": 0.98,
            "fidelity_passed": True,
        },
    )


async def example_restore_from_checkpoint(task_id: str, level: int = 1):
    """Example: Restoring from a checkpoint"""
    await checkpoint_db.initialize()

    # Check if checkpoint exists
    state = await checkpoint_db.load_checkpoint(task_id, level)
    if state is None:
        print(f"Checkpoint CP{level} not found for task {task_id}")
        return

    # Restore and continue from checkpoint
    if level == 1:
        document = UnifiedDocument(**state["document"])
        print(f"Restored document with {len(document.texts)} text elements")
    elif level == 3:
        edit_plan = MagazineEditPlan(**state["edit_plan"])
        print(f"Restored edit plan with {len(edit_plan.pages)} pages")

    # Cleanup after completion
    await checkpoint_db.delete_task_checkpoints(task_id)
    await checkpoint_db.close()


async def example_list_checkpoints(task_id: str):
    """Example: Listing all checkpoints for a task"""
    await checkpoint_db.initialize()

    checkpoints = await checkpoint_db.list_checkpoints(task_id)
    print(f"Task {task_id} has {len(checkpoints)} checkpoints:")
    for cp in checkpoints:
        print(f"  - CP{cp.level} ({cp.phase_name}): {cp.created_at}")

    # Get latest checkpoint
    latest = await checkpoint_db.get_latest_checkpoint(task_id)
    if latest:
        level, state = latest
        print(f"Latest checkpoint: CP{level}")