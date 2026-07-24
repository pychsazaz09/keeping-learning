import json
import random as rand
from pathlib import Path
import aiofiles

from models.question import Question


class JsonStorage:
    """JSON 文件持久化存储 —— 所有题目存为一个 JSON 数组"""

    def __init__(self, file_path: str):
        self.file_path=Path(file_path)

    async def _read_all(self) -> list[dict]:
        """读取全部题目，返回字典列表"""
        if not self.file_path.exists():
            return []
        async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content) if content.strip() else []

    async def _write_all(self, data: list[dict]) -> None:
        """写入全部题目"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    # ── 对外接口 ──

    async def add(self, question: Question) -> None:
        questions = await self._read_all()
        questions.append(question.model_dump())
        await self._write_all(questions)

    async def list_all(self, tag: str | None = None) -> list[Question]:
        questions = await self._read_all()
        result = [Question(**q) for q in questions]
        if tag:
            result = [q for q in result if tag in q.tags]
        return result

    async def search(self, keyword: str) -> list[Question]:
        questions = await self._read_all()
        kw = keyword.lower()
        return [
            Question(**q) for q in questions
            if kw in q["title"].lower() or kw in q["answer"].lower()
        ]

    async def random(self, tag: str | None = None, limit: int = 1) -> list[Question]:
        questions = await self.list_all(tag=tag)
        if not questions:
            return []
        return rand.sample(questions, min(limit, len(questions)))

    async def update(self,question:Question):
        question_dicts=await self._read_all()
        if not question_dicts:
            raise StorageError("题目库为空")
        for q in question_dicts:
            if question.id==q["id"]:
                q.update(question.model_dump())
                await self._write_all(question_dicts)
                return
        

    async def delete(self,question_id:str):
        question_dicts=await self._read_all()
        if not question_dicts:
            raise StorageError("题目库为空")
        for q in question_dicts:
            if question_id==q["id"]:
                question_dicts.remove(q)
                await self._write_all(question_dicts)
                return
        raise StorageError("题目库为空")

class StorageError(Exception):     # 纯 Python，无第三方依赖
    pass

    