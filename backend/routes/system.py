"""
시스템 상태 및 모니터링 API
"""

from fastapi import APIRouter
from utils.concurrency import get_concurrency_manager

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/stats", summary="시스템 통계 조회")
async def get_system_stats():
    """
    시스템 동시성 및 리소스 사용 통계 조회

    Returns:
        - tts_active: 현재 실행 중인 TTS 요청 수
        - tts_queued: 대기 중인 TTS 요청 수
        - tts_completed: 완료된 총 TTS 요청 수
        - tts_failed: 실패한 총 TTS 요청 수
        - embedding_active: 현재 실행 중인 임베딩 생성 수
        - embedding_queued: 대기 중인 임베딩 생성 수
        - embedding_completed: 완료된 총 임베딩 생성 수
        - embedding_failed: 실패한 총 임베딩 생성 수
        - avg_tts_wait_time: 평균 TTS 대기 시간 (초)
        - avg_embedding_wait_time: 평균 임베딩 대기 시간 (초)
        - max_concurrent_tts: 최대 동시 TTS 실행 수 (설정값)
        - max_concurrent_embedding: 최대 동시 임베딩 실행 수 (설정값)
        - max_queue_size: 최대 큐 크기 (설정값)
    """
    concurrency = get_concurrency_manager()
    stats = concurrency.get_stats()

    return {
        "success": True,
        "data": stats
    }


@router.get("/health", summary="헬스 체크")
async def health_check():
    """
    시스템 헬스 체크 엔드포인트

    Returns:
        - status: healthy 또는 unhealthy
        - message: 상태 메시지
    """
    concurrency = get_concurrency_manager()
    stats = concurrency.get_stats()

    # 큐가 가득 찬 경우 경고
    if stats["tts_queued"] >= stats["max_queue_size"]:
        return {
            "status": "unhealthy",
            "message": "TTS 요청 큐가 가득 찼습니다."
        }

    if stats["embedding_queued"] >= stats["max_queue_size"]:
        return {
            "status": "unhealthy",
            "message": "임베딩 요청 큐가 가득 찼습니다."
        }

    return {
        "status": "healthy",
        "message": "시스템이 정상적으로 작동 중입니다."
    }
