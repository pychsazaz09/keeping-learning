from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

embedding_client=AsyncOpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
)