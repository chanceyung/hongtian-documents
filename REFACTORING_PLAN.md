# 弘天文档 V2 重构工作计划

> 从 V1 原型到 V2 生产级任务落地架构
> 基于「多Agent系统生产化 6 阶段方法论」+ V2 架构图谱

---

## 〇、现状盘点：已实现 vs 待建设

### 已实现（8,577 行业务代码 + 2,826 行测试）

| 模块 | 文件 | 行数 | 状态 |
|------|------|------|------|
| 5 个 Agent | `agents/*.py` | 952 | ✅ 全部实现，功能完整 |
| 5 个 Parser | `parsers/*.py` | 857 | ✅ 全部实现，含 Docling 子进程 |
| 2 个渲染引擎 | `exporters/*.py` | 727 | ✅ PDF + PPTX 双轨 |
| LangGraph 流水线 | `workflow/magazine_pipeline.py` | 287 | ✅ 顺序流水线 + 修复循环 |
| 数据模型 | `models/*.py` | 157 | ✅ UnifiedDocument + EditPlan + DesignSpec |
| LLM 客户端 | `services/llm_client.py` | 151 | ✅ 异步 + 重试 + 成本追踪 |
| 配置/Redis/KV | `core/*.py` | 715 | ✅ 桌面/服务器双模式 |
| SSE 事件流 | `api/v1/__init__.py` | 413 | ✅ 实时状态推送 |
| 模板系统 | `templates/` | 24 文件 | ✅ 3 风格 × 2 格式 |
| 前端 | `app/src/` | 完整 | ✅ Chat + AgentPanel + Settings |
| 桌面端 | `desktop/src/` | 完整 | ✅ Electron 双后端管理 |
| 测试 | `tests/` | 2,826 | ✅ Agent + API 测试覆盖 |

### 待建设（V2 架构新增需求）

| 模块 | 对应图谱 | 优先级 | 工作量估算 |
|------|---------|--------|-----------|
| **Planner Agent** | 图 4 | P0 高 | 3 天 |
| **Assembly Agent** | 图 2 | P0 高 | 2 天 |
| **Quality Agent（拆分 Fidelity）** | 图 9 | P0 高 | 3 天 |
| **3 个 Validation Gate** | 图 2 | P0 高 | 4 天 |
| **检查点系统** | 图 12 | P0 高 | 5 天 |
| **Designer ∥ Supplement 并行** | 图 2 | P1 中 | 3 天 |
| **页级并行渲染** | 图 7 | P1 中 | 5 天 |
| **数据模型增强** | 图 5 | P1 中 | 3 天 |
| **PPTX 版式/母版提取** | 图 8 | P1 中 | 3 天 |
| **WebSocket 双向通道** | 图 11 | P1 中 | 4 天 |
| **前端进度仪表盘重构** | 图 3,11 | P1 中 | 5 天 |
| **错误恢复策略库** | 图 12 | P2 低 | 4 天 |
| **Prometheus 指标** | 图 6 | P2 低 | 3 天 |
| **分布式追踪** | 图 6 | P2 低 | 3 天 |
| **负载测试** | - | P2 低 | 3 天 |
| **CI/CD 完善** | - | P2 低 | 2 天 |

---

## 一、阶段 1：架构重构与模块加固（1-2 周）

> 目标：新增 3 个 Agent + 3 个 Validation Gate + 检查点系统

### 任务 1.1：新增 Planner Agent

**文件**：`backend/app/agents/planner_agent.py`（新建）

**实现内容**：
```python
class PlannerAgent:
    """任务规划智能体：评估复杂度，选择执行路径"""

    async def plan(self, file_path: Path) -> ExecutionPlan:
        # 1. 快速扫描（元数据 + 前 3 页样本）
        scan = await self._quick_scan(file_path)
        # 2. 复杂度评分（0-100）
        score = self._complexity_score(scan)
        # 3. 选择路径：fast(≤30) / standard(31-70) / deep(>70)
        path = self._select_path(score)
        # 4. 生成执行计划（耗时估算、API 成本、检查点列表）
        plan = self._generate_plan(scan, path)
        return plan
```

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 在 parser_node 前增加 planner_node
- `backend/app/models/` — 新增 `ExecutionPlan` 模型（path、estimated_time、cost、checkpoints）
- `backend/app/api/v1/__init__.py` — 新增 `GET /magazine/plan/{task_id}` 端点

**验证标准**：
- [ ] 上传 5 页简单 PPTX → 识别为 fast 路径
- [ ] 上传 50 页复杂 PDF → 识别为 deep 路径
- [ ] 返回预计耗时与实际耗时误差 < 50%

### 任务 1.2：拆分 Fidelity Agent → Quality Agent

**文件**：
- `backend/app/agents/quality_agent.py`（新建，替换 fidelity_agent.py）
- `backend/app/agents/fidelity_agent.py`（保留为 content_fidelity 内部模块）

**实现内容**：
```python
class QualityAgent:
    """双重质量校验：内容保真 + 视觉质量"""

    async def verify(self, doc, output_path, task_id):
        # 阶段 1：内容保真（L1-L3）
        content_result = await self._content_fidelity(doc, output_path)
        if not content_result.passed:
            return content_result

        # 阶段 2：视觉质量（V1-V4）
        visual_result = await self._visual_quality(output_path)
        if not visual_result.passed:
            return visual_result

        # 阶段 3：生成对比报告
        report = await self._generate_report(content_result, visual_result)
        return QualityResult(passed=True, report=report)

    async def _visual_quality(self, output_path):
        """V1-V4 视觉质量校验"""
        # V1: 文字可读性（无溢出/截断/乱码）
        # V2: 图片清晰度（无模糊/拉伸）
        # V3: 布局合理性（间距/对齐/层级）
        # V4: Logo 规范性（颜色匹配/位置）
```

**新增模型**：
- `backend/app/models/quality.py` — QualityResult, VisualCheckResult, ContentFidelityResult

**验证标准**：
- [ ] L1-L3 校验逻辑保留不变（从原 fidelity_agent.py 迁移）
- [ ] V1-V4 新增视觉质量校验通过
- [ ] 能区分「内容丢失」vs「渲染瑕疵」两种不同失败类型

### 任务 1.3：新增 Assembly Agent

**文件**：`backend/app/agents/assembly_agent.py`（新建）

**实现内容**：
```python
class AssemblyAgent:
    """页面装配与最终输出"""

    async def assemble(self, rendered_pages, doc, design_spec):
        # 1. 按原始页序排列
        # 2. 合并 PDF（PyPDF2）或 PPTX（python-pptx merge）
        # 3. 嵌入弘天 Logo（根据背景色自动选择 White/Black）
        # 4. 写入元数据（生成信息、保真报告）
        # 5. 返回最终文件路径
```

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 将 renderer_node 输出的合并逻辑移入 assembly_node

**验证标准**：
- [ ] PDF 合并后页序正确
- [ ] PPTX 合并后动画不丢失
- [ ] Logo 自动根据模板背景色选择正确版本

### 任务 1.4：3 个 Validation Gate

**文件**：`backend/app/core/validation_gates.py`（新建）

**实现内容**：
```python
class ValidationGate:
    """流水线校验门"""

    async def gate1_parse完整性(self, doc: UnifiedDocument) -> GateResult:
        """Gate 1: 文本提取率 ≥98%，图片全部提取，表格数据无损"""
        text_rate = len(doc.texts) / max(doc.total_pages, 1)
        all_images = all(Path(img.local_path).exists() for img in doc.images)
        return GateResult(passed=text_rate >= 0.98 and all_images, ...)

    async def gate2_content理解(self, analysis: dict, doc: UnifiedDocument) -> GateResult:
        """Gate 2: 内容分组覆盖所有原始元素"""

    async def gate3_render质量(self, rendered_pages: list) -> GateResult:
        """Gate 3: 无文字溢出、图片清晰、布局无重叠、Logo 合规"""
```

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 在每个阶段间插入 gate 校验节点
- `backend/app/models/` — 新增 GateResult 模型

**验证标准**：
- [ ] 解析提取率不足时，自动重试解析
- [ ] 内容分组遗漏时，自动重新分析
- [ ] 渲染质量不合格时，只修复失败页面

### 任务 1.5：检查点系统

**文件**：`backend/app/core/checkpoint.py`（新建）

**实现内容**：
```python
class CheckpointManager:
    """5 级检查点：CP0-CP4"""

    async def save(self, task_id: str, level: int, state: dict):
        """保存检查点快照到 SQLite"""

    async def restore(self, task_id: str, level: int) -> dict:
        """回退到指定检查点"""

    async def list_checkpoints(self, task_id: str) -> list[CheckpointInfo]:
        """列出所有可用检查点"""

    async def cleanup(self, task_id: str):
        """任务完成后清理检查点数据"""
```

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 在每个阶段完成后调用 checkpoint.save()
- `backend/app/api/v1/__init__.py` — 新增 `POST /magazine/checkpoint/{task_id}/rollback`
- `backend/app/db/schema.ts` 或 `backend/app/core/database.py` — 新增 checkpoints 表

**验证标准**：
- [ ] 5 个检查点全部正确保存
- [ ] 从任意检查点回退后，流水线可继续执行
- [ ] 服务重启后检查点数据不丢失

---

## 二、阶段 2：可靠性与容错能力（2 周）

> 目标：每个 Agent 有独立错误恢复策略，单点失败不扩散

### 任务 2.1：Agent 级错误恢复策略

**文件**：`backend/app/core/recovery.py`（新建）

**实现内容**：
```python
class RecoveryStrategy:
    """三级恢复：重试 → 降级 → 用户协商"""

    # 每个 Agent 的降级策略表
    STRATEGIES = {
        "parser": [
            {"trigger": "docling_memory_error", "fallback": "pymupdf"},
            {"trigger": "image_extract_failed", "fallback": "mark_needs_supplement"},
        ],
        "analyzer": [
            {"trigger": "glm5_timeout", "fallback": "retry_3x"},
            {"trigger": "all_retries_failed", "fallback": "rule_based_analysis"},
        ],
        "designer": [
            {"trigger": "template_mismatch", "fallback": "generic_layout"},
            {"trigger": "glm5_error", "fallback": "rule_based_design"},
        ],
        "renderer": [
            {"trigger": "single_page_fail", "fallback": "skip_page"},
            {"trigger": "playwright_timeout", "fallback": "weasyprint_fallback"},
        ],
    }
```

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 每个节点包裹 try/except + recovery
- `backend/app/core/retry.py` — 增强为支持策略表的统一重试框架

**验证标准**：
- [ ] Docling 崩溃后自动降级到 PyMuPDF
- [ ] GLM-5 超时后重试 3 次，仍失败则规则引擎降级
- [ ] 单页渲染失败不影响其余页面

### 任务 2.2：幂等性保证

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 为每个阶段增加幂等检查
- `backend/app/core/task_tracker.py` — 增加阶段状态记录

**实现要点**：
- 每个任务有唯一 `task_id`
- 每个阶段记录 `phase_status`（pending/running/completed/failed）
- 阶段开始前检查状态，已完成则跳过
- 失败后重试时，从失败阶段开始，不重复已完成阶段

**验证标准**：
- [ ] 任务重复执行同一阶段，只运行一次
- [ ] 服务重启后，可从上次中断的阶段继续

### 任务 2.3：健康检查与优雅关闭

**修改文件**：
- `backend/app/main.py` — 增强 `/health` 端点，包含各组件状态
- `backend/app/main.py` — 实现优雅关闭（等待当前任务完成或超时）

**验证标准**：
- [ ] `/health` 返回 Redis/SQLite/LLM 连接状态
- [ ] 关闭进程时，正在执行的任务能完成或安全回滚

---

## 三、阶段 3：状态持久化（1 周）

> 目标：检查点系统已覆盖大部分需求，本阶段补充数据模型和持久化细节

### 任务 3.1：增强数据模型

**修改文件**：
- `backend/app/models/unified_document.py` — 增强字段

```python
class TextElement(BaseModel):
    # 新增字段
    original_font: str | None = None      # 原始字体名
    original_size: float | None = None    # 原始字号 pt
    original_color: str | None = None     # 原始颜色 hex
    reading_order: int = 0                # 阅读顺序索引
    importance: float = 0.5               # 视觉重要性 0-1

class ImageElement(BaseModel):
    # 新增字段
    dpi: int = 0                          # 图片 DPI
    quality_score: float = 0.0            # 0-1, GLM-5V 评估
    needs_supplement: bool = False        # 是否需要补充
    supplement_source: str = "original"   # original/pexels/unsplash/ai_generated

class PageLayout(BaseModel):
    # 新增模型
    page_number: int
    layout_type: str     # cover/text_image/data_card/two_column/full_text
    visual_hierarchy: list[str]  # 元素ID按重要性排序
    whitespace_ratio: float      # 留白比例
    dominant_color: str          # 主色调
    original_structure: dict     # 原始版式结构描述

class UnifiedDocument(BaseModel):
    # 新增字段
    page_layouts: list[PageLayout] = []
    complexity_score: float = 0.0         # Planner 评估
    processing_path: str = "standard"     # fast/standard/deep
```

**验证标准**：
- [ ] 新字段有默认值，不影响现有测试
- [ ] PPTX 解析器填充 original_font/original_size/original_color
- [ ] PDF 解析器填充 dpi/quality_score

### 任务 3.2：PPTX 版式信息提取

**修改文件**：
- `backend/app/parsers/pptx_parser.py` — 增加版式/母版/主题提取

```python
async def _extract_layout_info(self, prs, slide_idx, slide):
    """提取版式信息"""
    layout = slide.slide_layout
    return PageLayout(
        page_number=slide_idx,
        layout_type=self._classify_layout(slide),  # 根据占位符类型分类
        visual_hierarchy=self._extract_hierarchy(slide),
        dominant_color=self._extract_dominant_color(slide),
        original_structure=self._describe_layout(layout),
    )
```

**验证标准**：
- [ ] 能识别封面页 vs 内容页 vs 数据页
- [ ] 提取的颜色方案传递给 Designer Agent 作为风格参考

---

## 四、阶段 4：可观测性（1-2 周）

> 目标：任何问题 5 分钟内定位到具体模块

### 任务 4.1：增强结构化日志

**修改文件**：
- `backend/app/core/logging.py` — 为每个日志条目自动注入 context

```python
# 每条日志自动包含
context = {
    "task_id": task_id,
    "phase": current_phase,
    "page": current_page,
    "agent": agent_name,
    "elapsed_ms": elapsed,
}
```

**验证标准**：
- [ ] 所有 Agent 操作输出 JSON 格式日志
- [ ] 日志中包含 task_id，可按任务筛选
- [ ] 敏感信息（API Key、文件内容）不出现在日志中

### 任务 4.2：实时通信增强

**修改文件**：
- `backend/app/api/v1/__init__.py` — 增强 SSE 事件流

```python
# 新增 SSE 事件类型
event_types = {
    "agent_thinking": "Agent 思维流（正在分析第3页版面...）",
    "page_preview": "页面预览缩略图（base64）",
    "quality_score": "实时质量评分更新",
    "cost_update": "API 成本累计",
    "checkpoint_saved": "检查点保存通知",
    "user_input_required": "需要用户确认",
    "error_occurred": "错误事件 + 建议操作",
}
```

**前端修改**：
- `app/src/components/AgentPanel.tsx` — 增加思维流展示
- `app/src/components/ChatInterface.tsx` — 增加预览缩略图

**验证标准**：
- [ ] 前端实时展示 Agent 分析过程文字
- [ ] 每完成一页即推送预览缩略图
- [ ] API 成本实时更新

### 任务 4.3：Prometheus 指标（可选）

**文件**：`backend/app/core/metrics.py`（新建）

**核心指标**：
- `magazine_tasks_total` — 任务总数（按状态分）
- `magazine_task_duration_seconds` — 任务耗时（按阶段分）
- `magazine_llm_tokens_total` — Token 消耗（按模型分）
- `magazine_llm_cost_total` — API 费用
- `magazine_agent_errors_total` — Agent 错误数（按类型分）
- `magazine_pages_processed` — 处理页数

**验证标准**：
- [ ] `/metrics` 端点输出 Prometheus 格式指标
- [ ] 可在 Grafana 中查看任务吞吐量和延迟

---

## 五、阶段 5：性能优化（2 周）

> 目标：首页预览 < 30 秒，支持 50+ 页文档

### 任务 5.1：Designer ∥ Supplement 并行执行

**修改文件**：
- `backend/app/workflow/magazine_pipeline.py` — 重构为并行分支

```python
# 当前：顺序执行
designer_node → supplement_node → renderer_node

# 目标：并行执行
designer_node ──┐
                ├──→ merge_node → renderer_node
supplement_node ┘
```

**实现方案**：
- LangGraph 支持 `parallel` 节点
- Supplement Agent 只处理 Analyzer 标记的 `needs_supplement=True` 的图片
- Designer Agent 预留图片占位符
- merge_node 检查两边都完成后才继续

**验证标准**：
- [ ] 10 页图文混排文档，并行比顺序快 30%+
- [ ] 无素材需补充时，Supplement 分支秒级完成

### 任务 5.2：页级并行渲染

**修改文件**：
- `backend/app/agents/renderer_agent.py` — 重构为页级并行

```python
async def render_parallel(self, edit_plan):
    """页级并行渲染"""
    import asyncio
    tasks = []
    for page_plan in edit_plan.pages:
        tasks.append(self._render_single_page(page_plan))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 分离成功和失败
    success = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    return success, failures
```

**修改文件**：
- `backend/app/agents/assembly_agent.py` — 支持合并并行渲染结果

**验证标准**：
- [ ] 30 页文档渲染时间从 T 降至 T/4（4 并发）
- [ ] 单页失败不影响其余页面
- [ ] 渲染顺序与原始页序一致

### 任务 5.3：渐进式输出

**修改文件**：
- `backend/app/api/v1/__init__.py` — SSE 推送单页预览

```python
async def page_event_generator(task_id):
    """每完成一页即推送预览"""
    async for page_result in renderer.render_streaming(edit_plan):
        # 推送页面缩略图
        yield {
            "event": "page_preview",
            "data": json.dumps({
                "page": page_result.page_number,
                "thumbnail": page_result.thumbnail_base64,
                "status": "completed"
            })
        }
```

**前端修改**：
- `app/src/components/AgentPanel.tsx` — 展示页面缩略图网格，完成即亮起

**验证标准**：
- [ ] 首页预览在 30 秒内推送到前端
- [ ] 用户能看到逐页完成的动画效果

---

## 六、阶段 6：安全加固与部署（1-2 周）

### 任务 6.1：安全审计

**检查项**：
- [ ] API Key 加密存储（已有，验证实现）
- [ ] 文件路径不暴露给前端（使用 task_id 映射）
- [ ] 上传文件大小限制
- [ ] 文件类型白名单（只允许 pptx/pdf/docx/xlsx/md）
- [ ] 用户数据隔离（多用户模式下 task_id 关联 user_id）
- [ ] 日志中不含文件内容

### 任务 6.2：Docker 配置更新

**修改文件**：
- `docker-compose-v4.yml` — 更新为 V2 架构

**新增服务（可选）**：
- Prometheus（指标收集）
- Grafana（仪表盘）

### 任务 6.3：CI/CD 完善

**修改文件**：
- `.github/workflows/` — 增强流水线

**步骤**：
1. 代码质量：flake8 + black + mypy
2. 单元测试：pytest --cov
3. 安全扫描：bandit + safety
4. Docker 构建：多阶段构建
5. 自动部署：推送到测试环境

---

## 七、实施时间线

```
Week 1-2  ┃ 阶段 1: 架构重构
          ┃ ├─ Planner Agent（3天）
          ┃ ├─ Quality Agent 拆分（3天）
          ┃ ├─ Assembly Agent（2天）
          ┃ ├─ 3 个 Validation Gate（4天）
          ┃ └─ 检查点系统（5天）

Week 3-4  ┃ 阶段 2: 可靠性
          ┃ ├─ Agent 级错误恢复（3天）
          ┃ ├─ 幂等性保证（2天）
          ┃ └─ 健康检查 + 优雅关闭（2天）

Week 5    ┃ 阶段 3: 数据模型增强
          ┃ ├─ 模型字段增强（3天）
          ┃ └─ PPTX 版式提取（3天）

Week 6-7  ┃ 阶段 4: 可观测性
          ┃ ├─ 结构化日志增强（2天）
          ┃ ├─ SSE 事件流增强（3天）
          ┃ └─ 前端进度仪表盘（5天）

Week 8-9  ┃ 阶段 5: 性能优化
          ┃ ├─ Designer ∥ Supplement 并行（3天）
          ┃ ├─ 页级并行渲染（5天）
          ┃ └─ 渐进式输出（3天）

Week 10   ┃ 阶段 6: 安全与部署
          ┃ ├─ 安全审计（2天）
          ┃ ├─ Docker 更新（1天）
          ┃ └─ CI/CD 完善（2天）
```

**总计：约 10 周（2.5 个月）**

---

## 八、每个阶段的 Claude Code 使用策略

### 阶段 1 指令模板

```
请阅读 backend/app/agents/ 目录下的所有现有 Agent 实现，
然后基于 backend/app/models/ 中的数据模型，
按照以下规格创建 Planner Agent：
- 输入：文件路径
- 输出：ExecutionPlan（复杂度评分、执行路径、预计耗时、API成本）
- 复杂度评分基于：页数、图片数、表格数、文字密度
- 三条路径：fast(≤30分) / standard(31-70分) / deep(>70分)
- 保持与现有 Agent 相同的异步接口风格
- 编写对应的单元测试
```

### 阶段 2 指令模板

```
请阅读 backend/app/core/retry.py 的现有实现，
然后创建 backend/app/core/recovery.py，实现三级错误恢复策略：
1. 重试（指数退避，3次）
2. 降级（按策略表选择备选方案）
3. 用户协商（通过 SSE 推送错误信息，等待用户决策）

为以下 Agent 编写具体的降级策略：
- Parser: Docling→PyMuPDF, 图片失败→标记补充
- Analyzer: GLM-5超时→规则引擎降级
- Designer: 模板不匹配→通用布局
- Renderer: 单页失败→跳过该页
```

### 阶段 5 指令模板

```
请阅读 backend/app/workflow/magazine_pipeline.py 的 LangGraph 实现，
然后将 designer_node 和 supplement_node 从顺序执行改为并行执行：
- 使用 LangGraph 的 parallel 分支
- 在 merge_node 中等待两边完成
- Supplement 分支无素材需补充时，立即完成
- 保持所有现有功能不变
```

---

## 九、关键风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LangGraph 并行节点不成熟 | 中 | 高 | 先用 asyncio.gather 实现，必要时绕过 LangGraph |
| 检查点快照过大影响性能 | 低 | 中 | 只保存关键状态，不保存渲染文件 |
| GLM-5 API 不稳定 | 中 | 高 | 已有 retry.py + 模型降级链 |
| 页级并行渲染内存暴涨 | 中 | 高 | 限制并发数（最多 4），完成后立即释放 |
| 前端 SSE 连接断开 | 低 | 中 | 断线重连 + 从最近检查点恢复 |
| 数据模型变更影响现有测试 | 高 | 低 | 新字段全部有默认值，分批迁移 |

---

## 十、成功标准

| 指标 | 当前状态 | 目标 |
|------|---------|------|
| Agent 数量 | 5 | 8（+Planner/Assembly/Quality） |
| 验证门 | 0 | 3（Gate1/2/3） |
| 检查点 | 0 | 5（CP0-CP4） |
| 并行度 | 全顺序 | Designer∥Supplement + 页级渲染 |
| 首页预览时间 | 无（全部完成才可见） | < 30 秒 |
| 错误恢复 | 重试后停 | 三级恢复（重试→降级→协商） |
| 可观测性 | print + 基础 structlog | 结构化日志 + SSE 思维流 + Prometheus |
| PPTX 解析 | 仅内容 | 内容 + 版式 + 母版 + 主题 |
| 质量校验 | 仅 L1-L4 | L1-L3 + V1-V4 双重校验 |
| 连续运行 | 未测试 | 7 天无崩溃 |
