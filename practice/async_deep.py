import asyncio
from contextlib import AsyncExitStack
async def fetch(i:int):
    await asyncio.sleep(2)
    if i==3:
        raise ValueError("i==3")
    print(f"结果{i}")
    return f"结果{i}"

async def demo_gather():
    return await asyncio.gather(*[fetch(i) for i in range(1,5)],return_exceptions=True)

async def demo_create_task():
    t1=asyncio.create_task(fetch(1))
    '''t2=asyncio.create_task(fetch(2))
    t3=asyncio.create_task(fetch(3))
    t4=asyncio.create_task(fetch(4))'''
    print("切出线程并等待所有任务完成")
    t1.cancel()
    try:
        return await t1
    except asyncio.CancelledError:
        print("任务被取消")
    

class FakeConnection:
    def __init__(self,name:str) -> None:

        self.name=name
    async def __aenter__(self):
        await asyncio.sleep(2)
        print(f"[{self.name}] 连接建立")
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.sleep(1)
        print(f"[{self.name}] 连接关闭 (LIFO)")
        return False

async def demo_stack():
    async with AsyncExitStack() as stack:
        c1=await stack.enter_async_context(FakeConnection("Agent"))
        c2=await stack.enter_async_context(FakeConnection("LLM"))
        c3=await stack.enter_async_context(FakeConnection("MCP"))
    print("退出AsyncExitStack上下文管理器")

if __name__=="__main__":
    asyncio.run(demo_create_task())

