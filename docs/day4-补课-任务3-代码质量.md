# 补课任务三：代码质量 — docstring + black/isort + .env.example + traceback（1h）

> **为什么补这个**：代码能跑只是第一步。能读、能维护、别人能接手才是工程化的标准。这四件事花一小时，换面试时"代码质量意识"的加分项。
>
> **学习方式**：边动手边理解——每个子任务 15 分钟，全是实践。

---

## 子任务 3.1：docstring — 写给 3 个月后的自己看（15min）

### 概念引出

```python
# ❌ 你现在的代码（典型的只有自己能看懂）
async def hash_password(password: str) -> str:
    ...

# ✅ 加上 docstring 后
async def hash_password(password: str) -> str:
    """把明文密码哈希为 bcrypt 格式的不可逆字符串。

    Args:
        password: 明文密码，长度 6-128

    Returns:
        bcrypt 哈希值，格式为 $2b$12$...

    Raises:
        ValueError: 密码为空时抛出
    """
```

### 架构决策

```
为什么用 Google 风格而不是其他？
  reStructuredText：太啰嗦（:param XXX: :type: :return:）
  NumPy 风格：科学计算圈用
  Google 风格：简洁、VS Code 原生支持、企业最常见

三要素就够了：
  Args: 输入什么
  Returns: 输出什么
  Raises: 什么情况炸
```

### 动手任务

给你现有的文件补 docstring。**重点是 Service 层和 Repository 层**——Router 层太薄可以不写。

**优先级从高到低：**

1. [services/auth_service.py](../services/auth_service.py) — 每个公开函数都要
2. [services/cache_service.py](../services/cache_service.py) — Redis 连接和缓存操作
3. [repositories/sqlalchemy_repo.py](../repositories/sqlalchemy_repo.py) — CRUD 方法
4. [dependencies.py](../dependencies.py) — `get_db()`、`get_current_user()` 特别重要

每个函数补三要素：`Args`、`Returns`、`Raises`。

> **只写"干什么"，不写"怎么干"**——docstring 是契约，不暴露实现细节。
>
> ✅ `Args: password: 明文密码，长度 6-128`
> ❌ `Args: password: 先用 encode() 转 bytes，再调 bcrypt.hashpw()`

### 写完后跑一下

```bash
# VS Code 里鼠标悬停到函数名上 → 应该显示你的 docstring
# 或者在终端验证
uv run python -c "from services.auth_service import hash_password; help(hash_password)"
```

---

## 子任务 3.2：`black` + `isort` — 格式化自动化（15min）

### 概念引出

```
black：代码格式化（缩进、换行、空格、引号统一）——不关心 import 顺序
isort：import 排序（标准库 → 第三方 → 本地）——不关心代码格式

两者互补。black 让你停止纠结格式，isort 让你停止纠结 import 顺序。
```

### 架构决策

```
Why black over autopep8 / yapf？
  black：零配置。跑就完了。社区标准（FastAPI / Django / pytest 都用）
  autopep8：太保守，只改 PEP8 违规，不统一风格
  yapf：可配置项太多，失去"统一格式"的意义

Why isort？
  import 散乱 → 合并冲突多、读代码找依赖慢
  isort 分区：标准库（os, json）→ 第三方（fastapi, sqlalchemy）→ 本地（from .models）
```

### 动手任务

```bash
# ① 安装
uv add black isort --dev

# ② 格式化整个项目
uv run black interview-agent/
uv run isort interview-agent/

# ③ 看 git diff —— 确认改了哪些地方
git diff

# ④ VS Code 设置保存时自动格式化（可选）
# Ctrl+, → 搜 "format on save" → 打勾
# 搜 "python formatting provider" → 选 black
# 搜 "editor.codeActionsOnSave" → 加 "source.organizeImports": true
```

> **重要**：第一次格式化会改很多地方——这是正常的。从今以后每次 commit 前跑一遍。

### 易错点

| 坑 | 现象 | 修复 |
|----|------|------|
| `black` 格式化后测试挂了 | 只可能发生在多行字符串（docstring 缩进变了） | 极罕见 |
| `isort` 把本地 import 错放到第三方 | 项目名和第三方包重名 | 在 `pyproject.toml` 加 `[tool.isort] known_first_party = ["models", "schemas", ...]` |
| CI 里格式检查不通过 | 本地没跑就 push | 每次 commit 前跑：`uv run black . --check && uv run isort . --check-only` |

---

## 子任务 3.3：`.env.example` — 新同事拉代码第一次就能跑（15min）

### 概念引出

```
.env = 真实密码 → 在 .gitignore 里 → 不提交
.env.example = 模板（密码写 YOUR_PASSWORD_HERE） → 提交到 git

新同事流程：
  git clone → cp .env.example .env → 填上自己的密码 → uv run 就能跑
```

### 架构决策

```
.env.example 里该写什么？
  ✅ 所有必需的环境变量名（DATABASE_URL, REDIS_HOST, JWT_SECRET_KEY...）
  ✅ 默认值（端口、主机名）
  ❌ 真实密码、真实密钥
  ❌ 生产环境的值
```

### 动手任务

1. 打开你现有的 `.env`，把真实密码替换为占位符
2. 保存为 `.env.example`
3. 确认 `.gitignore` 里有 `.env`（没有就加）

参考结构：

```bash
# .env.example —— 复制此文件为 .env 并填入真实值
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/interview_agent
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET_KEY=YOUR_RANDOM_SECRET_KEY_HERE
```

> **验证**：`git status` → 应该看到 `.env.example` 是新增文件，`.env` 没有出现。

### 易错点

| 坑 | 现象 | 修复 |
|----|------|------|
| `.env.example` 里写了真实密码 | 密码进 git 历史 → 永远删不掉 | 立刻改密码 + `git rebase` 或重写历史 |
| `.gitignore` 里没有 `.env` | `git status` 看到 `.env` 被追踪 | `.gitignore` 加一行 `.env` |

---

## 子任务 3.4：`traceback.print_exc()` — 报错但不死（15min）

### 概念引出

```python
# 场景：CLI 命令执行失败时，想打印完整错误信息，但不中断程序

try:
    result = await some_risky_operation()
except Exception:
    traceback.print_exc()    # ← 打印完整堆栈，但程序继续执行！
    result = "操作失败，请重试"
```

### 架构决策

```
什么时候用 traceback.print_exc() vs 让异常继续抛？

traceback.print_exc()：
  批量任务（100 个里失败了 3 个，其余继续）
  CLI 工具（给用户友好的错误信息，但你自己看到完整堆栈）
  try/except 吞掉异常但不想丢失调试信息

让异常继续抛（re-raise）：
  关键路径（注册失败 → 不能继续 → 必须停止）
  API 请求（FastAPI 的 exception_handler 会处理）
```

### 动手任务

1. 找到你 Day 1 写的 [cli.py](../cli.py)（或任何有 `try/except` 的地方）
2. 在 `except` 块里加 `traceback.print_exc()`
3. 故意触发一个异常 → 看终端输出（完整堆栈 + 程序继续运行）

> **验证方式**：
> 在 Python 交互环境里试：
> ```python
> import traceback
> try:
>     1/0
> except Exception:
>     traceback.print_exc()
>     print("但我没挂！")
> ```

### 和 Java 对照

```python
# Python
try:
    risky()
except Exception:
    traceback.print_exc()    # 打印堆栈 + 继续执行

# Java
try {
    risky();
} catch (Exception e) {
    e.printStackTrace();     // 打印堆栈 + 继续执行
}
```

完全一样的概念。但 Python 的 `traceback` 模块还有更多：
- `traceback.format_exc()` — 返回字符串，不直接打印（适合写日志）
- `traceback.print_exc(file=sys.stderr)` — 打印到指定输出流
- `logger.exception("出错")` — Loguru 内置，等价 `logger.error() + traceback`

---

## ✅ 任务三验收

- [ ] `help(hash_password)` 显示完整的 Args / Returns / Raises
- [ ] Service 层和 Repository 层所有公开函数都有 docstring
- [ ] `black .` 跑步通过（无格式变化）
- [ ] `isort .` 跑步通过（import 顺序已排序）
- [ ] `.env.example` 已创建，不含真实密码
- [ ] `git status` 里 `.env` 不出现（被 gitignore）
- [ ] `traceback.print_exc()` 在 CLI 的 except 块里能打印完整堆栈
- [ ] 能口述：为什么选 Google 风格 docstring、black 和 isort 分别管什么、.env.example 的作用
- [ ] git commit: `补课三：docstring + black/isort + .env.example + traceback`
