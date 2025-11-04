"""
재시도 로직 및 Circuit Breaker 패턴
시스템 복원력(resilience) 향상을 위한 유틸리티
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Optional, Type, Tuple, Any
from loguru import logger

from utils.exceptions import (
    ModelLoadError,
    RequestTimeoutError,
    ResourceUnavailableError
)


# ==================== Exponential Backoff Retry ====================

class RetryConfig:
    """재시도 설정"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        """
        Args:
            max_retries: 최대 재시도 횟수
            initial_delay: 초기 대기 시간 (초)
            max_delay: 최대 대기 시간 (초)
            exponential_base: 지수 베이스 (2.0이면 2^n)
            jitter: 랜덤 지터 추가 여부
            retriable_exceptions: 재시도 가능한 예외 튜플
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retriable_exceptions = retriable_exceptions or (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,
        )


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """재시도 대기 시간 계산 (exponential backoff)"""
    import random

    # 지수 백오프: initial_delay * (base ^ attempt)
    delay = config.initial_delay * (config.exponential_base ** attempt)

    # 최대 지연 시간 제한
    delay = min(delay, config.max_delay)

    # 지터 추가 (랜덤성)
    if config.jitter:
        delay = delay * (0.5 + random.random())  # 50-150% 범위

    return delay


def retry_sync(config: Optional[RetryConfig] = None):
    """동기 함수용 재시도 데코레이터"""

    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except config.retriable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{config.max_retries + 1}). "
                            f"{delay:.2f}초 후 재시도... 에러: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} 최종 실패 ({config.max_retries + 1}번 시도). 에러: {e}"
                        )

            # 모든 재시도 실패
            raise last_exception

        return wrapper

    return decorator


def retry_async(config: Optional[RetryConfig] = None):
    """비동기 함수용 재시도 데코레이터"""

    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except config.retriable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{config.max_retries + 1}). "
                            f"{delay:.2f}초 후 재시도... 에러: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} 최종 실패 ({config.max_retries + 1}번 시도). 에러: {e}"
                        )

            # 모든 재시도 실패
            raise last_exception

        return wrapper

    return decorator


# ==================== Circuit Breaker Pattern ====================

class CircuitState:
    """Circuit Breaker 상태"""
    CLOSED = "closed"  # 정상 동작
    OPEN = "open"  # 차단됨 (요청 거부)
    HALF_OPEN = "half_open"  # 복구 시도


class CircuitBreaker:
    """Circuit Breaker 패턴 구현"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        name: str = "CircuitBreaker"
    ):
        """
        Args:
            failure_threshold: 실패 임계값 (이 횟수만큼 연속 실패하면 OPEN)
            recovery_timeout: OPEN 상태 유지 시간 (초)
            expected_exception: 카운트할 예외 타입
            name: Circuit Breaker 이름
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """함수 호출 (Circuit Breaker를 통해)"""

        # OPEN 상태 체크
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"{self.name}: HALF_OPEN 상태로 전환")
                self.state = CircuitState.HALF_OPEN
            else:
                raise ResourceUnavailableError(
                    f"{self.name}: Circuit이 OPEN 상태입니다. "
                    f"복구까지 대기 시간: {self._time_until_reset():.1f}초"
                )

        try:
            # 함수 실행
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """비동기 함수 호출 (Circuit Breaker를 통해)"""

        # OPEN 상태 체크
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"{self.name}: HALF_OPEN 상태로 전환")
                self.state = CircuitState.HALF_OPEN
            else:
                raise ResourceUnavailableError(
                    f"{self.name}: Circuit이 OPEN 상태입니다. "
                    f"복구까지 대기 시간: {self._time_until_reset():.1f}초"
                )

        try:
            # 함수 실행
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """성공 시 호출"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # 2번 연속 성공 시 복구
                logger.info(f"{self.name}: CLOSED 상태로 복구")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """실패 시 호출"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN 상태에서 실패하면 다시 OPEN
            logger.warning(f"{self.name}: 복구 실패, OPEN 상태로 복귀")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.failure_threshold:
            # 임계값 도달 시 OPEN
            logger.error(
                f"{self.name}: 실패 임계값 도달 ({self.failure_count}회). "
                f"Circuit OPEN"
            )
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """복구 시도 가능한지 확인"""
        if self.last_failure_time is None:
            return True

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _time_until_reset(self) -> float:
        """복구까지 남은 시간"""
        if self.last_failure_time is None:
            return 0.0

        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def reset(self):
        """Circuit Breaker 리셋"""
        logger.info(f"{self.name}: 수동 리셋")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def get_state(self) -> dict:
        """현재 상태 조회"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_until_reset": self._time_until_reset() if self.state == CircuitState.OPEN else None
        }


# ==================== 전역 Circuit Breaker 인스턴스 ====================

# 모델 로딩용 Circuit Breaker
model_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120.0,  # 2분
    expected_exception=Exception,
    name="ModelLoadCircuit"
)
