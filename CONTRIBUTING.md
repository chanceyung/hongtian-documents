# 贡献指南 — 弘天文档

感谢你对弘天文档项目的关注！本指南帮助你规范地参与项目开发。

---

## 一、开发环境搭建

### 必要工具
- Python ≥ 3.11
- Node.js ≥ 18
- Docker + Docker Compose
- Git

### 搭建步骤

```bash
# 1. Fork 并克隆
git clone <your-fork-url>
cd 弘天文档

# 2. 创建开发分支
git checkout -b feat/your-feature

# 3. 后端环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-v4.txt
playwright install chromium

# 4. 前端环境
cd ../frontend
npm install

# 5. 配置环境变量
cp ../.env.example ../.env
# 编辑 .env 填入必要的 API Key
```

---

## 二、必读文档

在提交任何代码之前，**必须阅读**以下文件：

1. **[CLAUDE.md](CLAUDE.md)** — 项目的绝对开发规则
2. **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** — 项目结构和核心流程
3. **[INTEGRATION_GUIDE_V4.md](INTEGRATION_GUIDE_V4.md)** — 架构设计和数据模型

不理解规则就写代码 = 浪费所有人的时间。

---

## 三、分支策略

```
main          ← 生产分支，只接受 PR
  │
  └── dev     ← 开发主分支，日常合并目标
       │
       ├── feat/parser-refactor    ← 功能分支
       ├── feat/pdf-template       ← 功能分支
       ├── fix/image-linkage       ← 修复分支
       └── docs/api-reference      ← 文档分支
```

### 命名规则

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能 | `feat/xlsx-parser` |
| `fix/` | Bug 修复 | `fix/image-linkage-broken` |
| `refactor/` | 重构 | `refactor/parser-routing` |
| `docs/` | 文档 | `docs/api-reference` |
| `test/` | 测试 | `test/parser-integration` |
| `chore/` | 构建/工具 | `chore/update-deps` |

### 规则
- 所有功能分支从 `dev` 创建
- 完成后向 `dev` 提交 PR
- 禁止直接推送到 `main`
- 分支名使用英文小写 + 短横线

---

## 四、提交信息规范

### 格式
```
类型(范围): 简要描述

[可选] 详细说明

[可选] 关联: #issue-number
```

### 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(parser): 添加 XLSX 解析器` |
| `fix` | Bug 修复 | `fix(fidelity): 修复 L2 图文关联误判` |
| `refactor` | 重构 | `refactor(renderer): 抽取渲染路由逻辑` |
| `docs` | 文档 | `docs: 更新 API 接口说明` |
| `test` | 测试 | `test(parser): 添加 PDF 解析器测试` |
| `chore` | 构建/工具 | `chore: 升级 langgraph 到 0.2` |
| `style` | 格式 | `style: 统一 import 排序` |

### 范围（Scope）

| 范围 | 对应模块 |
|------|----------|
| `parser` | 文档解析 |
| `analyzer` | 内容分析 |
| `designer` | 排版设计 |
| `renderer` | 渲染生成 |
| `fidelity` | 保真校验 |
| `supplement` | 素材补充 |
| `api` | API 接口 |
| `ui` | 前端界面 |
| `infra` | 基础设施 |
| `workflow` | LangGraph 工作流 |

### 规则
- 描述使用中文
- 描述不超过 50 字符
- 不以句号结尾
- 一个提交只做一件事

---

## 五、代码规范

### 5.1 Python

```python
# ✅ 正确 — 完整类型注解，async，Pydantic V2
async def parse_document(file: UploadFile, fmt: str) -> UnifiedDocument:
    parser = get_parser(fmt)
    return await parser.parse(file)

# ❌ 错误 — 无类型注解，同步 I/O
def parse_document(file, fmt):
    parser = get_parser(fmt)
    return parser.parse(file)
```

#### 必须遵守
- 所有函数有完整类型注解
- I/O 操作使用 async/await
- Pydantic V2 语法（`model_validate` 而非 `parse_obj`）
- 导入顺序: stdlib → 第三方 → 本项目
- 不使用 `print()`，使用 `logging`
- 不抛裸 `Exception`，使用自定义异常

#### 禁止
- 禁止使用 `requests` 库（使用 `httpx`）
- 禁止在业务逻辑中使用 `Any` 类型
- 禁止硬编码配置值（使用 `settings`）
- 禁止忽略 lint 警告（`# noqa` 需注释原因）

### 5.2 TypeScript

```typescript
// ✅ 正确 — 严格类型，通过 api.ts 调用
const result: MagazineResponse = await api.generateMagazine(params);

// ❌ 错误 — 无类型，直接 fetch
const result = await fetch('/api/v1/magazine/generate', { ... });
```

#### 必须遵守
- `strict: true`
- 函数组件 + Hooks
- 状态管理通过 Zustand（`store.ts`）
- API 调用通过 `api.ts`

### 5.3 安全红线

以下行为**零容忍**，违反即打回：

- 将用户文件内容上传到非 GLM-5 的第三方服务
- 在日志中记录完整文件内容或 API Key
- 在代码中硬编码密钥、Token
- 跳过保真校验直接输出
- 改写用户原始文字内容

---

## 六、PR 流程

### 提交 PR 前的检查清单

- [ ] 已阅读 CLAUDE.md 中的相关规则
- [ ] 所有新增代码有类型注解
- [ ] 所有 I/O 操作使用 async
- [ ] 新增依赖已加入 requirements-v4.txt 并注明用途
- [ ] 通过所有现有测试
- [ ] 新功能有对应的单元测试
- [ ] 不包含真实用户数据或 API Key
- [ ] PR 变更不超过 500 行（超出需拆分）

### PR 模板

```markdown
## 变更类型
- [ ] feat (新功能)
- [ ] fix (修复)
- [ ] refactor (重构)
- [ ] docs (文档)
- [ ] test (测试)
- [ ] chore (工具)

## 变更说明
简要描述做了什么、为什么做。

## 影响范围
列出受影响的模块和文件。

## 测试
- [ ] 单元测试通过
- [ ] 手动测试通过

## 关联
关联的 Issue 或任务编号。
```

### Code Review 标准

1. **正确性**: 逻辑是否正确，边界情况是否处理
2. **保真性**: 是否遵守"只替换不重写"原则
3. **安全性**: 是否有数据泄露风险
4. **性能**: 是否有不必要的同步阻塞或内存泄漏
5. **可维护性**: 命名是否清晰，抽象是否合理

---

## 七、测试规范

### 测试结构

```
backend/app/tests/
├── test_parser/          # 解析器测试
│   ├── test_pptx_parser.py
│   ├── test_pdf_parser.py
│   └── fixtures/         # 测试样本文件
├── test_agents/          # 智能体测试
├── test_fidelity/        # 保真校验测试
└── test_api/             # API 端点测试
```

### 测试命名
```python
def test_<功能>_<场景>_<预期结果>():
    # 例:
    def test_parser_pptx_with_images_returns_unified_document():
    def test_fidelity_l1_missing_text_fails_validation():
```

### 测试要求
- 测试文件不放真实用户数据
- 外部 API 调用必须 mock
- 每个智能体至少一个单元测试
- 每个解析器至少一个真实文件格式测试
- 保真校验必须有端到端测试

---

## 八、问题反馈

### Bug 报告模板

```markdown
**环境**: Docker / 本地开发
**版本**: V4 / commit hash
**复现步骤**:
1. ...
2. ...
**预期行为**:
**实际行为**:
**相关日志**:
```

### 功能建议模板

```markdown
**需求描述**: 
**应用场景**: 
**期望方案**: 
**替代方案**: 
```

---

## 九、Logo 使用规范

项目使用弘天 AI 品牌 Logo，具体规则：

| 场景 | 使用文件 | 背景色 |
|------|----------|--------|
| PDF/PPTX 封面（深色） | `logo/White.png` | `#1a1a2e` 等暗色 |
| PDF/PPTX 封面（浅色） | `logo/Black.png` | `#ffffff` 等亮色 |
| 网页页头/页脚 | 根据背景色选择 | — |
| README.md 顶部 | `logo/Black.png` | 白色背景 |
| README.md 底部 | `logo/White.png` | 深色背景 |

- Logo 尺寸不超过所在页面/容器宽度的 8%
- Logo 不做颜色修改、拉伸变形
- 不使用其他品牌 Logo

---

感谢你的贡献！
