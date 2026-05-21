# 测试快速开始指南

## 5 分钟快速启动

### 1. 安装依赖

```bash
cd D:/Aisoft/弘天文档/backend
pip install -r tests/requirements-test.txt
```

### 2. 运行所有测试

**Windows:**
```cmd
tests\run_tests.bat
```

**Linux/Mac:**
```bash
./tests/run_tests.sh
```

**或者直接使用 pytest:**
```bash
pytest tests/
```

### 3. 查看覆盖率报告

```bash
pytest tests/ --cov=app --cov-report=html
# 然后打开 htmlcov/index.html
```

## 常用命令

### 运行特定测试

```bash
# 只测试某个智能体
pytest tests/test_agents/test_parser_agent.py

# 只测试某个类
pytest tests/test_agents/test_parser_agent.py::TestParserAgentParse

# 只测试某个方法
pytest tests/test_agents/test_parser_agent.py::TestParserAgentParse::test_parse_pptx_routes_to_pptx_parser
```

### 按类型运行

```bash
# 只运行异步测试
pytest -m asyncio

# 只运行单元测试
pytest -m unit

# 只运行 API 测试
pytest -m api

# 跳过慢速测试
pytest -m "not slow"
```

### 查看详细输出

```bash
pytest -v              # 详细输出
pytest -vv             # 更详细
pytest -s              # 显示 print 输出
pytest --tb=long       # 完整错误信息
```

### 并行运行（更快）

```bash
pytest -n auto         # 自动并行
pytest -n 4            # 使用 4 个进程
```

## 测试结构速览

```
tests/
├── test_agents/       # 6 个智能体测试（88 个测试）
├── test_workflow/     # 工作流测试（13 个测试）
└── test_api/          # API 测试（18 个测试）
```

## 快速故障排除

### 问题：ImportError

```bash
# 确保在正确的目录
cd D:/Aisoft/弘天文档/backend
pytest tests/
```

### 问题：异步测试失败

```bash
# 确保安装了 pytest-asyncio
pip install pytest-asyncio
```

### 问题：Redis 连接错误

测试使用 mock Redis，不应该有真实连接。如果遇到此错误，检查 mock 是否正确配置。

### 问题：GLM-5 API 调用

测试使用 mock GLM-5，不应该有真实 API 调用。如果遇到此错误，检查 mock 是否正确配置。

## 下一步

1. 查看 `README.md` 了解详细文档
2. 查看 `TEST_SUMMARY.md` 了解测试覆盖范围
3. 运行 `pytest --collect-only` 查看所有可用测试
4. 开始编写自己的测试！

## 获取帮助

- 详细文档：`README.md`
- 测试覆盖：`TEST_SUMMARY.md`
- Pytest 文档：https://docs.pytest.org/