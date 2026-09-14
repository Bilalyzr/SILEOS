"""
Redis connection and utilities
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle
from datetime import timedelta

from .config import get_settings

settings = get_settings()

class RedisClient:
    """Redis client singleton"""

    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        """Get Redis instance"""
        if cls._instance is None:
            cls._instance = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
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
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

async def get_redis() -> redis.Redis:
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
            value = pickle.dumps(value)

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
            # Try pickle if JSON fails
            try:
                return pickle.loads(value.encode() if isinstance(value, str) else value)
            except:
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
        return await client.exists(key)

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

# Session management
class SessionManager:
    """Session management utilities"""

    SESSION_PREFIX = "session:"

    @staticmethod
    async def create_session(user_id: int, session_data: dict) -> str:
        """Create user session"""
        import uuid
        session_id = str(uuid.uuid4())
        key = f"{SessionManager.SESSION_PREFIX}{session_id}"

        session_data.update({
            "user_id": user_id,
            "created_at": str(timedelta.now())
        })

        await CacheManager.set(key, session_data, expire=86400)  # 24 hours
        return session_id

    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """Get session data"""
        key = f"{SessionManager.SESSION_PREFIX}{session_id}"
        return await CacheManager.get(key)

    @staticmethod
    async def update_session(session_id: str, data: dict):
        """Update session data"""
        key = f"{SessionManager.SESSION_PREFIX}{session_id}"
        existing_data = await CacheManager.get(key) or {}
        existing_data.update(data)
        await CacheManager.set(key, existing_data, expire=86400)

    @staticmethod
    async def delete_session(session_id: str):
        """Delete session"""
        key = f"{SessionManager.SESSION_PREFIX}{session_id}"
        await CacheManager.delete(key)

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
            await client.setex(key, window, 1)
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

# Course progress caching
class CourseProgressCache:
    """Cache course progress data"""

    @staticmethod
    def get_progress_key(user_id: int, course_id: int) -> str:
        """Get cache key for course progress"""
        return f"progress:{user_id}:{course_id}"

    @staticmethod
    async def set_progress(user_id: int, course_id: int, progress_data: dict):
        """Cache course progress"""
        key = CourseProgressCache.get_progress_key(user_id, course_id)
        await CacheManager.set(key, progress_data, expire=3600)  # 1 hour

    @staticmethod
    async def get_progress(user_id: int, course_id: int) -> Optional[dict]:
        """Get cached course progress"""
        key = CourseProgressCache.get_progress_key(user_id, course_id)
        return await CacheManager.get(key)

    @staticmethod
    async def invalidate_progress(user_id: int, course_id: int):
        """Invalidate course progress cache"""
        key = CourseProgressCache.get_progress_key(user_id, course_id)
        await CacheManager.delete(key)