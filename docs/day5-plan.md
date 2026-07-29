# Day 5：AI 增强 — LLM + Embedding + RAG（6h）

> **今天是转折点**——从"后端 CRUD 程序员"升级为"AI 应用工程师"。前面 4 天是地基，今天盖第一层楼。
>
> **三个核心产出**：LLM 流式出题 + 语义搜索 + RAG 问答。每一个都是面试可讲的项目亮点。

---

## 任务之前：API Key 准备

```bash
# 注册 DeepSeek（https://platform.deepseek.com）→ 开发者中心 → API Key
# 充 10 块钱够你练一个月
# 价格：每 100 万 token 输入 1 元，输出 2 元

# 把 key 加到 .env
echo "DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx" >> .env
echo "DEEPSEEK_BASE_URL=https://api.deepseek.com" >> .env
```

---

## 子任务 5.1：AsyncOpenAI 客户端 — LLM 调用的地基（1.5h）

### 概念引出

你 Java 调过 LLM API 吗？Python 侧的 SDK 叫 `openai`，但它不只是给 OpenAI 用——**任何兼容 OpenAI 接口的模型都能调**（DeepSeek、通义千问、GLM）。

```
你写的 Python 代码
     ↓
openai SDK  → HTTP POST → https://api.deepseek.com/v1/chat/completions
     ↓                        ↑
返回 JSON                 这是兼容 OpenAI 格式的 API
     ↓
SDK 把 JSON 解成 Python 对象 → response.choices[0].message.content
```

OpenAI 定义了一套 HTTP API 规范（`/v1/chat/completions`）。DeepSeek 实现了同款规范。换个 `base_url` 就是换模型——这就是为什么要学 `AsyncOpenAI` 而不是某个模型专用 SDK。

### 架构决策

```
为什么用 AsyncOpenAI 而不是同步 OpenAI？
  同步：调 LLM → 线程卡死 30 秒 → 不能干别的
  异步：调 LLM → 释放线程 → 其他请求进来 → 30 秒后 LLM 返回 → 拿到结果
  
  FastAPI 是异步的 → LLM 客户端也必须是异步的 → AsyncOpenAI

为什么用 DeepSeek 而不是直接 OpenAI？
  ① 便宜 10-20 倍（练习够用）
  ② API 完全兼容 OpenAI 格式（代码不用改，只换 base_url）
  ③ 中文能力强（面试题库全是中文）
```

### 怎么用 — 逐层拆

```python
from openai import AsyncOpenAI  # ← 注意：不是 OpenAI，是 AsyncOpenAI！

client = AsyncOpenAI(
    api_key="sk-xxx",                         # 从 .env 读，不要硬编码！
    base_url="https://api.deepseek.com",       # ← 这行决定了调哪个模型
)

response = await client.chat.completions.create(
    model="deepseek-chat",                    # 模型名（DeepSeek V3 用这个）
    messages=[                                 # 消息数组——核心结构
        {"role": "system", "content": "你是资深面试官"},       # ① 系统指令
        {"role": "user",   "content": "解释 Python 装饰器"},   # ② 用户问题
    ],
    temperature=0.7,                           # 0=死板 1=创意（出题用 0.8）
    max_tokens=1024,                            # 最多返回 1024 个 token
    stream=False,                               # False=一次性返回 True=逐字流式
)

# 拿到结果
print(response.choices[0].message.content)
```

### 参数速查

| 参数 | 类型 | 含义 | 设错了会怎样 |
|------|------|------|------------|
| `model` | `str` | 模型名 | 写错 → API 返回 404 |
| `messages` | `list[dict]` | 对话历史，**必须按时间顺序** | 乱序 → LLM 失忆 |
| `temperature` | `float`（0-2） | 0=确定性 2=随机性 | 出题用 0.7-0.9（要创意），搜索用 0（要精确） |
| `max_tokens` | `int` | 返回上限 | 太小 → 话没说完就断了；太大 → 费钱 |
| `stream` | `bool` | 是否逐字返回 | `False`→等全部；`True`→流式 |
| `timeout` | `float` | 超时秒数 | LLM 慢的时候直接抛异常 |

### 四种消息角色（面试必问）

| 角色 | `role` 值 | 含义 | 什么时候用 |
|------|----------|------|-----------|
| 系统 | `"system"` | 设定 AI 的人设和行为边界 | 每次请求第一条，定调 |
| 用户 | `"user"` | 用户说的话 | 每次用户输入 |
| 助手 | `"assistant"` | AI 的回复 | 多轮对话时把上一轮的 AI 回复放进来 |
| 工具 | `"tool"` | 函数调用的结果回填 | Tool Calling（Day 7 才需要） |

**关键规则**：单次响应中 `content` 和 `tool_calls` 不会同时出现——AI 要么说话，要么调工具，二选一。这是 LLM API 的设计约束，面试高频。

### 费曼测试

> 口述：`AsyncOpenAI` 的 `messages` 参数为什么要按时间顺序？如果上一轮的 `assistant` 消息没放进 `messages`，LLM 会怎样？（答：会丢失上下文，像失忆了一样）

---

## 子任务 5.2：流式 SSE — 逐字输出是怎么做到的（1h）

### 概念引出

LLM 生成 500 字需要 10-30 秒。两种方式：

```
非流式（stream=False）：                 流式（stream=True）：
  请求 → 等 30 秒 → 一次返回全部           请求 → 0.5s → 第1个字
                                                   → 0.5s → 第2个字
  用户看到：白屏 30 秒 → 突然出现                    → 0.5s → 第3个字
                                                        ...
  体验：差                                  用户看到：字一个个蹦出来
                                                   体验：好（ChatGPT 就是这样）
```

### 全局流程

```
用户 HTTP 请求 POST /ai/generate
     ↓
FastAPI StreamingResponse 建立 SSE 连接
     ↓
await client.chat.completions.create(stream=True)
     ↓
async for chunk in response:          ← Python 异步迭代器
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content   ← 逐字推给前端
     ↓
SSE 协议：每个 chunk 用 "data: xxx\n\n" 格式发送
     ↓
前端 EventSource 逐条接收 → 拼成完整回答
```

### 非流式 vs 流式 — 结构对比

```python
# 非流式返回结构
response.choices[0].message.content          # str：完整的回复

# 流式返回结构——每个 chunk 是一小片
for chunk in response:
    chunk.choices[0].delta.content           # str | None：这一片的文字
                                              # 第一个 chunk 可能是 None
                                              # 最后一个 chunk 的 finish_reason = "stop"
```

|| 非流式 | 流式 |
|---|---|---|
| 访问内容 | `.message.content` | `.delta.content` |
| content 类型 | `str`（完整） | `str \| None`（片段、可能为空） |
| 返回值 | `ChatCompletion` | `ChatCompletionChunk`（迭代器） |
| 结束标志 | 函数返回 | `finish_reason="stop"` |

### 架构决策

```
为什么用 SSE 而不是 WebSocket？
  SSE：单向推送（服务端→客户端），HTTP 协议，更简单
  WebSocket：双向通信，协议升级，更复杂
  LLM 流式输出是单向的 → SSE 完美匹配

FastAPI 的 StreamingResponse：
  from fastapi.responses import StreamingResponse
  return StreamingResponse(generate_stream(), media_type="text/event-stream")
  # generate_stream 是你写的异步生成器函数
```

### 易错点

| 坑 | 现象 | 根因 | 修复 |
|----|------|------|------|
| 第一个 chunk 的 content 是 None | `AttributeError` | LLM 先发元数据，第二个 chunk 才开始有字 | 判空：`if chunk.choices[0].delta.content:` |
| `StreamingResponse` 的 status_code | 默认 200，出错了也是 200 | Streaming 已开始，改不了 status 了 | 在开始 stream 之前先验证输入 |
| 同步函数里调 `await` | `SyntaxError` | `def` 不是 `async def` | 流式函数必须 `async def` |
| `media_type` 写错 | 前端不解析流 | 写了 `text/plain` 而不是 `text/event-stream` | 必须是 `text/event-stream` |

---

## 子任务 5.3：AI 自动出题 — Prompt Engineering 实战（1.5h）

### 概念引出

```
之前：用户手动敲 cli.py add → 录入题目
之后：POST /ai/generate {"topic": "Python异步", "difficulty": "hard", "count": 3}
       → LLM 自动生成 3 道题 → 流式返回到前端 → 用户点"保存"→ 存入数据库
```

### Prompt 模板设计

你写 Prompt 就是在给 LLM 写"岗位说明书"。三要素：

```python
GENERATE_QUESTIONS_PROMPT = """你是一位资深 {topic} 面试官，有 10 年以上技术面试经验。

要求：
1. 生成 {count} 道 {difficulty} 难度的面试题
2. 每题包含：题目标题、标签（逗号分隔）、参考答案（100-300字）
3. 题目要有区分度——不是简单的"XX是什么"，而是考察理解和应用

请用 JSON 数组格式返回：
[
  {{"title": "...", "tags": "xxx,yyy", "answer": "..."}},
  ...
]
"""
```

### 架构决策

```
Prompt 放哪里？
  方案 A：写在 router 里 —— 改了要改路由代码，不内聚
  方案 B：prompts/templates.py —— 集中管理，像 SQL 文件一样
  → 选 B。Prompt 和数据一样需要版本管理。

为什么指定 JSON 格式？
  LLM 返回自由文本 → 解析困难 → 无法自动存储
  LLM 返回 JSON → Pydantic 反序列化 → 直接入库
```

### 关键参数组合

| 场景 | temperature | max_tokens | 为什么 |
|------|------------|------------|--------|
| 出题 | 0.7-0.9 | 2048 | 需要创意，三道题可能很长 |
| 搜索 | 0.0 | 256 | 只要匹配结果，不要瞎编 |
| RAG 回答 | 0.3-0.5 | 1024 | 基于事实回答，适当流畅 |

### 易错点

| 坑 | 现象 | 根因 |
|----|------|------|
| LLM 返回的 JSON 不合法 | `json.loads` 炸 | 多了逗号、少了引号、有注释 |
| temperature=0 但每次结果不同 | 以为 0=绝对确定 | 0≈确定但不保证，LLM 有随机性 |
| Prompt 写太短 | 题目跑偏，格式不对 | 给 LLM 的指令要像给外包一样详细 |
| 不带 `[]` 包裹 | LLM 返回的不是数组 | 明确说"请用 JSON 数组格式返回" |

---

## 子任务 5.4：Embedding 向量化 — 让机器理解语义（1h）

### 概念引出

```
关键词搜索（你现在 GET /questions?tag=Python）：
  搜索 "内存管理" → 匹配 title 包含"内存管理"的题 → 0 条
  因为题目里写的可能是 "GC原理"、"引用计数"——没有"内存管理"四个字

语义搜索（Embedding）：
  搜索 "内存管理" → 向量化 → [0.123, -0.456, ... 1536维向量]
  和题库里所有题目的向量算余弦相似度
  "GC原理"的向量离"内存管理"最近 → 返回 ✅
  "装饰器"的向量离"内存管理"很远 → 不返回 ✅
```

### 全局流程

```
文本 "Python内存管理"
  ↓
Embedding API (DeepSeek / OpenAI)
  ↓
返回 1536 个浮点数: [0.123, -0.456, 0.789, ...]
  ↓
这就是文本的"语义坐标"
  ↓
"GC原理" 的坐标离这个坐标很近 → 语义相似
"装饰器" 的坐标离这个坐标很远 → 语义无关
```

### 怎么用

```python
response = await client.embeddings.create(
    model="text-embedding-3-small",      # OpenAI 的 embedding 模型
    input="Python 异步编程详解",          # 要向量化的文本
)

vector = response.data[0].embedding      # list[float] — 1536 个浮点数
```

**DeepSeek 注意**：当前 DeepSeek 不提供 Embedding API → 需要用 OpenAI 的 embedding 或通义千问。**练习阶段**：用 `python -c "import numpy; print(numpy.random.randn(1536).tolist())"` 生成随机向量代替，等实际跑通了再切换。

### 架构决策

```
为什么用 1536 维的浮点数？
  这是 OpenAI text-embedding-3-small 的输出维度
  维度越高=编码的语义信息越多，但也越占内存/计算慢
  1536 是工程上的甜点

为什么要对你自己的题库做 Embedding？
  用户搜索时实时向量化问题 → 和题库所有向量比 → 返回最像的
  如果不预计算 → 每次搜索都要实时 Embedding 整个题库 → 慢 + 贵
  预计算 → 题库向量存 FAISS → 搜索时只 Embedding 用户问题 → 快
```

### 易错点

| 坑 | 现象 | 根因 |
|----|------|------|
| Embedding 模型和 LLM 模型搞混 | 用 `deepseek-chat` 调 embedding → 404 | `text-embedding-3-small` 是专用模型，不是聊天模型 |
| 中文向量不准 | 搜"内存"返回"磁盘"但不返回"GC" | 不同 Embedding 模型对中文的语义理解不同 |
| 每请求都 Embedding 整个题库 | 搜索太慢 | 新建/更新题目时 Embedding 存库，搜索时只算查询 |

---

## 子任务 5.5：FAISS 向量索引 + 语义搜索（1h）

### 概念引出

```
FAISS = Facebook AI Similarity Search
      = 给你一堆向量 + 一个查询向量 → 快速找到最像的 K 个

你的使用场景：
  题库 1000 道题 → 每道题一个 1536 维向量 → 全塞进 FAISS 索引
  用户搜索 → Embedding 问题 → FAISS.search(问题向量, k=5) → 返回最像的 5 道题
```

### 全局流程

```
启动时（或新增题目时）：
  QuestionTable 所有行
    ↓
  每行的 title 调用 Embedding API → 1536 维向量
    ↓
  向量 + ID 存入 FAISS 索引

搜索时：
  GET /ai/semantic-search?q=Python内存
    ↓
  Embedding API("Python内存") → 向量
    ↓
  FAISS.search(向量, k=5) → [id1, id2, id3, id4, id5]
    ↓
  用 id 从数据库取完整题目 → 返回
```

### 架构决策

```
为什么用 FAISS 而不是 Chroma / Milvus？
  FAISS：纯内存 / 文件，无服务器，适合入门理解原理
  Chroma：嵌入式向量库，功能更全但多一个依赖
  Milvus：生产级分布式，个人项目杀鸡用牛刀
  → Day 5 用 FAISS 搞懂核心逻辑，面试时能说"FAISS 试过，Chroma 也在看"

FAISS 索引什么时候构建？
  方案 A：启动时从数据库全量重建（简单，小数据量 OK）
  方案 B：新增/更新题目时增量更新（复杂，大数据量必须）
  → Day 5 用方案 A，1000 条以内秒级完成
```

### 怎么用

```python
import faiss
import numpy as np

# ① 创建索引（1536 维，L2 距离）
index = faiss.IndexFlatL2(1536)

# ② 把题库向量塞进去
vectors = np.array([题目1的向量, 题目2的向量, ...], dtype=np.float32)
index.add(vectors)     # 向量和行号一一对应：vectors[0] → 题目1

# ③ 搜索
query_vector = np.array([用户问题的向量], dtype=np.float32)
distances, indices = index.search(query_vector, k=5)
# distances[i] = 距离（越小越像）
# indices[i]   = 题目的行号 → 去数据库取完整题目
```

### 参数速查

| API | 参数 | 含义 |
|-----|------|------|
| `faiss.IndexFlatL2(d)` | `d` | 向量维度（OpenAI=1536） |
| `index.add(vec)` | `vec` | `np.array`，shape=(N, 1536)，dtype=float32 |
| `index.search(q, k)` | `q` | 查询向量，shape=(1, 1536) |
| | `k` | 返回前 K 个最相似的 |
| 返回值 `distances` | | L2 距离，0 = 完全相同 |
| 返回值 `indices` | | 整数数组 → 和 `index.add()` 时的顺序对应 |

### 易错点

| 坑 | 现象 | 根因 |
|----|------|------|
| 维度不匹配 | `RuntimeError` | Embedding 是 1536 维，FAISS 创建了 768 维 |
| dtype 不是 float32 | `RuntimeError` | numpy 默认 float64，FAISS 要 float32 → `np.array(..., dtype=np.float32)` |
| indices 不对应数据库 ID | 查出来牛头不对马嘴 | FAISS 返回的是 add 时的行号，不是数据库 ID → 自己维护映射表 |
| 题库更新后索引没刷新 | 新增题目搜不到 | 每次新增/更新题目 → 重建索引 |

---

## 子任务 5.6：RAG 完整链路 — 检索增强生成（1h）

### 概念引出

```
直接问 LLM："Python 装饰器在 FastAPI 里怎么用？"
 → LLM 给通用答案，可能不准确，可能编造（幻觉）

RAG 之后：
  ① 用户问题 → Embedding → FAISS 检索仓库里相关的 3 道题
  ② 把检索结果拼进 Prompt：
     "参考以下现有题目的风格：{检索结果}\n\n出 3 道类似的题"
  ③ LLM 基于这些真实资料生成 → 风格一致、不编造
```

### 全局流程

```
用户：POST /ai/rag-ask {"question": "出一道Python异步的困难题"}
  │
  ├── ① Embedding("出一道Python异步的困难题") → 向量
  │
  ├── ② FAISS.search(向量, k=3) → 取回 3 道最相关的已有题目
  │
  ├── ③ 拼接 Prompt：
  │      "参考以下题目的风格和难度设置：
  │       题目1: XXX
  │       题目2: XXX
  │       题目3: XXX
  │       
  │       请根据用户要求出新题：出一道Python异步的困难题"
  │
  ├── ④ LLM 流式生成 → SSE 推给前端
  │
  └── ⑤ 返回结果含来源标注："参考了题目 #12、#34、#56"
```

### 架构决策

```
RAG 为什么比直接问更可控？
  ① 防幻觉：LLM 基于你的真实数据回答，不凭空编造
  ② 风格一致：检索到的题目给 LLM 做"范文"→ 新题风格一致
  ③ 可追溯：告诉用户"参考了哪几道题"→ 可解释

什么时候直接问 LLM vs 什么时候 RAG？
  直接问：通用问题（"装饰器是什么"），不需要特定领域数据
  RAG：需要基于你的题库风格出题 / 回答关于你题库内容的问题
```

---

## 文件结构（Day 5 新增）

```
interview-agent/
├── routers/
│   └── ai.py                     # POST /ai/generate + GET /ai/semantic-search + POST /ai/rag-ask
├── services/
│   ├── llm_client.py             # AsyncOpenAI 封装（单例）
│   └── embedding_service.py      # Embedding 调用 + FAISS 索引管理
├── prompts/
│   └── templates.py              # Prompt 模板常量
├── schemas/
│   └── ai.py                     # GenerateRequest / GenerateResponse / RagRequest
└── .env                          # 加 DEEPSEEK_API_KEY + DEEPSEEK_BASE_URL
```

---

## 今天执行顺序

```
5.1 AsyncOpenAI 客户端 (1.5h)：写一个小脚本调通 LLM → 拿到第一个 AI 回复
5.2 流式 SSE (1h)：把 stream=True → 看字一个个蹦出来
5.3 AI 出题 (1.5h)：写 Prompt → 调 LLM → 解析 JSON → 流式返回
5.4 Embedding (1h)：理解向量 → 调 API → 返回 1536 个数字
5.5 FAISS (1h)：建索引 → 搜索 → 验证语义相关性
5.6 RAG (1h)：把 5.4+5.5 串起来 → 检索+生成
```

## ✅ Day 5 验收标准

- [ ] `AsyncOpenAI` 调通 DeepSeek，拿到第一个 LLM 回复
- [ ] 流式调用跑通，终端逐字打印
- [ ] `POST /ai/generate` 流式返回 3 道 JSON 格式题目
- [ ] 生成的题目用 Swagger 看 SSE 实时输出
- [ ] FAISS 索引构建成功，语义搜索"内存管理"能找到"GC原理"
- [ ] `POST /ai/rag-ask` 检索已有题目的风格生成新题
- [ ] 能口述：RAG 的 R-A-G 三步分别做了什么
- [ ] 能口述：`content` 和 `tool_calls` 为什么不可能同时出现
- [ ] git commit: `V5: AI generation + semantic search + RAG pipeline`
