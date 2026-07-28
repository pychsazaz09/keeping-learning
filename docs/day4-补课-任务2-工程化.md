# 补课任务二：工程化补全 — Field 校验 + 分页 + 异常处理 + 事务（1.5h）

> **为什么补这个**：Day 1-4 代码能跑，但不够"工程化"——缺少输入校验、分页、统一异常处理、事务管理。这四件事是生产环境必做的。
>
> **学习方式**：直接在 interview-agent 项目里改代码，每个子任务改完跑 `/docs` 验证。

---

## 子任务 2.1：Pydantic `Field` 校验（25min）

### 概念引出

你现在写的：

```python
class QuestionCreate(BaseModel):
    title: str          # 只规定了类型——但"空字符串"也能通过！
    difficulty: str     # 没限制值——"super_easy"也能通过！
```

Pydantic 的 `Field` 可以加**约束**——长度、正则、数值范围。不写代码实现校验逻辑，只声明规则。

### 架构决策

```
数据校验放哪一层？
  ❌ Router 层手写 if len(title) < 2 → 业务逻辑混在 HTTP 层
  ✅ Pydantic 层 Field 声明 → 请求进来时自动校验，Router 里全是纯业务
  ❌ 数据库层 CHECK 约束 → 太晚了，而且报错信息不友好

最佳实践：Pydantic 做输入校验 + 数据库做最后兜底
```

### 动手任务

修改 [schemas/question.py](../schemas/question.py) 的 `QuestionCreate`：

1. `title`：最小长度 2，最大 500
2. `difficulty`：只能是 `easy` / `medium` / `hard`（用正则 `pattern`）
3. `tags`：默认值 `""`，最大长度 500
4. `answer`：默认值 `""`，最大长度 5000

再到 [schemas/user.py](../schemas/user.py) 的 `UserCreate`：

1. `username`：最小长度 2，最大 30
2. `password`：最小长度 6，最大 128

> **验证**：启动服务 → 访问 `/docs` → 看 Swagger 里字段多了什么 → 故意传一个空 title → 看 422 返回的错误信息长什么样。

### Field 常用参数速查

| 参数 | 适用于 | 含义 | 例子 | 校验失败返回 |
|------|--------|------|------|------------|
| `min_length` | `str` | 最少字符数 | `min_length=2` | 422: "ensure at least 2 characters" |
| `max_length` | `str` | 最多字符数 | `max_length=500` | 422: "ensure at most 500 characters" |
| `pattern` | `str` | 正则匹配 | `pattern=r"^(easy\|medium\|hard)$"` | 422: "string does not match regex" |
| `gt` | `int/float` | 大于 | `gt=0` | 422: "ensure > 0" |
| `ge` | `int/float` | 大于等于 | `ge=1` | 422: "ensure >= 1" |
| `lt` / `le` | `int/float` | 小于 / 小于等于 | `lt=150` | 同上 |
| `default` | 任意 | 不传时用的默认值 | `default="medium"` | — |
| `description` | 任意 | Swagger 文档说明 | `description="题目标题"` | 不影响校验，只影响文档 |

### 易错点

| 坑 | 现象 | 原因 |
|----|------|------|
| `Field` 用在普通函数参数 | 不校验 | Field 只在 Pydantic `BaseModel` 里生效 |
| `Field("medium")` 而非 `Field(default="medium")` | 也行！ | 第一个位置参数就是 `default`，所以 `Field("medium")` 等价 `Field(default="medium")` |
| 正则忘了 `^` 和 `$` | `pattern=r"easy\|medium\|hard"` 匹配 `"super_easy"`（包含 easy） | 必须用 `^...$` 锚定首尾：`r"^(easy\|medium\|hard)$"` |

---

## 子任务 2.2：分页查询（30min）

### 概念引出

现在 `GET /questions` 一次返回所有数据——100 条、1000 条全返回。生产环境必须分页。

```
GET /questions?page=1&page_size=10
     ↓
SELECT * FROM question LIMIT 10 OFFSET 0    ← 第 1 页，跳过 0 条
SELECT * FROM question LIMIT 10 OFFSET 10   ← 第 2 页，跳过 10 条
```

### 架构决策

```
分页信息放哪？
  请求：Query 参数（page、page_size）
  响应：body 里返回 items + total + page + total_pages

返回结构为什么不是 {"questions": [...], "total": 100}？
  前端需要知道：当前第几页、总页数（用来渲染分页组件）
  所以返回：items + total + page + page_size + total_pages

为什么 page 从 1 开始而不是 0？
  用户心智模型——"第 1 页"。内部 offset = (page - 1) * page_size 转换即可。
```

### 动手任务

**三步走**——每层只改该层的事：

**第一步：Repository 层加两个方法**

在 [repositories/sqlalchemy_repo.py](../repositories/sqlalchemy_repo.py) 里：

1. 改造 `list_all`——增加 `limit` 和 `offset` 参数，SQL 查询加 `.limit(limit).offset(offset)`
2. 新增 `count` 方法——接收可选的 `tag` 过滤，返回符合条件的总记录数

```sql
-- list_all 应该生成：
SELECT * FROM question WHERE tags ILIKE '%tag%' LIMIT 10 OFFSET 0

-- count 应该生成：
SELECT COUNT(*) FROM question WHERE tags ILIKE '%tag%'
```

> **检索任务**：SQLAlchemy 的 `func.count()` 怎么用？和 `SELECT COUNT(*)` 是什么关系？

**第二步：Router 层加 Query 参数**

在 [routers/questions.py](../routers/questions.py) 的 `list_questions` 里：

1. 加 `page: int = Query(1, ge=1)` 和 `page_size: int = Query(10, ge=1, le=100)`
2. 计算 `offset = (page - 1) * page_size`
3. 调 `storage.list_all(tag=tag, limit=page_size, offset=offset)` 和 `storage.count(tag=tag)`
4. 返回结构改为 `{"items": ..., "total": ..., "page": ..., "page_size": ..., "total_pages": ...}`

> **关键**：`total_pages` 计算——`(total + page_size - 1) // page_size`（整数向上取整）

**第三步：Swagger 验证**

1. 访问 `/docs` → 看 `GET /questions` 的参数面板多了什么
2. 测试 `?page=1&page_size=2` → 应该只返回 2 条 + total 是全部数量
3. 测试 `?page=99999` → 返回空列表，total 不变

### `Query` 参数速查

| 参数 | 含义 |
|------|------|
| 第一个位置参数 `1` | 默认值 |
| `ge=1` | greater or equal → ≥ 1（防止传 page=0）|
| `le=100` | less or equal → ≤ 100（防止一次查 10000 条）|
| `description="..."` | Swagger 文档里显示的说明文字 |

---

## 子任务 2.3：全局异常处理器（20min）

### 概念引出

你现在每个 Router 里都有 `try/except`——重复、容易漏。Java 有 `@ControllerAdvice`，FastAPI 有 `@app.exception_handler`。

```
之前：每个路由 try/except → 重复 + 容易漏
之后：定义一个 handler → 所有没被捕获的异常统一处理
```

### 架构决策

```
全局异常处理器的层级：
  Pydantic 校验失败 → FastAPI 自动 422（不需要你写）
  HTTPException → FastAPI 自动转 JSON（不需要你写）
  你代码里 raise 的异常 → ❌ 没人兜底 → 500 Internal Server Error（空白页）
  
  全局异常处理器补的就是这个兜底——把未处理异常变成友好的 JSON。
```

### 动手任务

在 [main.py](../main.py) 里加两个异常处理器：

**① 兜底异常处理器**（任何没被捕获的 Exception）

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    ...
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
```

> 注意区分：`exc` 是异常实例，`request` 是 FastAPI 的 `Request` 对象。

**② 404 处理器**（路径不存在时返回友好 JSON）

```python
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    ...
    return JSONResponse(status_code=404, content={"detail": f"路径不存在: {request.url.path}"})
```

### 验证

1. 故意访问 `GET /nonexistent` → 应该返回 404 JSON，格式 `{"detail": "路径不存在: /nonexistent"}`
2. 在某个路由里 `raise ValueError("测试")` → 应该返回 500 JSON，不会看到空白页

### 和 Java 对照

| Java Spring | FastAPI |
|-------------|---------|
| `@ControllerAdvice` | `@app.exception_handler(Exception)` |
| `@ExceptionHandler(MyException.class)` | `@app.exception_handler(MyException)` |
| `ResponseEntity.status(500).body(...)` | `JSONResponse(status_code=500, content={...})` |

---

## 子任务 2.4：事务管理（15min）

### 概念引出

你现在每个操作都是单条 SQL——`db.add(user)` → `commit()`。够用，但遇到"两条 INSERT 必须同时成功"就麻烦了。

```
事务 = 一组操作要么全部成功，要么全部回滚
  成功：所有操作都执行 → commit
  失败：任何一个报错 → rollback（已执行的撤销）
```

### 什么时候需要事务

| 场景 | 例子 |
|------|------|
| 单条 SQL | `POST /questions` 创建一道题 | ❌ 不需要显式事务（默认每条 SQL 自动提交） |
| 多条 SQL | 注册用户 + 自动创建默认数据 | ✅ 必须事务（两条同时成功或同时失败） |

### 动手任务

在 [services/auth_service.py](../services/auth_service.py) 里加一个新函数：

```python
async def register_with_default_data(db: AsyncSession, data: UserCreate):
    """注册用户，同时创建一条默认题目——两条必须一起成功"""
    async with db.begin():       # ← 开启事务
        user = ...
        db.add(user)
        # 此时还没 commit！失败自动回滚
        
        default_q = ...
        db.add(default_q)
        # 事务块结束 → 自动 commit（两条一起落盘）
    # with 块外 → 事务已提交
```

### 关键理解

```
db.begin() vs db.commit()

begin()  → 开启一个事务边界
  add()  → 标记"这个对象要插入"
  add()  → 标记"这个也要插入"
  flush()→ 把 SQL 发给 PG（但不提交，其他连接看不到）
  commit() → with 块结束时自动调
  或 rollback() → 异常时自动调

commit() → 单独提交（单条 SQL 时够用）
```

> **检索任务**：`db.begin()` 和 `db.commit()` 的区别？`flush()` 和 `commit()` 的区别？

### 易错点

| 坑 | 现象 |
|----|------|
| `async with db.begin():` 然后在外面还调 `commit()` | 事务已提交，再 commit 报错 |
| 事务里 `return` 了 | 事务还没 commit！`return` 不在 with 块里 |
| 忘记 `await session.refresh(obj)` | 返回的对象缺少数据库生成的字段（如 `id`、`created_at`） |

---

## ✅ 任务二验收

- [ ] `QuestionCreate` 传空 title → 422 + 友好错误信息
- [ ] `difficulty` 传 `"super_easy"` → 422（正则拦截）
- [ ] `GET /questions?page=1&page_size=10` 返回分页结构（items + total + page + total_pages）
- [ ] `GET /questions?page=99999` 返回空列表不报错
- [ ] 访问不存在的路径 → 404 JSON（不是 HTML 空白页）
- [ ] 路由里 `raise ValueError` → 500 JSON（兜底异常处理器生效）
- [ ] 能口述：`Field` 校验和手写 `if` 校验的区别、为什么要分页返回 `total_pages`、事务 `begin()` 和 `commit()` 的区别
- [ ] git commit: `补课二：Field 校验 + 分页查询 + 全局异常处理 + 事务管理`
