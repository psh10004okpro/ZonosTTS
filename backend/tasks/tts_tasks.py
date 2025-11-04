"""
비동기 TTS 생성 태스크
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from celery import Task
from celery_app import celery_app
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from models.database import Job, AudioFile, Speaker
from services.tts_service import TTSService
from services.speaker_service import SpeakerService
from models.zonos_model import get_zonos_model
from config import DATABASE_URL
from utils.metrics import metrics_collector


# 비동기 데이터베이스 엔진 (Celery 워커용)
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class AsyncTaskBase(Task):
    """비동기 태스크 베이스 클래스"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """태스크 실패 시 호출"""
        logger.error(f"Task {task_id} failed: {exc}")
        asyncio.run(self._update_job_status(
            task_id,
            status="failed",
            error_message=str(exc),
            error_type=type(exc).__name__
        ))

    def on_success(self, retval, task_id, args, kwargs):
        """태스크 성공 시 호출"""
        logger.info(f"Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """태스크 재시도 시 호출"""
        logger.warning(f"Task {task_id} is being retried: {exc}")

    async def _update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result_data: Optional[Dict] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """작업 상태 업데이트"""
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(Job).where(Job.job_id == job_id))
                job = result.scalar_one_or_none()

                if not job:
                    logger.error(f"Job not found: {job_id}")
                    return

                if status:
                    job.status = status
                    if status == "processing" and not job.started_at:
                        job.started_at = datetime.utcnow()
                    elif status in ("completed", "failed"):
                        job.completed_at = datetime.utcnow()

                if progress is not None:
                    job.progress = progress

                if result_data:
                    job.result_data = json.dumps(result_data)

                if error_message:
                    job.error_message = error_message

                if error_type:
                    job.error_type = error_type

                await db.commit()
                logger.info(f"Job {job_id} status updated: {status}")

            except Exception as e:
                logger.error(f"Failed to update job status: {e}")
                await db.rollback()


@celery_app.task(
    base=AsyncTaskBase,
    bind=True,
    name="tasks.tts_tasks.generate_tts_async",
    max_retries=3,
    default_retry_delay=60
)
def generate_tts_async(
    self,
    job_id: str,
    text: str,
    speaker_id: Optional[int] = None,
    language: str = "en-us",
    speaking_rate: float = 1.0,
    pitch_shift: float = 0.0,
    emotion: str = "neutral"
) -> Dict[str, Any]:
    """
    비동기 TTS 생성 태스크

    Args:
        job_id: 작업 ID
        text: 생성할 텍스트
        speaker_id: 화자 ID
        language: 언어 코드
        speaking_rate: 말하기 속도
        pitch_shift: 피치 조절
        emotion: 감정

    Returns:
        결과 딕셔너리 (audio_id, filename, duration 등)
    """
    logger.info(f"[{job_id}] Starting async TTS generation")

    try:
        # 진행 상태 업데이트
        asyncio.run(self._update_job_status(job_id, status="processing", progress=10))

        # TTS 서비스 실행 (동기 → 비동기 브릿지)
        result = asyncio.run(_generate_tts_internal(
            job_id=job_id,
            text=text,
            speaker_id=speaker_id,
            language=language,
            speaking_rate=speaking_rate,
            pitch_shift=pitch_shift,
            emotion=emotion,
            progress_callback=lambda p: asyncio.run(
                self._update_job_status(job_id, progress=p)
            )
        ))

        # 성공 처리
        asyncio.run(self._update_job_status(
            job_id,
            status="completed",
            progress=100,
            result_data=result
        ))

        # 메트릭 기록
        metrics_collector.record_tts_request(
            status="success",
            language=language,
            has_speaker=speaker_id is not None,
            duration=result.get("duration"),
            text_length=len(text)
        )

        logger.info(f"[{job_id}] TTS generation completed: {result['filename']}")
        return result

    except Exception as e:
        logger.error(f"[{job_id}] TTS generation failed: {e}")

        # 메트릭 기록
        metrics_collector.record_error(
            error_type=type(e).__name__,
            endpoint="async_tts"
        )

        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"[{job_id}] Retrying... (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)

        # 실패 처리
        asyncio.run(self._update_job_status(
            job_id,
            status="failed",
            error_message=str(e),
            error_type=type(e).__name__
        ))

        raise


async def _generate_tts_internal(
    job_id: str,
    text: str,
    speaker_id: Optional[int],
    language: str,
    speaking_rate: float,
    pitch_shift: float,
    emotion: str,
    progress_callback
) -> Dict[str, Any]:
    """내부 TTS 생성 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 진행률 업데이트
            progress_callback(30)

            # TTS 서비스 생성
            tts_service = TTSService()

            # 진행률 업데이트
            progress_callback(50)

            # 음성 생성
            file_path, metadata = await tts_service.generate_audio_file(
                text=text,
                db=db,
                speaker_id=speaker_id,
                language=language,
                speaking_rate=speaking_rate,
                pitch_shift=pitch_shift,
                emotion=emotion,
                save_to_db=True
            )

            # 진행률 업데이트
            progress_callback(90)

            # Job 업데이트 (result_audio_id 저장)
            if metadata.get("id"):
                result = await db.execute(select(Job).where(Job.job_id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.result_audio_id = metadata["id"]
                    await db.commit()

            return {
                "audio_id": metadata.get("id"),
                "filename": metadata["filename"],
                "file_path": str(file_path),
                "duration": metadata["duration"],
                "file_size": metadata["file_size"],
                "sample_rate": metadata["sample_rate"]
            }

        except Exception as e:
            logger.error(f"[{job_id}] Internal TTS generation error: {e}")
            raise


@celery_app.task(
    base=AsyncTaskBase,
    bind=True,
    name="tasks.tts_tasks.generate_speaker_embedding_async",
    max_retries=2,
    default_retry_delay=30
)
def generate_speaker_embedding_async(
    self,
    job_id: str,
    speaker_id: int,
    audio_path: str,
    language: str = "en-us"
) -> Dict[str, Any]:
    """
    비동기 화자 임베딩 생성 태스크

    Args:
        job_id: 작업 ID
        speaker_id: 화자 ID
        audio_path: 오디오 파일 경로
        language: 언어 코드

    Returns:
        결과 딕셔너리
    """
    logger.info(f"[{job_id}] Starting async speaker embedding generation")

    try:
        asyncio.run(self._update_job_status(job_id, status="processing", progress=20))

        # 임베딩 생성
        result = asyncio.run(_generate_embedding_internal(
            job_id=job_id,
            speaker_id=speaker_id,
            audio_path=audio_path,
            language=language,
            progress_callback=lambda p: asyncio.run(
                self._update_job_status(job_id, progress=p)
            )
        ))

        # 성공 처리
        asyncio.run(self._update_job_status(
            job_id,
            status="completed",
            progress=100,
            result_data=result
        ))

        # 메트릭 기록
        metrics_collector.record_speaker_embedding(
            status="success",
            language=language,
            duration=result.get("duration")
        )

        logger.info(f"[{job_id}] Speaker embedding generation completed")
        return result

    except Exception as e:
        logger.error(f"[{job_id}] Speaker embedding generation failed: {e}")

        # 재시도 로직
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # 실패 처리
        asyncio.run(self._update_job_status(
            job_id,
            status="failed",
            error_message=str(e),
            error_type=type(e).__name__
        ))

        raise


async def _generate_embedding_internal(
    job_id: str,
    speaker_id: int,
    audio_path: str,
    language: str,
    progress_callback
) -> Dict[str, Any]:
    """내부 임베딩 생성 로직"""
    async with AsyncSessionLocal() as db:
        try:
            progress_callback(40)

            # Speaker 서비스 생성
            speaker_service = SpeakerService()

            progress_callback(60)

            # 임베딩 생성 (이미 생성되어 있다면 재사용)
            result = await db.execute(select(Speaker).where(Speaker.id == speaker_id))
            speaker = result.scalar_one_or_none()

            if not speaker:
                raise ValueError(f"Speaker not found: {speaker_id}")

            progress_callback(90)

            # Job 업데이트
            job_result = await db.execute(select(Job).where(Job.job_id == job_id))
            job = job_result.scalar_one_or_none()
            if job:
                job.result_speaker_id = speaker_id
                await db.commit()

            return {
                "speaker_id": speaker_id,
                "embedding_path": speaker.embedding_path,
                "duration": speaker.duration
            }

        except Exception as e:
            logger.error(f"[{job_id}] Internal embedding generation error: {e}")
            raise


@celery_app.task(name="tasks.tts_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """
    오래된 완료/실패 작업 정리 (주기적 실행)
    7일 이상 된 작업 삭제
    """
    logger.info("Starting cleanup of old jobs")

    try:
        result = asyncio.run(_cleanup_old_jobs_internal())
        logger.info(f"Cleanup completed: {result['deleted_count']} jobs deleted")
        return result

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


async def _cleanup_old_jobs_internal() -> Dict[str, int]:
    """내부 정리 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 7일 이전 날짜
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            # 완료/실패 작업 삭제
            stmt = delete(Job).where(
                Job.status.in_(["completed", "failed"]),
                Job.completed_at < cutoff_date
            )
            result = await db.execute(stmt)
            await db.commit()

            deleted_count = result.rowcount
            return {"deleted_count": deleted_count}

        except Exception as e:
            await db.rollback()
            logger.error(f"Internal cleanup error: {e}")
            raise


@celery_app.task(name="tasks.tts_tasks.update_job_statistics")
def update_job_statistics():
    """
    작업 통계 업데이트 (주기적 실행)
    """
    logger.info("Updating job statistics")

    try:
        result = asyncio.run(_update_statistics_internal())
        logger.info(f"Statistics updated: {result}")
        return result

    except Exception as e:
        logger.error(f"Statistics update failed: {e}")
        raise


async def _update_statistics_internal() -> Dict[str, int]:
    """내부 통계 업데이트 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 상태별 작업 수 조회
            from sqlalchemy import func

            pending = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == "pending")
            )
            processing = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == "processing")
            )
            completed = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == "completed")
            )
            failed = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == "failed")
            )

            stats = {
                "pending": pending.scalar(),
                "processing": processing.scalar(),
                "completed": completed.scalar(),
                "failed": failed.scalar()
            }

            # 메트릭 업데이트 (선택사항)
            # metrics_collector.update_job_stats(stats)

            return stats

        except Exception as e:
            logger.error(f"Internal statistics update error: {e}")
            raise
