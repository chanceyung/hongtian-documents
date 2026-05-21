"""Unit tests for Markdown parser."""

from pathlib import Path

import pytest

from app.parsers.md_parser import MDParser
from app.models.unified_document import UnifiedDocument


class TestMDParser:
    """Test suite for Markdown parser."""

    @pytest.fixture
    def sample_markdown_file(self, tmp_path: Path) -> Path:
        """Create a sample Markdown file with headings, paragraphs, images, and tables."""
        content = """# Main Title

This is an introductory paragraph with some **bold** and *italic* text.

## Subsection 1

Content for subsection 1. Here's an image:

![Sample Image](path/to/image.png)

### Sub-subsection

More content here.

## Subsection 2

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

Another paragraph after the table.

[Link to somewhere](https://example.com)
"""
        file_path = tmp_path / "sample.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.fixture
    def empty_markdown_file(self, tmp_path: Path) -> Path:
        """Create an empty Markdown file."""
        file_path = tmp_path / "empty.md"
        file_path.write_text("", encoding='utf-8')
        return file_path

    @pytest.fixture
    def markdown_with_multiple_headings(self, tmp_path: Path) -> Path:
        """Create Markdown file with multiple headings of various levels."""
        content = """# H1 Heading

Content under H1.

## H2 Heading A

Content under H2 A.

### H3 Heading A

Content under H3 A.

## H2 Heading B

Content under H2 B.

### H3 Heading B

Content under H3 B.

#### H4 Heading

Content under H4.
"""
        file_path = tmp_path / "headings.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.fixture
    def markdown_with_images(self, tmp_path: Path) -> Path:
        """Create Markdown file with various image references."""
        content = """# Document with Images

First image:

![Image 1](images/figure1.png "Figure 1 Caption")

Second image with different syntax:

<img src="images/figure2.jpg" alt="Image 2" title="Figure 2 Caption">

Third image:

![Image 3](./diagrams/schema.svg)
"""
        file_path = tmp_path / "images.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.fixture
    def markdown_with_tables(self, tmp_path: Path) -> Path:
        """Create Markdown file with multiple tables."""
        content = """# Document with Tables

First table:

| Name | Age | City |
|------|-----|------|
| Alice | 28 | NY |
| Bob | 32 | LA |

Text between tables.

Second table:

| Product | Price | Stock |
|---------|-------|-------|
| Apple | 1.5 | 100 |
| Banana | 0.8 | 200 |
| Orange | 1.2 | 150 |

Complex table:

| ID | Name | Description |
|----|------|-------------|
| 001 | Item A | Description with **bold** text |
| 002 | Item B | Description with *italic* text |
"""
        file_path = tmp_path / "tables.md"
        file_path.write_text(content, encoding='utf-8')
        return file_path

    @pytest.mark.asyncio
    async def test_parser_md_with_various_content_returns_unified_document(
        self,
        sample_markdown_file: Path
    ) -> None:
        """Test parsing Markdown with headings, paragraphs, images, tables returns UnifiedDocument."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Verify type
        assert isinstance(result, UnifiedDocument)

        # Verify texts extracted
        assert len(result.texts) > 0, "Should extract text from Markdown"

        # Verify fingerprint generated
        assert result.fingerprint != "", "Should generate fingerprint"

        # Verify parse method
        assert result.parse_method == "markdown-it", "Should use markdown-it parser"

    @pytest.mark.asyncio
    async def test_parser_md_heading_level_1_recognition(self, sample_markdown_file: Path) -> None:
        """Test that heading level 1 is correctly recognized."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Find heading with level 1
        heading1_found = any(
            t.content == "Main Title" and hasattr(t, 'level') and t.level == 1
            for t in result.texts
        )
        assert heading1_found, "Should identify heading level 1"

    @pytest.mark.asyncio
    async def test_parser_md_heading_level_2_recognition(self, sample_markdown_file: Path) -> None:
        """Test that heading level 2 is correctly recognized."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Find headings with level 2
        level2_headings = [
            t.content for t in result.texts
            if hasattr(t, 'level') and t.level == 2
        ]
        assert len(level2_headings) >= 2, "Should identify at least 2 headings at level 2"
        assert "Subsection 1" in level2_headings, "Should identify 'Subsection 1'"
        assert "Subsection 2" in level2_headings, "Should identify 'Subsection 2'"

    @pytest.mark.asyncio
    async def test_parser_md_heading_level_3_recognition(self, sample_markdown_file: Path) -> None:
        """Test that heading level 3 is correctly recognized."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Find heading with level 3
        heading3_found = any(
            t.content == "Sub-subsection" and hasattr(t, 'level') and t.level == 3
            for t in result.texts
        )
        assert heading3_found, "Should identify heading level 3"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_headings(self, markdown_with_multiple_headings: Path) -> None:
        """Test parsing Markdown with multiple headings of various levels."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(markdown_with_multiple_headings)

        # Count headings by level
        level1_headings = [t for t in result.texts if hasattr(t, 'level') and t.level == 1]
        level2_headings = [t for t in result.texts if hasattr(t, 'level') and t.level == 2]
        level3_headings = [t for t in result.texts if hasattr(t, 'level') and t.level == 3]
        level4_headings = [t for t in result.texts if hasattr(t, 'level') and t.level == 4]

        assert len(level1_headings) == 1, "Should identify 1 level 1 heading"
        assert len(level2_headings) == 2, "Should identify 2 level 2 headings"
        assert len(level3_headings) == 2, "Should identify 2 level 3 headings"
        assert len(level4_headings) == 1, "Should identify 1 level 4 heading"

    @pytest.mark.asyncio
    async def test_parser_md_image_reference_extraction(self, sample_markdown_file: Path) -> None:
        """Test that image references are extracted."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Check that images are extracted (either in texts or separate images field)
        text_content = " ".join([t.content for t in result.texts])
        assert "image" in text_content.lower() or len(result.images) > 0, "Should extract image reference"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_image_references(self, markdown_with_images: Path) -> None:
        """Test parsing Markdown with multiple image references."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(markdown_with_images)

        # Should extract multiple images
        assert len(result.images) > 0, "Should extract images"

        # Check that image paths are captured
        image_paths = [img.src for img in result.images if hasattr(img, 'src')]
        assert any("figure1.png" in path for path in image_paths), "Should capture first image path"
        assert any("figure2.jpg" in path for path in image_paths), "Should capture second image path"
        assert any("schema.svg" in path for path in image_paths), "Should capture third image path"

    @pytest.mark.asyncio
    async def test_parser_md_table_extraction(self, sample_markdown_file: Path) -> None:
        """Test that table structure is correctly extracted."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        assert len(result.tables) == 1, "Should extract exactly one table"

        table = result.tables[0]
        assert len(table.headers) == 3, "Table should have 3 headers"
        assert len(table.rows) == 2, "Table should have 2 data rows"

        # Verify header content
        header_texts = [h.content for h in table.headers]
        assert "Column 1" in header_texts, "Should extract first header"
        assert "Column 2" in header_texts, "Should extract second header"
        assert "Column 3" in header_texts, "Should extract third header"

        # Verify row content
        row_content = " ".join([cell.content for row in table.rows for cell in row.cells])
        assert "Data 1" in row_content, "Should extract first row data"
        assert "Data 6" in row_content, "Should extract last row data"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_tables(self, markdown_with_tables: Path) -> None:
        """Test parsing Markdown with multiple tables."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(markdown_with_tables)

        assert len(result.tables) == 3, "Should extract all 3 tables"

        # Check first table
        first_table = result.tables[0]
        first_table_content = " ".join([cell.content for row in first_table.rows for cell in row.cells])
        assert "Alice" in first_table_content, "Should extract first table data"

        # Check second table
        second_table = result.tables[1]
        second_table_content = " ".join([cell.content for row in second_table.rows for cell in row.cells])
        assert "Apple" in second_table_content, "Should extract second table data"

        # Check third table (complex)
        third_table = result.tables[2]
        assert len(third_table.rows) == 2, "Third table should have 2 rows"

    @pytest.mark.asyncio
    async def test_parser_md_paragraph_extraction(self, sample_markdown_file: Path) -> None:
        """Test that paragraph content is correctly extracted."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Check for expected paragraph content
        text_content = " ".join([t.content for t in result.texts])
        assert "introductory paragraph" in text_content.lower(), "Should extract first paragraph"
        assert "bold" in text_content.lower(), "Should extract bold text"
        assert "italic" in text_content.lower(), "Should extract italic text"

    @pytest.mark.asyncio
    async def test_parser_md_empty_file(self, empty_markdown_file: Path) -> None:
        """Test parsing empty Markdown file."""
        parser = MDParser()
        result: UnifiedDocument = await parser.parse(empty_markdown_file)

        assert isinstance(result, UnifiedDocument)
        assert result.fingerprint != "", "Should still generate fingerprint for empty file"
        assert result.parse_method == "markdown-it"
        # Empty file should have no texts or tables
        assert len(result.texts) == 0, "Empty Markdown should have no texts"
        assert len(result.tables) == 0, "Empty Markdown should have no tables"

    @pytest.mark.asyncio
    async def test_parser_md_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing non-existent Markdown file raises appropriate error."""
        parser = MDParser()
        nonexistent_file = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            await parser.parse(nonexistent_file)

    @pytest.mark.asyncio
    async def test_parser_md_markdown_formatting(self, tmp_path: Path) -> Path:
        """Test that Markdown formatting (bold, italic, links) is preserved."""
        content = """# Formatting Test

This has **bold** and *italic* text.

This has ~~strikethrough~~ text.

Here's a [link](https://example.com) and `code`.
"""
        file_path = tmp_path / "formatting.md"
        file_path.write_text(content, encoding='utf-8')

        parser = MDParser()
        result: UnifiedDocument = await parser.parse(file_path)

        text_content = " ".join([t.content for t in result.texts])
        assert "bold" in text_content.lower(), "Should preserve bold text"
        assert "italic" in text_content.lower(), "Should preserve italic text"
        assert "strikethrough" in text_content.lower(), "Should preserve strikethrough"
        assert "link" in text_content.lower(), "Should preserve link text"

        return file_path

    @pytest.mark.asyncio
    async def test_parser_md_fingerprint_uniqueness(self, sample_markdown_file: Path) -> None:
        """Test that fingerprint is unique and consistent for same file."""
        parser = MDParser()

        # Parse same file twice
        result1: UnifiedDocument = await parser.parse(sample_markdown_file)
        result2: UnifiedDocument = await parser.parse(sample_markdown_file)

        # Fingerprints should be identical for same file
        assert result1.fingerprint == result2.fingerprint, "Fingerprint should be consistent"

        # Fingerprint should not be empty
        assert len(result1.fingerprint) > 0, "Fingerprint should not be empty"

    @pytest.mark.asyncio
    async def test_parser_md_code_blocks(self, tmp_path: Path) -> None:
        """Test parsing Markdown with code blocks."""
        content = """# Code Examples

Inline code: `print("Hello")`

```python
def hello():
    print("World")
```

```bash
echo "Shell command"
```
"""
        file_path = tmp_path / "code.md"
        file_path.write_text(content, encoding='utf-8')

        parser = MDParser()
        result: UnifiedDocument = await parser.parse(file_path)

        text_content = " ".join([t.content for t in result.texts])
        assert "print" in text_content, "Should extract code content"
        assert "def hello" in text_content, "Should extract function definition"

    @pytest.mark.asyncio
    async def test_parser_md_list_items(self, tmp_path: Path) -> None:
        """Test parsing Markdown with lists."""
        content = """# Lists

Unordered list:
- Item 1
- Item 2
- Item 3

Ordered list:
1. First
2. Second
3. Third
"""
        file_path = tmp_path / "lists.md"
        file_path.write_text(content, encoding='utf-8')

        parser = MDParser()
        result: UnifiedDocument = await parser.parse(file_path)

        text_content = " ".join([t.content for t in result.texts])
        assert "Item 1" in text_content, "Should extract list item 1"
        assert "Item 3" in text_content, "Should extract list item 3"
        assert "First" in text_content, "Should extract ordered list item"
        assert "Third" in text_content, "Should extract ordered list item 3"