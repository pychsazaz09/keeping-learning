import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from middleware.logging import log_request
from routers.auth import router as auth_router
from routers.questions import router as question_router

app = FastAPI(title="interview-agent", description="面试题库管理 API")

# CORS 中间件 — 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志中间件 — 记录每次请求的方法、路径、耗时
app.middleware("http")(log_request)

# 注册路由
app.include_router(question_router)
app.include_router(auth_router)


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
    """兜底异常处理 — 任何未捕获的异常到这里

    等价 Java 的 @ControllerAdvice + @ExceptionHandler
    """
    logger.error(f"未处理异常 | {request.method} {request.url.path} | {exc}")
    traceback.print_exc()  # ← 打印完整堆栈到控制台，不中断服务
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )
