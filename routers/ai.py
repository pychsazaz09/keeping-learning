from fastapi import APIRouter,Depends

#from services.embedding_service import EmbeddingService
from services.chroma_service import ChromaStore
from services.rag_service import RagRetriever
from dependencies import get_storage,get_rag_retriever
from services.stream_service import generate_question
from schemas.rag_request import RagRequest

router = APIRouter(prefix="/ai", tags=["AI"])

embedding_question:RagRetriever|None=None
embedding_md:RagRetriever|None=None
chroma_store=ChromaStore("./chroma_db","chroma_collection")

doc_path="D:\\code\\agent-learing\\Python-Learning\\interview-agent\\data\\data_python.md"

'''async def get_question_sql()->RagRetriever:
    global embedding_question
    if embedding_question is None:
        chroma_store=ChromaStore(doc_path,"chroma_collection")
        documents=await get_docs_str()
        embedding_question=RagRetriever(chroma_store,documents)
    return embedding_question

async def get_question_md()->RagRetriever:
    global embedding_md
    if embedding_md is None:
        chroma_store=ChromaStore(doc_path,"chroma_collection")
        documents=await get_docs_str()
        embedding_md=RagRetriever(chroma_store,documents)
    return embedding_md'''


@router.post("/rag-task")
async def rag_ask(
        rag_request:RagRequest,
        rag_retriever:RagRetriever=Depends(get_rag_retriever)
    ):
    docs=await rag_retriever.retriever(rag_request.question,rag_request.k)
    context="\n".join(docs)
    prompt=f"""参考资料:{context}.
    问题:{rag_request.question}.
    """
    return await generate_question(prompt)



