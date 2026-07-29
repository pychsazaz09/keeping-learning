import time

from fastapi import Request
from loguru import logger

# ============================================================
# Loguru 配置：控制台 + 文件日志轮转
# ============================================================

# 移除默认的 sink（避免重复日志）
logger.remove()

# 控制台输出（开发时用，生产可关闭）
logger.add(
    sink=lambda msg: print(msg, end=""),  # 输出到 stdout
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
)

# 文件日志：每天一个文件，保留 7 天（自动清理旧日志）
logger.add(
    sink="logs/api_{time:YYYY-MM-DD}.log",
    rotation="1 day",  # 每天轮转一次
    retention="7 days",  # 只保留最近 7 天的文件
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    encoding="utf-8",
)


async def log_request(request: Request, call_next):
    """记录每次 HTTP 请求的方法、路径、状态码和耗时。

    同时输出到控制台和日志文件，方便本地开发和线上排查。
    """
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    logger.info(
        "{} {} ---{} {:.3f}s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response
