"""Day 8 预检：确保 Chroma 索引已构建"""
import asyncio
import sys
sys.path.insert(0, "..")

from services.chroma_service import ChromaStore

DOC_PATH = "../data/data_python.md"

async def main():
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read()
    documents = [s.strip() for s in raw_text.split("##") if s.strip()]
    print(f"文档分片数: {len(documents)}")

    store = ChromaStore("../chroma_db", "chroma_collection")
    print(f"当前集合文档数: {store.collection.count()}")

    if store.collection.count() == 0:
        print("索引为空，正在构建...")
        await store.build_index(documents)
        print(f"构建完成，文档数: {store.collection.count()}")
    else:
        print("索引已存在，跳过构建。")

if __name__ == "__main__":
    asyncio.run(main())
