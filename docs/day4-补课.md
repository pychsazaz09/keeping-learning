# Day 4 补课：四天遗漏知识点全面补齐

> **原则**：每个知识点走完"概念地图 → 架构决策 → 怎么用 → 参数 → 易错点"完整闭环。
> 今天不赶进度，只打地基。

---

## 补课一：Python 核心概念（装饰器 + 生成器 + 陷阱）

> **为什么先补这个**：装饰器和生成器是 Python 两大核心特性，FastAPI 到处用 `@`，Depends 的 `yield` 本质是生成器。不理解它们 = 不理解框架为什么这样设计。

---

### 1.1 装饰器 `@xxx`

#### 概念地图

```
装饰器 = 给函数套一层壳，不改原函数代码，增加前后逻辑

@timer
def my_func():
    pass

等价于：
my_func = timer(my_func)   ← 装饰器本质：高阶函数（函数接收函数，返回函数）
```

#### 用在什么场景

| 场景 | 实际例子 | 你项目里的对应 |
|------|---------|--------------|
| 计时 | `@timer` 记录函数耗时 | Loguru 中间件做的事（但装饰器更通用） |
| 重试 | `@retry(max=3)` 失败后自动重试 | 无（LLM 调用时需要） |
| 缓存 | `@cache(ttl=60)` 缓存返回值 | Redis 缓存（装饰器版更优雅） |
| 路由注册 | `@app.get("/")` 注册 HTTP 端点 | 你的 questions.py 每天都在用！ |
| 鉴权 | `@login_required` | 你的 `Depends(get_current_user)` |

#### 架构决策

```
为什么用装饰器而不是在函数内部加代码？
  → 横切关注点（计时、重试、缓存、鉴权）不属于业务逻辑
  → 装饰器让这些"附加功能"独立于业务函数，可复用、可组合
  → 和 Java AOP 一样的设计思想

什么时候用装饰器 vs 什么时候用中间件？
  装饰器：给单个函数加能力（缓存某接口、重试某调用）
  中间件：给所有请求加能力（日志、CORS）
```

#### 怎么用：三层递进

```python
# ① 无参装饰器（最简单）
import time
from functools import wraps

def timer(func):
    """计时装饰器：打印函数执行耗时"""
    @wraps(func)          # ← 保留原函数的 __name__、__doc__
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)   # ← 执行原函数
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} 耗时 {elapsed:.3f}s")
        return result
    return wrapper

# 使用
@timer
def slow_task():
    time.sleep(2)

slow_task()  # 输出：slow_task 耗时 2.001s
```

| 参数 | 含义 | 易错 |
|------|------|------|
| `func` | 被装饰的原函数 | 不需要你传，`@timer` 自动传 |
| `*args, **kwargs` | 万能参数接收 | `*args`=位置参数打包为元组, `**kwargs`=关键字参数打包为字典 |
| `@wraps(func)` | 把原函数名和文档字符串复制到 wrapper | 不加 → `slow_task.__name__` 变成 `wrapper` |

```python
# ② 带参装饰器（需要多一层）
def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器：失败后自动重试"""
    def decorator(func):                    # ← 第二层：接收被装饰函数
        @wraps(func)
        async def wrapper(*args, **kwargs):  # ← 第三层：实际执行的函数
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise  # 最后一次还失败 → 真的抛出
                    await asyncio.sleep(delay)
            return None
        return wrapper
    return decorator

# 使用
@retry(max_attempts=3, delay=2.0)    # ← 调用 retry()，返回 decorator
async def call_llm(prompt: str):
    ...
```

**为什么有三层？**

```
@retry(max_attempts=3)   call_llm
       ↓                      ↓
  retry(3) 执行 → 返回 decorator
                      ↓
                @decorator 装饰 call_llm → decorator(call_llm) → 返回 wrapper
```

```python
# ③ 类装饰器（需要维护状态的场景）
class Singleton:
    """单例装饰器"""
    _instances = {}
    
    def __init__(self, cls):
        self._cls = cls
    
    def __call__(self, *args, **kwargs):
        if self._cls not in self._instances:
            self._instances[self._cls] = self._cls(*args, **kwargs)
        return self._instances[self._cls]

@Singleton
class Database:
    def __init__(self):
        print("初始化数据库连接")

db1 = Database()  # 第一次：输出"初始化数据库连接"
db2 = Database()  # 第二次：不输出，直接返回之前的实例
print(db1 is db2)  # True
```

#### 易错点

| 坑 | 现象 | 原因 | 正确做法 |
|----|------|------|---------|
| 忘写 `@wraps(func)` | `slow_task.__name__` 变成 `"wrapper"` | 装饰器返回的是 wrapper，不是原函数 | 必须加 `@wraps(func)` |
| `return wrapper` 忘写 | 装饰后函数变成 None | 装饰器必须返回新函数 | 确认 `return wrapper` |
| 带参装饰器忘了 `()` | `@retry` 而不是 `@retry()` | 不带括号 → `func=3` → 炸 | `@retry()` 或 `@retry(max_attempts=3)` |
| 同步装饰器套异步函数 | `TypeError: coroutine was never awaited` | `wrapper` 里没 `await` | 装饰器里的 wrapper 也要 `async def` |
| 装饰器函数里改了原函数参数 | 被装饰的函数行为变了 | 在 wrapper 里 `args[0] = "xxx"` | 只读不改 |

---

### 1.2 生成器 `yield` / `yield from`

#### 概念地图

```
普通函数：return → 一次性返回全部 → 结束
生成器：  yield → 吐出一个值 → 暂停（下次 next() 从暂停处继续）
```

#### 用在什么场景

| 场景 | 例子 |
|------|------|
| 读大文件 | 逐行 yield，不把整个文件加载到内存 |
| 惰性序列 | `range(1000000)` 不创建 100 万个元素的列表 |
| 资源管理 | FastAPI Depends 的 `yield` — yield 前获取资源，yield 后释放 |
| 流式数据 | 逐 chunk 返回 LLM 生成的内容 |

#### 架构决策

```
什么时候用 yield 而不是 return list？
  数据量大（10万条记录）→ yield（内存 O(1)）
  数据量小（几十条） → return list（更简单）
  
FastAPI 为什么用 yield 管理 session？
  yield 前 = 请求进来，开启数据库会话
  yield    = 会话交给路由函数
  yield 后 = 路由返回后，自动关闭会话
  
  这就是 Python 的 "try-with-resources"——用语言特性实现资源管理，不需要 Java 的 @Transactional
```

#### 怎么用

```python
# ① 基本生成器
def read_large_file(path: str):
    """逐行读大文件，不加载到内存"""
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield line.strip()       # ← yield = 返回这一行，然后暂停

# 使用：for 循环自动驱动生成器
for line in read_large_file("big_file.txt"):
    print(line)  # 每次循环只处理一行，内存里只有一行

# ② yield from — 委托给另一个生成器
def all_questions():
    """从多个文件读题，但调用方不需要知道有几个文件"""
    yield from read_large_file("python.txt")    # ← 先把 python.txt 吐完
    yield from read_large_file("java.txt")      # ← 再吐 java.txt

# ③ FastAPI Depends 的 yield — 资源管理模式
async def get_db():
    session = AsyncSessionLocal()
    try:
        yield session       # ← ① 交出 session → 路由函数用它
    finally:
        await session.close()  # ← ② 路由返回后执行（无论成功还是异常！）
```

#### 易错点

| 坑 | 现象 | 原因 | 正确做法 |
|----|------|------|---------|
| `yield` 后的代码不执行 | 资源没释放 | `for` 循环 `break` 了 | 用 `with` 或 `try/finally` 包裹 yield |
| 把生成器当列表用 | `len(gen)` 报错 | 生成器没有长度 | `list(gen)` 转列表（小心内存） |
| 生成器只能迭代一次 | 第二次遍历为空 | 生成器是消耗品 | 每次需要时重新调用生成器函数 |
| `yield from` 返回值和 `yield` 混用 | 嵌套生成器写不出来 | `yield from gen` = `for x in gen: yield x` 的简写 | 多文件合并用 `yield from` |

---

### 1.3 可变对象默认参数陷阱

#### 概念地图

```python
# ❌ 陷阱
def add_question(title: str, tags: list = []):
    tags.append("面试")
    return tags

add_question("GIL")  # 返回 ['面试']
add_question("装饰器")  # 返回 ['面试', '面试'] ← 两次调用共享同一个 list！

# ✅ 正确
def add_question(title: str, tags: list | None = None):
    if tags is None:
        tags = []
    tags.append("面试")
    return tags
```

#### 为什么

```
Python 函数默认值在定义时创建一次，不是每次调用时创建。
def foo(a=[]):  ← 这个 [] 在 import 这个文件时就创建了，之后每次调用都指向同一个对象

Java 里每次调用方法都是新的：public void foo(List a = new ArrayList())  ← 编译不过
```

#### 什么场景会碰到

```
Pydantic 模型：
class QuestionCreate(BaseModel):
    tags: list[str] = []      # ← Pydantic 会特殊处理，这里是安全的！

普通函数：
def search(keyword: str, filters: list = []):  # ← 陷阱！
```

**Pydantic 安全，普通函数不安全。** 简单规则：默认值只用不可变类型（`None`、`str`、`int`），可变类型在函数体内创建。

---

### 1.4 `@property` / `@staticmethod` / `@classmethod`

#### 概念地图

```python
class Question:
    DIFFICULTY_LEVELS = {"easy": 1, "medium": 2, "hard": 3}   # 类变量
    
    def __init__(self, title: str, difficulty: str):
        self.title = title                     # 实例变量
        self._difficulty = difficulty          # _ 前缀 = 约定为私有
    
    # @property：方法变身属性，访问不加括号
    @property
    def difficulty_score(self) -> int:
        """计算难度分数（看起来像属性读，实际是方法）"""
        return self.DIFFICULTY_LEVELS.get(self._difficulty, 0)
    
    # @staticmethod：和类无关的工具函数，放在类里只是为了组织代码
    @staticmethod
    def is_valid_title(title: str) -> bool:
        return len(title) >= 2 and len(title) <= 500
    
    # @classmethod：接收类本身而不是实例，做工厂方法
    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """工厂方法：从字典创建 Question"""
        return cls(title=data["title"], difficulty=data.get("difficulty", "medium"))
```

#### 用在什么场景

| 装饰器 | 场景 | 怎么调 |
|--------|------|--------|
| `@property` | 计算属性（如全名=姓+名）、属性校验 | `q.difficulty_score`（不加括号！） |
| `@staticmethod` | 不需要访问 `self` 的工具函数 | `Question.is_valid_title("xxx")` |
| `@classmethod` | 工厂方法、多构造器 | `Question.from_dict({...})` |

#### Java 对照

| Python | Java |
|--------|------|
| `@property` | getter 方法（但调用时不用括号） |
| `@staticmethod` | `static` 方法 — 一模一样 |
| `@classmethod` | 静态工厂方法 `Question.of(...)` |

---

## 补课二：工程化补全（Field 校验 + 分页 + 异常处理 + 事务）

### 2.1 Pydantic `Field` 校验

#### 概念地图

```python
from pydantic import BaseModel, Field

# 之前（Day 1-4 都在用）
class UserCreate(BaseModel):
    username: str          # 只规定类型
    password: str          # 没限制长度

# 之后（加校验）
class UserCreate(BaseModel):
    username: str = Field(
        min_length=2,      # 最少 2 个字符
        max_length=30,     # 最多 30 个字符
        description="用户名",
    )
    password: str = Field(
        min_length=6,
        max_length=128,
        description="密码 6-128 位",
    )
```

#### 怎么用

```python
from pydantic import BaseModel, Field

class QuestionCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=500,
        description="题目标题",
    )
    tags: str = Field(
        default="",
        max_length=500,
        description="标签，逗号分隔",
    )
    difficulty: str = Field(
        default="medium",
        pattern=r"^(easy|medium|hard)$",   # ← 正则：只能是这三个值
    )
    answer: str = Field(
        default="",
        max_length=5000,
    )
```

| 参数 | 含义 | 校验失败返回 |
|------|------|------------|
| `min_length` / `max_length` | 字符串长度限制 | 422: "ensure this value has at least 2 characters" |
| `pattern` | 正则表达式匹配 | 422: "string does not match regex" |
| `gt` / `lt` | 大于/小于（数字） | `Field(gt=0, lt=150)` |
| `default` | 默认值 | 不传就用这个 |
| `description` | 给 Swagger 看的字段说明 | 不影响校验 |

#### 易错点

| 坑 | 现象 | 正确 |
|----|------|------|
| `Field` 放在 Pydantic 还能用在普通函数参数 | 普通参数不校验 | Field 只在 Pydantic BaseModel 里生效 |
| 忘了 `default` 的位置 | `Field("medium")` 而不是 `Field(default="medium")` | `Field` 第一个位置参数是 `default` |

---

### 2.2 分页查询

#### 概念地图

```
GET /questions?page=1&page_size=10
     ↓
SELECT * FROM question LIMIT 10 OFFSET 0    ← 第 1 页，跳过 0 条
SELECT * FROM question LIMIT 10 OFFSET 10   ← 第 2 页，跳过 10 条
```

#### 改造你的 `list_questions`

```python
from fastapi import Query

@router.get("/")
async def list_questions(
    tag: str | None = None,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数，最多 100"),
    storage=Depends(get_storage),
):
    """分页查询题目列表"""
    offset = (page - 1) * page_size
    questions = await storage.list_all(tag=tag, limit=page_size, offset=offset)
    total = await storage.count(tag=tag)
    return {
        "items": questions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,  # 向上取整
    }
```

#### `Query` 参数

| 参数 | 含义 |
|------|------|
| `1` | 默认值 |
| `ge=1` | greater or equal → ≥ 1 |
| `le=100` | less or equal → ≤ 100 |
| `description` | Swagger 文档显示 |

**需要在 repository 加两个方法**：`list_all(..., limit, offset)` 和 `count()`。

---

### 2.3 全局异常处理器

#### 概念地图

```
之前：每个路由都要写 try/except → 重复
之后：定义一个 handler → 所有没被捕获的异常统一处理
```

#### 怎么用

```python
# main.py 加这个
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：任何没被捕获的异常到这里"""
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": f"路径不存在: {request.url.path}"},
    )
```

等价 Java 的 `@ControllerAdvice` + `@ExceptionHandler`。

---

### 2.4 事务管理

#### 概念地图

```
事务 = 一组操作要么全部成功，要么全部回滚

你现在的代码：
  db.add(user)
  await db.commit()    ← 只一个操作，简单场景够用

需要事务的场景：
  注册用户 + 创建默认数据（两条 INSERT 必须同时成功）
```

#### 怎么用（留给 Day 5 实际用）

```python
async def register_with_default_data(db: AsyncSession, data: UserCreate):
    async with db.begin():       # ← 开启事务
        user = UserTable(...)
        db.add(user)
        # 还没 commit，失败了自动回滚
        
        default_q = QuestionTable(title=f"{data.username}的第一题", ...)
        db.add(default_q)
        # 事务结束 → 自动 commit（两条一起成功）
    # with 块外 → 事务已提交
```

---

## 补课三：代码质量（docstring + 格式化 + .env.example + traceback）

### 3.1 docstring

#### 怎么用

```python
def hash_password(password: str) -> str:
    """把明文密码哈希为 bcrypt 格式的不可逆字符串。
    
    Args:
        password: 明文密码，长度 6-128
        
    Returns:
        bcrypt 哈希值，$2b$12$... 格式
        
    Raises:
        ValueError: 密码为空时抛出
    """
    if not password:
        raise ValueError("密码不能为空")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

Google 风格三要素：`Args`、`Returns`、`Raises`。

---

### 3.2 `black` + `isort`

```bash
uv add black isort --dev

# 格式化（一条命令）
uv run black . && uv run isort .

# VS Code 里设置保存时自动格式化：
#   Ctrl+, → 搜 "format on save" → 打勾
```

---

### 3.3 `.env.example`

```bash
# .env.example — 提交到 git，不含真实密码
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/interview_agent
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET_KEY=YOUR_SECRET_KEY_HERE
```

---

### 3.4 `traceback.print_exc()`

```python
import traceback

# 场景：CLI 命令执行失败时，打印错误但不中断程序
try:
    result = await some_risky_operation()
except Exception:
    traceback.print_exc()    # ← 打印完整堆栈，但程序继续
    result = "操作失败，请重试"
```

和 Java `catch (Exception e) { e.printStackTrace(); }` 一样，但 Python 的 `traceback.print_exc()` 不抛异常，只打印。

---

## 补课四：运维能力（多阶段 Dockerfile + Loguru 文件日志）

### 4.1 多阶段 Dockerfile

#### 概念地图

```
单阶段（你现在的）：
  COPY 所有代码 → RUN uv sync（装依赖） → CMD
  问题：最终镜像包含 uv 缓存、测试文件 = 体积大

多阶段：
  阶段 1（构建阶段）：装依赖 → 产生 .venv
  阶段 2（运行阶段）：从阶段 1 只拷贝 .venv + 必要代码
  结果：镜像体积减半
```

```dockerfile
# 阶段 1：构建
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install uv && uv sync

# 阶段 2：运行（只留必要文件）
FROM python:3.12-slim AS runner
WORKDIR /app
COPY --from=builder /app/.venv ./.venv   # ← 从阶段1拷贝 venv
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 4.2 Loguru 文件日志轮转

```python
# middleware/logging.py 加一行
logger.add(
    "logs/api_{time:YYYY-MM-DD}.log",  # 每天一个文件
    rotation="1 day",                  # 轮转规则：每天
    retention="7 days",                # 保留 7 天
    level="INFO",
    format="{time} | {level} | {message}",
)
```

| 参数 | 含义 |
|------|------|
| `rotation="1 day"` | 每天生成新文件 |
| `retention="7 days"` | 自动删 7 天前的日志 |
| `level="INFO"` | 只记录 INFO 及以上级别 |

---

## 今日执行顺序

```
补课一（2h）：装饰器 → 生成器 → 可变对象陷阱 → @property
补课二（1.5h）：Field 校验 → 分页 → 异常处理器 → 事务管理
补课三（1h）：docstring → black/isort → .env.example → traceback
补课四（0.5h）：多阶段 Dockerfile → Loguru 文件日志
```

每个知识点拆成：**阅读理解 → 手敲代码 → 跑通验证** 三步。不走马观花。
