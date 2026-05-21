# API 文档 — 杂志级文档重构智能体 V4

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **认证**: 无（API Key 通过 `/api-keys/save` 会话级存储）

---

## API Key 管理

### POST /api-keys/save

保存 API Key 到 Redis 会话（24 小时过期）。

**请求体：**
```json
{
  "session_id": "uuid",
  "zhipu_api_key": "xxx.xxxxx",
  "zhipu_model": "glm-5-pro"
}
```

### GET /api-keys/status/{session_id}

检查 API Key 配置状态（不返回密钥本身）。

### POST /api-keys/test/zhipu?session_id=xxx

测试智谱 API Key 是否有效。

---

## 杂志重构 API

### POST /magazine/upload

上传文件并启动处理流程。

**请求**: `multipart/form-data`
- `file`: 文件（支持 .pptx, .pdf, .docx, .xlsx, .md, .txt）
- 最大 100MB

**响应：**
```json
{
  "task_id": "uuid",
  "status": "pending"
}
```

**错误码：**
- 400: 不支持的格式 / 文件内容与扩展名不匹配
- 413: 文件超过大小限制
- 429: 请求过于频繁

### GET /magazine/status/{task_id}

查询处理进度。

**响应：**
```json
{
  "task_id": "uuid",
  "status": "parsing | analyzing | designing | rendering | verifying | completed | failed",
  "progress": 0.8,
  "message": "",
  "fidelity_score": 0.97,
  "output_path": "/data/output/xxx/magazine.pptx"
}
```

### GET /magazine/fidelity/{task_id}

获取保真校验报告。

**响应：**
```json
{
  "output_path": "...",
  "fidelity_score": 0.97,
  "fidelity_passed": true,
  "repair_count": 0,
  "supplemented": false
}
```

### GET /magazine/export/{task_id}?format=pdf

下载生成结果。

- `format`: `pdf` 或 `pptx`

**响应**: 文件流（application/pdf 或 application/vnd.openxmlformats-officedocument.presentationml.presentation）

---

## 健康检查

### GET /health

```json
{"status": "ok", "version": "4.0.0"}
```
