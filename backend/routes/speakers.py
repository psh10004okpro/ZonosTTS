"""
화자 관리 API 라우터
화자 샘플 업로드, 목록 조회, 삭제 등
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from models.database import get_db, SpeakerResponse, SpeakerCreate
from services.speaker_service import SpeakerService
from loguru import logger

router = APIRouter(prefix="/api/speakers", tags=["Speakers"])

# 서비스 인스턴스
speaker_service = SpeakerService()


@router.post("/upload", response_model=SpeakerResponse)
async def upload_speaker(
    name: str = Form(..., description="화자 이름"),
    language: str = Form("en-us", description="언어"),
    audio_file: UploadFile = File(..., description="화자 샘플 오디오 (5-30초)"),
    db: AsyncSession = Depends(get_db)
):
    """
    새 화자 샘플 업로드

    **Form 데이터:**
    - name: 화자 이름 (필수)
    - language: 언어 (기본 en-us)
    - audio_file: 오디오 파일 (5-30초, WAV/MP3/FLAC 등)

    **응답:**
    - 생성된 화자 정보
    """
    try:
        logger.info(f"화자 업로드 요청: 이름={name}, 파일={audio_file.filename}")

        # 파일 형식 검증
        allowed_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
        file_ext = audio_file.filename.split(".")[-1].lower()
        if f".{file_ext}" not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. 허용: {allowed_extensions}"
            )

        # 화자 생성
        speaker = await speaker_service.create_speaker(
            db=db,
            name=name,
            audio_file=audio_file,
            language=language
        )

        logger.info(f"✓ 화자 업로드 완료: ID={speaker.id}, 이름={name}")
        return speaker

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"화자 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"화자 업로드 실패: {str(e)}")


@router.get("/list", response_model=List[SpeakerResponse])
async def list_speakers(db: AsyncSession = Depends(get_db)):
    """
    모든 화자 목록 조회

    **응답:**
    - 화자 목록 배열
    """
    try:
        speakers = await speaker_service.list_speakers(db)
        return speakers

    except Exception as e:
        logger.error(f"화자 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"화자 목록 조회 실패: {str(e)}")


@router.get("/{speaker_id}", response_model=SpeakerResponse)
async def get_speaker(
    speaker_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 화자 정보 조회

    **경로 파라미터:**
    - speaker_id: 화자 ID

    **응답:**
    - 화자 정보
    """
    try:
        speaker = await speaker_service.get_speaker(db, speaker_id)
        if not speaker:
            raise HTTPException(status_code=404, detail="화자를 찾을 수 없습니다")

        return speaker

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"화자 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"화자 조회 실패: {str(e)}")


@router.delete("/{speaker_id}")
async def delete_speaker(
    speaker_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    화자 삭제

    **경로 파라미터:**
    - speaker_id: 화자 ID

    **응답:**
    - 삭제 성공 메시지
    """
    try:
        success = await speaker_service.delete_speaker(db, speaker_id)
        if not success:
            raise HTTPException(status_code=404, detail="화자를 찾을 수 없습니다")

        return {"message": "화자가 삭제되었습니다", "speaker_id": speaker_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"화자 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"화자 삭제 실패: {str(e)}")
