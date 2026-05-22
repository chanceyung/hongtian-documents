# Test Files Model Migration Summary

This document summarizes the changes made to fix all test files in `D:/Aisoft/弘天文档/backend/tests/` to match the current data models.

## Changes Overview

All test files have been updated to use the correct model definitions from `app/models/`:

### Common Model Mappings

| Old Model | New Model | Key Changes |
|-----------|-----------|-------------|
| `ContentItem` | `TextElement` | `text` → `content`, `page_number` → `page` |
| `ImageItem` | `ImageElement` | `path` → `local_path`, `page_number` → `page`, `description` → `alt_text` |
| `Document` / `ParsedDocument` | `UnifiedDocument` | `elements` → `texts`/`images`/`tables`, removed `metadata` |
| `UnifiedDocument` | `UnifiedDocument` | Removed `fingerprint` field, use `compute_fingerprint()` method |
| `BoundingBox` | `BoundingBox` | `[left, top, right, bottom]` → `{left, top, width, height}` |
| `TableElement` | `TableElement` | Removed `rows`, use `data` (list of lists) |
| `EditAction` | `EditAction` | `action` → `type`, `id` → `source_id`, added `target_selector` |
| `MagazineEditPlan` | `MagazineEditPlan` | `template` → `template_id`, `actions` → `pages[].actions` |
| `SlideEditPlan` | `SlideEditPlan` | Added for page-level action organization |
| `ContentAssetLink` | `ContentAssetLink` | `image_id` → `asset_id`, `asset_type` field |
| `FidelityReport` | `FidelityReport` | Removed `repair_suggestions` field |

## Files Modified

### 1. `tests/conftest.py`
- Changed `sample_text_content` fixture to use `content` instead of `text`
- Changed `sample_image_content` fixture to use `local_path` instead of `path`
- Updated BoundingBox format to use `{left, top, width, height}`

### 2. `tests/test_parse.py`
- Updated `_parse_pptx` and `_parse_pdf` test functions to use new model APIs
- Changed result access from dictionary to model attributes
- Updated `compute_fingerprint()` method usage
- Fixed `bbox_distance` test to use BoundingBox model

### 3. Parser Test Files

#### `test_parsers/test_pptx_parser.py`
- Fixed table structure tests to use `table.data` instead of `table.rows`
- Updated header access from `table.headers` list of objects to `table.headers` list of strings

#### `test_parsers/test_docx_parser.py`
- Fixed table extraction tests to use `table.data` field
- Updated row content access patterns

#### `test_parsers/test_xlsx_parser.py`
- Fixed all table row access patterns to use `table.data` instead of `table.rows`
- Removed metadata access patterns (no longer supported)
- Updated numeric value tests to work with data field

#### `test_parsers/test_md_parser.py`
- Fixed table structure tests to use `table.data` field
- Updated row content extraction patterns

#### `test_parsers/test_pdf_parser.py`
- No major model changes needed (PDF tests already compatible)

### 4. Agent Test Files

#### `test_agents/test_parser_agent.py`
- Updated all `UnifiedDocument` instantiations to include `source_file` and `source_format`
- Changed `ContentItem` → `TextElement`, `ImageItem` → `ImageElement`
- Updated BoundingBox usage throughout
- Fixed metadata removal

#### `test_agents/test_analyzer_agent.py`
- Updated model imports and instantiations
- Changed document construction to use new field names
- Updated linkage test to use `ContentAssetLink` model

#### `test_agents/test_designer_agent.py`
- Updated `MagazineEditPlan` construction with `pages` structure
- Changed `EditAction` field names (`action` → `type`, `id` → `source_id`)
- Updated mock response content to match new action format

#### `test_agents/test_fidelity_agent.py`
- Updated `MagazineEditPlan` and `EditAction` usage throughout
- Changed document model instantiations
- Fixed linkage tests to use `ContentAssetLink` model
- Removed `repair_suggestions` field usage

#### `test_agents/test_supplement_agent.py`
- Updated `ImageElement` model usage
- Changed `MagazineEditPlan` construction to use `pages` structure
- Updated action access patterns to use `result.pages[].actions`

#### `test_agents/test_renderer_agent.py`
- Updated `MagazineEditPlan` construction throughout
- Changed all action-related tests to use new field names
- Updated document model instantiations

### 5. Workflow Test Files

#### `test_workflow/test_magazine_pipeline.py`
- Updated all `UnifiedDocument` constructions
- Changed `MagazineEditPlan` usage throughout
- Fixed `FidelityReport` instantiations (removed `repair_suggestions`)
- Updated `ImageElement` model usage
- Fixed all state management tests

### 6. API Test Files

#### `test_api/test_magazine_api.py`
- No major model changes needed (API tests use response parsing, not direct model construction)

## Key Pattern Changes

### 1. Document Construction
**Before:**
```python
UnifiedDocument(
    title="Test",
    content=[ContentItem(...)],
    images=[ImageItem(...)],
    metadata={"format": "pptx"}
)
```

**After:**
```python
UnifiedDocument(
    source_file="test.pptx",
    source_format="pptx",
    title="Test",
    texts=[TextElement(...)],
    images=[ImageElement(...)]
)
```

### 2. Action Plan Construction
**Before:**
```python
MagazineEditPlan(
    template="modern",
    actions=[
        EditAction(
            action="replace_span",
            id="text-1",
            content="Text"
        )
    ]
)
```

**After:**
```python
MagazineEditPlan(
    document_id="test-doc",
    template_id="modern",
    pages=[
        SlideEditPlan(
            page_number=1,
            template_page="cover",
            actions=[
                EditAction(
                    type="replace_text",
                    target_selector="text-1",
                    source_id="text-1",
                    content="Text"
                )
            ]
        )
    ]
)
```

### 3. Table Data Access
**Before:**
```python
for row in table.rows:
    for cell in row.cells:
        print(cell.content)
```

**After:**
```python
for row in table.data:
    for cell in row:
        print(cell)
```

### 4. Bounding Box Usage
**Before:**
```python
bbox=[0.1, 0.1, 0.5, 0.3]  # [left, top, right, bottom]
```

**After:**
```python
bbox=BoundingBox(left=10, top=10, width=50, height=30)  # {left, top, width, height}
```

## Validation

All test files have been validated for:
1. Correct syntax (no import or compilation errors)
2. Proper model imports from `app.models`
3. Consistent use of new field names
4. Removal of deprecated fields and methods
5. Correct usage of new data structures

## Testing

To verify all test files are syntactically correct:
```bash
cd D:/Aisoft/弘天文档/backend
python -c "
import sys
test_files = [
    'tests/conftest.py',
    'tests/test_parse.py',
    'tests/test_parsers/test_pptx_parser.py',
    'tests/test_parsers/test_pdf_parser.py',
    'tests/test_parsers/test_docx_parser.py',
    'tests/test_parsers/test_md_parser.py',
    'tests/test_parsers/test_xlsx_parser.py',
    'tests/test_agents/test_parser_agent.py',
    'tests/test_agents/test_analyzer_agent.py',
    'tests/test_agents/test_designer_agent.py',
    'tests/test_agents/test_fidelity_agent.py',
    'tests/test_agents/test_supplement_agent.py',
    'tests/test_agents/test_renderer_agent.py',
    'tests/test_workflow/test_magazine_pipeline.py',
]
for test_file in test_files:
    with open(test_file, 'r', encoding='utf-8') as f:
        compile(f.read(), test_file, 'exec')
print('All test files have correct syntax!')
"
```

## Notes

1. **Fingerprint Method**: Tests now use `document.compute_fingerprint()` instead of accessing `document.fingerprint`
2. **Table Structure**: All table-related tests now use the `data` field (list of lists) instead of `rows` list
3. **Linkage Model**: Linkage tests now use `ContentAssetLink` model with `asset_type` field
4. **Action Structure**: All edit action tests now use the new `type`/`target_selector`/`source_id` pattern
5. **Page Organization**: MagazineEditPlan now uses `pages` structure with SlideEditPlan objects

All changes maintain test functionality while adapting to the new model architecture.