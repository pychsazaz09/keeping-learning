import random as rand

from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_current_user, get_storage
from models.question import Question
from schemas.question import QuestionCreate
from services import cache_service

router = APIRouter(prefix="/questions", tags=["questions"])

# storage=get_storage()


@router.get("/")
async def list_questions(
    tag: str | None = None,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数，最多 50"),
    storage=Depends(get_storage),
):
    """分页查询题目列表

    分页公式：OFFSET = (page - 1) * page_size, LIMIT = page_size
    """
    offset = (page - 1) * page_size
    questions = await storage.list_all(tag=tag, limit=page_size, offset=offset)
    total = await storage.count(tag=tag)
    return {
        "items": questions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,  # 向上取整
    }


@router.get("/random")
async def random_question(
    tag: str | None = None,
    limit: int = 1,
    storage=Depends(get_storage),
):

    redis_key = f"question:{tag or "all"}"
    cached = await cache_service.get_cached(redis_key)
    if cached:
        questions = [Question(**q) for q in cached]
    else:
        questions = await storage.list_all(tag)
        await cache_service.set_cache(
            redis_key, [q.model_dump(mode="json") for q in questions], ttl=60
        )
    if limit < 1:
        limit = 1
    return rand.sample(questions, min(limit, len(questions)))


@router.get("/{question_id}")
async def get_question(question_id: str, storage=Depends(get_storage)):
    question_list = await storage.list_all()
    if question_list is None:
        raise HTTPException(status_code=404, detail="问题库为空")
    for question in question_list:
        if question.id == question_id:
            return question
    raise HTTPException(status_code=404, detail="找不到这个问题")


@router.post("/")
async def create_question(
    body: QuestionCreate,
    storage=Depends(get_storage),
    current_user=Depends(get_current_user),
):

    q = Question(**body.model_dump())
    await storage.add(q)
    return q


@router.put("/{question_id}")
async def update_question(
    question_id: str,
    body: QuestionCreate,
    storage=Depends(get_storage),
    current_user=Depends(get_current_user),
):

    question_dict = body.model_dump()
    question_dict["id"] = question_id
    question = Question.model_validate(question_dict)
    await storage.update(question)


@router.delete("/{question_id}")
async def delete_question(
    question_id: str,
    storage=Depends(get_storage),
    current_user=Depends(get_current_user),
):

    await storage.delete(question_id)
