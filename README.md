# interview-agent
**AI 驱动的面试题库管理系统**
*— FastAPI 异步 REST API，*
*支持 CRUD、语义搜索、RAG 检索增强生成，Docker 一键部署。*
支持添加、搜索、随机抽题、数据持久化到postgresql
可以投喂文档并生成你的问题并配备答案

# 快速开始
git pull
uv sync
uv run uvicorn main:app --reload

# 技术栈
| 技术 | 选型理由 |
|------|---------|
| **FastAPI** | 原生 async/await，`StreamingResponse` 开箱即用（SSE 流式），自动生成 Swagger 文档 |
| **SQLAlchemy 2.0 async** | ORM 不阻塞事件循环，asyncpg 驱动 |
| **PostgreSQL** | 稳定 ACID，JSONB 字段存储动态 tags |
| **Redis** | 随机抽题缓存，TTL 60s 避免每次扫全表 |
| **DeepSeek** | OpenAI 兼容协议，中文能力强，成本低 |
| **FAISS** | Meta 开源轻量向量索引，CPU 可跑，不需单独部署向量数据库 |
| **JWT** | 无状态双 token（access + refresh），`HTTPBearer` 拦截器 |
| **Loguru** | 文件日志按天轮转 + 请求耗时中间件 |
| **Docker** | 多阶段构建 + docker-compose 三服务编排（api + db + redis） |

## 目录结构

\```
interview-agent/
├── main.py                 # FastAPI 入口 + CORS + 异常处理
├── database.py             # 异步引擎 + Session 工厂
├── dependencies.py         # get_db / get_storage / get_current_user
├── .env.example            # 环境变量模板
├── docker-compose.yml      # 三服务编排 (api + db + redis)
├── Dockerfile              # 多阶段镜像构建
├── pyproject.toml          # uv 项目配置 + 依赖
│
├── routers/                # 路由层 — 接请求、调 service、返回
│   ├── auth.py             # 注册/登录/刷新
│   ├── questions.py        # CRUD + 随机抽题
│   └── ai.py               # RAG + 语义搜索
│
├── services/               # 业务逻辑层
│   ├── auth_service.py     # bcrypt 密码 + JWT 签发/验证
│   ├── cache_service.py    # Redis 连接 + get/set/delete
│   ├── embedding_client.py # Ollama Embedding 客户端
│   ├── embedding_service.py# FAISS 索引构建 + 语义搜索
│   ├── llm_client.py       # DeepSeek 异步客户端
│   └── stream_service.py   # SSE 流式生成器
│
├── models/                 # ORM 模型
│   ├── question_orm.py     # QuestionTable
│   └── user_orm.py         # UserTable
│
├── schemas/                # Pydantic 请求/响应模型
│   ├── ai.py               # GenerateRequest
│   ├── question.py         # QuestionCreate / QuestionResponse
│   ├── rag_request.py      # RagRequest
│   └── user.py             # UserCreate / TokenResponse
│
├── repositories/           # 数据访问层
│   └── sqlalchemy_repo.py  # PostgreSQL CRUD 实现
│
├── middleware/
│   └── logging.py          # 请求日志中间件
│
├── migration/              # Alembic 数据库迁移
│   └── versions/
│
├── data/                   # 知识库文档
├── prompts/                # Prompt 模板
└── logs/                   # 运行日志（按天轮转）
\```

# 设计决策
**为什么选择fastapi** ——web-api框架、异步流式、swagger文档
**为什么选FAISS而不是ChromaDB**——轻量向量数据库
**SSE而不是WebSocket**——单向传输，协议简单

# 快速启动
docker compose up -d

