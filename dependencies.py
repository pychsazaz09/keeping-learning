# from storage.json_storage import JsonStorage
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from services import auth_service

from services.chroma_service import ChromaStore
from services.rag_service import RagRetriever
from services.read_doc import get_docs_str



"""def get_storage()->JsonStorage:
    return JsonStorage("data/questions.json")"""


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_storage(db: AsyncSession = Depends(get_db)):
    return SqlalchemyRepositories(db)


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):

    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(401, detail="解析token出错")
    username = payload.get("username")
    if not username:
        raise HTTPException(401, detail="用户信息可能被篡改")
    user = await auth_service.get_user_by_name(db, username)
    if not user:
        raise HTTPException(401, detail="用户不存在")
    return user

_chroma_store:ChromaStore|None=None
_rag_retriever:RagRetriever|None=None
persistent_path="D:\\code\\agent-learing\\Python-Learning\\interview-agent\\data\\chroma_db"

async def get_chroma_store()->ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store=ChromaStore(persistent_path=persistent_path,collection_name="chroma_collection")
        documents=await get_docs_str()
        await _chroma_store.build_index(documents)
    return _chroma_store

async def get_rag_retriever()->RagRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        store=await get_chroma_store()
        documents=await get_docs_str()
        _rag_retriever=RagRetriever(store,documents)
    return _rag_retriever