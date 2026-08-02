# Day 7：缓冲日 — 深挖 Agent 地基（~6h）

> Day 1-6 把项目从 CLI 推到了 RAG。Day 7 不堆新功能，而是深挖三个面试高频 + 一个 Agent 核心能力。每个主题都从"你现在缺什么"出发，落到"能写能讲"。

---

## 子任务 7.1：异步编程深度 — 事件循环 + AsyncExitStack（1.5h）

### 背景

你已经会写 `async def` + `await`。但面试官会问三个更深的问题：

> "事件循环到底是什么？怎么调度协程的？"
> "`gather()` 和 `create_task()` 有什么区别？"
> "十个协程同时跑，出错了几个，剩下的怎么办？"

这三个问题你的项目代码里都有线索，但你还没系统讲清。

### 源头

| 来源 | 具体内容 |
|------|---------|
| **30-day-plan Day 4** | `gather()` 并发执行多个协程、`create_task()` 创建后台任务、事件循环是单线程任务调度器 |
| **30-day-plan Day 5** | `AsyncExitStack` — Agent 开发必备，管理多个异步连接 |
| **7-day-plan Day 7** | 为什么 CPU 密集计算不能放协程里 |

### 知识点

```
事件循环（Event Loop）:
├── 是单线程的任务调度器，不是线程池
├── await = 挂起点，把控制权还给循环
├── 循环挑一个"ready"的协程继续跑
└── CPU 密集运算 → 不让出控制权 → 循环被卡死

gather() vs create_task():
├── gather(*coros) → 等所有完成，有错默认抛（可配 return_exceptions=True）
├── create_task() → 不等待，返回 Task 对象，后台跑
└── 典型误用：create_task 后忘了 await → 任务可能没跑完就被事件循环关闭

AsyncExitStack（30-day-plan Day 5 重点）:
├── 场景：一个 Agent 同时连 LLM + 数据库 + Redis + MCP Server
├── async with AsyncExitStack() as stack:
│     llm = await stack.enter_async_context(AsyncOpenAI(...))
│     db = await stack.enter_async_context(AsyncSessionLocal())
│     redis = await stack.enter_async_context(Redis(...))
├── 退出时 LIFO 顺序自动关闭：redis → db → llm
└── 面试价值：手写 MCP 多连接管理时这是标准姿势
```

### 练习

写一个 `practice/async_deep.py`：

```python
import asyncio
from contextlib import AsyncExitStack

# ① gather() 并发 + 异常处理
async def fetch(i: int):
    await asyncio.sleep(1)
    if i == 3:
        raise ValueError(f"第{i}个炸了")
    return f"结果{i}"

async def demo_gather():
    results = await asyncio.gather(*[fetch(i) for i in range(5)],
                                    return_exceptions=True)
    # results: ["结果0", "结果1", "结果2", ValueError(...), "结果4"]
    # 关键：其他 4 个正常完成，不像 Java CompletableFuture.allOf 那样一个炸全炸

# ② create_task() → Task 对象
async def demo_create_task():
    task = asyncio.create_task(fetch(1))   # 不等待，立即返回
    # task.cancel()                        # 可以取消
    # task.done()                          # 查状态
    result = await task                    # 这里才真正等结果

# ③ AsyncExitStack 管理 3 个模拟资源
class FakeConnection:
    def __init__(self, name): self.name = name
    async def __aenter__(self):
        print(f"[{self.name}] 连接建立")
        return self
    async def __aexit__(self, *args):
        print(f"[{self.name}] 连接关闭 (LIFO)")
        return False

async def demo_exit_stack():
    async with AsyncExitStack() as stack:
        conn1 = await stack.enter_async_context(FakeConnection("LLM"))
        conn2 = await stack.enter_async_context(FakeConnection("Redis"))
        conn3 = await stack.enter_async_context(FakeConnection("PostgreSQL"))
        # do work...
    # 退出顺序：PostgreSQL → Redis → LLM
```

### 验收

- `gather(return_exceptions=True)` 跑了 5 个协程，1 个炸了其余 4 个正常
- `create_task()` 拿到 Task 对象，能 `cancel()` 和 `done()`
- AsyncExitStack 退出时按 LIFO 打印关闭顺序

### 易错点

| 坑 | 表现 | 原因 |
|----|------|------|
| `create_task()` 后没 `await` | 任务没跑完就被关 | Task 是后台任务，你不等它就不保证完成 |
| `gather()` 不加 `return_exceptions=True` | 一个炸全炸 | 默认异常传播 |
| `asyncio.run()` 里调 `asyncio.run()` | RuntimeError | 事件循环不能嵌套 |

---

## 子任务 7.2：Tool Calling 手动实现（2h）

### 背景

Day 5 你用了 `AsyncOpenAI` 调 LLM，但只用了 `system` + `user` 两种角色。**Tool Calling 是 Agent 的灵魂**——AI 不是只会聊天，它会主动调你的函数。

30-day-plan Day 16 专门一天讲这个。7-day-plan Day 7 列为第一优先级深挖主题。

### 概念引出：Tool Calling 做了什么

```
用户："北京今天天气怎么样？"
  ↓
第一次 LLM 请求（带 tools 定义）→ LLM 不回答文本，返回 tool_calls:
  {
    "name": "get_weather",
    "arguments": {"city": "北京"}
  }
  ↓
你的代码执行 get_weather("北京") → "北京 25°C 晴"
  ↓
结果回填为 tool 角色消息 → 第二次 LLM 请求
  ↓
LLM 基于真实数据生成回答："北京今天 25°C，晴天，适合出行。"
```

### 核心规则（面试必问）

**单次响应中 `content` 和 `tool_calls` 不会同时出现。** AI 要么说话（content），要么调工具（tool_calls），二选一。

### 四种消息角色完整版

| role | 谁说的 | 什么时候用 |
|------|--------|-----------|
| `system` | 你写的 | 设定 AI 人设 |
| `user` | 用户 | 每次用户说话 |
| `assistant` | AI | AI 的回复（可能含 `tool_calls`） |
| `tool` | 你的代码 | 函数执行结果回填，必须带 `tool_call_id` |

### 实践：手写完整循环

`practice/tool_calling_bare.py`：

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="ollama",  # 或者你本地的任何模型
    base_url="http://localhost:11434/v1",
)

# ① 定义工具（按 OpenAI 标准格式）
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"}
            },
            "required": ["city"]
        }
    }
}]

# ② 本地函数 — Tool Calling 调的就是这个
def get_weather(city: str) -> str:
    # 实际项目里这里是调 API
    fake_data = {"北京": "25°C 晴", "上海": "28°C 多云"}
    return fake_data.get(city, "未知城市")

# ③ 完整循环
async def tool_calling_loop(user_input: str):
    messages = [{"role": "user", "content": user_input}]

    # 第一次请求
    response = await client.chat.completions.create(
        model="deepseek-chat",  # 或 qwen2.5 等支持 tool calling 的模型
        messages=messages,
        tools=tools,
    )

    msg = response.choices[0].message

    # 关键判断：AI 要调工具还是直接说话？
    if msg.tool_calls:
        # 把 AI 的 tool_calls 请求加入消息历史
        messages.append(msg.model_dump())

        for tc in msg.tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)

            # 执行本地函数
            result = get_weather(**func_args)

            # 结果回填 — 注意 role 是 "tool"，必须带 tool_call_id
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # 第二次请求 — AI 拿到数据后生成自然语言回答
        final = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
        )
        return final.choices[0].message.content

    else:
        # AI 不需要调工具，直接回答
        return msg.content
```

### 面试追问：如果 AI 要同时调两个工具呢

`msg.tool_calls` 是一个列表 — 可能同时包含 `get_weather` 和 `search_web`。遍历执行，把所有结果填回去，再发一次请求。

### 验收

- [ ] 输入"北京天气" → AI 调 get_weather → 返回含温度的自然语言回答
- [ ] 输入"你好" → AI 不调工具，直接返回问候
- [ ] 口述 `content` 和 `tool_calls` 为什么不能同时出现

### 易错点

| 坑 | 表现 | 根本原因 |
|----|------|---------|
| tool 消息没带 `tool_call_id` | API 400 | LLM 用它匹配"哪个调用对应哪个结果" |
| `msg.model_dump()` 不是 `.dict()` | AttributeError | OpenAI SDK v1.x 用 model_dump |
| Ollama 小模型不支持 tool calling | 返回空 | `qwen2.5:7b` 或 `llama3.1:8b` 才支持 |

---

## 子任务 7.3：流式 Tool Calls 分片拼接（1.5h）

### 背景

7.2 是非流式 — 等 AI 返回完整的 `tool_calls` JSON 再执行函数。生产环境用 `stream=True`，tool_calls 的 JSON **是一块一块来的**——需要实时拼接。

30-day-plan Day 17 专门一天讲这个，面试高频。

### 为什么分片

```
流式模式下 LLM 逐 token 生成：
  chunk 1: {"name": "get_we           ← 半个字符串
  chunk 2: ather", "argumen          ← 继续
  chunk 3: ts": {"city": "          ← 继续
  chunk 4: 北京"}}                    ← 完整了

你的代码要等 4 个 chunk 都到了，拼起来才是合法 JSON
```

更麻烦的是：**工具按 index 区分，index 大的 chunk 可能先到。**

### 实践

`practice/stream_tool_calls.py`：

```python
import json

async def stream_with_tools(user_input: str):
    messages = [{"role": "user", "content": user_input}]

    stream = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=True,
    )

    tool_calls_acc = []  # 按 index 存储的拼接缓冲区

    async for chunk in stream:
        delta = chunk.choices[0].delta

        # ① 正常文本流 — 直接 yield（SSE 返回）
        if delta.content:
            yield f"data: {json.dumps({'chunk': delta.content})}\n\n"

        # ② tool_calls 流 — 分片拼接
        if delta.tool_calls:
            for tc in delta.tool_calls:
                # 扩容 — 防止乱序 index
                while len(tool_calls_acc) <= tc.index:
                    tool_calls_acc.append({
                        "id": "", "name": "", "arguments": ""
                    })

                acc = tool_calls_acc[tc.index]
                if tc.id:
                    acc["id"] += tc.id           # id 也可能分片！
                if tc.function and tc.function.name:
                    acc["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    acc["arguments"] += tc.function.arguments  # 逐片拼 JSON

    # 流结束后，拼接完成
    for tc in tool_calls_acc:
        tc["arguments_parsed"] = json.loads(tc["arguments"])
        print(f"工具: {tc['name']}, 参数: {tc['arguments_parsed']}")

    yield "data: [DONE]\n\n"
```

### 关键点

| 概念 | 为什么 |
|------|--------|
| `while len(acc) <= tc.index` 扩容 | 网络乱序可能先收到 `index=2` 再收到 `index=0` |
| `id` 也要拼接 | 长的 tool_call_id 可能跨多个 chunk |
| `arguments` 最后才 `json.loads` | 流结束前 JSON 不完整 → 解析必炸 |

### 验收

- [ ] 流式模式下 tool_calls 分片被正确拼接成完整 JSON
- [ ] 能口述为什么 `index` 可能乱序（网络 TCP 不保证顺序 + LLM 内部并行生成）

---

## 子任务 7.4：RAG 进阶（1h）

### 背景

Day 5 的 RAG 是**最简版**：`text.split("##")` 切片 + L2 距离暴搜。面试官问"如果题库有 10 万条怎么优化"时，你需要知道这两点。

### 7.4.1 切片策略对比

| 策略 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **固定长度** | 每 500 字一刀，100 字重叠 | 实现简单 | 可能在句子中间切开 |
| **语义切片** | 按 `##` 标题/段落边界切 | 每个 chunk 语义完整 | 标题短的 chunk 信息太少 |
| **递归切片** | 先按大标题，不够再按小标题切 | 层级清晰 | 复杂 |

**你 Day 5 用的是语义切片（`text.split("##")`）。** 面试时可以说："根据文档结构选择策略——面试题知识库按章节组织，语义切片就够了。"

### 7.4.2 MMR 检索 vs 纯相似度

```
纯相似度（L2 距离取 Top K）：
  搜"装饰器" → 返回 3 个结果全是"装饰器概述"的不同段落
  → 内容重复，浪费上下文窗口

MMR（Maximum Marginal Relevance）：
  搜"装饰器" → 第 1 个取最相似的
  → 第 2 个取"既相似又和第 1 个不重复的"
  → 第 3 个取"既相似又和前 2 个都不重复的"
  → 三个结果覆盖不同角度
```

**目前不需要实现**——面试能说出 MMR 的思路和适用场景就够了。代码是 FAISS 的一行参数：

```python
# faiss 不原生支持 MMR → 要用 sklearn 或 numpy 手写
# 面试时可说"理解了原理后，实现是选型问题不是技术难点"
```

### 验收

- [ ] 能口述 RAG 查询量 10 万 → 百万级时的优化方向（IVF 索引、量化、混合搜索）
- [ ] 能口述 MMR 为什么能解决"结果重复"的问题

---

## ✅ Day 7 验收标准

- [ ] `practice/async_deep.py` — gather + create_task + AsyncExitStack 全跑通
- [ ] `practice/tool_calling_bare.py` — AI 成功调 get_weather 并返回结果
- [ ] `practice/stream_tool_calls.py` — 流式 tool_calls 分片正确拼接
- [ ] 口述 Tool Calling 完整循环（第一次请求 → tool_calls → 执行函数 → 回填 → 第二次请求）
- [ ] 口述 `content` 和 `tool_calls` 二选一规则 + 流式分片为什么需要 index
- [ ] 口述 AsyncExitStack 的 LIFO 关闭顺序 + Agent 场景应用
- [ ] git commit: `V7: async deep dive + tool calling + stream merge + RAG advanced`

---

## 时间分配

```
7.1 异步深度       1.5h
7.2 Tool Calling   2h      ← 最核心
7.3 流式分片        1.5h    ← 面试高频
7.4 RAG 进阶       1h      ← 概念为主
```

## 30-day-plan 对照

| 30 天计划 | 今天覆盖 |
|----------|---------|
| Day 4 — 异步编程基础（gather/create_task） | ✅ 7.1 |
| Day 5 — AsyncExitStack | ✅ 7.1 |
| Day 16 — Tool Calling 手写 | ✅ 7.2 |
| Day 17 — 流式 tool_calls 分片拼接 | ✅ 7.3 |
| Day 18 — 多模型适配器 | ⬜ 暂缓（只有 DeepSeek + Ollama） |
| Day 19 — Prompt Engineering | ⬜ Day 5 已做基础版 |

## Day 8+ 预告（如果继续）

- Day 8：前端页面（HTML + JS 调用 SSE 接口）
- Day 9：pytest + httpx.AsyncClient 单元测试
- Day 10：部署 + 发技术文章
