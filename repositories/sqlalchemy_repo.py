from sqlalchemy.ext.asyncio import AsyncSession
from models.question import Question
from models.question_orm import QuestionTable
from sqlalchemy import select
import json
import random as rand
class SqlalchemyRepositories:

    def __init__(self,session:AsyncSession):
        self.session=session
    def _to_pydantic(self, row: QuestionTable) -> Question:
        question=Question(
            id=row.id,
            title=row.title,
            tags=json.loads(row.tags) if row.tags else [],
            difficulty=row.difficulty,
            answer=row.answer,
        )
        return question


    async def add(self,question:Question):
        row=QuestionTable(
            id=question.id,
            title=question.title,
            tags=json.dumps(question.tags),
            difficulty=question.difficulty,
            answer=question.answer,
        )
        self.session.add(row)
        await self.session.commit()
    async def list_all(self,tag:str|None=None)->list[Question]:
        stmt=select(QuestionTable)
        if tag:
            stmt=stmt.where(QuestionTable.tags.contains(tag))
        result=await self.session.execute(stmt)
        rows=result.scalars().all()
        return [self._to_pydantic(r) for r in rows]

    async def search(self,keyword:str)->list[Question]:
        stmt=select(QuestionTable).where(QuestionTable.title.ilike(f"%{keyword}%")|QuestionTable.tags.contains(keyword))
        result=await self.session.execute(stmt)
        rows=result.scalars().all()
        return [self._to_pydantic(r) for r in rows]

    async def random(self,tag:str|None=None,limit:int=1)->list[Question]:
        stmt=select(QuestionTable)
        if tag:
            stmt=stmt.where(QuestionTable.tags.ilike(f"%{tag}%"))
        result=await self.session.execute(stmt)
        rows=result.scalars().all()
        questions=[self._to_pydantic(r) for r in rows]
        if not questions:
            return []
        if limit<=0:
            limit=1
        return rand.sample(questions,min(limit,len(questions)))

    async def update(self,question:Question):
        stmt=select(QuestionTable).where(QuestionTable.id==question.id)
        result=await self.session.execute(stmt)
        row=result.scalars().first()
        if row is None:
            return
        row.title = question.title
        row.tags = json.dumps(question.tags, ensure_ascii=False)
        row.difficulty = question.difficulty
        row.answer = question.answer
        await self.session.commit()

    async def delete(self,question_id:str):
        stmt=select(QuestionTable).where(QuestionTable.id==question_id)
        result=await self.session.execute(stmt)
        row=result.scalars().first()
        if row is None:
            return
        await self.session.delete(row)
        await self.session.commit()


        