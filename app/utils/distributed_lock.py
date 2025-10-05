"""
Distributed Locking System using Redis
As specified in MD file: Redis-based distributed locks for concurrent issue processing
"""
import redis
import time
import asyncio
from typing import Optional
import structlog
import os
from contextlib import asynccontextmanager

logger = structlog.get_logger()

class RedisDistributedLock:
    """
    Redis-based distributed lock implementation as specified in MD file
    Prevents concurrent processing of same issue with exponential backoff retry
    """
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
    def acquire_lock(
        self, 
        lock_key: str, 
        timeout: int = 300,  # 5 minutes default
        retry_delay: float = 0.1,
        max_retries: int = 10
    ) -> Optional[str]:
        """
        Acquire distributed lock with exponential backoff retry as specified in MD file
        Returns lock identifier if successful, None if failed
        """
        lock_value = f"{time.time()}_{os.getpid()}"
        
        for attempt in range(max_retries):
            # Try to acquire lock
            if self.redis_client.set(lock_key, lock_value, nx=True, ex=timeout):
                logger.info(f"Acquired lock: {lock_key}")
                return lock_value
                
            # Exponential backoff as specified in MD file
            wait_time = retry_delay * (2 ** attempt)
            logger.info(f"Lock acquisition failed, retrying in {wait_time:.2f}s (attempt {attempt + 1})")
            time.sleep(wait_time)
        
        logger.warning(f"Failed to acquire lock after {max_retries} attempts: {lock_key}")
        return None
    
    def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """
        Release distributed lock safely using Lua script
        """
        # Lua script to ensure we only release our own lock
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis_client.eval(release_script, 1, lock_key, lock_value)
            if result:
                logger.info(f"Released lock: {lock_key}")
                return True
            else:
                logger.warning(f"Lock was already released or expired: {lock_key}")
                return False
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False
    
    @asynccontextmanager
    async def acquire_lock_async(
        self, 
        lock_key: str, 
        timeout: int = 300,
        retry_delay: float = 0.1,
        max_retries: int = 10
    ):
        """
        Async context manager for distributed locking as used in MD file flowchart
        """
        lock_value = None
        
        try:
            # Convert sync acquire to async
            for attempt in range(max_retries):
                lock_value = f"{time.time()}_{os.getpid()}"
                if self.redis_client.set(lock_key, lock_value, nx=True, ex=timeout):
                    logger.info(f"Acquired async lock: {lock_key}")
                    break
                    
                wait_time = retry_delay * (2 ** attempt)
                logger.info(f"Async lock acquisition failed, retrying in {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            else:
                raise Exception(f"Failed to acquire lock after {max_retries} attempts: {lock_key}")
            
            yield lock_value
            
        finally:
            if lock_value:
                self.release_lock(lock_key, lock_value)

# Global instance
distributed_lock = RedisDistributedLock()

def get_issue_lock_key(issue_id: int) -> str:
    """Generate lock key for issue processing"""
    return f"issue_lock:{issue_id}"

def get_claim_lock_key(issue_id: int, user_id: int) -> str:
    """Generate lock key for claim processing"""
    return f"claim_lock:{issue_id}:{user_id}"