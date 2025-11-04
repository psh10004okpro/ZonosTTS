"""
비동기 작업 상태 조회 API
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from models.database import Job, JobResponse, AudioFileResponse, get_db
from celery_app import celery_app

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    작업 상태 조회

    Args:
        job_id: Celery 작업 ID

    Returns:
        작업 상태 정보
    """
    try:
        # 데이터베이스에서 작업 조회
        result = await db.execute(
            select(Job).where(Job.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        # request_params와 result_data를 dict로 변환
        import json
        job_dict = {
            "id": job.id,
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "request_params": json.loads(job.request_params) if job.request_params else None,
            "result_data": json.loads(job.result_data) if job.result_data else None,
            "error_message": job.error_message,
            "error_type": job.error_type,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result_audio_id": job.result_audio_id,
            "result_speaker_id": job.result_speaker_id
        }

        return JobResponse(**job_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail="작업 상태 조회 실패")


@router.get("/{job_id}/result")
async def get_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    작업 결과 조회 (완료된 경우에만)

    Args:
        job_id: Celery 작업 ID

    Returns:
        작업 결과 (완료 시) 또는 상태 정보
    """
    try:
        # Eager loading으로 N+1 쿼리 방지
        result = await db.execute(
            select(Job)
            .options(
                selectinload(Job.result_audio),
                selectinload(Job.result_speaker)
            )
            .where(Job.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        # 작업이 완료되지 않은 경우
        if job.status not in ("completed", "failed"):
            return {
                "status": job.status,
                "progress": job.progress,
                "message": f"작업이 {'처리 중' if job.status == 'processing' else '대기 중'}입니다"
            }

        # 작업이 실패한 경우
        if job.status == "failed":
            return {
                "status": "failed",
                "error_message": job.error_message,
                "error_type": job.error_type
            }

        # 작업이 완료된 경우
        import json
        result_data = json.loads(job.result_data) if job.result_data else {}

        response = {
            "status": "completed",
            "job_type": job.job_type,
            "result": result_data
        }

        # TTS 작업인 경우 오디오 파일 정보 추가 (이미 eager load됨)
        if job.job_type == "tts" and job.result_audio:
            response["audio"] = AudioFileResponse.from_orm(job.result_audio).dict()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {e}")
        raise HTTPException(status_code=500, detail="작업 결과 조회 실패")


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="상태 필터 (pending, processing, completed, failed)"),
    job_type: Optional[str] = Query(None, description="작업 타입 필터 (tts, embedding)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db)
):
    """
    작업 목록 조회 (페이지네이션)

    Args:
        status: 상태 필터
        job_type: 작업 타입 필터
        page: 페이지 번호
        page_size: 페이지 크기

    Returns:
        작업 목록
    """
    try:
        # 기본 쿼리 (eager loading으로 N+1 쿼리 방지)
        query = select(Job).options(
            selectinload(Job.result_audio),
            selectinload(Job.result_speaker)
        ).order_by(Job.created_at.desc())

        # 필터 적용
        if status:
            query = query.where(Job.status == status)
        if job_type:
            query = query.where(Job.job_type == job_type)

        # 페이지네이션
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        jobs = result.scalars().all()

        # JSON 필드 파싱
        import json
        jobs_list = []
        for job in jobs:
            job_dict = {
                "id": job.id,
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "request_params": json.loads(job.request_params) if job.request_params else None,
                "result_data": json.loads(job.result_data) if job.result_data else None,
                "error_message": job.error_message,
                "error_type": job.error_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "result_audio_id": job.result_audio_id,
                "result_speaker_id": job.result_speaker_id
            }
            jobs_list.append(JobResponse(**job_dict))

        return jobs_list

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="작업 목록 조회 실패")


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    작업 취소 (처리 중인 작업만 가능)

    Args:
        job_id: Celery 작업 ID

    Returns:
        취소 결과
    """
    try:
        # 데이터베이스에서 작업 조회
        result = await db.execute(
            select(Job).where(Job.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        # 이미 완료되거나 실패한 작업은 취소 불가
        if job.status in ("completed", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"작업이 이미 {job.status} 상태입니다. 취소할 수 없습니다."
            )

        # Celery 작업 취소
        celery_app.control.revoke(job_id, terminate=True)

        # DB 상태 업데이트
        job.status = "failed"
        job.error_message = "사용자에 의해 취소됨"
        job.error_type = "UserCancelled"
        job.completed_at = None

        await db.commit()

        logger.info(f"Job {job_id} cancelled by user")

        return {
            "success": True,
            "message": "작업이 취소되었습니다",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail="작업 취소 실패")


@router.get("/statistics/summary")
async def get_job_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    작업 통계 조회

    Returns:
        작업 통계 (상태별 개수, 평균 처리 시간 등)
    """
    try:
        # 상태별 작업 수
        status_counts = {}
        for status in ["pending", "processing", "completed", "failed"]:
            result = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == status)
            )
            status_counts[status] = result.scalar()

        # 타입별 작업 수
        type_counts = {}
        for job_type in ["tts", "embedding"]:
            result = await db.execute(
                select(func.count()).select_from(Job).where(Job.job_type == job_type)
            )
            type_counts[job_type] = result.scalar()

        # 평균 처리 시간 (완료된 작업만)
        from sqlalchemy import extract
        completed_jobs = await db.execute(
            select(Job).where(
                Job.status == "completed",
                Job.started_at.isnot(None),
                Job.completed_at.isnot(None)
            )
        )
        jobs = completed_jobs.scalars().all()

        avg_duration = 0.0
        if jobs:
            durations = [
                (job.completed_at - job.started_at).total_seconds()
                for job in jobs
            ]
            avg_duration = sum(durations) / len(durations)

        return {
            "status_counts": status_counts,
            "type_counts": type_counts,
            "total_jobs": sum(status_counts.values()),
            "average_duration_seconds": round(avg_duration, 2),
            "success_rate": (
                status_counts["completed"] / sum(status_counts.values()) * 100
                if sum(status_counts.values()) > 0 else 0
            )
        }

    except Exception as e:
        logger.error(f"Failed to get job statistics: {e}")
        raise HTTPException(status_code=500, detail="작업 통계 조회 실패")
