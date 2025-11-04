"""
캐싱 서비스
Redis 기반 캐싱 및 LRU 전략
"""

import hashlib
import json
import pickle
from typing import Optional, Any, Dict
from loguru import logger

import config
from utils.redis_client import get_redis_client


class CacheService:
    """캐싱 서비스 클래스"""

    @staticmethod
    def generate_cache_key(prefix: str, **kwargs) -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 프리픽스
            **kwargs: 키 생성에 사용할 파라미터

        Returns:
            생성된 캐시 키
        """
        # 파라미터를 정렬하여 일관된 키 생성
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)

        # SHA256 해시 생성
        hash_obj = hashlib.sha256(params_str.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]  # 처음 16자만 사용

        return f"{prefix}:{hash_hex}"

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """
        캐시에서 데이터 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 데이터 또는 None
        """
        redis = await get_redis_client()
        if redis is None:
            return None

        try:
            data = await redis.get(key)
            if data is None:
                logger.debug(f"캐시 미스: {key}")
                return None

            # pickle로 역직렬화
            result = pickle.loads(data)
            logger.debug(f"캐시 히트: {key}")
            return result

        except Exception as e:
            logger.error(f"캐시 조회 실패: {key}, 에러: {e}")
            return None

    @staticmethod
    async def set(
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 데이터 저장

        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: Time To Live (초), None이면 무제한

        Returns:
            성공 여부
        """
        redis = await get_redis_client()
        if redis is None:
            return False

        try:
            # pickle로 직렬화
            serialized = pickle.dumps(value)

            if ttl:
                await redis.setex(key, ttl, serialized)
            else:
                await redis.set(key, serialized)

            logger.debug(f"캐시 저장: {key} (TTL: {ttl}초)")
            return True

        except Exception as e:
            logger.error(f"캐시 저장 실패: {key}, 에러: {e}")
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """
        캐시에서 데이터 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        redis = await get_redis_client()
        if redis is None:
            return False

        try:
            result = await redis.delete(key)
            logger.debug(f"캐시 삭제: {key}")
            return result > 0

        except Exception as e:
            logger.error(f"캐시 삭제 실패: {key}, 에러: {e}")
            return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """
        패턴과 일치하는 모든 키 삭제

        Args:
            pattern: 키 패턴 (예: "zonos_tts:speaker_embedding:*")

        Returns:
            삭제된 키 개수
        """
        redis = await get_redis_client()
        if redis is None:
            return 0

        try:
            # 패턴과 일치하는 모든 키 찾기
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    deleted = await redis.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            logger.info(f"캐시 패턴 삭제: {pattern} (삭제됨: {deleted_count}개)")
            return deleted_count

        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패: {pattern}, 에러: {e}")
            return 0

    @staticmethod
    async def exists(key: str) -> bool:
        """
        캐시 키 존재 여부 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        redis = await get_redis_client()
        if redis is None:
            return False

        try:
            return await redis.exists(key) > 0
        except Exception as e:
            logger.error(f"캐시 존재 확인 실패: {key}, 에러: {e}")
            return False

    @staticmethod
    async def get_ttl(key: str) -> Optional[int]:
        """
        캐시 키의 남은 TTL 조회

        Args:
            key: 캐시 키

        Returns:
            남은 TTL (초) 또는 None
        """
        redis = await get_redis_client()
        if redis is None:
            return None

        try:
            ttl = await redis.ttl(key)
            if ttl < 0:  # -1: 만료 없음, -2: 키 없음
                return None
            return ttl
        except Exception as e:
            logger.error(f"캐시 TTL 조회 실패: {key}, 에러: {e}")
            return None

    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 통계 정보
        """
        redis = await get_redis_client()
        if redis is None:
            return {
                "enabled": False,
                "message": "Redis가 연결되어 있지 않습니다"
            }

        try:
            # Redis INFO 명령 실행
            info = await redis.info()

            # DB 정보 조회
            db_info = await redis.info('keyspace')
            db_key = f'db{config.REDIS_DB}'
            db_stats = db_info.get(db_key, {})

            # 캐시 크기 계산 (MB)
            memory_used_bytes = info.get('used_memory', 0)
            memory_used_mb = memory_used_bytes / (1024 * 1024)

            # 키 개수 계산
            total_keys = db_stats.get('keys', 0)

            # 프리픽스별 키 개수
            speaker_embedding_count = 0
            tts_result_count = 0

            cursor = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor=cursor,
                    match=f"{config.CACHE_KEY_PREFIX}:*",
                    count=1000
                )

                for key in keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    if key_str.startswith(config.CACHE_KEY_SPEAKER_EMBEDDING):
                        speaker_embedding_count += 1
                    elif key_str.startswith(config.CACHE_KEY_TTS_RESULT):
                        tts_result_count += 1

                if cursor == 0:
                    break

            return {
                "enabled": True,
                "memory_used_mb": round(memory_used_mb, 2),
                "max_memory_mb": config.MAX_CACHE_SIZE_MB,
                "total_keys": total_keys,
                "speaker_embeddings_cached": speaker_embedding_count,
                "tts_results_cached": tts_result_count,
                "connected_clients": info.get('connected_clients', 0),
                "uptime_seconds": info.get('uptime_in_seconds', 0),
            }

        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {
                "enabled": True,
                "error": str(e)
            }

    @staticmethod
    async def clear_all() -> bool:
        """
        모든 캐시 삭제 (주의: 현재 DB의 모든 키 삭제)

        Returns:
            성공 여부
        """
        redis = await get_redis_client()
        if redis is None:
            return False

        try:
            await redis.flushdb()
            logger.warning("모든 캐시 삭제됨")
            return True

        except Exception as e:
            logger.error(f"캐시 전체 삭제 실패: {e}")
            return False


# 전역 캐시 서비스 인스턴스
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """전역 캐시 서비스 인스턴스 반환"""
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService()

    return _cache_service
