# CLAUDE.md — 杂志级文档重构智能体开发规则

> 本文件是 Claude Code 在本项目中必须遵守的绝对规则。
> 每条规则都有存在原因，不得绕过。

---

## 一、项目身份

- **项目名称**: 弘天文档 (HongTian Docs)
- **所属组织**: 弘天 AI (HongTian AI)
- **项目定位**: 杂志级文档重构智能体，将客户文档（PPTX/PDF/Word/Excel/Markdown）转化为杂志品质的 PDF 或 PPTX
- **架构版本**: V4 — 基于 Presenton + PPTAgent + PPT Master 三项目集成

---

## 二、品牌与 Logo 规则

### Logo 文件位置
- `logo/White.png` — 白色 Logo，**仅用于深色背景**
- `logo/Black.png` — 黑色 Logo，**仅用于浅色背景**

### 强制规则
1. **绝不使用其他 Logo** — 所有生成的 PDF、PPTX、网页、报告必须使用上述 Logo
2. **颜色匹配** — 深色背景（`#1a1a2e`, `#0f3460`, `#16213e` 等暗色）用 White.png；浅色背景（`#ffffff`, `#f5f5f5` 等）用 Black.png
3. **Logo 位置** — PDF/PPTX 封面右上角或右下角，页脚右侧，尺寸不超过页面宽度的 8%
4. **HTML 模板** — 在所有 `templates/pdf/*/template.html` 和 `templates/pptx/*/pages/*.svg` 中嵌入 Logo

---

## 三、内容保真 — 不可违反的铁律

### 3.1 编辑动作原则（源自 PPTAgent）
- **只替换，不重写** — 所有内容修改必须通过 `replace_span` / `replace_image` 动作完成
- **禁止**: 改写用户文字、调整措辞、添加原文没有的内容、删除原文中的任何文字
- **允许**: 调整字体大小、颜色、位置、排版布局（视觉层面）
- **允许**: 为缺失图片补充素材（需在保真报告中标记为"补充素材"）

### 3.2 图文关联 — 三重绑定
每张图片必须通过以下至少两种方式与文字建立关联：
1. 空间距离（原图中的位置关系）
2. 结构关键词（标题、说明文字）
3. 语义关联（GLM-5 分析）

### 3.3 保真校验四层流程（必须执行）
- **L1 指纹完整性**: 所有原始文本片段的哈希值必须在校验集中
- **L2 图文关联**: 每张原始图片必须关联到输出中的对应位置
- **L3 语义保真**: GLM-5 对比原文与输出，相似度 ≥ 0.95
- **L4 人工确认**: 前端展示对比报告，用户确认后才算完成

---

## 四、架构约束

### 4.1 五智能体架构（不可更改执行顺序）
```
Parser Agent → Analyzer Agent → Designer Agent → Supplement Agent → Renderer Agent → Fidelity Agent
```
- 顺序不可颠倒，不可跳过任何阶段
- Fidelity Agent 校验不通过时，回退到 Designer Agent 重新设计（最多重试 `MAX_REPAIR_ATTEMPTS` 次）

### 4.2 数据模型 — 必须使用统一模型
所有智能体之间的数据传递必须通过以下模型（定义在 `backend/app/models/`）：
- `UnifiedDocument` — 解析后的统一文档
- `EditAction` / `MagazineEditPlan` — 编辑动作
- `DesignSpec` — 设计规格

**禁止** 在智能体之间传递原始字符串、字典或非结构化数据。

### 4.3 工作流编排 — LangGraph
- 工作流定义在 `backend/app/workflow/magazine_pipeline.py`
- 使用 LangGraph StateGraph，状态类型为 `MagazineState`
- 所有分支逻辑在状态图中定义，不在智能体内部

### 4.4 文件格式路由
每个文件格式有独立的解析器模块，由 `ParserAgent` 统一路由：

| 格式 | 解析器 | 依赖 |
|------|--------|------|
| PPTX | `pptx_parser.py` | python-pptx |
| PDF | `pdf_parser.py` | Docling(主) + PyMuPDF(降级) |
| DOCX | `docx_parser.py` | python-docx |
| XLSX | `xlsx_parser.py` | openpyxl |
| MD | `md_parser.py` | markdown-it-py |

**Docling 必须在子进程中运行**，防止内存泄漏影响主进程。

### 4.5 双轨渲染
- **PDF 输出**: Playwright（视觉页：封面、数据卡片）+ WeasyPrint（文字/表格页）→ PyPDF2 合并
- **PPTX 输出**: PPT Master SVG → DrawingML → PPTX

---

## 五、安全与隐私

### 5.1 数据不出本地
- 原始文件和提取的图片**永不离开本地服务器**
- 发送给 GLM-5 API 的**只有脱敏后的纯文本摘要**，不含文件名、路径、用户信息
- API Key **不持久化**，Redis 中加密存储，24 小时自动过期

### 5.2 禁止的行为
- 禁止将用户文件上传到任何第三方服务（除 GLM-5 API 文本调用外）
- 禁止在日志中记录完整的用户文件内容
- 禁止将 API Key 写入文件系统（除 Redis 临时存储外）

---

## 六、代码规范

### 6.1 Python 后端
- **Python 版本**: ≥ 3.11
- **类型注解**: 所有函数必须有完整的类型注解
- **Pydantic V2**: 所有数据模型使用 Pydantic V2（`model_validate` 而非 `parse_obj`）
- **异步优先**: 所有 I/O 操作必须使用 `async/await`（httpx 而非 requests）
- **错误处理**: 使用自定义异常层级（`app/exceptions.py`），不抛裸 Exception
- **日志**: 使用 `structlog` 或标准 `logging`，不使用 `print()`
- **导入顺序**: stdlib → 第三方 → 本项目，每组之间空一行

### 6.2 TypeScript 前端
- **TypeScript 严格模式**: `strict: true`
- **状态管理**: Zustand，状态定义在 `src/lib/store.ts`
- **API 调用**: 统一通过 `src/lib/api.ts`，不直接使用 fetch/axios
- **组件**: 函数组件 + Hooks，不使用 class component

### 6.3 通用规则
- **不写注释说明 "what"** — 代码本身应足够清晰
- **只在 "why" 不明显时写注释** — 如隐藏约束、历史原因、性能权衡
- **不创建不必要的抽象** — 三行相似代码优于一个过早抽象
- **不添加未被要求的功能** — YAGNI 原则
- **提交信息**: 中文，格式 `类型: 简要描述`（如 `feat: 添加 PDF 解析器`）

---

## 七、测试要求

### 7.1 单元测试
- 每个智能体必须有对应的单元测试
- 每个解析器必须有针对真实文件格式的测试
- 保真校验必须有端到端测试

### 7.2 测试命名
```python
def test_<功能>_<场景>_<预期结果>():
    # 例如: test_parser_pptx_with_images_returns_unified_document
```

### 7.3 测试文件不放真实用户数据
- 测试用 PPTX/PDF/DOCX 必须是人工构造的样本
- 测试中的 API Key 使用 mock

---

## 八、模板系统

### 8.1 PDF 模板（HTML + CSS）
- 位于 `backend/app/templates/pdf/<模板名>/`
- 必须包含: `template.html`, `styles.css`, `config.json`
- Logo 必须通过 `<img>` 标签嵌入，根据背景色选择 White/Black 版本

### 8.2 PPTX 模板（SVG）
- 位于 `backend/app/templates/pptx/<模板名>/`
- SVG 必须遵守 PPT Master 约束:
  - **禁止** mask、@font-face、CSS class
  - **必须** 使用 inline style
  - **必须** 包含 viewBox 属性
  - 文字使用 `<text>` 元素，图片使用 `<image>` 元素
- 占位符使用 `data-placeholder` 属性标记

---

## 九、依赖管理

### 9.1 新增依赖必须满足
- 有明确的维护状态（近 6 个月内有更新）
- 不引入已知的 CVE 漏洞
- 不与现有依赖冲突
- 必须添加到 `requirements-v4.txt` 并注明用途

### 9.2 禁止的依赖
- 禁止引入需要 GPU 的依赖
- 禁止引入 Dify 相关依赖
- 禁止引入 LangChain（使用 LangGraph 即可）

---

## 十、Git 工作流

### 10.1 分支策略
- `main` — 生产分支，只接受 PR 合入
- `dev` — 开发分支，日常开发在此
- `feat/<功能名>` — 功能分支，从 dev 创建
- `fix/<问题描述>` — 修复分支，从 dev 或 main 创建

### 10.2 提交信息格式
```
类型(范围): 简要描述

类型: feat | fix | refactor | docs | test | chore | style
范围: parser | analyzer | designer | renderer | fidelity | supplement | api | ui | infra
```

### 10.3 PR 要求
- 必须关联 Issue 或任务描述
- 必须通过所有 CI 检查
- 至少一人 Code Review
- 不超过 500 行变更（超出需拆分）

---

## 十一、关键文件索引

| 文件 | 用途 |
|------|------|
| `INTEGRATION_GUIDE_V4.md` | 集成指南 — 架构、接口、数据模型定义 |
| `IMPLEMENTATION_COMPLETE.md` | 完整实现代码 — 所有模块可直接使用 |
| `ARCHITECTURE_V4_OPENSOURCE.md` | 开源选型论证 |
| `PROJECT_STRUCTURE.md` | 文件结构与流程说明 |
| `docker-compose-v4.yml` | V4 Docker 部署配置 |
| `backend/requirements-v4.txt` | Python 依赖清单 |
| `.env.example` | 环境变量模板 |

---

## 十二、开发前必读

在开始任何开发工作之前，必须阅读以下文件（按顺序）：

1. **本文件 (CLAUDE.md)** — 开发规则
2. **PROJECT_STRUCTURE.md** — 理解项目结构
3. **INTEGRATION_GUIDE_V4.md** — 理解架构和数据模型
4. **IMPLEMENTATION_COMPLETE.md** — 查看已有实现代码

每次开始新的对话时，Claude Code 应主动读取本文件确认规则。
