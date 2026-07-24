from fastapi import FastAPI
from routers.questions import router as question_router
from fastapi.middleware.cors import CORSMiddleware


app=FastAPI(title="interview-agent",description="面试题库管理 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(question_router)
