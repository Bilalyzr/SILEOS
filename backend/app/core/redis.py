"""
Redis mock for testing (when redis is not available)
"""
from typing import Optional, Any
import json
import asyncio

class MockRedis:
    """Mock Redis client for testing"""

    def __init__(self):
        self._data = {}

    async def ping(self):
        return b"PONG"

    async def get(self, key: str):
        return self._data.get(key)

    async def set(self, key: str, value: str):
        self._data[key] = value
        return True

    async def setex(self, key: str, time: int, value: str):
        self._data[key] = value
        return True

    async def delete(self, key: str):
        self._data.pop(key, None)
        return True

    async def exists(self, key: str):
        return 1 if key in self._data else 0

    async def expire(self, key: str, seconds: int):
        return True

    async def incrby(self, key: str, amount: int):
        current = int(self._data.get(key, 0))
        self._data[key] = str(current + amount)
        return current + amount

    async def decrby(self, key: str, amount: int):
        current = int(self._data.get(key, 0))
        self._data[key] = str(current - amount)
        return current - amount

    async def incr(self, key: str):
        return await self.incrby(key, 1)

    async def ttl(self, key: str):
        return 300  # Mock TTL

    async def close(self):
        pass

class RedisClient:
    """Redis client singleton with mock fallback"""

    _instance: Optional[Any] = None

    @classmethod
    async def get_instance(cls):
        """Get Redis instance"""
        if cls._instance is None:
            try:
                # Try to import real redis
                import redis.asyncio as redis
                from .config import get_settings
                settings = get_settings()
                cls._instance = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except ImportError:
                # Fallback to mock
                print("Warning: Redis not available, using mock")
                cls._instance = MockRedis()
        return cls._instance

    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

async def init_redis():
    """Initialize Redis connection"""
    try:
        client = await RedisClient.get_instance()
        await client.ping()
        print("Redis connected successfully")
    except Exception as e:
        print(f"Redis connection failed (using mock): {e}")

async def get_redis():
    """Get Redis client dependency"""
    return await RedisClient.get_instance()

# Cache utilities
class CacheManager:
    """Cache management utilities"""

    @staticmethod
    async def set(key: str, value: Any, expire: Optional[int] = None):
        """Set cache value"""
        client = await get_redis()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)

        if expire:
            await client.setex(key, expire, value)
        else:
            await client.set(key, value)

    @staticmethod
    async def get(key: str) -> Any:
        """Get cache value"""
        client = await get_redis()
        value = await client.get(key)

        if value is None:
            return None

        # Try to parse as JSON first
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    @staticmethod
    async def delete(key: str):
        """Delete cache key"""
        client = await get_redis()
        await client.delete(key)

    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists"""
        client = await get_redis()
        result = await client.exists(key)
        return bool(result)

    @staticmethod
    async def expire(key: str, seconds: int):
        """Set expiration for key"""
        client = await get_redis()
        await client.expire(key, seconds)

    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """Increment counter"""
        client = await get_redis()
        return await client.incrby(key, amount)

    @staticmethod
    async def decrement(key: str, amount: int = 1) -> int:
        """Decrement counter"""
        client = await get_redis()
        return await client.decrby(key, amount)

# Rate limiting
class RateLimiter:
    """Rate limiting utilities"""

    @staticmethod
    async def is_rate_limited(key: str, limit: int, window: int) -> bool:
        """Check if rate limited"""
        client = await get_redis()

        # Get current count
        current = await client.get(key)

        if current is None:
            # First request
            await client.setex(key, window, "1")
            return False

        if int(current) >= limit:
            return True

        # Increment counter
        await client.incr(key)
        return False

    @staticmethod
    async def get_rate_limit_info(key: str) -> dict:
        """Get rate limit information"""
        client = await get_redis()

        current = await client.get(key)
        ttl = await client.ttl(key)

        return {
            "current": int(current) if current else 0,
            "remaining_time": ttl if ttl > 0 else 0
        }