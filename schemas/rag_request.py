from pydantic import BaseModel

class RagRequest(BaseModel):
    question:str
    k:int=2