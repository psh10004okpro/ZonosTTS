"""
오디오 파일 관리 API 라우터
생성된 오디오 파일 목록, 다운로드, 삭제 등
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from models.database import get_db, AudioListResponse, AudioFileResponse
from services.tts_service import TTSService
from loguru import logger

router = APIRouter(prefix="/api/audio", tags=["Audio Files"])

# 서비스 인스턴스
tts_service = TTSService()


@router.get("/list", response_model=AudioListResponse)
async def list_audio_files(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    search: str = Query(None, description="텍스트 검색"),
    db: AsyncSession = Depends(get_db)
):
    """
    생성된 오디오 파일 목록 조회 (페이지네이션)

    **쿼리 파라미터:**
    - page: 페이지 번호 (기본 1)
    - page_size: 페이지당 항목 수 (기본 20, 최대 100)
    - search: 텍스트 검색 (선택)

    **응답:**
    - total: 총 항목 수
    - page: 현재 페이지
    - page_size: 페이지 크기
    - items: 오디오 파일 배열
    """
    try:
        items, total = await tts_service.list_audio_files(
            db=db,
            page=page,
            page_size=page_size,
            search=search
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    except Exception as e:
        logger.error(f"오디오 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio_file(
    audio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 오디오 파일 정보 조회

    **경로 파라미터:**
    - audio_id: 오디오 파일 ID

    **응답:**
    - 오디오 파일 정보
    """
    try:
        audio = await tts_service.get_audio_file(db, audio_id)
        if not audio:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다")

        return audio

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"오디오 파일 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 조회 실패: {str(e)}")


@router.get("/download/{audio_id}")
async def download_audio_file(
    audio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    오디오 파일 다운로드

    **경로 파라미터:**
    - audio_id: 오디오 파일 ID

    **응답:**
    - 오디오 파일 (WAV 형식)
    """
    try:
        audio = await tts_service.get_audio_file(db, audio_id)
        if not audio:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다")

        # 파일 경로
        file_path = Path(tts_service.upload_dir) / audio.filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

        # 파일 다운로드 응답
        return FileResponse(
            path=str(file_path),
            media_type="audio/wav",
            filename=audio.filename,
            headers={
                "Content-Disposition": f'attachment; filename="{audio.filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 다운로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"다운로드 실패: {str(e)}")


@router.delete("/{audio_id}")
async def delete_audio_file(
    audio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    오디오 파일 삭제

    **경로 파라미터:**
    - audio_id: 오디오 파일 ID

    **응답:**
    - 삭제 성공 메시지
    """
    try:
        success = await tts_service.delete_audio_file(db, audio_id)
        if not success:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다")

        return {"message": "오디오 파일이 삭제되었습니다", "audio_id": audio_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"삭제 실패: {str(e)}")


@router.get("/stream/{audio_id}")
async def stream_audio_file(
    audio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    오디오 파일 스트리밍 (브라우저 재생용)

    **경로 파라미터:**
    - audio_id: 오디오 파일 ID

    **응답:**
    - 오디오 스트림
    """
    try:
        audio = await tts_service.get_audio_file(db, audio_id)
        if not audio:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다")

        # 파일 경로
        file_path = Path(tts_service.upload_dir) / audio.filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

        # 스트리밍 응답
        return FileResponse(
            path=str(file_path),
            media_type="audio/wav",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_path.stat().st_size)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 스트리밍 실패: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 실패: {str(e)}")
