from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self):
        self.model=CrossEncoder("BAAI/bge-reranker-v2-m3")

    def rerank(self,query_text:str,documents:list[str],k:int):
        pairs=[[query_text,doc]for doc in documents]
        scores=self.model.predict(pairs)
        ranked=sorted(zip(documents,scores),key=lambda x:x[1],reverse=True)
        return [doc for doc,_ in ranked[:k]]