from fastapi import APIRouter
from dependencies import get_storage
from schemas.question import (QuestionCreate,QuestionResponse)
from models.question import Question
from fastapi import HTTPException


router=APIRouter(prefix="/questions",tags=["questions"])

storage=get_storage()

@router.get("/")
async def list_questions(tag:str|None=None):
    return await storage.list_all(tag=tag)

@router.get("/random")
async def random_question(tag:str|None=None,limit:int=1):
    return await storage.random(tag,limit)

@router.get("/{question_id}")
async def get_question(question_id:str):
    question_list=await storage.list_all()
    if question_list is None:
        raise HTTPException(status_code=404,detail="问题库为空")
    for question in question_list:
        if question.id==question_id:
            return question
    raise HTTPException(status_code=404,detail="找不到这个问题")

@router.post("/")
async def create_question(body:QuestionCreate):
    q=Question(**body.model_dump())
    await storage.add(q)
    return q

@router.put("/{question_id}")
async def update_question(question_id:str,body:QuestionCreate):
    question_dict=body.model_dump()
    question_dict["id"]=question_id
    question=Question.model_validate(question_dict)
    await storage.update(question)

@router.delete("/{question_id}")
async def delete_question(question_id:str):
    await storage.delete(question_id)


        

