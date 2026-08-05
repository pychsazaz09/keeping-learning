import faiss 
import numpy as np
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from services.embedding_client import embedding_client



class EmbeddingService:
    def __init__(self) -> None:
        self.dim = 1024
        self.index: faiss.Index | None = None
        self.id_map: list[str] = []
        self.emb=embedding_client


    async def add_index(self,texts:list[str],ids:list[str]):
        self.index = faiss.IndexFlatL2(self.dim)
        for text,id in zip(texts,ids):
            #title_vector = np.random.randn(self.dim)
            response=await self.emb.embeddings.create(
                model="BAAI/bge-large-zh-v1.5",
                input=text,
            )
            vector=response.data[0].embedding
            print(f"*******实际维度: {len(vector)}")
            self.index.add(np.array([vector], dtype=np.float32))
            self.id_map.append(id)

    async def build_index_db(self,repoQ:SqlalchemyRepositories):
        questions=await repoQ.list_all_questions()
        if not questions:
            raise ValueError("题库里没题目")
        texts = [q.title for q in questions]
        ids = [q.id for q in questions]
        await self.add_index(texts,ids)

    async def build_index_md(self):
        with open("data/data_python.md","r",encoding="utf-8") as f:
            text=f.read()
        if not text:
            raise ValueError("md文件为空")
        sections=text.split("##")
        await self.add_index(sections,sections)

    def save_index(self, path: str):
        if self.index is None:
            raise ValueError("Index has not been built")
        faiss.write_index(self.index, path)

    def load_index(self,path:str):
        self.index=faiss.read_index(path)

    async def search(self,query_text:str,k:int=2):
        if self.index is None:
            #raise ValueError("索引未构建，请先调用 build_index()")
            return []
        k=min(k,self.index.ntotal)

        #vector=np.random.randn(self.dim)
        response=await self.emb.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=query_text,
        )
        vector=response.data[0].embedding
        query_vector=np.array([vector],dtype=np.float32)
        distances,indeices=self.index.search(query_vector,k)
        result=[]
        for idx,dist in zip(indeices[0],distances[0]):
            result.append({"id":self.id_map[idx],"distance":dist})
        return result[:k]

