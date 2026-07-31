# Day 6：工程收尾 + 面试准备（~6h）

> 今天是"把代码从能跑变成能看"的一天。Day 1-5 堆了功能，Day 6 做三件事：重构、文档、面试准备。
> 继续沿用 Day 5 的 Ollama Embedding 方案完成 RAG 全链路验证。

---

## 子任务 6.0：Day 5 收尾 — Ollama Embedding（30min）

### 背景

Day 5 RAG 链路代码写完了，但 SiliconFlow Embedding API 402 余额不足。改用 Ollama 本地免费方案。

### 步骤

```bash
# 1. 装 Ollama（如果没有）
# https://ollama.com/download/windows

# 2. 拉 embedding 模型（768 维，中英文，免费）
ollama pull nomic-embed-text

# 3. 确保 Ollama 在运行
ollama serve
```

### 改代码

`services/embedding_client.py`：
```python
embedding_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",  # Ollama 本地
    api_key="ollama",                       # 不需要真实 key
)
```

`services/embedding_service.py`：`self.dim = 768`

### 验收

Swagger 测 `POST /ai/rag-ask`，确认 SSE 流式返回基于知识库文档生成的题目。

---

## 子任务 6.1：代码重构（2h）

### 概念引出：重构解决什么问题？

Day 1-5 每天都在加新功能。代码开始出现"坏味道"：

```
routers/ai.py: 92 行 — 塞了 3 个端点 + 生成器 + 2 个 EmbeddingService 实例
                 → 职责混乱

generate_stream() 和 generate_question():
  后者只是给前者套 StreamingResponse → 薄包装

embedding_service.py: 两个 build 方法 90% 重复
  → embedding 调用、np.array 构造、index.add 完全一样
```

### 三个重构原则

**DRY（Don't Repeat Yourself）**：`build_index_db` 和 `build_index_md` 抽公共方法 `_embed_and_add(texts: list[str])`

**单一职责**：router 只做"接请求 → 调 service → 返回"，service 做业务逻辑

**依赖倒置**：`EmbeddingService.__init__` 接收 client 参数，换 Embedding 实现不改类代码

### 审视清单

| 文件 | 审视问题 |
|------|---------|
| `routers/ai.py` | 92 行太多，`generate_stream` 能不能抽到 `services/`？ |
| `services/embedding_service.py` | `build_index_db` 和 `build_index_md` 重复代码 |
| `services/llm_client.py` | 只有 DeepSeek，如果同时用多个 LLM 怎么设计？ |
| `schemas/rag_request.py` | 单独文件只放一个 class，和 `schemas/ai.py` 合并？ |

### 易错点

| 坑 | 表现 | 修复 |
|----|------|------|
| 为了 DRY 而 DRY | 抽出 5 参数方法，比原来更难读 | 重复 2 次不抽，3 次以上才抽 |
| 重构不测试 | 改完不知道什么炸了 | 每次改完跑 `/docs` 手动测一遍 |
| 过度设计 | 给 200 行代码加一堆抽象层 | 项目规模决定架构复杂度 |

---

## 子任务 6.2：README 工程文档（2h）

### 概念引出：README 是给谁看的？

面试官看 GitHub 先看 README。核心目的：**5 分钟理解"这是什么、怎么跑、为什么这样设计"**。

### README 结构

```
1. 项目名称 + 一句话定位
2. 架构图（mermaid，GitHub 原生渲染）
3. 技术栈 + 选型理由（为什么选这个，不只是"是什么"）
4. 快速启动（3 步跑通）
5. API 端点一览
6. 项目目录结构
7. 设计决策记录（指向 learning-journal.md）
```

### 关键：技术栈写"为什么"

```markdown
| 技术 | 为什么选它 |
|------|-----------|
| FastAPI | 原生异步，StreamingResponse 开箱即用，自动 Swagger |
| SQLAlchemy 2.0 async | ORM 不阻塞事件循环 |
| PostgreSQL | JSONB 字段存储动态 tags |
| DeepSeek | OpenAI 兼容，中文强，便宜 |
| FAISS | 轻量向量索引，不需单独部署数据库 |
| Ollama | 本地免费 Embedding，零运维 |
```

### 架构图（mermaid）

```
graph TD
    Client --> FastAPI
    FastAPI --> Auth["JWT Auth"]
    FastAPI --> AI["/ai Router"]
    FastAPI --> Q["/questions Router"]
    AI --> DeepSeek["DeepSeek LLM"]
    AI --> FAISS["FAISS 索引"]
    AI --> Knowledge["知识库 md"]
    Q --> PostgreSQL
    Q --> Redis
```

---

## 子任务 6.3：模拟面试清单（1.5h）

### 概念引出

面试不是背答案，是讲**决策链**。正确的回答结构：**场景 → 约束 → 决策 → 后果**。

```
"我的项目需要 SSE 流式输出 LLM 回复（场景）。
 Django 的 async 支持不够成熟（约束）。
 选了 FastAPI——原生 async，StreamingResponse 开箱即用（决策）。
 代价是生态比 Django 小，但 AI 应用不需要 Django Admin（后果）。"
```

### 10 道核心面试题

| # | 问题 | 指向你的项目 |
|---|------|------------|
| 1 | 为什么 FastAPI 而不是 Django？ | SSE 流式、自动 docs、原生 async |
| 2 | `async def` vs `def`？什么场景用哪个？ | `get_db()` + yield session 生命周期 |
| 3 | 数据库 session 怎么管理？ | `Depends(get_db)` + yield |
| 4 | 为什么 PostgreSQL 而不是 MySQL？ | JSONB 存 tags，asyncpg 驱动 |
| 5 | JWT 认证流程从头到尾 | `auth_service.py` → `get_current_user` |
| 6 | Redis 做了什么？为什么 60s TTL？ | 随机抽题缓存 |
| 7 | RAG 的 R-A-G 三步 | 知识库双检索 → 拼 Prompt → LLM 流式 |
| 8 | Embedding 是什么？为什么 N 维？ | 语义坐标，L2 距离 |
| 9 | SSE vs WebSocket？为什么选 SSE？ | 单向推送，协议更简单 |
| 10 | 你的代码怎么分层？换存储改多少？ | Router → Repository → DB，只改一处 |

### 费曼测试

抽任意一题，不看笔记口述，说清"场景 → 约束 → 决策 → 后果"，指向具体代码行。

---

## ✅ Day 6 验收标准

- [ ] Ollama Embedding 拉通，`/ai/rag-ask` SSE 流式返回正常
- [ ] `routers/ai.py` 瘦身，stream 生成器抽到 `services/`
- [ ] `EmbeddingService` 公共逻辑抽取，两个 build 方法复用
- [ ] README 写完后，给一个没看过项目的人 5 分钟能看懂
- [ ] 10 道面试题每道能口述决策链，指向具体代码
- [ ] git commit: `V6: refactor + README + interview prep checklist`

---

## Day 7 预告（缓冲日）

```
Day 7: 深挖薄弱点
  → 异步事件循环深入（TaskGroup、create_task 实战）
  → Tool Calling 手写（Day 5 的 tool role 到这里才真正用上）
  → RAG 进阶（真实 Embedding 切换、重排序 re-rank、混合搜索）
```
