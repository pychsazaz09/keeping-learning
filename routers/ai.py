import json

from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from services.llm_client import get_llm_client
from services.embedding_service import EmbeddingService
from dependencies import get_storage
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from models.question import Question 

from schemas.rag_request import RagRequest

router = APIRouter(prefix="/ai", tags=["AI"])
embedding_question=EmbeddingService()
embedding_md=EmbeddingService()
@router.post("/rag-task")
async def rag_ask(
        rag_request:RagRequest,
        repoQ:SqlalchemyRepositories=Depends(get_storage)
    ):
    if embedding_md.index is None:
            await embedding_md.build_index_md()
    md_str=await embedding_md.search(rag_request.question)
    ref_data="\n".join(
        f"参考资料{i+1}:{d["id"]}"
        for i,d in enumerate(md_str,0)
    )

    if embedding_question.index is None:
        await embedding_question.build_index_db(repoQ)
    questions=await embedding_question.search(rag_request.question,rag_request.k)
    questions=[q["id"] for q in questions]
    references:list[Question]=await repoQ.get_by_ids(questions)
    ref_text="\n".join(
        f"题目{i+1}:{q.title}\n参考答案:{q.answer}" 
        for i,q in enumerate(references,0)
    )

    augmented_prompt = f"""{ref_data}
    并参考以下题目的风格和深度：
    {ref_text}
    根据以上风格，给用户问题：{rag_request.question}"""
    return await generate_question(augmented_prompt)



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


'''模块级单例：embedding_service = EmbeddingService() 放文件顶部
    端点：@router.get("/semantic-search")，参数 q: str 和 k: int = 5，依赖注入 db
    逻辑：如果 embedding_service.index is None → await build_index(db) → 
    然后 embedding_service.search(q, k) → 返回'''
@router.get("/semantic-search")
async def embedding_search(query_text:str,k:int=2,repoQ:SqlalchemyRepositories=Depends(get_storage)):
    if embedding_question.index is None:
        await embedding_question.build_index_db(repoQ) 
    map_id=await embedding_question.search(query_text,k)
    ids=[]
    for i in map_id:
        ids.append(i["id"])
    return ids

