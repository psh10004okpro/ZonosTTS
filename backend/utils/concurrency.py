"""
동시성 제어 및 리소스 관리
GPU 메모리 부족 방지 및 요청 큐 관리
"""

import asyncio
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from loguru import logger


class ConcurrencyManager:
    """
    동시성 관리자

    세마포어를 사용하여 동시 실행 가능한 작업 수를 제한합니다.
    GPU 메모리 부족 및 시스템 과부하를 방지합니다.
    """

    def __init__(
        self,
        max_concurrent_tts: int = 2,
        max_concurrent_embedding: int = 1,
        max_queue_size: int = 10,
        timeout: float = 300.0  # 5분
    ):
        """
        Args:
            max_concurrent_tts: 동시 TTS 생성 최대 수
            max_concurrent_embedding: 동시 임베딩 생성 최대 수
            max_queue_size: 최대 대기 큐 크기
            timeout: 작업 타임아웃 (초)
        """
        # 세마포어 생성
        self.tts_semaphore = asyncio.Semaphore(max_concurrent_tts)
        self.embedding_semaphore = asyncio.Semaphore(max_concurrent_embedding)

        # 설정
        self.max_concurrent_tts = max_concurrent_tts
        self.max_concurrent_embedding = max_concurrent_embedding
        self.max_queue_size = max_queue_size
        self.timeout = timeout

        # 통계
        self.stats = {
            "tts_active": 0,
            "tts_queued": 0,
            "tts_completed": 0,
            "tts_failed": 0,
            "embedding_active": 0,
            "embedding_queued": 0,
            "embedding_completed": 0,
            "embedding_failed": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
        }

        # 잠금
        self.stats_lock = asyncio.Lock()

        logger.info(
            f"ConcurrencyManager 초기화: "
            f"TTS={max_concurrent_tts}, "
            f"Embedding={max_concurrent_embedding}, "
            f"Queue={max_queue_size}"
        )

    @asynccontextmanager
    async def acquire_tts(self, request_id: Optional[str] = None):
        """
        TTS 생성을 위한 세마포어 획득

        Args:
            request_id: 요청 ID (로깅용)

        Yields:
            컨텍스트 (세마포어 보유)

        Raises:
            asyncio.TimeoutError: 타임아웃 발생
            Exception: 큐가 가득 찬 경우
        """
        request_id = request_id or f"req_{int(time.time() * 1000)}"
        start_time = time.time()

        # 큐 크기 체크
        if self.stats["tts_queued"] >= self.max_queue_size:
            logger.warning(f"[{request_id}] TTS 큐가 가득 참 ({self.max_queue_size})")
            raise Exception(
                f"서버가 현재 많은 요청을 처리 중입니다. "
                f"잠시 후 다시 시도해주세요. (대기 중: {self.stats['tts_queued']})"
            )

        # 대기 시작
        async with self.stats_lock:
            self.stats["tts_queued"] += 1

        try:
            # 세마포어 획득 (타임아웃 적용)
            logger.info(
                f"[{request_id}] TTS 세마포어 대기 중... "
                f"(활성: {self.stats['tts_active']}/{self.max_concurrent_tts}, "
                f"대기: {self.stats['tts_queued']})"
            )

            await asyncio.wait_for(
                self.tts_semaphore.acquire(),
                timeout=self.timeout
            )

            # 대기 시간 기록
            wait_time = time.time() - start_time
            async with self.stats_lock:
                self.stats["tts_queued"] -= 1
                self.stats["tts_active"] += 1
                self.stats["total_wait_time"] += wait_time
                if wait_time > self.stats["max_wait_time"]:
                    self.stats["max_wait_time"] = wait_time

            logger.info(
                f"[{request_id}] TTS 세마포어 획득 "
                f"(대기 시간: {wait_time:.2f}초)"
            )

            # 작업 실행
            yield

            # 성공
            async with self.stats_lock:
                self.stats["tts_completed"] += 1

        except asyncio.TimeoutError:
            logger.error(f"[{request_id}] TTS 타임아웃 ({self.timeout}초)")
            async with self.stats_lock:
                self.stats["tts_failed"] += 1
                self.stats["tts_queued"] -= 1
            raise asyncio.TimeoutError(
                f"요청 처리 시간이 초과되었습니다 ({self.timeout}초). "
                f"텍스트를 짧게 나눠서 시도해주세요."
            )

        except Exception as e:
            logger.error(f"[{request_id}] TTS 작업 실패: {e}")
            async with self.stats_lock:
                self.stats["tts_failed"] += 1
                if self.stats["tts_queued"] > 0:
                    self.stats["tts_queued"] -= 1
            raise

        finally:
            # 세마포어 해제
            if self.tts_semaphore.locked():
                self.tts_semaphore.release()
                async with self.stats_lock:
                    if self.stats["tts_active"] > 0:
                        self.stats["tts_active"] -= 1

                logger.info(
                    f"[{request_id}] TTS 세마포어 해제 "
                    f"(활성: {self.stats['tts_active']}/{self.max_concurrent_tts})"
                )

    @asynccontextmanager
    async def acquire_embedding(self, request_id: Optional[str] = None):
        """
        임베딩 생성을 위한 세마포어 획득

        Args:
            request_id: 요청 ID (로깅용)

        Yields:
            컨텍스트 (세마포어 보유)

        Raises:
            asyncio.TimeoutError: 타임아웃 발생
            Exception: 큐가 가득 찬 경우
        """
        request_id = request_id or f"emb_{int(time.time() * 1000)}"
        start_time = time.time()

        # 큐 크기 체크
        if self.stats["embedding_queued"] >= self.max_queue_size:
            logger.warning(f"[{request_id}] 임베딩 큐가 가득 참")
            raise Exception(
                f"서버가 현재 많은 요청을 처리 중입니다. "
                f"잠시 후 다시 시도해주세요."
            )

        # 대기 시작
        async with self.stats_lock:
            self.stats["embedding_queued"] += 1

        try:
            # 세마포어 획득
            logger.info(
                f"[{request_id}] 임베딩 세마포어 대기 중... "
                f"(활성: {self.stats['embedding_active']}/{self.max_concurrent_embedding})"
            )

            await asyncio.wait_for(
                self.embedding_semaphore.acquire(),
                timeout=self.timeout
            )

            # 대기 시간 기록
            wait_time = time.time() - start_time
            async with self.stats_lock:
                self.stats["embedding_queued"] -= 1
                self.stats["embedding_active"] += 1

            logger.info(
                f"[{request_id}] 임베딩 세마포어 획득 "
                f"(대기 시간: {wait_time:.2f}초)"
            )

            # 작업 실행
            yield

            # 성공
            async with self.stats_lock:
                self.stats["embedding_completed"] += 1

        except asyncio.TimeoutError:
            logger.error(f"[{request_id}] 임베딩 타임아웃")
            async with self.stats_lock:
                self.stats["embedding_failed"] += 1
                self.stats["embedding_queued"] -= 1
            raise asyncio.TimeoutError(
                f"화자 임베딩 생성 시간이 초과되었습니다 ({self.timeout}초)."
            )

        except Exception as e:
            logger.error(f"[{request_id}] 임베딩 작업 실패: {e}")
            async with self.stats_lock:
                self.stats["embedding_failed"] += 1
                if self.stats["embedding_queued"] > 0:
                    self.stats["embedding_queued"] -= 1
            raise

        finally:
            # 세마포어 해제
            if self.embedding_semaphore.locked():
                self.embedding_semaphore.release()
                async with self.stats_lock:
                    if self.stats["embedding_active"] > 0:
                        self.stats["embedding_active"] -= 1

                logger.info(
                    f"[{request_id}] 임베딩 세마포어 해제 "
                    f"(활성: {self.stats['embedding_active']}/{self.max_concurrent_embedding})"
                )

    async def get_stats(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        async with self.stats_lock:
            stats = self.stats.copy()

        # 추가 계산
        total_completed = stats["tts_completed"] + stats["embedding_completed"]
        if total_completed > 0:
            stats["avg_wait_time"] = stats["total_wait_time"] / total_completed
        else:
            stats["avg_wait_time"] = 0.0

        return stats

    def reset_stats(self):
        """통계 초기화 (완료/실패 카운트만)"""
        self.stats["tts_completed"] = 0
        self.stats["tts_failed"] = 0
        self.stats["embedding_completed"] = 0
        self.stats["embedding_failed"] = 0
        self.stats["total_wait_time"] = 0.0
        self.stats["max_wait_time"] = 0.0
        logger.info("통계 초기화 완료")


# 전역 동시성 관리자 (싱글톤)
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """전역 동시성 관리자 인스턴스 반환"""
    global _concurrency_manager

    if _concurrency_manager is None:
        from config import (
            MAX_CONCURRENT_TTS,
            MAX_CONCURRENT_EMBEDDING,
            MAX_QUEUE_SIZE,
            REQUEST_TIMEOUT
        )

        _concurrency_manager = ConcurrencyManager(
            max_concurrent_tts=MAX_CONCURRENT_TTS,
            max_concurrent_embedding=MAX_CONCURRENT_EMBEDDING,
            max_queue_size=MAX_QUEUE_SIZE,
            timeout=REQUEST_TIMEOUT
        )

    return _concurrency_manager
