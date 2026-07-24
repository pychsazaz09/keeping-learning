# Session State — 2026-07-24

## 当前进度

- [x] Day 1 — CLI 命令行工具
- [x] Day 2 — FastAPI REST API
- [ ] Day 3 — SQLAlchemy + PostgreSQL（明天开始）
- [ ] Day 4 — JWT + Redis + Docker
- [ ] Day 5 — LLM + RAG

## 项目结构

```
interview-agent/
├── main.py              # FastAPI 入口（app + CORS）
├── cli.py               # argparse 四个子命令（add/list/search/random）
├── dependencies.py      # get_storage() 依赖注入
├── routers/
│   └── questions.py     # 6 个 API 端点（CRUD + random）
├── schemas/
│   └── question.py      # QuestionCreate / QuestionResponse
├── models/
│   └── question.py      # Question Pydantic 模型（内部用）
├── storage/
│   └── json_storage.py  # JSON 文件读写（目前是 FastAPI + CLI 共用）
├── data/
│   └── questions.json   # 题目数据
├── pyproject.toml       # 项目元信息
├── .gitignore           # .venv/ __pycache__/ *.pyc
└── README.md
```

## 当前技术栈

| 组件 | 版本 |
|------|------|
| Python | 3.12 |
| 包管理 | uv |
| 数据模型 | Pydantic 2.x |
| 文件 IO | aiofiles |
| Web 框架 | FastAPI |
| 服务器 | Uvicorn |
| 存储 | JSON 文件 |
| 数据库 | 还没上 |

## 当前能用什么

```bash
# CLI
uv run python cli.py add "题目" -t "标签" -d medium -a "答案"
uv run python cli.py list -t "标签"
uv run python cli.py search "关键词"
uv run python cli.py random -n 3

# Web API
uv run uvicorn main:app --reload
# → 打开 http://localhost:8000/docs
```

## 未提交变更

- `storage/json_storage.py` 有修改（加了 update/delete 方法）

## 明天 Day 3 要做的事

> **目标**：把 JSON 存储替换为 PostgreSQL，体会"换存储层，路由层几乎不改"

1. 装 Docker → `docker run postgres:16`
2. 安装 `sqlalchemy[asyncio]` + `asyncpg`
3. 写 ORM 模型（SQLAlchemy 2.0 Mapped 语法）
4. 封装异步 Engine + Session 工厂
5. 写 `SqlalchemyRepository`（实现和 JsonStorage 一样的接口方法）
6. 改 `dependencies.py`，把注入的实例从 JsonStorage 换成 SqlalchemyRepository
7. **核心体验**：router 代码一行不改，只换依赖注入

## 昨天的坑（Day 2 教训）

1. **async 函数必加 await** — 忘记就拿到协程对象
2. **路由顺序** — `/random` 必须写在 `/{id}` 前面
3. **`model_dump()` 要加 `()`** — 不然拿到方法对象
4. **`model_dump_json()` 返回字符串** — 不能当 dict 往里加字段
5. **uv run 构建报错** — 绕过：`.venv/Scripts/python.exe -m uvicorn main:app --reload`

## 参考文件

| 文件 | 位置 |
|------|------|
| 7 天计划 | `../7-day-plan.md` |
| 7 天参考 | `../7-day-reference.md` |
| 学习日志 | `../learning-journal.md` |
| 知识蒸馏 | `c:\Users\Lenovo1\Desktop\check\python\knowledge-distilled.md` |
