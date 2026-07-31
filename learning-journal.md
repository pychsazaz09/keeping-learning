# 学习日志 — AI Agent 开发之路

> 记录每一次架构决策、概念突破、踩坑复盘。不是流水账，是可追溯的思维轨迹。

---

## Day 5：AI 增强 — LLM + Embedding + RAG（2026-07-31）

### 一、概念地图：今天学了什么

```
Day 5 新增概念全景：

LLM 调用层：
├── AsyncOpenAI        — 异步 LLM 客户端，所有 OpenAI 兼容模型通用
├── 四种消息角色         — system / user / assistant / tool
├── stream=True        — 流式输出，delta.content 逐片推送
└── SSE 协议           — Server-Sent Events，单向推送，HTTP 协议

Embedding 语义层：
├── Embedding 向量化    — 文字 → 1536/1024/768 个浮点数
├── FAISS 向量索引      — 存向量 + 暴搜最相似的 K 个
├── L2 距离            — 欧几里得距离，越小越相似
└── Chunk 切片          — 文档按 ## 标题/段落切成小块

RAG 检索增强层：
├── R = Retrieval      — Embedding 用户问题 → FAISS 搜知识库
├── A = Augmented      — 检索结果拼进 Prompt
└── G = Generation     — LLM 基于资料流式生成
```

### 二、架构决策记录

#### 决策 1：为什么 `AsyncOpenAI` 而不是 `OpenAI`？

**场景**：FastAPI 路由函数是 `async def`，事件循环是单线程。

**决策**：用 `AsyncOpenAI`。

**原因**：同步 `OpenAI` 调 LLM 会阻塞线程 30 秒，事件循环卡死。`AsyncOpenAI` 遇到网络 IO 时 `await` 挂起，释放事件循环去处理其他请求。**FastAPI 是异步的 → 所有 IO 必须异步 → LLM 客户端必须 AsyncOpenAI**。

**适用判断**：调 LLM、查数据库、读 Redis 这种有网络等待的 → `await`。纯 CPU（numpy 运算、FAISS 搜索）→ 不需要。

#### 决策 2：为什么 LLM 客户端用模块级单例？

**场景**：每次请求都需要调 LLM。

**决策**：`client = AsyncOpenAI(...)` 放模块级别，`get_llm_client()` 返回同一个实例。

**原因**：每次 `new AsyncOpenAI()` = 重复创建 HTTP 连接池。100 个请求 new 100 次 = 浪费连接、浪费内存。单例 = 一个连接池全局复用。这和 `dependencies.py` 里 `security = HTTPBearer()` 是同一个模式。

#### 决策 3：为什么 Embedding 索引和题库索引用两个独立实例？

**场景**：知识库文档 chunk + 题库标题，两者是不同的语义空间。

**决策**：`embedding_md = EmbeddingService()` 和 `embedding_question = EmbeddingService()` 两个独立实例。

**原因**：
- 文档语义（"装饰器是什么"）和题库语义（"出一道装饰器困难题"）混在一起，搜索互相污染
- 两个实例各自维护独立的 FAISS 索引 + id_map，互不干扰
- 同一个 `EmbeddingService` 类，new 两次 = 两个完全独立的搜索系统。**分层架构的价值又验证了一次**

#### 决策 4：为什么 Prompt 模板放 `prompts/templates.py`？

**场景**：Prompt 字符串写在哪个文件。

**决策**：独立 `prompts/templates.py`。

**原因**：Prompt 和数据一样需要版本管理。写在 router 里 → 改了要动路由代码，不内聚。独立的 prompt 文件 → 像 SQL 文件一样集中可维护。

#### 决策 5：为什么 SSE 而不是 WebSocket？

**场景**：LLM 流式输出推送给前端。

**决策**：`StreamingResponse(stream_generator, media_type="text/event-stream")`。

**原因**：LLM 流式是单向推送（服务端→客户端）。SSE 就是 HTTP 协议，不需要协议升级。WebSocket 是双向通信，更重。**杀鸡不用牛刀**。

### 三、分层架构 — 今天再次验证了它的价值

Day 3 的核心收获是"Router 不改，换存储"——从 JSON 文件存储换成 PostgreSQL，只改了 `dependencies.py` 和 `repositories/`，路由零改动。

今天同样的原则又出现了：

```
Embedding 实现层     →  embedding_client  ← 今天换过 3 次
                         ├── SiliconFlow (BAAI/bge-large-zh-v1.5)
                         ├── Ollama (nomic-embed-text)      ← 本地免费
                         └── np.random.randn                ← 占位验证

EmbeddingService 层  →  不关心向量从哪来，只管"拿到向量 → 存 FAISS → 搜索"
                         build_index_db / build_index_md / search 全部不变

Router 层            →  POST /ai/rag-ask / GET /ai/semantic-search 全部不变
```

换 Embedding 实现 = 只改 `embedding_client.py` 和 `self.dim`，不动 `EmbeddingService` 和 Router。**和 Day 3 换存储一个道理**。

### 四、逐个模块深讲

#### 前置补课：异步事件循环的思维模型

**概念**：事件循环是单线程的任务调度器。`await` = 挂起点，不是阻塞点。

**场景**：调 LLM、查数据库时会等几秒到几十秒。同步模型下线程空等；异步模型下事件循环去处理别的请求。

**核心对比**：
```
time.sleep(2)          → 线程卡死 2 秒 → 什么都不能干
await asyncio.sleep(2) → 挂起 → 事件循环去跑别的 → 2 秒后回来继续
```

**费曼测试**：`await asyncio.sleep(2)` 和 `time.sleep(2)` 的区别？为什么前者不阻塞事件循环？

---

#### 任务 5.1：AsyncOpenAI 客户端 + 流式调用

**概念**：`AsyncOpenAI` 是 OpenAI SDK 的异步客户端，通过换 `base_url` 可以调任何兼容 OpenAI 接口的模型。

**场景**：FastAPI 里调 LLM。

**怎么用**：
```python
from openai import AsyncOpenAI  # 注意：不是 OpenAI

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),   # 从 .env 读，不硬编码
    base_url=os.getenv("DEEPSEEK_BASE_URL"),  # 这行决定了调哪个模型
)
```

**四种消息角色**（面试必问）：

| role | 含义 | 用在哪 |
|------|------|--------|
| `"system"` | 设定 AI 人设 | 每次请求第一条 |
| `"user"` | 用户输入 | 每次用户说话 |
| `"assistant"` | AI 回复 | 多轮对话，保持上下文 |
| `"tool"` | 函数调用结果 | Day 7 Tool Calling |

**关键规则**：单次响应中 `content` 和 `tool_calls` 不会同时出现——AI 要么说话要么调工具。

**非流式 vs 流式**：

| | 非流式 | 流式 |
|---|---|---|
| 内容位置 | `.message.content` | `.delta.content` |
| 类型 | `str` | `str \| None`（片段，第一个可能为 None） |
| 结束标志 | 函数返回 | `finish_reason == "stop"` |

**易错点**：
- 第一个 chunk 的 `delta.content` 可能是 `None` → 必须 `if delta:` 判空
- `model` 名是 API 服务端的枚举值，不是自定义的 → 写错直接 404
- 流式函数必须 `async def`，不能用普通 `def`

---

#### 任务 5.2：SSE 流式响应

**概念**：SSE（Server-Sent Events）= HTTP 协议上的服务端单向推送。`StreamingResponse` 包装异步生成器，`media_type="text/event-stream"`。

**场景**：LLM 生成 500 字要 10-30 秒，SSE 让字一个个蹦出来。

**流程**：
```
POST /ai/generate → FastAPI → AsyncOpenAI stream=True
    → async for chunk → yield f"data: {json}\n\n"
    → StreamingResponse 包裹 → 前端逐条接收
```

**`yield` 和 `return` 的区别**：
- `return`：函数结束，一次返回全部
- `yield`：函数暂停，把当前值推出去，下次从暂停点继续

**这就是 `yield` 的生成器语义**——函数变成可暂停恢复的状态机。

**易错点**：
- `media_type` 写错（`text/plain`）→ 前端不解析流，等全部才显示
- `StreamingResponse` 内部抛异常 → 流已开始，HTTP 状态改不了，仍返回 200

---

#### 任务 5.3：AI 自动出题 + Prompt Engineering

**概念**：Prompt = 给 LLM 的岗位说明书。三要素：角色设定 + 任务描述 + 格式约束。

**场景**：用户填 topic/difficulty/count → LLM 生成 JSON 数组格式的面试题 → SSE 流式返回。

**关键参数组合**：

| 场景 | temperature | max_tokens |
|------|------------|------------|
| 出题 | 0.7-0.9 | 2048 |
| 搜索 | 0.0 | 256 |
| RAG 问答 | 0.3-0.5 | 1024 |

**为什么指定 JSON 格式返回**：LLM 返回自由文本 → 解析困难。JSON → Pydantic 直接校验 → 可自动存储。

**易错点**：
- `f-string` 里有 `{` → `.format()` 报 `KeyError` → 用 `{{` 转义
- `temperature=0` 不保证结果一致 → 0 ≈ 确定但不完全确定

---

#### 任务 5.4：Embedding 向量化

**概念**：Embedding = 把文字变成一串浮点数（向量）。语义相近的文字 → 向量也相近。

**场景**：用户搜"内存管理"，传统关键词匹配找不到"GC原理"。Embedding 把两者都向量化，算距离 → "GC原理" 距离"内存管理"很近 → 返回。

**怎么用**：
```python
response = await client.embeddings.create(
    model="BAAI/bge-large-zh-v1.5",  # 专用 Embedding 模型，不是聊天模型
    input="Python 异步编程详解",
)
vector = response.data[0].embedding  # list[float]
```

**关键区分**：Embedding 模型和聊天模型不能互换。用聊天模型调 embeddings endpoint → 404。

**Embedding 提供方对比**：

| 方案 | 维度 | 费用 | 中文 |
|------|------|------|------|
| SiliconFlow BGE-large-zh | 1024 | 免费额度 | 优秀 |
| Ollama nomic-embed-text | 768 | 本地免费 | 良好 |
| OpenAI text-embedding-3-small | 1536 | 收费 | 一般 |

**易错点**：
- Embedding 模型名 ≠ 聊天模型名 → 写错 404
- 每请求都 Embedding 整个题库 → 太慢 → 预计算存 FAISS

---

#### 任务 5.5：FAISS 向量索引 + 语义搜索

**概念**：FAISS（Facebook AI Similarity Search）= 给你一堆向量 + 查询向量 → 找最相似的 K 个。

**场景**：题库 1000 道题，每道题存一个向量。用户搜索 → Embedding 问题 → FAISS.search → 返回最像的 5 道。

**核心 API**：
```python
import faiss
import numpy as np

# 创建索引
index = faiss.IndexFlatL2(dim)           # dim=向量维度

# 添加向量
index.add(np.array(vectors, dtype=np.float32))   # 必须是 float32，2维

# 搜索
distances, indices = index.search(query, k=5)     # query 也是 2维
# distances = 距离（越小越像）
# indices   = FAISS 行号（不是数据库 ID！）
```

**关键概念：`indices` 不是数据库 ID**

FAISS 返回的是 `add()` 时的顺序号（0, 1, 2...）。需要 `id_map` 翻译：
```python
id_map[faiss返回的行号] = 数据库 UUID  #（题库索引）
id_map[faiss返回的行号] = chunk 文字   #（文档索引）
```

**索引什么时候构建**：
- 方案 A：启动时从数据库全量重建（你用的）
- 方案 B：增量更新（数据量大时用）

**易错点**：
- `dtype` 不是 `float32` → `RuntimeError`
- 维度不匹配 → `AssertionError: d == self.d`
- `indices` 直接当数据库 ID 用 → 查出错的题
- `search()` 查询向量也用随机向量 → 和存储的 Embedding 不在同一语义空间 → 结果随机

---

#### 任务 5.6：RAG 完整链路

**概念**：RAG = Retrieval-Augmented Generation，三步走。

**场景**：用户请求出题 → ① 从知识库检索相关资料 → ② 从题库检索风格参考 → ③ 两者拼进 Prompt → ④ LLM 基于真实资料生成。

**你的设计：双路检索**

```
POST /ai/rag-ask {"question": "出3道Python装饰器困难题"}

  R1: embedding_md.search()     → 知识文档 chunk（保证内容准确）
  R2: embedding_question.search() → 题库风格参考（保证风格一致）

  A:  两者拼接 Prompt → "参考资料 + 参考风格 + 用户问题"

  G:  generate_stream() → SSE 流式返回
```

**RAG vs 直接问 LLM**：

| | 直接问 | RAG |
|---|---|---|
| 内容来源 | LLM 记忆（可能过时、编造） | 你的知识库（可控） |
| 风格一致性 | 随机 | 参考已有题库 |
| 可追溯性 | 不知道答案从哪来 | 告诉用户参考了哪些资料 |

### 五、技术选型判断力

#### 什么时候用异步 `await`？

| 操作 | 用异步吗 | 原因 |
|------|---------|------|
| 调 LLM API | ✅ `await` | 网络 IO，30 秒 |
| 查数据库 | ✅ `await` | 网络 IO，ms 级 |
| FAISS search | ❌ `def` | CPU 运算，纯计算 |
| `np.random.randn` | ❌ 同步 | CPU 运算 |
| 读本地文件（启动时） | ❌ `with open()` | 启动一次，几十 KB |
| numpy 切片 | ❌ 同步 | 纯计算 |

**判断公式**：操作涉及"等别人"（网络、磁盘）= `await`。操作是"自己算"（CPU）= 不需要。

#### 为什么 `AsyncOpenAI()` 构造函数是同步的但 API 调用是异步的？

- `new AsyncOpenAI()`：在内存里创建一个 Python 对象，设 `api_key`、`base_url`，不涉及网络 → 同步
- `.chat.completions.create()`：发 HTTP 请求，等 30 秒，依赖网络 → 异步

**判断标准不是"这个类名字带 Async"，而是"这个操作需不需要等 IO"。**

### 六、踩坑清单

| 坑 | 表现 | 根因 | 教训 |
|----|------|------|------|
| `le`/`ge` 写反 | 422 Validation Error | `le=1, ge=10`，逻辑矛盾 | `ge=下限, le=上限`，数轴从小到大 |
| FAISS dtype 不是 float32 | RuntimeError | numpy 默认 float64 | FAISS 只要 float32 |
| FAISS 向量维度和索引维度不匹配 | AssertionError | API 返回 1024 维，索引建了 512 维 | 维度做成常量，和 Embedding 模型绑定 |
| `indices` 当数据库 ID | 查出的题不相关 | FAISS 返回行号 | 必须 `id_map` 翻译 |
| SSE `media_type` 写错 | 前端不实时显示 | 写了 `text/plain` | 必须 `text/event-stream` |
| 流式第一个 chunk content 是 None | AttributeError | LLM 先发元数据 | `if delta:` 判空 |
| `search()` 用随机向量查真实 Embedding 索引 | 搜索结果随机 | 存和查不在同一语义空间 | 存和查必须用同一个 Embedding 模型 |
| `search()` 是 `def` 但内部要 `await` API | SyntaxError | async 和 sync 混用 | 要调 `await` 的方法必须 `async def` |
| 模块级单例 `Depends` 失效 | NoneType | `Depends` 只在 FastAPI 路由里有效 | 普通类的参数由调用方显式传入 |

### 七、费曼测试（Day 5 结束时口述）

- [ ] 口述 `AsyncOpenAI` 的 `messages` 参数四角色，为什么按时间顺序？
- [ ] 口述非流式 `.message.content` 和流式 `.delta.content` 的区别？
- [ ] 口述 RAG 的 R-A-G 三步分别做了什么？
- [ ] 口述 `content` 和 `tool_calls` 为什么不能同时出现？
- [ ] 口述 `asyncio.sleep(2)` 和 `time.sleep(2)` 的区别？
- [ ] 口述 FAISS 的 `indices` 为什么不是数据库 ID？
- [ ] 口述 `ge` 和 `le` 哪个是上限哪个是下限？

### 八、git commit

```bash
git add -A && git commit -m "V5: LLM streaming + Embedding semantic search + RAG pipeline

- AsyncOpenAI client with DeepSeek streaming via SSE
- AI auto-generate questions (POST /ai/generate)
- Embedding service with FAISS vector index (SiliconFlow/Ollama)
- Semantic search (GET /ai/semantic-search)
- Dual-retrieval RAG pipeline (POST /ai/rag-ask)
  - Knowledge base retrieval for accuracy
  - Question bank retrieval for style consistency
- Prompt template management (prompts/templates.py)
- Embedding provider abstraction (embedding_client.py)
"
```
