"""
Concurrency manager unit tests
"""

import pytest
import asyncio

from utils.concurrency import ConcurrencyManager
from utils.exceptions import QueueFullError, RequestTimeoutError


@pytest.mark.asyncio
class TestConcurrencyManager:
    """ConcurrencyManager 테스트"""

    async def test_tts_semaphore_basic(self):
        """기본 TTS 세마포어 동작"""
        manager = ConcurrencyManager(max_concurrent_tts=2)

        # 첫 번째 작업
        async with manager.acquire_tts("test1"):
            assert manager.stats["tts_active"] == 1
            assert manager.stats["tts_queued"] == 0

        # 작업 완료 후
        assert manager.stats["tts_active"] == 0
        assert manager.stats["tts_completed"] == 1

    async def test_tts_semaphore_limit(self):
        """TTS 동시 실행 수 제한"""
        manager = ConcurrencyManager(max_concurrent_tts=2)
        active_count = []

        async def task(task_id: str):
            async with manager.acquire_tts(task_id):
                active_count.append(manager.stats["tts_active"])
                await asyncio.sleep(0.1)

        # 3개 작업 동시 실행
        await asyncio.gather(
            task("task1"),
            task("task2"),
            task("task3")
        )

        # 최대 활성 작업 수가 2를 초과하지 않았는지 확인
        assert max(active_count) <= 2
        assert manager.stats["tts_completed"] == 3

    async def test_tts_queue_full(self):
        """TTS 큐 가득 참"""
        manager = ConcurrencyManager(
            max_concurrent_tts=1,
            max_queue_size=1
        )

        async def long_task():
            async with manager.acquire_tts("long"):
                await asyncio.sleep(1.0)

        # 첫 번째 작업 시작
        task1 = asyncio.create_task(long_task())
        await asyncio.sleep(0.1)  # 작업이 시작되도록 대기

        # 두 번째 작업은 큐에 들어감
        task2 = asyncio.create_task(long_task())
        await asyncio.sleep(0.1)

        # 세 번째 작업은 큐가 가득 차서 실패해야 함
        with pytest.raises(QueueFullError) as exc_info:
            async with manager.acquire_tts("should_fail"):
                pass

        assert "많은 요청을 처리 중" in str(exc_info.value)
        assert exc_info.value.details["queue_type"] == "tts"

        # 정리
        await task1
        await task2

    async def test_tts_timeout(self):
        """TTS 타임아웃"""
        manager = ConcurrencyManager(
            max_concurrent_tts=1,
            timeout=0.2  # 0.2초 타임아웃
        )

        async def blocking_task():
            async with manager.acquire_tts("blocker"):
                await asyncio.sleep(10)  # 10초 대기

        # 첫 번째 작업이 세마포어 점유
        task1 = asyncio.create_task(blocking_task())
        await asyncio.sleep(0.1)

        # 두 번째 작업은 타임아웃되어야 함
        with pytest.raises(RequestTimeoutError) as exc_info:
            async with manager.acquire_tts("timeout_task"):
                pass

        assert "초과되었습니다" in str(exc_info.value)
        assert exc_info.value.details["timeout"] == 0.2

        # 정리
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass

    async def test_embedding_semaphore(self):
        """임베딩 세마포어 동작"""
        manager = ConcurrencyManager(max_concurrent_embedding=1)

        async with manager.acquire_embedding("emb1"):
            assert manager.stats["embedding_active"] == 1

        assert manager.stats["embedding_active"] == 0
        assert manager.stats["embedding_completed"] == 1

    async def test_stats_tracking(self):
        """통계 추적"""
        manager = ConcurrencyManager(max_concurrent_tts=2)

        async def task():
            async with manager.acquire_tts():
                await asyncio.sleep(0.1)

        # 여러 작업 실행
        await asyncio.gather(*[task() for _ in range(5)])

        stats = manager.get_stats()

        assert stats["tts_completed"] == 5
        assert stats["tts_failed"] == 0
        assert stats["tts_active"] == 0
        assert stats["max_concurrent_tts"] == 2

    async def test_concurrent_mixed_operations(self):
        """TTS와 임베딩 동시 실행"""
        manager = ConcurrencyManager(
            max_concurrent_tts=2,
            max_concurrent_embedding=1
        )

        async def tts_task(task_id: str):
            async with manager.acquire_tts(task_id):
                await asyncio.sleep(0.1)

        async def emb_task(task_id: str):
            async with manager.acquire_embedding(task_id):
                await asyncio.sleep(0.1)

        # TTS 2개, 임베딩 1개 동시 실행
        await asyncio.gather(
            tts_task("tts1"),
            tts_task("tts2"),
            emb_task("emb1")
        )

        assert manager.stats["tts_completed"] == 2
        assert manager.stats["embedding_completed"] == 1

    async def test_error_handling_in_context(self):
        """컨텍스트 내 에러 처리"""
        manager = ConcurrencyManager(max_concurrent_tts=1)

        # 컨텍스트 내에서 에러 발생
        with pytest.raises(ValueError):
            async with manager.acquire_tts("error_task"):
                raise ValueError("Test error")

        # 실패 카운트 증가, 세마포어는 해제되어야 함
        assert manager.stats["tts_failed"] == 1
        assert manager.stats["tts_active"] == 0

        # 다음 작업은 정상 실행되어야 함
        async with manager.acquire_tts("next_task"):
            assert manager.stats["tts_active"] == 1
