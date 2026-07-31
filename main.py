import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from middleware.logging import log_request
from routers.auth import router as auth_router
from routers.questions import router as question_router
from routers.ai import router as ai_router

app = FastAPI(title="interview-agent", description="面试题库管理 API")

# CORS 中间件 — 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.add(
    "logs/api_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    encoding="utf-8",
)

# 日志中间件 — 记录每次请求的方法、路径、耗时
app.middleware("http")(log_request)

# 注册路由
app.include_router(question_router)
app.include_router(auth_router)
app.include_router(ai_router)

# ============================================================
# 全局异常处理器 — 兜底未捕获的异常
# ============================================================


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """路径不存在时的友好提示"""
    return JSONResponse(
        status_code=404,
        content={"detail": f"路径不存在: {request.url.path}"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常:{request.method} {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误"},
    )
