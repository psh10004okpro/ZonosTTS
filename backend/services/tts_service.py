"""
TTS 서비스 로직
음성 생성, 파일 저장, DB 저장 등의 비즈니스 로직
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AudioFile, Speaker
from models.zonos_model import ZonosModelWrapper, get_zonos_model
from utils.concurrency import get_concurrency_manager
from loguru import logger


class TTSService:
    """TTS 비즈니스 로직 서비스"""

    def __init__(self, upload_dir: str = "uploads/generated"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio_file(
        self,
        text: str,
        db: AsyncSession,
        speaker_id: Optional[int] = None,
        language: str = "en-us",
        speaking_rate: float = 1.0,
        pitch_shift: float = 0.0,
        emotion: str = "neutral",
        save_to_db: bool = True
    ) -> Tuple[str, dict]:
        """
        음성 파일 생성 및 저장

        Args:
            text: 생성할 텍스트
            db: 데이터베이스 세션
            speaker_id: 화자 ID (없으면 기본 음성)
            language: 언어 코드
            speaking_rate: 말하기 속도
            pitch_shift: 피치 조절
            emotion: 감정
            save_to_db: DB 저장 여부

        Returns:
            (파일 경로, 메타데이터) 튜플
        """
        # 동시성 관리자 가져오기
        concurrency = get_concurrency_manager()
        request_id = f"tts_{uuid.uuid4().hex[:8]}"

        # 세마포어를 사용하여 동시 실행 제한
        async with concurrency.acquire_tts(request_id):
            try:
                # Zonos 모델 가져오기
                model = get_zonos_model()

                # 화자 임베딩 로드 (있는 경우)
                speaker_embedding = None
                if speaker_id:
                    speaker_embedding = await self._load_speaker_embedding(db, speaker_id)

                # 음성 생성
                logger.info(f"[{request_id}] 음성 생성 시작: 텍스트={text[:50]}... 화자={speaker_id}")
                audio, sample_rate = model.generate_speech(
                    text=text,
                    speaker=speaker_embedding,
                    language=language,
                    speaking_rate=speaking_rate,
                    pitch_shift=pitch_shift,
                    emotion=emotion
                )

                # 파일명 생성
                file_id = uuid.uuid4().hex[:12]
                filename = f"tts_{file_id}_{int(datetime.now().timestamp())}.wav"
                file_path = self.upload_dir / filename

                # 파일 저장
                model.save_audio(audio, sample_rate, str(file_path))
                file_size = file_path.stat().st_size
                duration = len(audio) / sample_rate

                logger.info(f"[{request_id}] ✓ 파일 저장 완료: {filename} ({duration:.2f}초, {file_size} bytes)")

                # DB에 저장
                audio_file_obj = None
                if save_to_db:
                    audio_file_obj = AudioFile(
                        filename=filename,
                        text=text,
                        speaker_id=speaker_id,
                        language=language,
                        speaking_rate=speaking_rate,
                        pitch_shift=pitch_shift,
                        emotion=emotion,
                        duration=duration,
                        file_size=file_size
                    )
                    db.add(audio_file_obj)
                    await db.commit()
                    await db.refresh(audio_file_obj)

                    # 화자 사용 횟수 증가
                    if speaker_id:
                        await self._increment_speaker_usage(db, speaker_id)

                    logger.info(f"[{request_id}] ✓ DB 저장 완료: ID={audio_file_obj.id}")

                # 메타데이터 반환
                metadata = {
                    "id": audio_file_obj.id if audio_file_obj else None,
                    "filename": filename,
                    "file_path": str(file_path),
                    "duration": duration,
                    "file_size": file_size,
                    "sample_rate": sample_rate
                }

                return str(file_path), metadata

            except Exception as e:
                logger.error(f"[{request_id}] 음성 파일 생성 실패: {e}")
                raise

    async def get_audio_file(self, db: AsyncSession, audio_id: int) -> Optional[AudioFile]:
        """오디오 파일 정보 조회"""
        result = await db.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        return result.scalar_one_or_none()

    async def list_audio_files(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Tuple[list[AudioFile], int]:
        """오디오 파일 목록 조회 (페이지네이션)"""
        # 기본 쿼리
        query = select(AudioFile).order_by(AudioFile.created_at.desc())

        # 검색 조건
        if search:
            query = query.where(AudioFile.text.contains(search))

        # 총 개수 조회
        count_query = select(func.count()).select_from(AudioFile)
        if search:
            count_query = count_query.where(AudioFile.text.contains(search))

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def delete_audio_file(self, db: AsyncSession, audio_id: int) -> bool:
        """오디오 파일 삭제"""
        try:
            audio = await self.get_audio_file(db, audio_id)
            if not audio:
                return False

            # 실제 파일 삭제
            file_path = self.upload_dir / audio.filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"파일 삭제: {file_path}")

            # DB에서 삭제
            await db.delete(audio)
            await db.commit()

            logger.info(f"✓ 오디오 파일 삭제 완료: ID={audio_id}")
            return True

        except Exception as e:
            logger.error(f"오디오 파일 삭제 실패: {e}")
            return False

    async def get_dashboard_stats(self, db: AsyncSession) -> dict:
        """대시보드 통계 조회"""
        # 총 오디오 파일 수
        total_audio_result = await db.execute(
            select(func.count()).select_from(AudioFile)
        )
        total_audio = total_audio_result.scalar()

        # 총 화자 수
        total_speaker_result = await db.execute(
            select(func.count()).select_from(Speaker)
        )
        total_speaker = total_speaker_result.scalar()

        # 총 재생 시간
        duration_result = await db.execute(
            select(func.sum(AudioFile.duration)).select_from(AudioFile)
        )
        total_duration = duration_result.scalar() or 0.0

        # 총 저장 용량
        size_result = await db.execute(
            select(func.sum(AudioFile.file_size)).select_from(AudioFile)
        )
        total_size = size_result.scalar() or 0

        return {
            "total_audio_files": total_audio,
            "total_speakers": total_speaker,
            "total_duration_seconds": round(total_duration, 2),
            "total_storage_mb": round(total_size / (1024 * 1024), 2)
        }

    async def _load_speaker_embedding(
        self,
        db: AsyncSession,
        speaker_id: int
    ) -> Optional[object]:
        """화자 임베딩 로드"""
        result = await db.execute(
            select(Speaker).where(Speaker.id == speaker_id)
        )
        speaker = result.scalar_one_or_none()

        if not speaker or not speaker.embedding_path:
            logger.warning(f"화자 임베딩을 찾을 수 없습니다: speaker_id={speaker_id}")
            return None

        # 임베딩 파일 로드
        model = get_zonos_model()
        return model.load_speaker_embedding(speaker.embedding_path)

    async def _increment_speaker_usage(self, db: AsyncSession, speaker_id: int):
        """화자 사용 횟수 증가"""
        result = await db.execute(
            select(Speaker).where(Speaker.id == speaker_id)
        )
        speaker = result.scalar_one_or_none()

        if speaker:
            speaker.usage_count += 1
            await db.commit()
