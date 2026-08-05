"""
Day 8 噪声实验脚本 —— 非流式调 LLM，方便看清完整回答。
跑完实验删掉即可，不用集成到项目。
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

# ============================================================
# 准备你的"正常检索结果"——这里你需要换成你实际检索到的文档内容
# ============================================================
normal_docs = """
文档1: Python 的 GIL（Global Interpreter Lock，全局解释器锁）是 CPython 解释器中的一个互斥锁。它确保同一时刻只有一个线程执行 Python 字节码。这意味着即使在多核 CPU 上，CPython 的多线程程序也无法真正并行执行计算密集型任务。
文档2: GIL 的存在简化了 CPython 的内存管理——因为同一时刻只有一个线程在运行，引用计数的增减操作不需要加锁。但代价是 CPU 密集型多线程程序几乎无法利用多核优势。对于 IO 密集型任务（网络请求、文件读写），GIL 会在 IO 操作时释放，所以影响较小。
文档3: Python 中绕过 GIL 的方式包括：使用多进程（multiprocessing 模块，每个进程有独立的 GIL）、使用 C 扩展（C 代码中可以手动释放 GIL）、使用其他 Python 实现（Jython 和 IronPython 没有 GIL）。
"""

# ============================================================
# 噪声文档 —— 与 GIL 完全无关
# ============================================================
noise_docs = """
文档X: HTML 文档结构基础——每个 HTML 页面都从一个标准的文档结构开始。<!DOCTYPE html> 声明告诉浏览器这是一个 HTML5 文档。<html> 标签是整个页面的根元素，包含 lang 属性来指定页面语言。常见 HTML 标签包括 h1 到 h6 标题标签、p 段落标签、a 超链接标签、img 图片标签、div 块级容器和 span 行内容器。
文档Y: CSS 样式与布局入门——CSS（层叠样式表）用于控制 HTML 页面的视觉效果。Flexbox 是 CSS3 引入的一维布局模型，常见模式 display: flex; justify-content: center; align-items: center 可以实现水平垂直居中。CSS Grid 是二维布局系统，通过 grid-template-columns 和 grid-template-rows 定义网格结构。
"""

SYSTEM_PROMPT = "你是一个技术问答助手。请根据提供的参考资料回答问题。如果参考资料中没有相关信息，请诚实告知。"

QUESTION = "Python中的IGL锁是什么？"


async def ask_llm(context: str, label: str):
    """非流式调用 LLM，打印完整回答"""
    prompt = f"""参考资料:
{context}

问题: {QUESTION}"""

    print(f"\n{'='*60}")
    print(f"【{label}】")
    print(f"{'='*60}")
    print(f"Prompt 中参考文档数量: {context.count('文档')} 篇\n")

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2048,
        stream=False,  # 非流式，一次返回完整结果
    )

    answer = response.choices[0].message.content
    print(f"LLM 回答:\n{answer}\n")
    return answer


async def main():
    # 实验 1：正常检索结果
    answer_normal = await ask_llm(normal_docs, "实验1（对照组）：正常检索结果")

    # 实验 2：注入噪声 —— 在正常文档后追加两篇无关文档
    answer_noise = await ask_llm(
        normal_docs + "\n" + noise_docs,
        "实验2（噪声组）：正常文档 + 两篇 HTML/CSS 无关文档"
    )

    # 实验 3：全是噪声 —— 只保留无关文档
    answer_only_noise = await ask_llm(
        noise_docs,
        "实验3（全噪声组）：只有 HTML/CSS 无关文档"
    )

    # 简单对比
    print(f"\n{'='*60}")
    print("【对比总结】")
    print(f"{'='*60}")
    print(f"对照组长度: {len(answer_normal or '')} 字符")
    print(f"噪声组长度: {len(answer_noise or '')} 字符")
    print(f"全噪声组长度: {len(answer_only_noise or '')} 字符")
    print("\n手动对比上面的三个回答，记录你的观察。")


if __name__ == "__main__":
    asyncio.run(main())
