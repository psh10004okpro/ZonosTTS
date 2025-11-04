"""
Retry logic and Circuit Breaker tests
"""

import pytest
import asyncio
import time

from utils.retry import (
    RetryConfig,
    calculate_delay,
    retry_sync,
    retry_async,
    CircuitBreaker,
    CircuitState,
)
from utils.exceptions import ResourceUnavailableError


class TestRetryLogic:
    """재시도 로직 테스트"""

    def test_calculate_delay(self):
        """지연 시간 계산"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )

        # 지수 백오프 검증
        assert calculate_delay(0, config) == 1.0   # 2^0 * 1
        assert calculate_delay(1, config) == 2.0   # 2^1 * 1
        assert calculate_delay(2, config) == 4.0   # 2^2 * 1
        assert calculate_delay(3, config) == 8.0   # 2^3 * 1

    def test_calculate_delay_with_max(self):
        """최대 지연 시간 제한"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False
        )

        # 최대값 제한 확인
        assert calculate_delay(10, config) == 5.0  # 1024초이지만 최대 5초로 제한

    def test_retry_sync_success(self):
        """동기 함수 재시도 성공"""
        call_count = [0]

        @retry_sync(RetryConfig(max_retries=3))
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count[0] == 3  # 2번 실패 후 3번째에 성공

    def test_retry_sync_failure(self):
        """동기 함수 재시도 최종 실패"""
        call_count = [0]

        @retry_sync(RetryConfig(max_retries=2, initial_delay=0.01))
        def always_fails():
            call_count[0] += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count[0] == 3  # 초기 시도 + 2번 재시도

    def test_retry_sync_non_retriable_error(self):
        """재시도 불가능한 에러"""
        call_count = [0]

        @retry_sync(RetryConfig(max_retries=3))
        def raises_value_error():
            call_count[0] += 1
            raise ValueError("Not retriable")

        with pytest.raises(ValueError):
            raises_value_error()

        # ValueError는 retriable_exceptions에 없으므로 재시도 안 함
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """비동기 함수 재시도 성공"""
        call_count = [0]

        @retry_async(RetryConfig(max_retries=3, initial_delay=0.01))
        async def flaky_async():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Connection failed")
            return "async success"

        result = await flaky_async()

        assert result == "async success"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_retry_async_with_timeout(self):
        """비동기 함수 재시도 타임아웃"""
        call_count = [0]

        @retry_async(RetryConfig(
            max_retries=5,
            initial_delay=0.01,
            retriable_exceptions=(asyncio.TimeoutError,)
        ))
        async def times_out():
            call_count[0] += 1
            raise asyncio.TimeoutError("Timeout")

        with pytest.raises(asyncio.TimeoutError):
            await times_out()

        assert call_count[0] == 6  # 초기 시도 + 5번 재시도


class TestCircuitBreaker:
    """Circuit Breaker 테스트"""

    def test_circuit_breaker_closed_state(self):
        """Circuit CLOSED 상태 (정상)"""
        circuit = CircuitBreaker(failure_threshold=3)

        def successful_operation():
            return "success"

        # 정상 동작
        result = circuit.call(successful_operation)

        assert result == "success"
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_circuit_breaker_opens_on_failures(self):
        """연속 실패 시 Circuit OPEN"""
        circuit = CircuitBreaker(failure_threshold=3)

        def failing_operation():
            raise Exception("Operation failed")

        # 3번 연속 실패
        for _ in range(3):
            with pytest.raises(Exception):
                circuit.call(failing_operation)

        # Circuit이 OPEN 상태가 되어야 함
        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count == 3

    def test_circuit_breaker_rejects_when_open(self):
        """Circuit OPEN 시 요청 거부"""
        circuit = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10.0
        )

        def failing_operation():
            raise Exception("Fail")

        # Circuit을 OPEN 상태로 만듦
        for _ in range(2):
            with pytest.raises(Exception):
                circuit.call(failing_operation)

        assert circuit.state == CircuitState.OPEN

        # 이후 요청은 즉시 거부되어야 함
        with pytest.raises(ResourceUnavailableError) as exc_info:
            circuit.call(lambda: "should not run")

        assert "OPEN 상태" in str(exc_info.value)

    def test_circuit_breaker_half_open_recovery(self):
        """Circuit HALF_OPEN 복구 시도"""
        circuit = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1  # 0.1초 후 복구 시도
        )

        def failing_operation():
            raise Exception("Fail")

        # Circuit을 OPEN으로 만듦
        for _ in range(2):
            with pytest.raises(Exception):
                circuit.call(failing_operation)

        assert circuit.state == CircuitState.OPEN

        # recovery_timeout 대기
        time.sleep(0.15)

        # 성공하는 작업으로 복구 시도
        def successful_operation():
            return "recovered"

        # 첫 번째 성공 (HALF_OPEN)
        result = circuit.call(successful_operation)
        assert circuit.state == CircuitState.HALF_OPEN

        # 두 번째 성공 (CLOSED로 복구)
        result = circuit.call(successful_operation)
        assert circuit.state == CircuitState.CLOSED

    def test_circuit_breaker_half_open_failure(self):
        """Circuit HALF_OPEN에서 실패 시 다시 OPEN"""
        circuit = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1
        )

        # Circuit을 OPEN으로 만듦
        for _ in range(2):
            with pytest.raises(Exception):
                circuit.call(lambda: (_ for _ in ()).throw(Exception("Fail")))

        # recovery_timeout 대기
        time.sleep(0.15)

        # HALF_OPEN에서 실패
        with pytest.raises(Exception):
            circuit.call(lambda: (_ for _ in ()).throw(Exception("Fail again")))

        # 다시 OPEN 상태로
        assert circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_async(self):
        """비동기 Circuit Breaker"""
        circuit = CircuitBreaker(failure_threshold=2)

        async def async_operation():
            return "async success"

        result = await circuit.call_async(async_operation)

        assert result == "async success"
        assert circuit.state == CircuitState.CLOSED

    def test_circuit_breaker_reset(self):
        """Circuit Breaker 수동 리셋"""
        circuit = CircuitBreaker(failure_threshold=2)

        # OPEN 상태로 만듦
        for _ in range(2):
            with pytest.raises(Exception):
                circuit.call(lambda: (_ for _ in ()).throw(Exception("Fail")))

        assert circuit.state == CircuitState.OPEN

        # 수동 리셋
        circuit.reset()

        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_circuit_breaker_get_state(self):
        """Circuit Breaker 상태 조회"""
        circuit = CircuitBreaker(
            failure_threshold=3,
            name="TestCircuit"
        )

        state = circuit.get_state()

        assert state["name"] == "TestCircuit"
        assert state["state"] == CircuitState.CLOSED
        assert state["failure_count"] == 0
        assert state["time_until_reset"] is None
