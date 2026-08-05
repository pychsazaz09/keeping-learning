"""
Day 8 噪声实验 v2 —— 模拟"更真实的噪声"：
不是完全不相关的文档，而是"看起来相关但其实在讲另一个东西"的文档。
"""
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

normal_docs = """
文档1: Python 的 GIL（Global Interpreter Lock，全局解释器锁）是 CPython 解释器中的一个互斥锁。它确保同一时刻只有一个线程执行 Python 字节码。即使在多核 CPU 上，CPython 的多线程程序也无法真正并行执行计算密集型任务。
文档2: GIL 的存在简化了 CPython 的内存管理——因为同一时刻只有一个线程在运行，引用计数的增减操作不需要加锁。但对于 IO 密集型任务，GIL 会在 IO 操作时释放，所以多线程对 IO 密集型任务仍然有效。
文档3: Python 中绕过 GIL 的方式包括：使用多进程（multiprocessing 模块，每个进程有独立的 GIL）、使用 C 扩展（C 代码中可以手动释放 GIL）、使用其他 Python 实现（Jython 和 IronPython 没有 GIL）。
"""

# 关键变化：噪声文档看起来"Python相关"，但讲的是另一个概念
tricky_noise = """
文档X: Python 中的锁机制——Python 提供了多种同步原语来处理多线程之间的数据竞争问题。threading.Lock 是最基础的互斥锁，用于保护临界区；threading.RLock 是可重入锁，允许同一个线程多次获取；threading.Semaphore 用于限制同时访问资源的线程数量。这些锁和 GIL 不同——GIL 是解释器级别的，而你代码里的 Lock 是应用级别的。
文档Y: Python 线程安全与死锁——当多个线程同时修改共享数据时，如果没有适当的同步机制，就会产生竞态条件。解决方案包括使用 threading.Lock 或 queue.Queue（线程安全队列）。一个常见的死锁场景是：线程 A 持有锁 1 等待锁 2，线程 B 持有锁 2 等待锁 1——两个线程永远等待下去。Python 的 threading 模块提供了 Lock.acquire(timeout=5) 来设置超时防止死锁。
"""

SYSTEM_PROMPT = "你是一个技术问答助手。请根据提供的参考资料回答问题。"

QUESTION = "Python中的GIL锁是什么？"


async def ask_llm(context: str, label: str):
    prompt = f"""参考资料:
{context}

问题: {QUESTION}"""

    print(f"\n{'='*60}")
    print(f"【{label}】")
    print(f"{'='*60}")

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2048,
        stream=False,
    )

    answer = response.choices[0].message.content
    print(f"LLM 回答:\n{answer}\n")
    return answer


async def main():
    # 对照组
    await ask_llm(normal_docs, "对照组：正常的 GIL 相关文档")

    # 实验组：掺入"看起来像但其实是另一个概念"的文档
    await ask_llm(
        normal_docs + "\n" + tricky_noise,
        "实验组：GIL 文档 + Python threading.Lock 文档（噪声更隐蔽）"
    )

    # 全是隐蔽噪声
    await ask_llm(
        tricky_noise,
        "极端组：只有 threading.Lock 文档，没有 GIL 文档"
    )

    print(f"\n{'='*60}")
    print("【和 v1 实验对比，观察三个问题】")
    print(f"{'='*60}")
    print("1. 这次噪声更隐蔽（都是 Python + 锁），LLM 有没有混淆 GIL 和 threading.Lock？")
    print("2. 如果混淆了，LLM 说的'GIL'的特征，哪些其实是 threading.Lock 的特征？")
    print("3. System Prompt 里没写'请诚实回答'的情况下，LLM 面对不相关文档时还会诚实吗？")


if __name__ == "__main__":
    asyncio.run(main())
