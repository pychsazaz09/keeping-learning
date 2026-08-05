"""
Day 8 核心实验：RAG 噪声注入 —— 理解 RAG 的脆弱性

三个实验，每个都会暴露 RAG 在不同失败模式下 LLM 的真实行为。
跑之前先猜：你觉得 LLM 会怎么反应？跑完之后对比你的猜测和实际结果。
"""

import asyncio
import sys
sys.path.insert(0, "..")

from services.chroma_service import ChromaStore
from services.rag_service import RagRetriever
from services.reranker import Reranker
from services.llm_client import get_llm_client


async def ask_llm(prompt: str) -> str:
    """非流式调用 LLM，返回完整文本。用于实验对比，不用 StreamingResponse。"""
    client = get_llm_client()
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个技术面试助手。请简洁准确地回答问题。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ── 准备：加载你的知识库 ──
DOC_PATH = "../data/data_python.md"
with open(DOC_PATH, "r", encoding="utf-8") as f:
    raw_text = f.read()

# 按 ## 分片（和你现有逻辑一致）
documents = [s.strip() for s in raw_text.split("##") if s.strip()]

chroma_store = ChromaStore("../chroma_db", "chroma_collection")
retriever = RagRetriever(chroma_store, documents)


# ══════════════════════════════════════════════════════════════
# 实验 1：噪声注入 —— 不相关文档混入检索结果
# ══════════════════════════════════════════════════════════════
async def experiment_1_noise_injection():
    """
    场景：正常的 RAG 检索返回 3 篇文档，其中 2 篇相关、1 篇不相关。
    问题：LLM 会被那篇不相关文档带偏吗？

    你的猜测（写下来再跑）：_______________________
    """

    print("\n" + "=" * 60)
    print("实验 1：噪声注入")
    print("=" * 60)

    query = "Python 中的装饰器是什么？怎么用？"

    # Step 1: 正常检索（干净的结果作参照）
    print("\n>>> 正常检索结果（参照组）：")
    clean_docs = await retriever.retriever(query, k=3)
    for i, doc in enumerate(clean_docs):
        print(f"  [{i}] {doc[:120]}...")

    # Step 2: 构造噪声 —— 注入一篇完全不相关的"文档"
    noise_doc = """
    2024年NBA季后赛精彩回顾：波士顿凯尔特人队在总决赛中以4-1击败达拉斯独行侠队，
    赢得队史第18座总冠军。杰森·塔图姆场均贡献27.5分、8.3篮板、5.7助攻，
    荣膺总决赛MVP。独行侠队卢卡·东契奇虽然场均32分但仍无力回天。
    """
    noisy_docs = [noise_doc] + clean_docs[:2]  # 噪声 + 2篇相关
    # 重排序（模拟检索噪声）
    reranker = Reranker()
    noisy_docs = reranker.rerank(query, noisy_docs, k=3)

    print("\n>>> 噪声注入后的检索结果：")
    for i, doc in enumerate(noisy_docs):
        print(f"  [{i}] {doc[:120]}...")

    # Step 3: 分别让 LLM 回答
    context_clean = "\n".join(clean_docs)
    prompt_clean = f"参考资料:\n{context_clean}\n\n问题: {query}\n\n请根据参考资料回答。如果资料中没有相关信息，请明确说'参考资料中未找到相关信息'。"

    context_noisy = "\n".join(noisy_docs)
    prompt_noisy = f"参考资料:\n{context_noisy}\n\n问题: {query}\n\n请根据参考资料回答。如果资料中没有相关信息，请明确说'参考资料中未找到相关信息'。"

    print("\n>>> 干净检索 → LLM 回答：")
    answer_clean = await ask_llm(prompt_clean)
    print(f"\n---\n{answer_clean}")

    print("\n\n>>> 噪声检索 → LLM 回答：")
    answer_noisy = await ask_llm(prompt_noisy)
    print(f"\n---\n{answer_noisy}")

    # Step 4: 对比分析
    print("\n\n>>> 分析（你自己填写）：")
    print("  1. 噪声文档是否出现在 LLM 的回答中？")
    print("  2. LLM 的回答质量下降了多少？")
    print("  3. 如果这是生产环境，用户会注意到什么异常？")

    return answer_clean, answer_noisy


# ══════════════════════════════════════════════════════════════
# 实验 2：关键文档缺失 —— LLM 会编造吗？
# ══════════════════════════════════════════════════════════════
async def experiment_2_missing_key_doc():
    """
    场景：用户问了一个问题，正确答案在知识库的某篇文档中。
    但检索系统把那篇文档漏掉了。
    问题：LLM 会诚实地回答"不知道"？还是会根据自己的参数化知识编造？

    你的猜测（写下来再跑）：_______________________
    """

    print("\n" + "=" * 60)
    print("实验 2：关键文档缺失")
    print("=" * 60)

    # 选一个你的知识库中确实有答案的问题
    query = "Python 中 async/await 的原理是什么？"

    # Step 1: 正常检索（包含正确文档）
    print("\n>>> 完整检索结果：")
    full_docs = await retriever.retriever(query, k=3)
    for i, doc in enumerate(full_docs):
        print(f"  [{i}] {doc[:150]}...")

    # Step 2: 故意移除最相关的文档（模拟检索失败）
    missing_docs = full_docs[1:]  # 丢掉第 1 篇（最相关的）
    print("\n>>> 移除最相关文档后：")
    for i, doc in enumerate(missing_docs):
        print(f"  [{i}] {doc[:150]}...")

    # Step 3: 对比 LLM 行为
    context_full = "\n".join(full_docs)
    prompt_full = f"参考资料:\n{context_full}\n\n问题: {query}\n\n请严格根据参考资料回答。如果资料中没有的信息，必须明确说明。"

    context_missing = "\n".join(missing_docs)
    prompt_missing = f"参考资料:\n{context_missing}\n\n问题: {query}\n\n请严格根据参考资料回答。如果资料中没有的信息，必须明确说明。"

    print("\n>>> 完整检索 → LLM 回答：")
    answer_full = await ask_llm(prompt_full)
    print(f"\n---\n{answer_full}")

    print("\n\n>>> 缺失检索 → LLM 回答：")
    answer_missing = await ask_llm(prompt_missing)
    print(f"\n---\n{answer_missing}")

    # Step 4: 分析
    print("\n\n>>> 分析（你自己填写）：")
    print("  1. LLM 在缺失正确文档时，是编造了答案还是诚实地说不知道？")
    print("  2. 编造的答案和正确答案有多大差距？")
    print("  3. 这个实验告诉你 RAG 系统最脆弱的地方是什么？")


# ══════════════════════════════════════════════════════════════
# 实验 3：排序质量对比 —— 重排序到底有没有用？
# ══════════════════════════════════════════════════════════════
async def experiment_3_reranker_value():
    """
    场景：同一个查询，对比「不做重排序」「仅 BM25」「仅向量」「混合+重排序」四种策略。
    问题：你的 Reranker 花了额外的推理时间，它到底值不值？

    你的猜测（写下来再跑）：_______________________
    """

    print("\n" + "=" * 60)
    print("实验 3：重排序的价值")
    print("=" * 60)

    query = "Python 中如何实现单例模式？"

    # 向量检索 Top 5
    vector_results = await chroma_store.query(query, k=5)
    print("\n>>> 仅向量检索 Top 5：")
    for i, doc in enumerate(vector_results):
        print(f"  [{i}] {doc[:100]}...")

    # BM25 检索 Top 5
    import jieba
    from rank_bm25 import BM25Okapi
    tokenized_docs = [list(jieba.cut(d)) for d in documents]
    bm25 = BM25Okapi(tokenized_docs)
    tokenized_query = list(jieba.cut(query))
    bm25_results = bm25.get_top_n(tokenized_query, documents, n=5)
    print("\n>>> 仅 BM25 检索 Top 5：")
    for i, doc in enumerate(bm25_results):
        print(f"  [{i}] {doc[:100]}...")

    # 混合 + 重排序（你现在的方案）
    reranker = Reranker()
    merged = list(dict.fromkeys(vector_results + bm25_results))
    reranked = reranker.rerank(query, merged, k=5)
    print("\n>>> 混合 + 重排序 Top 5：")
    for i, doc in enumerate(reranked):
        print(f"  [{i}] {doc[:100]}...")

    # 用 LLM 回答同一问题，对比策略
    async def answer_with(strategy_name, docs_list):
        context = "\n".join(docs_list[:3])
        prompt = f"参考资料:\n{context}\n\n问题: {query}\n\n请根据参考资料回答。"
        answer = await ask_llm(prompt)
        print(f"\n>>> {strategy_name} → 答案：\n{answer[:300]}...")
        return answer

    await answer_with("仅向量", vector_results)
    await answer_with("仅 BM25", bm25_results)
    await answer_with("混合+重排序", reranked)

    print("\n\n>>> 分析（你自己填写）：")
    print("  1. 四种策略的答案质量排序是？")
    print("  2. 重排序改变了前 3 篇文档的顺序吗？改变后答案变好了还是变差了？")
    print("  3. 结论：你的 Reranker 值得那个额外的推理时间吗？")


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════
async def main():
    print("Day 8 噪声注入实验")
    print("每个实验跑之前，先在纸上写下你的猜测。")
    print("跑完后对比：哪些你猜对了？哪些让你意外？")
    print()

    await experiment_1_noise_injection()
    await experiment_2_missing_key_doc()
    await experiment_3_reranker_value()

    print("\n\n" + "=" * 60)
    print("三个实验全部完成。最重要的输出不是代码，而是你写在分析区域的答案。")
    print("面试官问'RAG失败了怎么办'——你的回答应该来自这些实验，而非猜测。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
