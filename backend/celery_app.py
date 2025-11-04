"""
Celery 애플리케이션 설정
"""

import os
from celery import Celery
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# Redis를 브로커와 결과 백엔드로 사용
if REDIS_PASSWORD:
    redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery 앱 생성
celery_app = Celery(
    "zonos_tts",
    broker=redis_url,
    backend=redis_url,
    include=["tasks.tts_tasks"]  # 태스크 모듈
)

# Celery 설정
celery_app.conf.update(
    # 태스크 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,

    # 결과 설정
    result_expires=3600,  # 결과 보관 시간 (1시간)
    result_backend_transport_options={
        "master_name": "mymaster",
    },

    # 워커 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나의 태스크만 가져오기 (GPU 메모리 관리)
    worker_max_tasks_per_child=50,  # 메모리 누수 방지
    worker_disable_rate_limits=False,

    # 태스크 타임아웃
    task_soft_time_limit=300,  # 5분 (soft limit)
    task_time_limit=360,  # 6분 (hard limit)

    # 재시도 설정
    task_acks_late=True,  # 태스크 완료 후 ACK
    task_reject_on_worker_lost=True,  # 워커 다운 시 태스크 재실행

    # 우선순위 큐 설정
    task_default_priority=5,
    task_queue_max_priority=10,

    # 브로커 설정
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # 모니터링
    task_send_sent_event=True,
    task_track_started=True,
    worker_send_task_events=True,
)

# 태스크 라우팅 (선택사항)
celery_app.conf.task_routes = {
    "tasks.tts_tasks.generate_tts_async": {"queue": "tts"},
    "tasks.tts_tasks.generate_speaker_embedding_async": {"queue": "embedding"},
}

# Celery Beat 스케줄 (주기적 작업 - 선택사항)
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # 매일 자정에 오래된 결과 정리
    "cleanup-old-results": {
        "task": "tasks.tts_tasks.cleanup_old_jobs",
        "schedule": crontab(hour=0, minute=0),
    },
    # 5분마다 작업 통계 업데이트
    "update-job-stats": {
        "task": "tasks.tts_tasks.update_job_statistics",
        "schedule": 300.0,  # 5분
    },
}


def get_celery_app() -> Celery:
    """Celery 앱 인스턴스 반환"""
    return celery_app


if __name__ == "__main__":
    # 워커 실행: celery -A celery_app worker --loglevel=info
    celery_app.start()
