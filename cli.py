import asyncio
import argparse
#from storage.json_storage import JsonStorage
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from database import AsyncSessionLocal
from models.question import Question

async def main() -> None:
    parser = argparse.ArgumentParser(prog="interview-agent", description="面试题库管理工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add 子命令
    add_cmd = subparsers.add_parser("add", help="添加题目")
    add_cmd.add_argument("title", help="题目标题")
    add_cmd.add_argument("-t", "--tags", default="", help="标签，逗号分隔")
    add_cmd.add_argument("-d", "--difficulty", default="medium", help="easy/medium/hard")
    add_cmd.add_argument("-a", "--answer", default="", help="答案")

    # list 子命令
    list_cmd = subparsers.add_parser("list", help="列出题目")
    list_cmd.add_argument("-t", "--tag", help="按标签筛选")

    # search 子命令
    search_cmd = subparsers.add_parser("search", help="搜索题目")
    search_cmd.add_argument("keyword", help="搜索关键词")

    # random 子命令
    rand_cmd = subparsers.add_parser("random", help="随机抽题")
    rand_cmd.add_argument("-t", "--tag", help="按标签筛选")
    rand_cmd.add_argument("-n", "--limit", type=int, default=1, help="抽几道题")

    args = parser.parse_args()
    print(args)

    #storage = JsonStorage("data/questions.json")
    async with AsyncSessionLocal() as session:
        storage=SqlalchemyRepositories(session)


    if args.command == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        q = Question(
            title=args.title,
            tags=tags,
            difficulty=args.difficulty,
            answer=args.answer,
        )
        await storage.add(q)
        print(f"[OK] 已添加：{q.title}")

    elif args.command == "list":
        questions = await storage.list_all(tag=args.tag)
        if not questions:
            print("[空] 暂无题目")
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. [{q.difficulty}] {q.title}")
            print(f"   标签：{', '.join(q.tags)}")

    elif args.command == "search":
        results = await storage.search(args.keyword)
        if not results:
            print(f"[搜索] 未找到与「{args.keyword}」相关的题目")
        for i, q in enumerate(results, 1):
            print(f"\n{i}. [{q.difficulty}] {q.title}")

    elif args.command == "random":
        questions = await storage.random(tag=args.tag, limit=args.limit)
        if not questions:
            print("[空] 暂无题目")
        for i, q in enumerate(questions, 1):
            print(f"\n[抽题] {i}. [{q.difficulty}] {q.title}")
            if q.answer:
                print(f"   答案：{q.answer}")

if __name__ == "__main__":
    asyncio.run(main())
