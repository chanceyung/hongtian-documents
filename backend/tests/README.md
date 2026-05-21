# 测试套件文档

## 概述

本测试套件为弘天文档 (HongTian Docs) 项目提供全面的测试覆盖，包括智能体测试、工作流测试和 API 测试。

## 目录结构

```
backend/tests/
├── __init__.py
├── conftest.py                 # 共享 fixtures 和配置
├── pytest.ini                  # Pytest 配置文件
├── README.md                   # 本文档
├── test_agents/                # 智能体测试
│   ├── __init__.py
│   ├── test_parser_agent.py
│   ├── test_analyzer_agent.py
│   ├── test_designer_agent.py
│   ├── test_renderer_agent.py
│   ├── test_fidelity_agent.py
│   └── test_supplement_agent.py
├── test_workflow/              # 工作流测试
│   ├── __init__.py
│   └── test_magazine_pipeline.py
└── test_api/                   # API 测试
    ├── __init__.py
    └── test_magazine_api.py
```

## 运行测试

### 运行所有测试

```bash
cd D:/Aisoft/弘天文档/backend
pytest
```

### 运行特定测试文件

```bash
# 运行智能体测试
pytest tests/test_agents/test_parser_agent.py

# 运行工作流测试
pytest tests/test_workflow/test_magazine_pipeline.py

# 运行 API 测试
pytest tests/test_api/test_magazine_api.py
```

### 运行特定测试类

```bash
pytest tests/test_agents/test_parser_agent.py::TestParserAgentParse
```

### 运行特定测试方法

```bash
pytest tests/test_agents/test_parser_agent.py::TestParserAgentParse::test_parse_pptx_routes_to_pptx_parser
```

### 使用标记运行测试

```bash
# 只运行异步测试
pytest -m asyncio

# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行特定智能体的测试
pytest -m parser
pytest -m analyzer
pytest -m designer
pytest -m renderer
pytest -m fidelity
pytest -m supplement
pytest -m workflow
pytest -m api
```

### 查看详细输出

```bash
pytest -v
```

### 显示打印输出

```bash
pytest -s
```

### 生成覆盖率报告

```bash
# 终端报告
pytest --cov=app --cov-report=term-missing

# HTML 报告
pytest --cov=app --cov-report=html

# 组合报告
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### 运行慢测试

```bash
pytest -m slow
```

### 并行运行测试（需要 pytest-xdist）

```bash
pytest -n auto
```

## 测试覆盖范围

### 智能体测试 (test_agents/)

#### test_parser_agent.py
- 解析器路由到正确的解析器（PPTX/PDF/DOCX/XLSX/MD）
- 不支持的格式抛出 ValueError
- 图文关联生成（空间距离 + 结构关键词）
- Bbox 距离计算

#### test_analyzer_agent.py
- 返回正确的分析结构（content_groups, layout_patterns, semantic_links）
- 调用 GLM-5 进行内容聚类
- 长文本截断（8000 字符限制）
- 语义关联跳过已有关联的文字

#### test_designer_agent.py
- 返回 MagazineEditPlan
- 自动追加遗漏文字（验证完整性）
- 编辑动作的 content 字段是原文（不经 LLM）
- 空文档处理

#### test_renderer_agent.py
- 按布局类型加载正确的 SVG 模板
- 文字替换
- 图片 base64 内嵌
- 生成有效的 fallback SVG

#### test_fidelity_agent.py
- 检测遗漏文字
- 满分场景
- 检测关联打破
- 综合得分计算（L1×0.4 + L2×0.3 + L3×0.3）

#### test_supplement_agent.py
- Pexels API 调用
- Unsplash 降级调用
- 调用 GLM-5 提取关键词
- 跳过已存在的图片

### 工作流测试 (test_workflow/)

#### test_magazine_pipeline.py
- 返回可编译的 LangGraph
- 条件路由：fidelity_passed=False + repair_count<2 → "repair"
- 条件路由：fidelity_passed=True → "finalize"
- 检测缺失图片 → "supplement"
- 所有图片存在 → "render"

### API 测试 (test_api/)

#### test_magazine_api.py
- POST /upload：拒绝不支持的格式 → 400
- POST /upload：接受 PPTX → 200 + task_id
- GET /status/{task_id}：返回任务状态
- GET /status/{不存在} → 404
- GET /fidelity/{task_id}：返回保真报告
- GET /export/{task_id}：未完成 → 400

## 测试约定

### 命名规范

- 测试文件：`test_<模块名>.py`
- 测试类：`Test<类名>`
- 测试方法：`test_<功能>_<场景>_<预期结果>`

### 异步测试

所有异步测试必须使用 `@pytest.mark.asyncio` 装饰器：

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mock 使用

- 使用 `unittest.mock.AsyncMock` 模拟异步函数
- 使用 `unittest.mock.MagicMock` 模拟同步对象
- 使用 `unittest.mock.patch` 临时替换依赖

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock 异步函数
mock_async_func = AsyncMock(return_value="result")

# Mock 对象
mock_client = MagicMock()
mock_client.method = AsyncMock(return_value="result")

# 临时替换
with patch('module.Class', return_value=mock_instance):
    result = function_under_test()
```

### Fixtures

共享的 fixtures 定义在 `conftest.py` 中：

- `mock_glm_client`: 模拟 GLM-5 API 客户端
- `mock_redis_client`: 模拟 Redis 客户端
- `mock_httpx_client`: 模拟 HTTPX 客户端
- `temp_directory`: 临时测试目录
- `sample_text_content`: 示例文本内容
- `sample_image_content`: 示例图片内容
- `test_config`: 测试配置

## 依赖安装

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

## 持续集成

在 CI/CD 中运行测试：

```bash
# 完整测试套件
pytest --cov=app --cov-report=xml --junitxml=pytest-report.xml

# 快速测试（跳过慢测试）
pytest -m "not slow"
```

## 最佳实践

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **可读性**: 测试名称应该清晰描述测试内容
3. **可维护性**: 使用 fixtures 共享测试数据
4. **覆盖率**: 目标是 ≥80% 的代码覆盖率
5. **速度**: 避免不必要的等待，使用 mock 替代实际 API 调用
6. **数据安全**: 测试文件不包含真实用户数据

## 故障排除

### 导入错误

如果遇到导入错误，确保在项目根目录运行测试：

```bash
cd D:/Aisoft/弘天文档/backend
pytest
```

### 异步测试失败

确保使用 `@pytest.mark.asyncio` 装饰器：

```python
@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Mock 不生效

确保 mock 路径正确：

```python
# 正确
with patch('app.agents.parser_agent.PPTXParser'):
    pass

# 错误（除非从 agents.parser_agent 导入）
with patch('PPTXParser'):
    pass
```

### Redis 连接错误

测试使用 mock Redis，如果遇到真实连接错误，检查是否正确 mock：

```python
@pytest.fixture
def mock_redis_client():
    client = MagicMock()
    client.set = MagicMock(return_value=True)
    return client
```

## 贡献指南

添加新测试时：

1. 遵循现有测试结构
2. 使用适当的标记（asyncio, unit, integration 等）
3. 确保测试独立运行
4. 添加必要的文档注释
5. 更新本 README 文档

## 联系方式

如有问题，请联系开发团队或提交 Issue。