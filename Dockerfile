# ============================================================
# 阶段 1：构建阶段（builder）
#   - 安装依赖 + 编译 → 产生 .venv
#   - 最终镜像不包含 uv 缓存、pip 缓存等构建垃圾
# ============================================================
FROM python:3.12-slim AS builder
WORKDIR /app

# 先只拷贝依赖声明文件（充分利用 Docker 层缓存）
COPY pyproject.toml uv.lock ./

# 安装 uv 并同步依赖（此时只有依赖，没有源码）
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

# ============================================================
# 阶段 2：运行阶段（runner）
#   - 从 builder 只拷贝 .venv + 必要源码
#   - 镜像体积减半，不含构建工具
# ============================================================
FROM python:3.12-slim AS runner
WORKDIR /app

# 从构建阶段拷贝虚拟环境（体积最大的部分）
COPY --from=builder /app/.venv /app/.venv

# 拷贝源代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

EXPOSE 8000

# 使用 uv run 启动 uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
