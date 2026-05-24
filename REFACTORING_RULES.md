# V2 重构执行约束规则

> 本文件是 V2 重构期间的**绝对执行法规**。
> 与 CLAUDE.md 具有同等约束力，任何代码变更必须同时遵守两份文件。
> 每条规则都绑定了对应的图谱图号和计划任务编号，可追溯、可验证。

---

## 〇、总则

### 0.1 权威文件层级

在重构期间，以下文件按优先级从高到低执行：

```
1. REFACTORING_RULES.md（本文件）— 重构执行约束
2. CLAUDE.md                          — 项目开发规则（品牌/保真/安全/代码规范）
3. REFACTORING_PLAN.md                — 重构工作计划（任务/时间线/验证标准）
4. ARCHITECTURE_DIAGRAMS.md           — V2 架构图谱（目标架构蓝图）
5. INTEGRATION_GUIDE_V4.md            — 集成指南（接口/模型定义）
```

**冲突处理**：当上述文件内容冲突时，编号小的文件优先。即本文件 > CLAUDE.md > 计划 > 图谱 > 指南。

### 0.2 适用范围

本文件适用于从 V1 到 V2 重构期间的**所有代码变更**，包括：
- 新增模块（Agent、模型、API、前端组件）
- 修改现有模块（重构、增强、修复）
- 配置变更（Docker、CI/CD、环境变量）
- 测试变更（新增、修改、删除）

**重构完成后**，本文件自动降级为参考文档，CLAUDE.md 恢复为唯一权威。

### 0.3 强制读取

每次开始新的对话时，Claude Code **必须按以下顺序读取**：

```
1. CLAUDE.md（确认基础规则未变）
2. 本文件（确认当前重构阶段和约束）
3. REFACTORING_PLAN.md 中「当前阶段」的部分
```

---

## 一、架构锁定规则

> 以下规则定义了 V2 架构的结构边界，不可违反。

### 1.1 八智能体架构 — 不可跳过、不可颠倒

**约束**：V2 流水线必须严格遵循以下执行顺序（对应 ARCHITECTURE_DIAGRAMS.md 图 2）：

```
Planner Agent → Parser Agent → [Gate 1] → Analyzer Agent → [Gate 2]
  → [Fork: Designer Agent ∥ Supplement Agent] → [Join]
  → Renderer Agent → [Gate 3] → Quality Agent → Assembly Agent → [L4]
```

**具体约束**：
- Planner Agent 必须是第一个执行的 Agent，不可跳过
- Parser → Analyzer → Designer 顺序不可颠倒
- Designer 和 Supplement 必须并行执行，不可改为顺序
- Quality Agent 必须在 Renderer 之后、Assembly 之前
- Assembly Agent 必须是最后一个 Agent，负责最终输出
- L4 人工确认必须在所有 Agent 完成后执行

**违反示例（禁止）**：
- 跳过 Planner 直接进入 Parser
- 将 Supplement 放在 Designer 之后顺序执行
- 跳过 Quality Agent 直接输出
- 在 Quality Agent 之前执行 Assembly

### 1.2 三个 Validation Gate — 不可跳过

**约束**：流水线中必须包含 3 个校验门（对应图 2 中的 Gate1/2/3）：

| Gate | 位置 | 校验内容 | 失败动作 |
|------|------|---------|---------|
| Gate 1 | Parser 之后 | 文本提取率 ≥98%，图片全部提取 | 回退 Parser 重新解析 |
| Gate 2 | Analyzer 之后 | 内容分组覆盖所有原始元素 | 回退 Analyzer 重新分析 |
| Gate 3 | Renderer 之后 | 文字可读、图片清晰、布局合理、Logo 合规 | 只修复失败页面 |

**约束**：每个 Gate 校验失败时，必须：
1. 生成详细的失败报告（哪些元素、什么问题）
2. 自动重试（最多 3 次）
3. 重试仍失败则通过 SSE 通知用户
4. 记录到检查点系统

### 1.3 检查点系统 — 5 级快照必须保存

**约束**：流水线必须在以下 5 个位置自动保存检查点（对应图 12）：

```
CP0: 文件上传后（原始文件快照）
CP1: 解析完成后（UnifiedDocument 快照）
CP2: 分析完成后（分析结果 + 内容分组）
CP3: 设计完成后（EditPlan + 素材集）
CP4: 渲染完成后（渲染文件集）
```

**具体约束**：
- 每个检查点必须保存到持久化存储（SQLite），不仅是内存
- 检查点数据必须包含足够的上下文，使回退后可继续执行
- 服务重启后检查点数据必须可恢复
- 任务完成后检查点数据自动清理
- 用户可通过 API `POST /magazine/checkpoint/{task_id}/rollback` 回退到任意检查点

### 1.4 双重质量校验 — 内容保真 + 视觉质量

**约束**：Quality Agent 必须执行两阶段校验（对应图 9）：

**阶段 1：内容保真（L1-L3）**
- L1：指纹完整性 — SHA256 哈希比对，100% 匹配
- L2：图文关联完整性 — 每张原始图片必须有归属
- L3：语义保真 — GLM-5 相似度 ≥ 0.95

**阶段 2：视觉质量（V1-V4）**
- V1：文字可读性 — 无溢出/截断/乱码/遮挡
- V2：图片清晰度 — 无模糊/拉伸/失真
- V3：布局合理性 — 间距/对齐/层级符合杂志标准
- V4：Logo 规范性 — 弘天品牌合规（颜色/位置/大小）

**约束**：
- L1-L3 任一失败 → 回退到 Designer Agent
- V1-V4 任一失败 → 精准修复（只修复失败页面，不重做全部）
- L1-L3 和 V1-V4 是**串联**关系，内容保真通过后才进入视觉质量
- 两阶段校验不可合并、不可跳过

---

## 二、数据模型锁定规则

### 2.1 模型增强字段 — 不可遗漏

**约束**：以下增强字段必须添加到对应模型（对应图 5）：

**TextElement 新增字段**：
```python
original_font: str | None = None      # 原始字体名
original_size: float | None = None    # 原始字号 pt
original_color: str | None = None     # 原始颜色 hex
reading_order: int = 0                # 阅读顺序索引
importance: float = 0.5               # 视觉重要性 0-1
```

**ImageElement 新增字段**：
```python
dpi: int = 0                          # 图片 DPI
quality_score: float = 0.0            # 0-1, GLM-5V 评估
needs_supplement: bool = False        # 是否需要补充
supplement_source: str = "original"   # original/pexels/unsplash/ai_generated
```

**新增模型 PageLayout**：
```python
page_number: int
layout_type: str     # cover/text_image/data_card/two_column/full_text
visual_hierarchy: list[str]
whitespace_ratio: float
dominant_color: str
original_structure: dict
```

**UnifiedDocument 新增字段**：
```python
page_layouts: list[PageLayout] = []
complexity_score: float = 0.0
processing_path: str = "standard"
```

**约束**：
- 所有新字段必须有默认值，确保现有代码不报错
- 新字段的填充由对应 Agent 负责（非一次性全部填充）
- 模型变更后必须更新对应的单元测试

### 2.2 数据传递规则

**约束（继承 CLAUDE.md 4.2 并扩展）**：
- 所有 Agent 之间必须通过 Pydantic 模型传递数据
- 禁止传递 `dict`、`str`、原始 JSON
- 新增的 Planner Agent 输出 `ExecutionPlan` 模型
- 新增的 Quality Agent 输出 `QualityResult` 模型
- 新增的 Assembly Agent 输出 `AssemblyResult` 模型
- 检查点系统的状态快照使用 Pydantic 模型的 `model_dump()` 序列化

---

## 三、执行顺序锁定规则

### 3.1 阶段执行顺序 — 严格按 6 阶段推进

**约束**：重构必须按 REFACTORING_PLAN.md 定义的 6 个阶段**顺序执行**：

```
阶段 1（W1-2）: 架构重构 → 阶段 2（W3-4）: 可靠性 → 阶段 3（W5）: 数据模型
→ 阶段 4（W6-7）: 可观测性 → 阶段 5（W8-9）: 性能 → 阶段 6（W10）: 安全部署
```

**禁止**：
- 跳过阶段 1 直接做性能优化（没有新 Agent 就没有并行基础）
- 在阶段 1 未完成时启动阶段 5（并行渲染依赖 Assembly Agent）
- 在 Quality Agent 未拆分时做性能优化（视觉质量校验会缺失）

### 3.2 阶段完成标准 — 未达标不推进

**约束**：每个阶段必须满足以下标准才能进入下一阶段：

**阶段 1 完成标准**：
- [ ] Planner Agent 可正确评估文档复杂度（误差 < 50%）
- [ ] Quality Agent 拆分为内容保真（L1-L3）+ 视觉质量（V1-V4）
- [ ] Assembly Agent 可正确合并 PDF 和 PPTX
- [ ] 3 个 Validation Gate 可检测并拦截不合格中间结果
- [ ] 检查点系统可在服务重启后恢复
- [ ] 所有现有测试仍然通过

**阶段 2 完成标准**：
- [ ] 每个 Agent 有独立的错误恢复策略
- [ ] Docling 崩溃后自动降级到 PyMuPDF
- [ ] GLM-5 超时后重试 3 次并降级
- [ ] 单页渲染失败不影响其余页面
- [ ] 任务幂等性：重复执行同一阶段只运行一次

**阶段 3 完成标准**：
- [ ] TextElement/ImageElement 新增字段全部填充
- [ ] PageLayout 模型由 PPTX/PDF 解析器正确生成
- [ ] 现有测试不受影响（新字段有默认值）

**阶段 4 完成标准**：
- [ ] 所有 Agent 操作输出 JSON 结构化日志
- [ ] SSE 推送 Agent 思维流和页面预览
- [ ] 前端实时展示进度和思维流
- [ ] 日志中无敏感信息（API Key、文件内容）

**阶段 5 完成标准**：
- [ ] Designer ∥ Supplement 并行执行，比顺序快 30%+
- [ ] 页级并行渲染（4 并发），大文档处理时间降至 T/4
- [ ] 首页预览 < 30 秒推送到前端

**阶段 6 完成标准**：
- [ ] 安全审计检查项全部通过
- [ ] CI/CD 流水线可自动测试+构建+部署
- [ ] 系统可连续运行 7 天无崩溃

### 3.3 单任务约束 — 每次只做一个变更

**约束**：在重构期间，每个代码变更（单次对话或单次提交）必须：
1. 只涉及**一个任务**（来自 REFACTORING_PLAN.md）
2. 不超过 **500 行变更**（超出需拆分）
3. 变更前必须说明对应**哪个阶段、哪个任务**
4. 变更后必须确认**所有现有测试仍通过**

---

## 四、禁止行为清单

> 以下行为在重构期间**绝对禁止**，除非通过本文件的特殊豁免流程。

### 4.1 架构类禁止

| 编号 | 禁止行为 | 原因 | 违反后果 |
|------|---------|------|---------|
| B-01 | 跳过 Planner Agent 直接解析 | 无法评估复杂度、无法选择最优路径 | 产出无执行计划的任务 |
| B-02 | 跳过任意 Validation Gate | 问题积累到最终校验才发现 | 修复成本指数级增长 |
| B-03 | 不保存检查点直接执行下一阶段 | 服务重启后无法恢复 | 所有进度丢失 |
| B-04 | 将 Designer 和 Supplement 改为顺序执行 | 性能退化、Designer 缺少素材信息 | 处理时间增加 30%+ |
| B-05 | 合并内容保真和视觉质量为单次校验 | 无法区分内容丢失 vs 渲染瑕疵 | 修复方向错误 |
| B-06 | 在 Quality Agent 之前执行 Assembly | 未校验的渲染结果直接输出 | 可能输出不合格文件 |
| B-07 | 删除或弱化 L1-L4 中的任何一层 | 保真铁律（CLAUDE.md 三） | 内容丢失或篡改 |

### 4.2 代码类禁止

| 编号 | 禁止行为 | 原因 |
|------|---------|------|
| B-08 | 新增字段不加默认值 | 破坏现有 2,826 行测试 |
| B-09 | 在 Agent 之间传递 dict/str | 违反 CLAUDE.md 4.2 数据模型规则 |
| B-10 | 使用 `print()` 替代 `structlog` | 违反 CLAUDE.md 6.1 日志规则 |
| B-11 | 引入 GPU 依赖或 LangChain | 违反 CLAUDE.md 9.2 禁止依赖 |
| B-12 | 在日志中记录 API Key 或文件内容 | 违反 CLAUDE.md 5.2 安全规则 |
| B-13 | 重写用户文字或调整措辞 | 违反 CLAUDE.md 3.1 保真铁律 |
| B-14 | 使用非弘天 Logo | 违反 CLAUDE.md 2 品牌规则 |

### 4.3 流程类禁止

| 编号 | 禁止行为 | 原因 |
|------|---------|------|
| B-15 | 一次性重写整个模块 | 违反增量重构原则，风险不可控 |
| B-16 | 不运行测试就提交代码 | 可能引入回归 |
| B-17 | 跨阶段执行任务 | 阶段间有依赖关系 |
| B-18 | 修改数据模型不更新对应测试 | 测试覆盖不全 |

---

## 五、验证规则

> 每次代码变更后必须执行的验证步骤。

### 5.1 变更前验证（Pre-check）

在开始任何代码变更之前，Claude Code 必须确认：

```
□ 当前任务属于 REFACTORING_PLAN.md 中的哪个阶段、哪个任务？
□ 该阶段的前置阶段是否已完成？（参见 3.2 完成标准）
□ 是否已读取相关图谱？（参见 ARCHITECTURE_DIAGRAMS.md 对应图号）
□ 变更会影响哪些现有测试？
```

### 5.2 变更后验证（Post-check）

代码变更完成后，Claude Code 必须确认：

```
□ 所有现有测试仍然通过（pytest）
□ 新增代码有对应的单元测试
□ 新增数据模型字段有默认值（不影响现有代码）
□ 类型注解完整（mypy 或手动检查）
□ 无 print() 语句
□ 无硬编码的 API Key 或文件路径
□ 日志中无敏感信息
□ 对应的 REFACTORING_PLAN.md 任务验证标准已满足
```

### 5.3 阶段验收验证（Phase Gate）

每个阶段完成后，必须执行完整的端到端验证：

```
□ 运行全部测试套件（pytest --cov）
□ 上传真实 PPTX 文件，验证完整流水线
□ 上传真实 PDF 文件，验证完整流水线
□ 检查检查点系统是否正常工作
□ 检查 SSE 事件流是否正常推送
□ 检查输出文件中的 Logo 是否正确
□ 运行保真校验，确认 L1-L3 + V1-V4 通过
□ 确认无 console 报错、无异常日志
```

---

## 六、文件路径锁定

> 以下文件路径在重构期间不得更改（可新增内容，不可移动/重命名/删除）。

### 6.1 现有文件 — 不可移动

```
backend/app/agents/parser_agent.py
backend/app/agents/analyzer_agent.py
backend/app/agents/designer_agent.py
backend/app/agents/supplement_agent.py
backend/app/agents/renderer_agent.py
backend/app/agents/fidelity_agent.py
backend/app/parsers/pptx_parser.py
backend/app/parsers/pdf_parser.py
backend/app/parsers/docx_parser.py
backend/app/parsers/xlsx_parser.py
backend/app/parsers/md_parser.py
backend/app/exporters/pdf_renderer.py
backend/app/exporters/ppt_master/svg_to_pptx.py
backend/app/exporters/ppt_master/finalize_svg.py
backend/app/workflow/magazine_pipeline.py
backend/app/models/unified_document.py
backend/app/models/edit_actions.py
backend/app/models/design_spec.py
backend/app/services/llm_client.py
backend/app/services/cost_tracker.py
backend/app/core/config.py
backend/app/core/redis.py
backend/app/core/database.py
backend/app/core/retry.py
backend/app/api/v1/__init__.py
backend/app/main.py
```

### 6.2 新增文件 — 按计划创建

```
阶段 1 新增:
  backend/app/agents/planner_agent.py
  backend/app/agents/assembly_agent.py
  backend/app/agents/quality_agent.py
  backend/app/core/validation_gates.py
  backend/app/core/checkpoint.py
  backend/app/models/execution_plan.py
  backend/app/models/quality.py

阶段 2 新增:
  backend/app/core/recovery.py

阶段 4 新增:
  backend/app/core/metrics.py（可选）

测试文件随业务文件同步创建。
```

---

## 七、回退与修复规则

### 7.1 检查点回退

**约束**：当变更导致系统不可用时，必须通过检查点系统回退：

1. 调用 `POST /magazine/checkpoint/{task_id}/rollback` 回退到最近检查点
2. 从该检查点重新开始执行
3. 记录回退原因到日志

### 7.2 代码回退

**约束**：当变更导致测试失败时：

1. 使用 `git stash` 或 `git checkout` 回退变更
2. 分析失败原因
3. 修复后重新提交
4. **禁止** 使用 `--no-verify` 跳过测试

### 7.3 架构回退

**约束**：当架构变更导致严重问题时：

1. 回退到上一个已验证的提交
2. 在 REFACTORING_PLAN.md 中记录回退原因
3. 重新评估该任务的实现方案
4. 不允许降级架构（如从 8 Agent 退回 5 Agent）

---

## 八、特殊情况处理

### 8.1 紧急修复

当线上出现紧急 bug 时：
1. 在 `fix/` 分支上修复，不走重构流程
2. 修复后必须确认不影响重构进度
3. 记录到 REFACTORING_PLAN.md 的风险日志

### 8.2 需求变更

当用户提出新的需求变更时：
1. 先评估变更是否影响当前重构阶段
2. 如不影响，作为独立任务处理
3. 如影响，更新 REFACTORING_PLAN.md 并重新评估时间线
4. 任何变更不得违反本文件的禁止行为清单

### 8.3 技术限制

当遇到技术限制（如 LangGraph 不支持某功能）时：
1. 记录具体限制和影响范围
2. 寻找替代方案（如用 asyncio.gather 替代 LangGraph parallel）
3. 替代方案必须在架构上等价（功能、可靠性、性能）
4. 在 REFACTORING_PLAN.md 中更新方案并说明原因

---

## 九、版本追踪

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-24 | V1.0 | 初始版本，定义 V2 重构全部约束规则 |
