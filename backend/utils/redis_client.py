"""
Redis 클라이언트 및 연결 관리
"""

import redis.asyncio as aioredis
from typing import Optional
from loguru import logger

import config


class RedisManager:
    """Redis 연결 관리자 (싱글톤)"""

    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.enabled = config.REDIS_ENABLED

    async def connect(self):
        """Redis 연결 생성"""
        if not self.enabled:
            logger.info("Redis 캐싱이 비활성화되어 있습니다")
            return

        if self.client is not None:
            logger.info("Redis가 이미 연결되어 있습니다")
            return

        try:
            self.client = await aioredis.from_url(
                f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
                password=config.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=False,  # 바이너리 데이터 지원
                max_connections=10,
            )

            # 연결 테스트
            await self.client.ping()
            logger.info(
                f"✓ Redis 연결 성공: {config.REDIS_HOST}:{config.REDIS_PORT}"
            )

        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            logger.warning("Redis 없이 동작합니다 (캐싱 비활성화)")
            self.client = None
            self.enabled = False

    async def close(self):
        """Redis 연결 종료"""
        if self.client:
            await self.client.close()
            logger.info("Redis 연결 종료")
            self.client = None

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Redis 클라이언트 반환"""
        if not self.enabled:
            return None

        if self.client is None:
            await self.connect()

        return self.client

    def is_available(self) -> bool:
        """Redis 사용 가능 여부"""
        return self.enabled and self.client is not None


# 전역 Redis 관리자 인스턴스 (싱글톤)
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """전역 Redis 관리자 인스턴스 반환"""
    global _redis_manager

    if _redis_manager is None:
        _redis_manager = RedisManager()

    return _redis_manager


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Redis 클라이언트 반환 (편의 함수)"""
    manager = get_redis_manager()
    return await manager.get_client()
