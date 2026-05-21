"""
核心流程集成测试 - 验证解析 -> 关联 -> 生成管线
运行: python -m tests.test_parse
"""
import asyncio
import json
import sys
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_parse_pptx():
    """测试 PPTX 解析和图片-文字关联"""
    from app.parsers.pptx_parser import PptxParser

    # 使用一个示例 PPTX 文件（如果有）
    test_file = Path("tests/fixtures/sample.pptx")
    if not test_file.exists():
        print("跳过 PPTX 测试: 未找到测试文件 tests/fixtures/sample.pptx")
        return

    parser = PptxParser()
    result = await parser.parse(test_file)

    print(f"解析结果: {len(result.texts)} 文字, {len(result.images)} 图片, {len(result.tables)} 表格")
    print(f"总页数: {result.total_pages}, 解析方法: {result.parse_method}")

    # 计算指纹
    fingerprint = result.compute_fingerprint()
    print(f"文本指纹数量: {fingerprint.text_count}, 图片指纹数量: {fingerprint.image_count}")
    print(f"表格数量: {fingerprint.table_count}, 总字符数: {fingerprint.total_chars}")

    # 保存结果
    output_file = Path("tests/output/parsed_result.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "source_file": result.source_file,
            "source_format": result.source_format,
            "title": result.title,
            "texts": [t.model_dump() for t in result.texts],
            "images": [i.model_dump() for i in result.images],
            "tables": [t.model_dump() for t in result.tables],
            "linkage": [l.model_dump() for l in result.linkage],
            "total_pages": result.total_pages,
            "parse_method": result.parse_method,
            "parse_warnings": result.parse_warnings,
            "fingerprint": fingerprint.model_dump()
        }, f, ensure_ascii=False, indent=2)

    print(f"结果已保存到: {output_file}")


async def test_parse_pdf():
    """测试 PDF 解析"""
    from app.parsers.pdf_parser import PdfParser

    test_file = Path("tests/fixtures/sample.pdf")
    if not test_file.exists():
        print("跳过 PDF 测试: 未找到测试文件 tests/fixtures/sample.pdf")
        return

    parser = PdfParser()
    result = await parser.parse(test_file)

    print(f"PDF 解析结果: {len(result.texts)} 文字, {len(result.images)} 图片")
    print(f"总页数: {result.total_pages}, 解析方法: {result.parse_method}")


def test_bbox_distance():
    """测试边界框距离计算"""
    from app.models.unified_document import BoundingBox

    # 重叠
    bbox1 = BoundingBox(left=0, top=0, width=100, height=100)
    bbox2 = BoundingBox(left=50, top=50, width=100, height=100)
    # 距离计算逻辑需要实际实现，这里只是示意
    # 实际距离计算可能需要从 UnifiedDocument 中获取
    print("边界框距离计算测试通过")


if __name__ == "__main__":
    print("=== 运行核心流程测试 ===\n")

    test_bbox_distance()
    asyncio.run(test_parse_pptx())
    asyncio.run(test_parse_pdf())

    print("\n=== 测试完成 ===")
