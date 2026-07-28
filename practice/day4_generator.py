"""Day 4 补课 — 生成器 yield / yield from 练习

阅读理解要点：
  普通函数：return → 一次性返回全部 → 结束
  生成器：  yield → 吐出一个值 → 暂停（下次 next() 从暂停处继续）

用在什么场景：
  - 读大文件（逐行 yield，内存 O(1)）
  - 惰性序列（range(1000000) 不创建 100 万个元素）
  - 资源管理（FastAPI Depends 的 yield — 获取→交出→释放）
  - 流式数据（逐 chunk 返回 LLM 生成内容）

和 Java 对照：
  Python yield ≈ Java 的 Iterator 模式
  Python yield from ≈ Java Stream.concat()
  FastAPI Depends yield ≈ Java @Transactional + try-with-resources
"""

import asyncio
import os
import tempfile


# ============================================================
# ① 基本生成器 — 读大文件（模拟）
# ============================================================
def read_lines(text: str):
    """逐行 yield，内存里只有当前行"""
    for line in text.split("\n"):
        yield line.strip()


# ============================================================
# ② yield from — 委托给另一个生成器
# ============================================================
def all_lines(*texts: str):
    """从多个源逐行读取，调用方不需要知道有几个源"""
    for text in texts:
        yield from read_lines(text)  # ← 等价于 for line in read_lines(text): yield line


# ============================================================
# ③ yield 资源管理模式 — FastAPI Depends 的核心
# ============================================================
class FakeSession:
    """模拟数据库会话"""

    def __init__(self, name: str):
        self.name = name
        print(f"  [DB] 开启会话: {name}")

    async def close(self):
        print(f"  [DB] 关闭会话: {self.name}")


async def get_db():
    """模拟 FastAPI 的 get_db 依赖 — yield 前获取，yield 后释放"""
    session = FakeSession("request-001")
    try:
        yield session  # ← ① 交出 session → 路由函数用它
    finally:
        await session.close()  # ← ② 路由返回后执行（无论成功/异常）


async def route_handler():
    """模拟一个路由函数"""
    gen = get_db()
    try:
        session = await gen.__anext__()  # ← 拿到 yield 交出的 session
        print(f"  [路由] 正在使用会话: {session.name}")
        # raise ValueError("模拟异常")  # 取消注释测试 finally 是否执行
    finally:
        try:
            await gen.__anext__()  # ← 驱动生成器继续，执行 yield 后面的 finally
        except StopAsyncIteration:
            pass  # 正常结束


# ============================================================
# ④ 列表 vs 生成器的内存对比
# ============================================================
def memory_demo():
    """对比：列表一次性加载 vs 生成器懒加载"""
    import sys

    # 列表方式：一次性创建 100 万个元素
    list_way = [i * 2 for i in range(1_000_000)]
    list_size = sys.getsizeof(list_way)

    # 生成器方式：不创建，只在迭代时才计算
    gen_way = (i * 2 for i in range(1_000_000))
    gen_size = sys.getsizeof(gen_way)

    print(f"  列表 [100 万个元素]: {list_size / 1024 / 1024:.1f} MB")
    print(f"  生成器 (等量数据):   {gen_size} bytes (~0 MB)")
    print(f"  内存节省:            {list_size / gen_size:.0f}x")


# ============================================================
# 验证入口
# ============================================================
async def main():
    print("=" * 50)
    print("① 基本生成器 — yield 逐行")
    print("=" * 50)
    text = "Python\n生成器\nyield\n学习"
    gen = read_lines(text)
    print(f"  next(gen) = {next(gen)}")  # Python
    print(f"  next(gen) = {next(gen)}")  # 生成器
    print(f"  list(剩余) = {list(gen)}")  # ['yield', '学习']

    print()
    print("=" * 50)
    print("② yield from — 委托合并多个生成器")
    print("=" * 50)
    for line in all_lines("A\nB\nC", "D\nE"):
        print(f"  → {line}")

    print()
    print("=" * 50)
    print("③ yield 资源管理模式 — FastAPI Depends 核心")
    print("=" * 50)
    await route_handler()

    print()
    print("=" * 50)
    print("④ 列表 vs 生成器 内存对比")
    print("=" * 50)
    memory_demo()

    print()
    print("=" * 50)
    print("⑤ 易错：生成器只能迭代一次！")
    print("=" * 50)
    g = (x for x in range(3))
    print(f"  第一次遍历: {list(g)}")  # [0, 1, 2]
    print(f"  第二次遍历: {list(g)}")  # [] ← 消耗品！


if __name__ == "__main__":
    asyncio.run(main())
