# 补课任务一：Python 核心概念 — 装饰器 + 生成器 + 陷阱（2h）

> **为什么先做这个**：装饰器和生成器是 Python 两大核心特性。FastAPI 到处用 `@`，Depends 的 `yield` 本质是生成器。不理解它们 = 不理解框架为什么这样设计。
>
> **学习方式**：每个知识点 → 创建一个独立 `.py` 文件实验 → 跑通 → 写一句费曼总结 → 再进下一个。

---

## 子任务 1.1：装饰器 `@xxx`（50min）

### 概念引出

你每天都在写 `@router.get("/")`、`@app.middleware("http")`。`@` 到底是什么？

```
装饰器 = 给函数套一层壳，不改原函数代码，增加前后逻辑

@timer
def my_func():
    pass

等价于：
my_func = timer(my_func)   ← 本质：高阶函数（函数接收函数，返回函数）
```

这不是 FastAPI 的魔法——是 Python 语言特性。`@app.get("/")` 内部就是：把下面的函数注册到路由表。

### 你要弄懂的三个层次

| 层次 | 做什么 | 复杂度 | 你写过的例子 |
|------|--------|--------|-------------|
| ① 无参装饰器 | 写一个 `@timer`，打印函数耗时 | ⭐ | 无（这次写） |
| ② 带参装饰器 | 写一个 `@retry(max=3)`，失败自动重试 | ⭐⭐ | 无（LLM 调用时需要） |
| ③ 类装饰器 | 写一个 `@Singleton`，类只能有一个实例 | ⭐⭐⭐ | 无（数据库连接池场景） |

### 动手任务

**1.1.1 无参装饰器 `@timer`（15min）**

创建 `interview-agent/tmp/task1_decorator.py`，完成：

1. 写一个 `timer` 装饰器，打印被装饰函数的**名字**和**耗时**
2. 分别装饰一个同步函数和一个 `async` 函数
3. 验证 `@wraps(func)` 的作用——对比加和不加时 `func.__name__` 的值

> **关键检索**：`functools.wraps` 做了什么？为什么要保留 `__name__` 和 `__doc__`？

**参数自查表**（理解每个参数，不要死记）：

| 参数/语法 | 它是什么 | 从哪来的 |
|-----------|---------|---------|
| `func`（装饰器参数） | 被装饰的原函数 | `@timer` 下面那个函数，Python 自动传 |
| `*args` | 位置参数打包成的元组 | 调用 `slow_task("hello", 42)` → `args = ("hello", 42)` |
| `**kwargs` | 关键字参数打包成的字典 | 调用 `slow_task(name="x")` → `kwargs = {"name": "x"}` |
| `@wraps(func)` | 把 `func` 的元信息复制到 wrapper | 必须手动加，否则被装饰后函数名变成 `"wrapper"` |

**1.1.2 带参装饰器 `@retry`（20min）**

1. 写一个 `retry(max_attempts=3, delay=1.0)` 装饰器
2. 装饰一个**异步函数**（模拟可能失败的 LLM 调用）
3. 思考：为什么比无参装饰器多一层函数嵌套？

```
@retry(max_attempts=3)   call_llm
       ↓                      ↓
  retry(3) 执行 → 返回 decorator
                      ↓
                @decorator 装饰 call_llm → decorator(call_llm) → wrapper
```

> **检索任务**：`@retry()` 有 `()`，`@timer` 没有 `()`。为什么？调用时机有什么不同？

**1.1.3 类装饰器 `@Singleton`（15min）**

1. 写一个 `Singleton` 类装饰器——同一个类只能创建一个实例
2. 验证 `db1 is db2` 返回 `True`

> **检索任务**：`__init__` 和 `__call__` 的区别？类装饰器用哪个？

### 易错点清单（做完后对照）

| 坑 | 你会看到的报错/现象 | 根因 | 修复 |
|----|-------------------|------|------|
| 忘写 `@wraps(func)` | `slow_task.__name__` → `"wrapper"` | 装饰器返回 wrapper，没保留原函数名 | 加 `@wraps(func)` |
| `return wrapper` 忘写 | 装饰后函数 → `None` | 装饰器必须返回新函数 | 检查 return |
| `@retry` 没加括号 | `TypeError: 'int' object is not callable` | `func` 参数收到了 `max_attempts=3` | `@retry()` 即可 |
| 同步装饰器套异步函数 | `TypeError: coroutine was never awaited` | wrapper 里没 `await` | wrapper 也声明 `async def` |
| 装饰器里改了 `args` | 原函数收到被篡改的参数 | wrapper 里 `args[0] = "xxx"` | 只读不改 |

### 架构决策（写一句总结）

> 什么时候用装饰器 vs 中间件？
>
> 装饰器：给**单个函数**加能力（缓存某个接口、重试某个调用）
> 中间件：给**所有请求**加能力（日志、CORS）
>
> 和 Java AOP 一样的设计思想——横切关注点从业务逻辑里分离出来。

---

## 子任务 1.2：生成器 `yield` / `yield from`（40min）

### 概念引出

```python
# 你每天在 dependencies.py 里写的：
async def get_db():
    session = AsyncSessionLocal()
    try:
        yield session       # ← 这行是生成器！交出 session，暂停等待
    finally:
        await session.close()  # ← 请求结束后从这行继续执行
```

FastAPI Depends 的 `yield` 就是 Python 生成器——只是用来管理资源生命周期。

### 你要弄懂的三个场景

| 场景 | 做什么 | 对应你项目里的 |
|------|--------|-------------|
| ① 惰性序列 | 用 `yield` 逐行读大文件，不加载整个文件到内存 | 无（这次写） |
| ② yield from | 把多个生成器串成一个 | 如果从多个文件读题 |
| ③ 资源管理 | `yield` 前获取资源，`yield` 后释放 | `get_db()` 每天都在用 |

### 动手任务

**1.2.1 基本生成器（10min）**

创建 `tmp/task1_generator.py`：

1. 创建一个 100 万行的文本文件（用 Python 脚本生成）
2. 写生成器函数 `read_large_file(path)` 逐行 `yield`
3. 对比：`return [所有行]` vs `yield 一行`——观察内存占用

> **关键认知**：`range(1000000)` 也是生成器。Python 3 里 `range` 返回的是一个惰性对象，不是 100 万个元素的列表。

**1.2.2 `yield from`（10min）**

1. 写两个生成器，分别 `yield` 不同的数据
2. 写第三个生成器，用 `yield from` 把前两个串起来
3. 验证：调用方不需要知道有几个子生成器

> `yield from gen` ≈ `for x in gen: yield x`，但前者会处理 `close()` / `throw()` / `return` 等边界情况。

**1.2.3 资源管理模式（10min）**

1. 不用 FastAPI——在纯 Python 脚本里写一个类似 `get_db()` 的资源管理器
2. 模拟：打开资源 → `yield` 交出 → 用完后自动释放
3. 验证 `finally` 块在 `break` / 异常 / 正常结束时都执行

> **关键问题**：为什么 `yield` 在 `try` 块里，`finally` 在 `yield` 后面？执行顺序是怎样的？

**1.2.4 读你项目里的 `get_db()`（10min）**

打开 [dependencies.py](../dependencies.py)，重新读 `get_db()` 函数。现在的你：
- 理解 `yield session` 不是魔法——是生成器暂停
- 理解 `finally: await session.close()` 是请求结束后执行的清理
- 理解 FastAPI Depends 做了什么：自动调用 `next(get_db())` 拿到 session，请求结束后自动继续执行到 `finally`

### 易错点

| 坑 | 现象 | 根因 | 正确做法 |
|----|------|------|---------|
| `yield` 后的代码不执行 | 资源没释放 | `for` 循环 `break` 提前退出 | `try/finally` 包裹 `yield` |
| 把生成器当列表用 | `len(gen)` 报错 | 生成器没长度 | 需要时 `list(gen)` 转列表（注意内存） |
| 生成器只能迭代一次 | 第二次 `for` 循环为空 | 生成器是消耗品 | 每次重新调用生成器函数 |
| `yield from` 和 `yield` 分不清 | 嵌套生成器写不出来 | `yield from` 是委托，`yield` 是吐值 | 合并多个子生成器用 `yield from` |

### 架构决策

```
什么时候用 yield 而不是 return list？
  数据量大（10 万条记录）→ yield（内存 O(1)）
  数据量小（几十条）→ return list（更简单）

FastAPI 为什么用 yield 管理 session？
  yield 前 = 请求进来，开启数据库会话
  yield    = 会话交给路由函数
  yield 后 = 路由返回后，自动关闭会话

  这就是 Python 的 "try-with-resources"——用语言特性实现资源管理。
```

---

## 子任务 1.3：可变对象默认参数陷阱（15min）

### 概念引出

```python
# 这段代码有 bug，先别看答案——自己预测输出，然后跑一遍
def add_question(title: str, tags: list = []):
    tags.append("面试")
    return tags

print(add_question("GIL"))       # 你预测：?
print(add_question("装饰器"))     # 你预测：?
```

### 动手任务

1. 创建 `tmp/task1_mutable.py`，跑上面那段代码
2. 解释为什么第二次调用结果是 `['面试', '面试']`
3. 写出正确的写法
4. 搞清楚：为什么 Pydantic `BaseModel` 里 `tags: list[str] = []` 是安全的？

> **检索关键词**："Python mutable default arguments"，"Python function default value evaluation time"
>
> **一句话原理**：Python 函数默认值在 `def` **定义时**求值一次，不是每次调用时求值。`def foo(a=[])` 那个 `[]` 在模块加载时就创建了——之后所有调用共享同一个 list 对象。

### 易混淆场景

| 场景 | 安全？ | 说明 |
|------|--------|------|
| `def f(x: list = [])` | ❌ | 普通函数——陷阱！ |
| `tags: list[str] = []` (Pydantic) | ✅ | Pydantic 特殊处理，每次创建新 list |
| `def f(x: int = 0)` | ✅ | `int` 是不可变类型，安全 |
| `def f(x: str = "")` | ✅ | `str` 是不可变类型，安全 |
| `def f(x: dict = {})` | ❌ | `dict` 是可变类型——同上陷阱 |

**黄金法则**：默认值只用不可变类型（`None`、`str`、`int`、`float`、`bool`、`tuple`），可变类型在函数体内创建。

---

## 子任务 1.4：`@property` / `@staticmethod` / `@classmethod`（15min）

### 概念引出

这三个也是装饰器——但它们改变的是**类内部的方法行为**，不是套壳。

```python
class Question:
    # @property：方法变属性，访问不加括号
    @property
    def difficulty_score(self) -> int:
        return ...

    # @staticmethod：和类/实例都无关的工具函数
    @staticmethod
    def is_valid_title(title: str) -> bool:
        return ...

    # @classmethod：接收类本身（不是实例），做工厂方法
    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        return cls(...)
```

### 动手任务

1. 创建一个 `Question` 类，包含以上三种方法
2. 验证：
   - `q.difficulty_score` 不加括号也能调用（`@property` 的效果）
   - `Question.is_valid_title("xxx")` 不需要实例
   - `Question.from_dict({...})` 返回一个 `Question` 实例
3. 写一个 `@property` setter：允许 `q.difficulty_score = 5`，但校验值的范围

### 怎么区分

| 装饰器 | 第一个参数 | 不需要实例？ | 典型场景 |
|--------|-----------|------------|---------|
| `@property` | `self` | ❌ | 计算属性（全名 = 姓 + 名） |
| `@staticmethod` | 无 `self`/`cls` | ✅ | 工具函数（校验、格式化） |
| `@classmethod` | `cls` | ✅ | 工厂方法（从不同来源构造实例） |

---

## ✅ 任务一验收

- [ ] `@timer` 能正确打印同步函数和异步函数的耗时
- [ ] `@retry(max_attempts=3)` 失败后自动重试，成功则不重试
- [ ] 能口述：`@wraps(func)` 不写会怎样、带参装饰器为什么多一层
- [ ] 生成器逐行读 100 万行文件，内存不爆
- [ ] `yield from` 成功合并两个子生成器
- [ ] 能口述：`get_db()` 里 `yield` 前后的代码分别在什么时候执行
- [ ] 可变默认参数陷阱——能预测输出并写出正确写法
- [ ] `@property` / `@staticmethod` / `@classmethod` 各写一个例子并能解释区别
- [ ] git commit: `补课一：装饰器 + 生成器 + 可变对象陷阱 + @property 三层装饰器`
