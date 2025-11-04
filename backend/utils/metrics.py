"""
Prometheus 메트릭 수집
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional
from loguru import logger


# ==================== 애플리케이션 정보 ====================

app_info = Info('zonos_tts_app', 'Zonos TTS API Application Info')
app_info.info({
    'version': '1.0.0',
    'model': 'Zonos-v0.1',
    'framework': 'FastAPI'
})


# ==================== HTTP 요청 메트릭 ====================
# (prometheus-fastapi-instrumentator가 자동으로 제공)


# ==================== TTS 생성 메트릭 ====================

# TTS 생성 요청 수
tts_requests_total = Counter(
    'tts_requests_total',
    'Total number of TTS generation requests',
    ['status', 'language', 'has_speaker']  # 레이블
)

# TTS 생성 시간 (초)
tts_generation_duration = Histogram(
    'tts_generation_duration_seconds',
    'TTS generation duration in seconds',
    ['language', 'has_speaker'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0]  # 시간 버킷
)

# 생성된 오디오 길이 (초)
tts_audio_duration = Histogram(
    'tts_audio_duration_seconds',
    'Generated audio duration in seconds',
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# 처리된 텍스트 길이 (문자 수)
tts_text_length = Histogram(
    'tts_text_length_characters',
    'Processed text length in characters',
    buckets=[10, 50, 100, 500, 1000, 2000, 5000]
)


# ==================== 화자 임베딩 메트릭 ====================

# 화자 임베딩 생성 수
speaker_embeddings_total = Counter(
    'speaker_embeddings_total',
    'Total number of speaker embeddings created',
    ['status', 'language']
)

# 임베딩 생성 시간
speaker_embedding_duration = Histogram(
    'speaker_embedding_duration_seconds',
    'Speaker embedding generation duration in seconds',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)


# ==================== 캐싱 메트릭 ====================

# 캐시 히트/미스
cache_requests_total = Counter(
    'cache_requests_total',
    'Total number of cache requests',
    ['cache_type', 'status']  # status: hit, miss
)

# 캐시 메모리 사용량 (MB)
cache_memory_usage_mb = Gauge(
    'cache_memory_usage_megabytes',
    'Cache memory usage in megabytes'
)

# 캐시된 키 개수
cache_keys_total = Gauge(
    'cache_keys_total',
    'Total number of cached keys',
    ['cache_type']  # speaker_embedding, tts_result, etc.
)


# ==================== 동시성 메트릭 ====================

# 활성 TTS 요청 수
active_tts_requests = Gauge(
    'active_tts_requests',
    'Number of active TTS requests'
)

# 대기 중인 TTS 요청 수
queued_tts_requests = Gauge(
    'queued_tts_requests',
    'Number of queued TTS requests'
)

# 활성 임베딩 생성 수
active_embedding_requests = Gauge(
    'active_embedding_requests',
    'Number of active embedding generation requests'
)

# TTS 대기 시간
tts_wait_time = Histogram(
    'tts_wait_time_seconds',
    'TTS request wait time in queue',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)


# ==================== 에러 메트릭 ====================

# 에러 발생 수
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'endpoint']
)

# 타임아웃 발생 수
timeouts_total = Counter(
    'timeouts_total',
    'Total number of timeout errors',
    ['operation']  # tts, embedding, cache
)

# 큐 가득참 거부 수
queue_full_rejections_total = Counter(
    'queue_full_rejections_total',
    'Total number of requests rejected due to full queue',
    ['queue_type']  # tts, embedding
)


# ==================== 모델 메트릭 ====================

# 모델 추론 시간
model_inference_duration = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration in seconds',
    ['operation'],  # tts, embedding
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# 모델 로드 시간
model_load_duration = Histogram(
    'model_load_duration_seconds',
    'Model loading duration in seconds',
    buckets=[1, 5, 10, 30, 60, 120]
)


# ==================== 데이터베이스 메트릭 ====================

# DB 쿼리 수
db_queries_total = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['operation', 'table']  # select, insert, update, delete
)

# DB 쿼리 시간
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)


# ==================== 유틸리티 클래스 ====================

class MetricsCollector:
    """메트릭 수집을 위한 헬퍼 클래스"""

    @staticmethod
    def record_tts_request(
        status: str,
        language: str,
        has_speaker: bool,
        duration: Optional[float] = None,
        audio_duration: Optional[float] = None,
        text_length: Optional[int] = None
    ):
        """TTS 요청 메트릭 기록"""
        speaker_label = 'yes' if has_speaker else 'no'

        tts_requests_total.labels(
            status=status,
            language=language,
            has_speaker=speaker_label
        ).inc()

        if duration is not None:
            tts_generation_duration.labels(
                language=language,
                has_speaker=speaker_label
            ).observe(duration)

        if audio_duration is not None:
            tts_audio_duration.observe(audio_duration)

        if text_length is not None:
            tts_text_length.observe(text_length)

    @staticmethod
    def record_speaker_embedding(
        status: str,
        language: str,
        duration: Optional[float] = None
    ):
        """화자 임베딩 메트릭 기록"""
        speaker_embeddings_total.labels(
            status=status,
            language=language
        ).inc()

        if duration is not None:
            speaker_embedding_duration.observe(duration)

    @staticmethod
    def record_cache_request(cache_type: str, is_hit: bool):
        """캐시 요청 메트릭 기록"""
        status = 'hit' if is_hit else 'miss'
        cache_requests_total.labels(
            cache_type=cache_type,
            status=status
        ).inc()

    @staticmethod
    def update_cache_stats(memory_mb: float, keys_by_type: dict):
        """캐시 통계 업데이트"""
        cache_memory_usage_mb.set(memory_mb)

        for cache_type, count in keys_by_type.items():
            cache_keys_total.labels(cache_type=cache_type).set(count)

    @staticmethod
    def update_concurrency_stats(stats: dict):
        """동시성 통계 업데이트"""
        active_tts_requests.set(stats.get('tts_active', 0))
        queued_tts_requests.set(stats.get('tts_queued', 0))
        active_embedding_requests.set(stats.get('embedding_active', 0))

    @staticmethod
    def record_error(error_type: str, endpoint: str):
        """에러 메트릭 기록"""
        errors_total.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()

    @staticmethod
    def record_timeout(operation: str):
        """타임아웃 메트릭 기록"""
        timeouts_total.labels(operation=operation).inc()

    @staticmethod
    def record_queue_rejection(queue_type: str):
        """큐 거부 메트릭 기록"""
        queue_full_rejections_total.labels(queue_type=queue_type).inc()

    @staticmethod
    def record_model_inference(operation: str, duration: float):
        """모델 추론 메트릭 기록"""
        model_inference_duration.labels(operation=operation).observe(duration)

    @staticmethod
    def record_db_query(operation: str, table: str, duration: Optional[float] = None):
        """DB 쿼리 메트릭 기록"""
        db_queries_total.labels(
            operation=operation,
            table=table
        ).inc()

        if duration is not None:
            db_query_duration.labels(operation=operation).observe(duration)


# 전역 메트릭 수집기 인스턴스
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """전역 메트릭 수집기 반환"""
    return metrics_collector
