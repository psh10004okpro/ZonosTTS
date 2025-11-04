"""
TTS API 라우터
음성 생성, 스트리밍, 통계 관련 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import (
    get_db,
    TTSStreamRequest,
    TTSGenerateRequest,
    AudioFileResponse,
    DashboardStats,
    AsyncTTSRequest,
    AsyncTTSResponse,
    Job
)
from services.tts_service import TTSService
from services.stream_service import StreamService
from loguru import logger

router = APIRouter(prefix="/api/tts", tags=["TTS"])

# 서비스 인스턴스
tts_service = TTSService()
stream_service = StreamService()


@router.post("/stream")
async def stream_tts(
    request: TTSStreamRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    실시간 스트리밍 TTS
    Server-Sent Events (SSE)로 오디오 청크를 전송

    **요청 본문:**
    - text: 생성할 텍스트 (최대 5000자)
    - speaker_id: 화자 ID (선택)
    - language: 언어 (en-us, ja, zh, fr, de)
    - speaking_rate: 말하기 속도 (0.5 ~ 2.0)
    - pitch_shift: 피치 조절 (-12.0 ~ 12.0 반음)
    - emotion: 감정 (neutral, happy, sad, angry, fear)

    **응답:**
    - Server-Sent Events 스트림
    - 각 이벤트는 base64 인코딩된 오디오 청크
    """
    try:
        logger.info(f"스트리밍 요청: 텍스트 길이={len(request.text)}, 화자={request.speaker_id}")

        # 스트리밍 생성
        stream_gen = stream_service.stream_tts(
            text=request.text,
            db=db,
            speaker_id=request.speaker_id,
            language=request.language,
            speaking_rate=request.speaking_rate,
            pitch_shift=request.pitch_shift,
            emotion=request.emotion
        )

        return StreamingResponse(
            stream_gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # nginx 버퍼링 방지
            }
        )

    except Exception as e:
        logger.error(f"스트리밍 실패: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 실패: {str(e)}")


@router.post("/generate", response_model=AudioFileResponse)
async def generate_audio(
    request: TTSGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    음성 파일 생성
    텍스트로부터 음성 파일을 생성하고 저장

    **요청 본문:**
    - text: 생성할 텍스트 (최대 5000자)
    - speaker_id: 화자 ID (선택)
    - language: 언어
    - speaking_rate: 말하기 속도
    - pitch_shift: 피치 조절
    - emotion: 감정
    - save_to_db: DB 저장 여부 (기본 True)

    **응답:**
    - 생성된 오디오 파일 정보
    """
    try:
        logger.info(f"파일 생성 요청: 텍스트 길이={len(request.text)}, 화자={request.speaker_id}")

        # 음성 생성
        file_path, metadata = await tts_service.generate_audio_file(
            text=request.text,
            db=db,
            speaker_id=request.speaker_id,
            language=request.language,
            speaking_rate=request.speaking_rate,
            pitch_shift=request.pitch_shift,
            emotion=request.emotion,
            save_to_db=request.save_to_db
        )

        # DB에서 저장된 파일 정보 조회
        if metadata["id"]:
            audio_file = await tts_service.get_audio_file(db, metadata["id"])
            return audio_file
        else:
            # DB에 저장하지 않은 경우 메타데이터만 반환
            return {
                "id": None,
                "filename": metadata["filename"],
                "text": request.text,
                "speaker_id": request.speaker_id,
                "language": request.language,
                "speaking_rate": request.speaking_rate,
                "pitch_shift": request.pitch_shift,
                "emotion": request.emotion,
                "duration": metadata["duration"],
                "file_size": metadata["file_size"],
                "created_at": None
            }

    except Exception as e:
        logger.error(f"파일 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 생성 실패: {str(e)}")


@router.post("/generate-async", response_model=AsyncTTSResponse)
async def generate_audio_async(
    request: AsyncTTSRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    비동기 음성 파일 생성
    백그라운드에서 음성을 생성하고 job_id를 반환

    **요청 본문:**
    - text: 생성할 텍스트 (최대 5000자)
    - speaker_id: 화자 ID (선택)
    - language: 언어
    - speaking_rate: 말하기 속도
    - pitch_shift: 피치 조절
    - emotion: 감정
    - priority: 작업 우선순위 (1-10, 기본 5)

    **응답:**
    - job_id: 작업 ID (상태 조회에 사용)
    - status: 초기 상태 ("pending")
    - message: 안내 메시지
    - estimated_time_seconds: 예상 처리 시간 (초)

    **사용 예:**
    1. 이 엔드포인트로 작업 시작 → job_id 받기
    2. GET /api/jobs/{job_id} 로 상태 폴링
    3. status="completed" 되면 GET /api/jobs/{job_id}/result 로 결과 받기
    """
    try:
        import json
        from tasks.tts_tasks import generate_tts_async

        logger.info(f"비동기 파일 생성 요청: 텍스트 길이={len(request.text)}, 화자={request.speaker_id}")

        # 예상 처리 시간 계산 (대략적)
        # 텍스트 100자당 약 10초 소요 (대략)
        estimated_time = max(10, len(request.text) // 10)

        # Celery 작업 시작
        task = generate_tts_async.apply_async(
            kwargs={
                "job_id": None,  # 나중에 설정
                "text": request.text,
                "speaker_id": request.speaker_id,
                "language": request.language,
                "speaking_rate": request.speaking_rate,
                "pitch_shift": request.pitch_shift,
                "emotion": request.emotion
            },
            priority=request.priority
        )

        job_id = task.id

        # DB에 작업 기록
        job = Job(
            job_id=job_id,
            job_type="tts",
            status="pending",
            progress=0,
            request_params=json.dumps({
                "text": request.text,
                "speaker_id": request.speaker_id,
                "language": request.language,
                "speaking_rate": request.speaking_rate,
                "pitch_shift": request.pitch_shift,
                "emotion": request.emotion
            })
        )
        db.add(job)
        await db.commit()

        logger.info(f"비동기 작업 시작: job_id={job_id}")

        return AsyncTTSResponse(
            job_id=job_id,
            status="pending",
            message="작업이 대기열에 추가되었습니다. job_id로 상태를 확인하세요.",
            estimated_time_seconds=estimated_time
        )

    except Exception as e:
        logger.error(f"비동기 파일 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비동기 작업 시작 실패: {str(e)}")


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    대시보드 통계 조회

    **응답:**
    - total_audio_files: 총 오디오 파일 수
    - total_speakers: 총 화자 수
    - total_duration_seconds: 총 재생 시간 (초)
    - total_storage_mb: 총 저장 용량 (MB)
    """
    try:
        stats = await tts_service.get_dashboard_stats(db)
        return stats

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")
