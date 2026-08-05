import chromadb
import uuid 
from openai import AsyncOpenAI

embedding_client=AsyncOpenAI(
    api_key="sk-gjocosqrxivhneflrlqrhzxznlibttxxszsarqadoztbdqvx",
    base_url="https://api.siliconflow.cn/v1",
)

class ChromaStore:
    def __init__(self,persistent_path:str,collection_name:str):
        chroma_client=chromadb.PersistentClient(persistent_path)
        self.collection=chroma_client.get_or_create_collection(collection_name)

    async def build_index(self,documents:list[str]):
        #避免硬编码
        #documents=await get_docs_str()
        response=await embedding_client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=documents,
        )
        emb_list=[d.embedding for d in response.data]
        ids=[uuid.uuid4().hex[:12] for _ in documents]

        self.collection.add(
            embeddings=emb_list,# pyright: ignore
            ids=ids,
            documents=documents
        )

    async def query(self,query_text:str,k:int)->list[str]:
        response=await embedding_client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=query_text,
        )
        results=self.collection.query(
            query_embeddings=[response.data[0].embedding],
            n_results=k,
            include=["documents"],
        )
        if not results["documents"]:
            return []
        docs=results["documents"][0]
        return docs