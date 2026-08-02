# 模拟面试清单 — 10 道核心技术题

> 所有回答按统一格式：**场景 → 约束 → 决策 → 后果**，每题指向具体代码。

---

## Q1：为什么 FastAPI 而不是 Django？

**指代码：** [stream_service.py:26-30](services/stream_service.py#L26) — StreamingResponse + SSE

**口述：**

我的项目需要 SSE 流式输出 LLM 回复，用户发一个问题，AI 一个字一个字吐回来。Django 的 async 支持到 4.x 才可用，视图层和 ORM 仍是同步优先，写流式响应得手动拼 `StreamingHttpResponse`，跟 async generator 配合不自然。选了 FastAPI——底层 Starlette + ASGI，原生 `async def` 端点，`StreamingResponse` 包一个 async generator 就完事，三行代码搞定。代价是生态比 Django 小，没有 Admin 这种开箱即用的后台，但我的项目不需要 Admin，需要的是流式和自动 Swagger。

---

## Q2：`async def` vs `def`？什么场景用哪个？

**指代码：** [dependencies.py:14-15](dependencies.py#L14) — `async def get_db()`；[auth_service.py](services/auth_service.py) — bcrypt（同步 `def`）

**口述：**

有 I/O wait 就用 `async def`——不等结果时可以处理别的请求。纯计算或不支持 async 的库用 `def`。我的项目所有端点都是 `async def`，因为每个端点都要 await 数据库或 Redis。唯一的 `def` 是密码哈希 bcrypt 调用——它是 CPU 密集计算，不是异步库，FastAPI 自动把它扔进线程池不阻塞事件循环。判断标准就一条：等别人（网络/磁盘/数据库）→ async；自己算（CPU）→ def。

---

## Q3：数据库 session 怎么管理？

**指代码：** [dependencies.py:14-20](dependencies.py#L14) — `get_db` + `get_storage` 依赖链

**口述：**

用 FastAPI 的 `Depends` + `yield` 管理 session 生命周期。`get_db` 里 `async with` 打开连接然后 `yield` 出去——`yield` 不是 return，它把值交给端点后还能回来：请求结束自动回到 yield 下一行，`async with` 自动关连接并归还到连接池。外面包了一层 `get_storage` 把 session 转成 Repository 对象。每个请求一个短生命周期 session，用完即弃不共享状态，这是 Web 框架的标准做法。

---

## Q4：为什么 PostgreSQL 而不是 MySQL？

**指代码：** [models/question_orm.py](models/question_orm.py) — `tags = Column(JSONB)`；[sqlalchemy_repo.py:53](repositories/sqlalchemy_repo.py#L53) — `tags.contains()`

**口述：**

因为 tags 是动态数组。PostgreSQL 的 JSONB 类型原生理解 JSON 结构，`tags.contains("Python")` 翻译成 `tags @> '"Python"'`——按数组元素精确匹配，不会被"基础设施"这种包含"基础"二字的不相关内容误命中。MySQL 的 JSON 支持是后来补的，索引和异步驱动都比不过。再加上 asyncpg 是 SQLAlchemy 2.0 官方推荐的异步驱动，性能比 aiomysql 好很多。

---

## Q5：JWT 认证流程从头到尾

**指代码：** [routers/auth.py](routers/auth.py) — 注册/登录/刷新；[dependencies.py:26-41](dependencies.py#L26) — `get_current_user`

**口述：**

实现了双 token 认证。注册时 bcrypt 哈希密码存库，不存明文。登录时校验密码后签发两个 JWT——access 短期（30min）用于业务请求，refresh 长期（7 天）用于续命。拦截器是 `get_current_user`：`HTTPBearer` 从请求头取出 token，decode 拿到 username，查库确认用户还存在，任何一步失败返回 401。access 过期后客户端拿 refresh 走 `/auth/refresh` 换新 token，不用重新输密码。access 和 refresh 分开是因为 access 暴露在网络里频率高，短过期限制了泄露窗口。

---

## Q6：Redis 做了什么？为什么 60s TTL？

**指代码：** [routers/questions.py:38-56](routers/questions.py#L38)；[cache_service.py](services/cache_service.py)

**口述：**

随机抽题每次要扫全表再 random.sample，高并发下数据库扛不住。加了一层 Redis——按 tag 做 key，第一次查完塞 Redis 设 60s TTL，后续同样 tag 的请求直接走缓存不查库。60 秒是权衡：题库更新频率低，1 分钟延迟无感，但 300 秒的话新增题目用户半天看不到。命中缓存时 0 次数据库查询，没命中才走 PostgreSQL。

---

## Q7：RAG 的 R-A-G 三步

**指代码：** [routers/ai.py:30-58](routers/ai.py#L30) — 完整链路；[embedding_service.py:55-68](services/embedding_service.py#L55) — search；[stream_service.py:5-24](services/stream_service.py#L5) — generate_stream

**口述：**

R = Retrieval：用户问题通过 Embedding 转成向量，并行检索两个 FAISS 索引——知识库文档提供知识点，题库提供格式和深度参考。A = Augmented：两路检索结果缝进 prompt。G = Generation：增强后的 prompt 发给 DeepSeek，stream=True 逐字推 SSE 给前端。为什么两路检索？单靠文档 → LLM 知道知识但不知道题目格式。单靠题库 → 知道格式但没有知识可考。两路一起才完整。

---

## Q8：Embedding 是什么？为什么 N 维？

**指代码：** [embedding_service.py:17-28](services/embedding_service.py#L17) — `add_index`；[embedding_service.py:67-68](services/embedding_service.py#L67) — FAISS search

**口述：**

Embedding 是文字的 GPS 坐标。训练好的模型把任意文字映射到 N 维空间的一个点，"Python 的 GIL"和"Python 全局解释器锁"文字完全不同但向量几乎一样——因为语义相同。维度数是模型训练时固定的，我用的 BGE 模型是 1024 维。每一维代表模型学到的某个语义特征，人读不懂但数学好用。搜索就是用户问题转向量，FAISS 在 1024 维空间里找 L2 距离最近的 K 个——几何距离越小，语义越相关。

---

## Q9：SSE vs WebSocket？为什么选 SSE？

**指代码：** [stream_service.py:26-30](services/stream_service.py#L26) — `StreamingResponse` + `text/event-stream`

**口述：**

LLM 流式输出是服务器向客户端的单向推送，用户发了 prompt 就等着收，不需要往回发。SSE 基于 HTTP 协议，协议更简单，`StreamingResponse` 一行实现，浏览器原生支持断线重连。WebSocket 是双向全双工，需要协议升级握手，代码要多写连接管理。单向推送选 SSE，双向通信才要 WebSocket。另外 SSE 只能传 UTF-8 文本不能传二进制，但我的场景就是 JSON 文本，完全够用。

---

## Q10：你的代码怎么分层？换存储改多少？

**指代码：** 调用链 [dependencies.py](dependencies.py) → [routers/questions.py](routers/questions.py) → [repositories/sqlalchemy_repo.py](repositories/sqlalchemy_repo.py)

**口述：**

分了四层：Router 接请求 + Schema 校验，Service 做业务逻辑，Repository 做数据访问，ORM 映射数据库。层之间通过 `Depends` 依赖注入串联——端点依赖 `get_storage` 接口，`dependencies.py` 负责注入具体实现。Router 只知道 storage 有 `add()` 方法，不知道底层是 PostgreSQL 还是 MongoDB。换数据库只需改 Repository 实现和依赖注入那一行，Router 和 Service 完全不动。这就是分层的核心价值——改动范围被控制在最底层。
