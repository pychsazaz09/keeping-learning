import aiofiles
from langchain_text_splitters import RecursiveCharacterTextSplitter

async def readDoc():
    async with aiofiles.open("D:\\code\\agent-learing\\Python-Learning\\interview-agent\\data\\data_python.md","r",encoding="utf-8") as f:
        context=await f.read()
    if not context:
        return None
    return context


splitter=RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n","\n","。",".",","],
)

async def get_docs_str():
    context=await readDoc()
    if not context:
        return []
    chunks=splitter.split_text(context)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
