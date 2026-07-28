# 补课任务四：运维能力 — 多阶段 Dockerfile + Loguru 文件日志（0.5h）

> **原则**：镜像大小和日志管理是"开发"和"运维"的分界线。这两件事花半小时搞定，面试时能说出所以然。

---

## 子任务 4.1：多阶段 Dockerfile（20min）

### 概念地图

```
单阶段（你现在的 Dockerfile）：
  COPY pyproject.toml → RUN uv sync → COPY . → CMD
  问题：最终镜像包含 uv 缓存 + 所有源码 = 镜像大

多阶段：
  阶段 1（builder）：装依赖 → 产生 .venv（虚拟环境）
  阶段 2（runner）：从阶段 1 只拷贝 .venv + 必要代码
  结果：镜像体积差不多减半
```

### 架构决策

```
为什么缩小镜像体积重要？
  ① 拉取更快（CI/CD 每次构建都要拉镜像）
  ② 启动更快（K8s 调度时镜像拉取是瓶颈）
  ③ 攻击面更小（没用的工具全删了 → 可被利用的东西更少）

多阶段 vs 单阶段 + .dockerignore？
  两个都做：.dockerignore 排除不必要文件（.git、__pycache__、.venv）
            多阶段只保留运行时需要的产物
```

### 动手改

把你现在的 `Dockerfile` 改成多阶段：

```dockerfile
# ===== 阶段 1：构建依赖（builder）=====
FROM python:3.12-slim AS builder

WORKDIR /app

# 先只拷依赖文件 → 利用 Docker 层缓存（代码改了不用重装依赖）
COPY pyproject.toml ./

# 装 uv 并安装依赖到 .venv
RUN pip install uv --no-cache-dir && \
    uv sync --frozen

# ===== 阶段 2：运行时（runner）=====
FROM python:3.12-slim AS runner

WORKDIR /app

# 从 builder 阶段只拷贝虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 拷贝应用代码
COPY . .

# 创建非 root 用户运行（安全基线）
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 关键参数解释

| Dockerfile 指令 | 含义 | 为什么 |
|----------------|------|--------|
| `AS builder` | 给阶段命名 | 后面 `COPY --from=builder` 才能引用 |
| `COPY --from=builder` | 从上一阶段拷贝文件 | 不拷贝整个 builder 镜像，只取 .venv |
| `uv sync --frozen` | 严格按 lock 文件装依赖 | 不加 --frozen → uv 会更新版本，CI 里可能装到不同版本 |
| `RUN useradd` + `USER appuser` | 创建非 root 用户运行 | 安全基线：容器被攻破不至于拿到宿主机 root |

### 对比体积

```bash
# 构建
docker build -t interview-agent:multi .

# 看镜像大小
docker images interview-agent

# 单阶段大约 400-600MB
# 多阶段大约 200-350MB（少了 uv 缓存、pip 缓存、不需要的系统包）
```

### 进阶：加 .dockerignore

创建 `interview-agent/.dockerignore`：

```
# 不拷进镜像的东西
__pycache__
*.pyc
.env
.git
.gitignore
*.md
data/
logs/
.venv/
migration/
```

为什么 `migration/` 不拷？Docker Compose 里 api 服务启动时不做数据库迁移（那是运维的事），可以单独跑 `alembic upgrade head`。

---

## 子任务 4.2：Loguru 文件日志轮转（10min）

### 概念地图

```
现在（只有控制台输出）：
  uvicorn 的日志 → 终端 → 终端关了日志就没了

加上文件日志后：
  uvicorn 的日志 → 终端 + 文件（每天一个文件，自动删旧的）
```

### 架构决策

```
为什么用文件日志轮转而不是所有日志写一个文件？
  一个文件 → 3 个月后 2GB → 打开卡死 → 删了又丢历史
  轮转     → 每天一个文件 → 7 天后自动删 → 磁盘可控

为什么用 Loguru 而不是 Python 标准库 logging？
  logging：配置复杂（Formatter + Handler + Logger 三层）
  Loguru：一行代码搞定，API 直观
```

### 动手改

在你现有的 `middleware/logging.py` 或 `main.py` 里加文件日志：

```python
# main.py 或 middleware/logging.py —— 在 logger 配置部分加

from loguru import logger
import sys

# 移除默认 handler（Loguru 默认输出到 stderr）
logger.remove()

# 控制台输出：开发时看
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)

# 文件输出：运维时查
logger.add(
    "logs/api_{time:YYYY-MM-DD}.log",
    rotation="1 day",       # 每天轮转 → api_2026-07-28.log
    retention="7 days",     # 保留7天，旧文件自动删
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    encoding="utf-8",
)
```

### 参数速查

| 参数 | 含义 | 不设会怎样 |
|------|------|-----------|
| `rotation="1 day"` | 每天凌晨生成新文件 | 一个文件无限增长 |
| `retention="7 days"` | 自动删 7 天前的日志 | 磁盘撑爆 |
| `level="INFO"` | 只记录 INFO 及以上 | `DEBUG` 也写 → 文件膨胀快 |
| `encoding="utf-8"` | 中文日志不乱码 | Windows 可能 GBK 乱码 |

### 验证

```bash
# 创建 logs 目录
mkdir -p logs

# 启动 API 并发几个请求
# 然后检查
ls logs/
cat logs/api_2026-07-28.log
```

---

## ✅ 任务四验收

- [ ] `docker build -t interview-agent:multi .` 成功
- [ ] `docker images interview-agent` 多阶段镜像体积明显小于之前的
- [ ] `.dockerignore` 已创建，排除不必要文件
- [ ] `logs/` 目录下有按日期的日志文件
- [ ] 日志文件内容正确（有方法、路径、状态码、耗时）
- [ ] 能口述多阶段构建的好处（体积、安全、缓存）
- [ ] 能口述 `rotation` / `retention` 的作用
- [ ] git commit: `补课四：多阶段 Dockerfile + Loguru 文件日志轮转`
