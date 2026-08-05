from rank_bm25 import BM25Okapi
from openai import AsyncOpenAI
import jieba
from services.reranker import Reranker
from services.chroma_service import ChromaStore

embedding_client=AsyncOpenAI(
    api_key="sk-gjocosqrxivhneflrlqrhzxznlibttxxszsarqadoztbdqvx",
    base_url="https://api.siliconflow.cn/v1",
)


class RagRetriever:
    def __init__(self,chroma_store:ChromaStore,documents:list[str]) -> None:
        #self.collection=chroma_collection
        self.chroma_store=chroma_store
        self.documents=documents

        tokenized=[list(jieba.cut(doc)) for doc in documents]
        self.bm25=BM25Okapi(tokenized)

    async def retriever(self,query:str,k:int):
        #向量检索(不用写了，chroma已经帮我们完成了)
        '''response=await embedding_client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=query,
        )'''
        docs=await self.chroma_store.query(query,k=k)
        #精确检索
        tokenized_query=list(jieba.cut(query))
        tokenized_list=self.bm25.get_top_n(tokenized_query,self.documents,k)
        fin_re=list(dict.fromkeys(docs+tokenized_list))
        #rerank
        re=Reranker()
        return re.rerank(query_text=query,documents=fin_re,k=k)