"""
쿼리 성능 모니터링 유틸리티
"""

import time
from contextlib import asynccontextmanager
from typing import Optional
from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

# 쿼리 성능 통계
query_stats = {
    "total_queries": 0,
    "slow_queries": 0,
    "total_duration": 0.0,
    "slowest_query": None,
    "slowest_duration": 0.0
}


class QueryMonitor:
    """쿼리 성능 모니터링"""

    def __init__(self, slow_query_threshold: float = 1.0):
        """
        Args:
            slow_query_threshold: 느린 쿼리 임계값 (초)
        """
        self.slow_query_threshold = slow_query_threshold

    @asynccontextmanager
    async def monitor_query(self, query_name: str):
        """
        쿼리 실행 시간 모니터링 컨텍스트 매니저

        Usage:
            async with query_monitor.monitor_query("list_audio_files"):
                result = await db.execute(query)
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time

            # 통계 업데이트
            query_stats["total_queries"] += 1
            query_stats["total_duration"] += duration

            # 느린 쿼리 로깅
            if duration > self.slow_query_threshold:
                query_stats["slow_queries"] += 1
                logger.warning(
                    f"⚠ 느린 쿼리 감지: {query_name} - {duration:.3f}초"
                )

                # 가장 느린 쿼리 기록
                if duration > query_stats["slowest_duration"]:
                    query_stats["slowest_query"] = query_name
                    query_stats["slowest_duration"] = duration
            else:
                logger.debug(
                    f"쿼리 실행: {query_name} - {duration:.3f}초"
                )

    @staticmethod
    def get_stats() -> dict:
        """쿼리 통계 반환"""
        total_queries = query_stats["total_queries"]
        avg_duration = (
            query_stats["total_duration"] / total_queries
            if total_queries > 0
            else 0.0
        )

        return {
            "total_queries": total_queries,
            "slow_queries": query_stats["slow_queries"],
            "slow_query_percentage": (
                query_stats["slow_queries"] / total_queries * 100
                if total_queries > 0
                else 0.0
            ),
            "average_duration_ms": round(avg_duration * 1000, 2),
            "total_duration_seconds": round(query_stats["total_duration"], 2),
            "slowest_query": query_stats["slowest_query"],
            "slowest_duration_seconds": round(query_stats["slowest_duration"], 2)
        }

    @staticmethod
    def reset_stats():
        """통계 초기화"""
        query_stats["total_queries"] = 0
        query_stats["slow_queries"] = 0
        query_stats["total_duration"] = 0.0
        query_stats["slowest_query"] = None
        query_stats["slowest_duration"] = 0.0


# 전역 쿼리 모니터 인스턴스
_query_monitor: Optional[QueryMonitor] = None


def get_query_monitor() -> QueryMonitor:
    """전역 쿼리 모니터 인스턴스 반환"""
    global _query_monitor
    if _query_monitor is None:
        _query_monitor = QueryMonitor(slow_query_threshold=1.0)
    return _query_monitor


def setup_sqlalchemy_event_listeners(engine: Engine, log_queries: bool = False):
    """
    SQLAlchemy 이벤트 리스너 설정
    모든 쿼리를 자동으로 로깅하고 모니터링

    Args:
        engine: SQLAlchemy 엔진
        log_queries: 모든 쿼리 로깅 여부
    """

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """쿼리 실행 전"""
        conn.info.setdefault("query_start_time", []).append(time.time())
        if log_queries:
            logger.debug(f"실행 쿼리: {statement[:200]}")

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """쿼리 실행 후"""
        total = time.time() - conn.info["query_start_time"].pop()

        # 통계 업데이트
        query_stats["total_queries"] += 1
        query_stats["total_duration"] += total

        # 느린 쿼리 로깅
        if total > 1.0:  # 1초 이상
            query_stats["slow_queries"] += 1
            logger.warning(
                f"⚠ 느린 쿼리: {total:.3f}초\n{statement[:500]}"
            )


# 데코레이터: 쿼리 성능 측정
def monitor_query(query_name: str):
    """
    쿼리 성능 모니터링 데코레이터

    Usage:
        @monitor_query("get_audio_file")
        async def get_audio_file(db, audio_id):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_query_monitor()
            async with monitor.monitor_query(query_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
