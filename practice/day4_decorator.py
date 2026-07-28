"""Day 4 补课 — 装饰器三层递进练习

阅读理解要点：
  装饰器 = 高阶函数：接收函数，返回函数
  @timer  def f(): ...  等价于  f = timer(f)

用在什么场景 vs 中间件：
  装饰器：给单个函数加能力（重试、缓存、鉴权）
  中间件：给所有请求加能力（日志、CORS）
"""

import asyncio
import time
from functools import wraps


# ============================================================
# ① 无参装饰器 — 计时器
# ============================================================
def timer(func):
    """计时装饰器：打印函数执行耗时"""

    @wraps(func)  # ← 必须！否则 func.__name__ 变成 "wrapper"
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)  # ← 执行原函数
        elapsed = time.perf_counter() - start
        print(f"[timer] {func.__name__} 耗时 {elapsed:.3f}s")
        return result

    return wrapper  # ← 必须！装饰器必须返回新函数


@timer
def slow_task():
    """模拟耗时操作"""
    time.sleep(1.5)


@timer
def add(a: int, b: int) -> int:
    return a + b


# ============================================================
# ② 带参装饰器 — 重试（三层结构！）
# ============================================================
def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器：失败后自动重试 max_attempts 次"""

    def decorator(func):  # ← 第二层：接收被装饰函数
        @wraps(func)
        async def wrapper(*args, **kwargs):  # ← 第三层：实际执行
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    print(f"[retry] 第 {attempt}/{max_attempts} 次失败: {e}")
                    if attempt == max_attempts:
                        raise  # 最后一次 → 真的抛出
                    await asyncio.sleep(delay)
            return None

        return wrapper

    return decorator


# 模拟一个不稳定的 LLM 调用
call_count = 0


@retry(max_attempts=3, delay=0.1)
async def call_llm(prompt: str) -> str:
    global call_count
    call_count += 1
    if call_count < 3:  # 前两次失败，第三次成功
        raise ConnectionError("LLM 服务暂时不可用")
    return f"LLM 回复: 收到你的消息「{prompt}」"


# ============================================================
# ③ 类装饰器 — 单例模式（需要维护状态）
# ============================================================
class Singleton:
    """单例装饰器：一个类只有一个实例"""

    _instances = {}

    def __init__(self, cls):
        self._cls = cls

    def __call__(self, *args, **kwargs):
        if self._cls not in self._instances:
            self._instances[self._cls] = self._cls(*args, **kwargs)
            print(f"[Singleton] 首次创建 {self._cls.__name__} 实例")
        return self._instances[self._cls]


@Singleton
class Database:
    def __init__(self):
        import random

        self.connection_id = random.randint(1000, 9999)


# ============================================================
# 验证入口
# ============================================================
async def main():
    print("=" * 50)
    print("① 无参装饰器 @timer")
    print("=" * 50)
    slow_task()
    result = add(3, 5)
    print(f"  add(3, 5) = {result}")
    # 验证 @wraps 是否生效
    print(f"  slow_task.__name__ = {slow_task.__name__}")  # 应该是 slow_task
    print(f"  slow_task.__doc__  = {slow_task.__doc__}")

    print()
    print("=" * 50)
    print("② 带参装饰器 @retry")
    print("=" * 50)
    try:
        result = await call_llm("什么是 Python 装饰器？")
        print(f"  最终结果: {result}")
    except Exception as e:
        print(f"  最终失败: {e}")

    print()
    print("=" * 50)
    print("③ 类装饰器 @Singleton")
    print("=" * 50)
    db1 = Database()
    db2 = Database()
    print(f"  db1.connection_id = {db1.connection_id}")
    print(f"  db2.connection_id = {db2.connection_id}")
    print(f"  db1 is db2 -> {db1 is db2}")  # 应该 True


if __name__ == "__main__":
    asyncio.run(main())
