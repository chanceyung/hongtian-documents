# 部署指南

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Docker | 20.10+ | 容器运行时 |
| Docker Compose | 2.20+ | 服务编排 |
| Redis | 7.0+ | 会话存储和缓存 |

## 快速部署

```bash
# 一键部署
./scripts/deploy.sh
```

## 手动部署

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入实际配置
```

必须配置的环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `CUSTOM_LLM_API_KEY` | 智谱 GLM-5 API Key | `xxx.xxxxx` |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` |
| `PEXELS_API_KEY` | Pexels 图片搜索（可选） | — |
| `UNSPLASH_ACCESS_KEY` | Unsplash 图片搜索（可选） | — |
| `REPLICATE_API_TOKEN` | AI 生图（可选） | — |

### 2. 启动服务

```bash
docker compose -f docker-compose-v4.yml up -d --build
```

### 3. 验证部署

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "4.0.0"}
```

访问地址：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 服务架构

```
┌─ Nginx (:80) ──────────────────────────┐
│  反向代理 → 前端(:3000) + 后端(:8000)    │
└─────────────────────────────────────────┘
┌─ Backend (:8000) ──────────────────────┐
│  FastAPI + 6 智能体 + LangGraph 工作流   │
└─────────────────────────────────────────┘
┌─ Redis (:6379) ────────────────────────┐
│  API Key 会话存储 + 解析结果缓存         │
└─────────────────────────────────────────┘
```

## 数据备份

```bash
# 备份
./scripts/backup.sh

# 恢复
./scripts/restore.sh backups/backup_xxx.tar.gz
```

## 更新部署

```bash
git pull origin main
docker compose -f docker-compose-v4.yml up -d --build
```

## 故障排查

| 问题 | 排查方法 |
|------|---------|
| 服务无法启动 | `docker compose logs backend` |
| Redis 连接失败 | 检查 REDIS_URL 和 Redis 容器状态 |
| GLM-5 API 报错 | 检查 API Key 有效性 |
| 文件上传失败 | 检查 UPLOAD_DIR 权限和磁盘空间 |
| PDF 渲染失败 | 确保 Playwright 浏览器已安装 |
