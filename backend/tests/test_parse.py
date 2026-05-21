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
    from app.services.parser import _parse_pptx, _build_content_asset_linkage
    from app.api.router import ParseTask

    # 使用一个示例 PPTX 文件（如果有）
    test_file = Path("tests/fixtures/sample.pptx")
    if not test_file.exists():
        print("跳过 PPTX 测试: 未找到测试文件 tests/fixtures/sample.pptx")
        return

    assets_dir = Path("tests/output/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    task = ParseTask(task_id="test", status="parsing", progress=0)
    result = await _parse_pptx(test_file, assets_dir, task)

    print(f"解析结果: {len(result['texts'])} 文字, {len(result['images'])} 图片, {len(result['tables'])} 表格")

    # 测试关联
    linkage = _build_content_asset_linkage(result)
    print(f"关联结果: {len(linkage['text_image'])} 文图关联, {len(linkage['low_confidence'])} 低置信度")

    # 保存结果
    output_file = Path("tests/output/parsed_result.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "parsed": result,
            "linkage": linkage,
        }, f, ensure_ascii=False, indent=2)

    print(f"结果已保存到: {output_file}")


async def test_parse_pdf():
    """测试 PDF 解析"""
    from app.services.parser import _parse_pdf
    from app.api.router import ParseTask

    test_file = Path("tests/fixtures/sample.pdf")
    if not test_file.exists():
        print("跳过 PDF 测试: 未找到测试文件 tests/fixtures/sample.pdf")
        return

    assets_dir = Path("tests/output/assets_pdf")
    assets_dir.mkdir(parents=True, exist_ok=True)

    task = ParseTask(task_id="test_pdf", status="parsing", progress=0)
    result = await _parse_pdf(test_file, assets_dir, task)

    print(f"PDF 解析结果: {len(result['texts'])} 文字, {len(result['images'])} 图片")


def test_bbox_distance():
    """测试边界框距离计算"""
    from app.services.parser import _bbox_distance

    # 重叠
    assert _bbox_distance([0, 0, 100, 100], [50, 50, 150, 150]) < 100
    # 远离
    assert _bbox_distance([0, 0, 100, 100], [500, 500, 600, 600]) > 400
    # 同位置
    assert _bbox_distance([0, 0, 100, 100], [0, 0, 100, 100]) < 1

    print("边界框距离计算测试通过")


if __name__ == "__main__":
    print("=== 运行核心流程测试 ===\n")

    test_bbox_distance()
    asyncio.run(test_parse_pptx())
    asyncio.run(test_parse_pdf())

    print("\n=== 测试完成 ===")
