from fastapi.responses import StreamingResponse
import json
from services.llm_client import get_llm_client

async def generate_stream(user_prompt:str):
    client = get_llm_client()  # 普通函数，不需要 await
    #prompt = Generate_Question_Prompts.format(topic=topic, difficulty=difficulty, count=count)

    #先准备“知识”,再检索给模板
    stream=await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"system","content":"返回一定要是json格式"},
            {"role":"user","content":user_prompt},
        ],
        temperature=0.7,
        max_tokens=2048,
        stream=True,
    )
    async for chunk in stream:
        delta=chunk.choices[0].delta.content
        if delta:
            yield f"data:{json.dumps({'chunk':delta})}\n\n"
    yield "data:[Done]\n\n"

async def generate_question(user_prompt:str):

    return StreamingResponse(
        generate_stream(user_prompt),
        media_type="text/event-stream",
    )