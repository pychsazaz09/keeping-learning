继续 Day 5：AI 增强 — LLM + Embedding + 语义搜索。

## 当前进度

- [x] Day 1-4 完成
- [x] Day 4 补课完成（装饰器/生成器/Field校验/分页/异常处理/事务/docstring/格式化/Dockerfile多阶段/Loguru轮转）
- [ ] Day 5：LLM + Embedding + RAG

## 我的项目

```
interview-agent/（FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Redis + JWT + Docker Compose）
├── main.py / database.py / dependencies.py
├── routers/（auth.py, questions.py）
├── services/（auth_service.py, cache_service.py）
├── models/（user_orm.py, question_orm.py）
├── schemas/（user.py, question.py）
├── repositories/sqlalchemy_repo.py
├── middleware/logging.py
├── docs/（day4-补课*.md, day5-plan.md）
└── tmp/（test.py — Day 4 补课装饰器实验用）
```

## 你的教学框架（必须遵守）

讲新东西用这个结构：
1. **概念引出**：用在什么场景（大局观、大框架、流程）
2. **作用是什么**
3. **怎么用**：import 引入了什么，参数分别代表什么，化抽象为具体，有一个架构
4. **架构决策**：选什么库、怎么分层、数据怎么流、选型判断
5. **易错点**
6. 自己检索思路链，考虑版本是否冲突

AI 开发核心能力：记概念地图（叫什么、能干吗）→ 写架构决策（选什么库、分层、数据流）→ 分层架构设计。

## Day 5 路线

参考 `docs/day5-plan.md`，顺序：

```
前置补课（30min）：事件循环实验 — sync vs async 对比、gather()、create_task()
  → 30-day-plan 的 Day 4 缺口，必须在 LLM 流式之前补
  → 写 tmp/async_event_loop.py

任务一（1.5h）：AsyncOpenAI 客户端 + 流式调用
  → 概念：AsyncOpenAI vs OpenAI、四种消息角色、stream=True、delta vs message
  → 产出：调通 DeepSeek，终端逐字打印

任务二（1.5h）：AI 自动出题 + SSE 返回
  → 概念：Prompt 模板、StreamingResponse、async 生成器
  → 产出：POST /ai/generate → 流式返回 JSON 格式题目

任务三（2h）：Embedding + FAISS 语义搜索
  → 概念：Embedding 向量化、FAISS 索引、L2 距离、语义相似度
  → 产出：GET /ai/semantic-search?q=Python内存 → 找到"GC原理"

任务四（1h）：RAG 最小可用链路
  → 概念：Retrieval → Augmented → Generation 三步
  → 产出：POST /ai/rag-ask → 检索已有题 → 参考风格 → LLM 出新题
```

## 关键约束

- **别写完整代码**，你先引出概念→场景→参数→易错点，让我自己写
- 每个任务完了我贴代码或输出，你说"继续"再进下一个
- 新概念按教学框架讲，不要跳过
- 遇到版本兼容问题自己检索后告诉我

## 需要新增的依赖

uv add openai numpy faiss-cpu

## 需要准备的

.env 里加 DEEPSEEK_API_KEY 和 DEEPSEEK_BASE_URL（我没有 OpenAI Key，用 DeepSeek）
