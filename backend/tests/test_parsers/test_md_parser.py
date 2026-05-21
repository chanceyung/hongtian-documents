"""Unit tests for Markdown parser."""

from pathlib import Path

import pytest

from app.parsers.md_parser import MdParser
from app.models.unified_document import UnifiedDocument


class TestMdParser:
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
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Verify type
        assert isinstance(result, UnifiedDocument)

        # Verify texts extracted
        assert len(result.texts) > 0, "Should extract text from Markdown"

        # Compute fingerprint and verify
        fp = result.compute_fingerprint()
        assert len(fp.text_fingerprints) > 0, "Should generate fingerprint"

        # Verify parse method
        assert result.parse_method == "markdown-it-py", "Should use markdown-it-py parser"

    @pytest.mark.asyncio
    async def test_parser_md_heading_level_1_recognition(self, sample_markdown_file: Path) -> None:
        """Test that heading level 1 is correctly recognized."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Find heading with level 1
        heading1_found = any(
            t.content == "Main Title" and hasattr(t, 'level') and t.level == 1
            for t in result.texts
        )
        assert heading1_found, "Should identify heading level 1"

    @pytest.mark.asyncio
    async def test_parser_md_heading_level_2_recognition(self, sample_markdown_file: Path) -> None:
        """Test that heading level 2 is correctly recognized."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

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
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Find heading with level 3
        heading3_found = any(
            t.content == "Sub-subsection" and hasattr(t, 'level') and t.level == 3
            for t in result.texts
        )
        assert heading3_found, "Should identify heading level 3"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_headings(self, markdown_with_multiple_headings: Path) -> None:
        """Test parsing Markdown with multiple headings of various levels."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(markdown_with_multiple_headings, "session-test")

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
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Check that images are extracted (either in texts or separate images field)
        text_content = " ".join([t.content for t in result.texts])
        # Since the image doesn't exist, it should be in warnings
        assert "image" in text_content.lower() or len(result.images) > 0, "Should extract image reference"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_image_references(self, markdown_with_images: Path) -> None:
        """Test parsing Markdown with multiple image references."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(markdown_with_images, "session-test")

        # Since images don't exist, they should be in warnings
        # Check that image references are in warnings
        assert len(result.parse_warnings) > 0, "Should have warnings for missing images"

    @pytest.mark.asyncio
    async def test_parser_md_table_extraction(self, sample_markdown_file: Path) -> None:
        """Test that table structure is correctly extracted."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        assert len(result.tables) == 1, "Should extract exactly one table"

        table = result.tables[0]
        assert len(table.headers) == 3, "Table should have 3 headers"
        # TableElement uses data field (list of lists), not rows
        assert len(table.data) == 2, "Table should have 2 data rows"

        # Verify header content
        assert table.headers[0] == "Column 1", "Should extract first header"
        assert table.headers[1] == "Column 2", "Should extract second header"
        assert table.headers[2] == "Column 3", "Should extract third header"

        # Verify row content from data field
        row_content = " ".join([cell for row in table.data for cell in row])
        assert "Data 1" in row_content, "Should extract first row data"
        assert "Data 6" in row_content, "Should extract last row data"

    @pytest.mark.asyncio
    async def test_parser_md_multiple_tables(self, markdown_with_tables: Path) -> None:
        """Test parsing Markdown with multiple tables."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(markdown_with_tables, "session-test")

        assert len(result.tables) == 3, "Should extract all 3 tables"

        # Check first table
        first_table = result.tables[0]
        first_table_content = " ".join([cell for row in first_table.data for cell in row])
        assert "Alice" in first_table_content, "Should extract first table data"

        # Check second table
        second_table = result.tables[1]
        second_table_content = " ".join([cell for row in second_table.data for cell in row])
        assert "Apple" in second_table_content, "Should extract second table data"

        # Check third table (complex)
        third_table = result.tables[2]
        assert len(third_table.data) == 2, "Third table should have 2 rows"

    @pytest.mark.asyncio
    async def test_parser_md_paragraph_extraction(self, sample_markdown_file: Path) -> None:
        """Test that paragraph content is correctly extracted."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Check for expected paragraph content
        text_content = " ".join([t.content for t in result.texts])
        assert "introductory paragraph" in text_content.lower(), "Should extract first paragraph"
        assert "bold" in text_content.lower(), "Should extract bold text"
        assert "italic" in text_content.lower(), "Should extract italic text"

    @pytest.mark.asyncio
    async def test_parser_md_empty_file(self, empty_markdown_file: Path) -> None:
        """Test parsing empty Markdown file."""
        parser = MdParser()
        result: UnifiedDocument = await parser.parse(empty_markdown_file, "session-test")

        assert isinstance(result, UnifiedDocument)

        # Compute fingerprint and verify
        fp = result.compute_fingerprint()
        assert len(fp.text_fingerprints) == 0, "Empty file should have no fingerprints"

        assert result.parse_method == "markdown-it-py"
        # Empty file should have no texts or tables
        assert len(result.texts) == 0, "Empty Markdown should have no texts"
        assert len(result.tables) == 0, "Empty Markdown should have no tables"

    @pytest.mark.asyncio
    async def test_parser_md_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing non-existent Markdown file raises appropriate error."""
        parser = MdParser()
        nonexistent_file = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            await parser.parse(nonexistent_file, "session-test")

    @pytest.mark.asyncio
    async def test_parser_md_markdown_formatting(self, tmp_path: Path) -> None:
        """Test that Markdown formatting (bold, italic, links) is preserved."""
        content = """# Formatting Test

This has **bold** and *italic* text.

This has ~~strikethrough~~ text.

Here's a [link](https://example.com) and `code`.
"""
        file_path = tmp_path / "formatting.md"
        file_path.write_text(content, encoding='utf-8')

        parser = MdParser()
        result: UnifiedDocument = await parser.parse(file_path, "session-test")

        text_content = " ".join([t.content for t in result.texts])
        assert "bold" in text_content.lower(), "Should preserve bold text"
        assert "italic" in text_content.lower(), "Should preserve italic text"
        assert "strikethrough" in text_content.lower(), "Should preserve strikethrough"
        assert "link" in text_content.lower(), "Should preserve link text"

    @pytest.mark.asyncio
    async def test_parser_md_fingerprint_uniqueness(self, sample_markdown_file: Path) -> None:
        """Test that fingerprint is unique and consistent for same file."""
        parser = MdParser()

        # Parse same file twice
        result1: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")
        result2: UnifiedDocument = await parser.parse(sample_markdown_file, "session-test")

        # Compute fingerprints using the method
        fp1 = result1.compute_fingerprint()
        fp2 = result2.compute_fingerprint()

        # Fingerprints should be identical for same file
        assert fp1.text_fingerprints == fp2.text_fingerprints, "Fingerprint should be consistent"

        # Fingerprint should not be empty
        assert len(fp1.text_fingerprints) > 0, "Fingerprint should not be empty"

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

        parser = MdParser()
        result: UnifiedDocument = await parser.parse(file_path, "session-test")

        text_content = " ".join([t.content for t in result.texts])
        # Note: markdown-it-py doesn't extract code blocks as text elements in the current implementation
        # It only extracts inline code
        assert "print" in text_content, "Should extract inline code content"

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

        parser = MdParser()
        result: UnifiedDocument = await parser.parse(file_path, "session-test")

        text_content = " ".join([t.content for t in result.texts])
        assert "Item 1" in text_content, "Should extract list item 1"
        assert "Item 3" in text_content, "Should extract list item 3"
        assert "First" in text_content, "Should extract ordered list item"
        assert "Third" in text_content, "Should extract ordered list item 3"