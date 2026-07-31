import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# 模块级单例 — AsyncOpenAI() 是同步的，不需要 async def
# 放在模块级别 = 只创建一次，全局复用 HTTP 连接池
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)


def get_llm_client() -> AsyncOpenAI:
    """返回模块级单例，不每次 new 一个新 client"""
    return client


