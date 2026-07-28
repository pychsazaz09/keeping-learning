import json
import os

from redis.asyncio import Redis

# Redis 连接实例（启动时创建，整个应用复用）
redis = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


async def get_cached(key: str) -> dict | list | None:
    """从 Redis 读取缓存数据。

    Args:
        key: 缓存键名

    Returns:
        反序列化后的 dict 或 list；缓存不存在时返回 None
    """
    data = await redis.get(key)
    if not data:
        return None
    return json.loads(data)


async def set_cache(key: str, value, ttl: int = 60):
    """写入 Redis 缓存，设置过期时间。

    Args:
        key: 缓存键名
        value: 要缓存的数据（支持 dict/list，自动 JSON 序列化）
        ttl: 过期秒数，默认 60 秒
    """
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def delete_cache(key: str):
    """删除 Redis 缓存。

    Args:
        key: 要删除的缓存键名
    """
    await redis.delete(key)
