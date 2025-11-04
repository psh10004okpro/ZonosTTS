"""
화자 관리 서비스
화자 샘플 업로드, 임베딩 생성, 화자 목록 관리
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from models.database import Speaker
from models.zonos_model import ZonosModelWrapper, get_zonos_model
from loguru import logger


class SpeakerService:
    """화자 관리 서비스"""

    def __init__(
        self,
        speaker_upload_dir: str = "uploads/speakers",
        embedding_dir: str = "uploads/embeddings"
    ):
        self.speaker_upload_dir = Path(speaker_upload_dir)
        self.embedding_dir = Path(embedding_dir)

        self.speaker_upload_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dir.mkdir(parents=True, exist_ok=True)

    async def create_speaker(
        self,
        db: AsyncSession,
        name: str,
        audio_file: UploadFile,
        language: str = "en-us"
    ) -> Speaker:
        """
        새 화자 생성 (샘플 업로드 및 임베딩 생성)

        Args:
            db: 데이터베이스 세션
            name: 화자 이름
            audio_file: 화자 샘플 오디오 파일
            language: 언어

        Returns:
            생성된 Speaker 객체
        """
        try:
            # 파일명 생성
            file_id = uuid.uuid4().hex[:12]
            ext = Path(audio_file.filename).suffix
            sample_filename = f"speaker_{file_id}_{int(datetime.now().timestamp())}{ext}"
            sample_path = self.speaker_upload_dir / sample_filename

            # 오디오 파일 저장
            logger.info(f"화자 샘플 저장 중: {sample_filename}")
            with open(sample_path, "wb") as f:
                content = await audio_file.read()
                f.write(content)

            # 오디오 재생 시간 계산
            model = get_zonos_model()
            duration = model.get_audio_duration(str(sample_path))

            # 화자 임베딩 생성
            embedding_filename = f"embedding_{file_id}.pt"
            embedding_path = self.embedding_dir / embedding_filename

            logger.info(f"화자 임베딩 생성 중: {name}")
            speaker_embedding = model.create_speaker_embedding(
                str(sample_path),
                str(embedding_path)
            )

            if speaker_embedding is None:
                raise Exception("화자 임베딩 생성 실패")

            # DB에 저장
            speaker = Speaker(
                name=name,
                sample_path=str(sample_path),
                embedding_path=str(embedding_path),
                language=language,
                duration=duration,
                usage_count=0
            )

            db.add(speaker)
            await db.commit()
            await db.refresh(speaker)

            logger.info(f"✓ 화자 생성 완료: ID={speaker.id}, 이름={name}")
            return speaker

        except Exception as e:
            logger.error(f"화자 생성 실패: {e}")
            # 롤백 및 파일 정리
            if sample_path.exists():
                sample_path.unlink()
            if embedding_path.exists():
                embedding_path.unlink()
            raise

    async def get_speaker(self, db: AsyncSession, speaker_id: int) -> Optional[Speaker]:
        """화자 정보 조회"""
        result = await db.execute(
            select(Speaker).where(Speaker.id == speaker_id)
        )
        return result.scalar_one_or_none()

    async def list_speakers(self, db: AsyncSession) -> List[Speaker]:
        """모든 화자 목록 조회"""
        result = await db.execute(
            select(Speaker).order_by(Speaker.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_speaker(self, db: AsyncSession, speaker_id: int) -> bool:
        """화자 삭제"""
        try:
            speaker = await self.get_speaker(db, speaker_id)
            if not speaker:
                return False

            # 샘플 파일 삭제
            sample_path = Path(speaker.sample_path)
            if sample_path.exists():
                sample_path.unlink()
                logger.info(f"샘플 파일 삭제: {sample_path}")

            # 임베딩 파일 삭제
            if speaker.embedding_path:
                embedding_path = Path(speaker.embedding_path)
                if embedding_path.exists():
                    embedding_path.unlink()
                    logger.info(f"임베딩 파일 삭제: {embedding_path}")

            # DB에서 삭제
            await db.delete(speaker)
            await db.commit()

            logger.info(f"✓ 화자 삭제 완료: ID={speaker_id}")
            return True

        except Exception as e:
            logger.error(f"화자 삭제 실패: {e}")
            return False

    async def validate_audio_duration(self, audio_path: str) -> Tuple[bool, float, str]:
        """
        오디오 파일 유효성 검사 (5~30초)

        Returns:
            (유효 여부, 재생 시간, 메시지)
        """
        try:
            model = get_zonos_model()
            duration = model.get_audio_duration(audio_path)

            if duration < 5.0:
                return False, duration, "오디오 샘플이 너무 짧습니다 (최소 5초 필요)"
            elif duration > 30.0:
                return False, duration, "오디오 샘플이 너무 깁니다 (최대 30초)"
            else:
                return True, duration, "유효한 오디오 샘플입니다"

        except Exception as e:
            logger.error(f"오디오 검증 실패: {e}")
            return False, 0.0, f"오디오 파일 읽기 실패: {str(e)}"
