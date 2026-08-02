
from fastapi import APIRouter,Depends

from services.embedding_service import EmbeddingService
from dependencies import get_storage
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from models.question import Question 
from services.stream_service import generate_question

from schemas.rag_request import RagRequest

router = APIRouter(prefix="/ai", tags=["AI"])

embedding_question:EmbeddingService|None=None
embedding_md:EmbeddingService|None=None

def get_question_sql()->EmbeddingService:
    global embedding_question
    if embedding_question is None:
          embedding_question=EmbeddingService()
    return embedding_question

def get_question_md()->EmbeddingService:
    global embedding_md
    if embedding_md is None:
          embedding_md=EmbeddingService()
    return embedding_md


@router.post("/rag-task")
async def rag_ask(
        rag_request:RagRequest,
        repoQ:SqlalchemyRepositories=Depends(get_storage)
    ):
    embedding_md=get_question_md()
    if embedding_md.index is None:
        await embedding_md.build_index_md()
    md_str=await embedding_md.search(rag_request.question)
    ref_data="\n".join(
        f"参考资料{i+1}:{d["id"]}"
        for i,d in enumerate(md_str,0)
    )
    embedding_question=get_question_sql()
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


'''模块级单例：embedding_service = EmbeddingService() 放文件顶部
    端点：@router.get("/semantic-search")，参数 q: str 和 k: int = 5，依赖注入 db
    逻辑：如果 embedding_service.index is None → await build_index(db) → 
    然后 embedding_service.search(q, k) → 返回'''
@router.get("/semantic-search")
async def embedding_search(query_text:str,k:int=2,repoQ:SqlalchemyRepositories=Depends(get_storage)):
    embedding_question=get_question_sql()
    if embedding_question.index is None:
        await embedding_question.build_index_db(repoQ) 
    map_id=await embedding_question.search(query_text,k)
    ids=[]
    for i in map_id:
        ids.append(i["id"])
    return ids

