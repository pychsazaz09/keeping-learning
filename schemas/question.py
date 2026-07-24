from pydantic import BaseModel

class QuestionResponse(BaseModel):
    id:str
    title:str
    tags:list[str]|None=None
    difficulty:str=""
    answer:str=""

class QuestionCreate(BaseModel):
    title:str
    tags:list[str]|None=None
    difficulty:str=""
    answer:str=""