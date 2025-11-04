"""
화자 관리 서비스
화자 샘플 업로드, 임베딩 생성, 화자 목록 관리
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from models.database import Speaker
from models.zonos_model import ZonosModelWrapper, get_zonos_model
from utils.file_validator import FileValidator, validate_audio_file
from utils.concurrency import get_concurrency_manager
from utils.cache_service import get_cache_service
from config import (
    SPEAKER_UPLOAD_DIR,
    EMBEDDING_DIR,
    CACHE_KEY_SPEAKER_EMBEDDING,
    CACHE_TTL_SPEAKER_EMBEDDING
)
from loguru import logger


class SpeakerService:
    """화자 관리 서비스"""

    def __init__(
        self,
        speaker_upload_dir: str = SPEAKER_UPLOAD_DIR,
        embedding_dir: str = EMBEDDING_DIR
    ):
        self.speaker_upload_dir = Path(speaker_upload_dir)
        self.embedding_dir = Path(embedding_dir)
        self.file_validator = FileValidator()

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
        sample_path = None
        embedding_path = None

        try:
            # ============ 1. 파일 보안 검증 ============
            logger.info(f"화자 생성 시작: {name}")

            # 파일 검증 (크기, MIME 타입, 확장자)
            mime_type, file_size = await validate_audio_file(audio_file)
            logger.info(f"파일 검증 완료: {mime_type}, {file_size / 1024:.2f}KB")

            # 화자 이름 검증
            if not name or not name.strip():
                raise HTTPException(status_code=400, detail="화자 이름을 입력해주세요")

            name = name.strip()[:100]  # 최대 100자

            # ============ 2. 안전한 파일명 생성 ============
            safe_filename = self.file_validator.generate_safe_filename(
                audio_file.filename,
                prefix="speaker"
            )
            sample_path = self.speaker_upload_dir / safe_filename

            # ============ 3. 파일 저장 ============
            logger.info(f"화자 샘플 저장 중: {safe_filename}")
            with open(sample_path, "wb") as f:
                # 파일을 처음으로 되돌림
                await audio_file.seek(0)
                content = await audio_file.read()
                f.write(content)

            # ============ 4. 오디오 길이 검증 ============
            model = get_zonos_model()
            duration = model.get_audio_duration(str(sample_path))

            # 길이 검증 (5-30초)
            self.file_validator.validate_audio_duration(duration)
            logger.info(f"오디오 길이 검증 완료: {duration:.1f}초")

            # ============ 5. 화자 임베딩 생성 (동시성 제어) ============
            embedding_filename = f"embedding_{safe_filename.split('_')[1]}.pt"
            embedding_path = self.embedding_dir / embedding_filename

            # 임베딩 생성은 GPU 집약적이므로 별도 세마포어 사용
            concurrency = get_concurrency_manager()
            request_id = f"emb_{name}_{uuid.uuid4().hex[:6]}"

            async with concurrency.acquire_embedding(request_id):
                logger.info(f"[{request_id}] 화자 임베딩 생성 중: {name}")
                speaker_embedding = model.create_speaker_embedding(
                    str(sample_path),
                    str(embedding_path)
                )

                if speaker_embedding is None:
                    raise HTTPException(
                        status_code=500,
                        detail="화자 임베딩 생성에 실패했습니다. 오디오 품질을 확인해주세요."
                    )

                # 임베딩을 캐시에 저장 (UUID를 키로 사용)
                embedding_uuid = safe_filename.split('_')[1]
                await self._cache_speaker_embedding(embedding_uuid, speaker_embedding)

            # ============ 6. DB에 저장 ============
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

            logger.info(f"✓ 화자 생성 완료: ID={speaker.id}, 이름={name}, 길이={duration:.1f}초")
            return speaker

        except HTTPException:
            # HTTPException은 그대로 전파
            raise
        except Exception as e:
            logger.error(f"화자 생성 실패: {e}", exc_info=True)

            # 파일 정리
            if sample_path and Path(sample_path).exists():
                Path(sample_path).unlink()
                logger.info(f"샘플 파일 정리: {sample_path}")
            if embedding_path and Path(embedding_path).exists():
                Path(embedding_path).unlink()
                logger.info(f"임베딩 파일 정리: {embedding_path}")

            # 일반적인 에러를 HTTPException으로 변환
            raise HTTPException(
                status_code=500,
                detail=f"화자 생성 중 오류가 발생했습니다: {str(e)}"
            )

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

    # ==================== 캐싱 관련 메서드 ====================

    async def _cache_speaker_embedding(self, embedding_id: str, embedding):
        """화자 임베딩을 캐시에 저장"""
        cache = get_cache_service()
        cache_key = cache.generate_cache_key(
            CACHE_KEY_SPEAKER_EMBEDDING,
            embedding_id=embedding_id
        )

        success = await cache.set(
            cache_key,
            embedding,
            ttl=CACHE_TTL_SPEAKER_EMBEDDING
        )

        if success:
            logger.debug(f"화자 임베딩 캐시됨: {embedding_id}")
        else:
            logger.warning(f"화자 임베딩 캐싱 실패: {embedding_id}")

    async def load_speaker_embedding_with_cache(self, speaker_id: int, embedding_path: str):
        """
        화자 임베딩 로드 (캐시 우선)

        Args:
            speaker_id: 화자 ID
            embedding_path: 임베딩 파일 경로

        Returns:
            임베딩 텐서 또는 None
        """
        # 캐시 키 생성
        cache = get_cache_service()
        embedding_id = str(speaker_id)
        cache_key = cache.generate_cache_key(
            CACHE_KEY_SPEAKER_EMBEDDING,
            embedding_id=embedding_id
        )

        # 1. 캐시에서 조회 시도
        cached_embedding = await cache.get(cache_key)
        if cached_embedding is not None:
            logger.debug(f"캐시에서 임베딩 로드: speaker_id={speaker_id}")
            return cached_embedding

        # 2. 캐시 미스 - 파일에서 로드
        logger.debug(f"캐시 미스 - 파일에서 임베딩 로드: {embedding_path}")
        model = get_zonos_model()
        embedding = model.load_speaker_embedding(embedding_path)

        if embedding is not None:
            # 캐시에 저장
            await cache.set(
                cache_key,
                embedding,
                ttl=CACHE_TTL_SPEAKER_EMBEDDING
            )
            logger.debug(f"임베딩 캐시에 저장: speaker_id={speaker_id}")

        return embedding

    async def invalidate_speaker_cache(self, speaker_id: int):
        """화자 임베딩 캐시 무효화"""
        cache = get_cache_service()
        embedding_id = str(speaker_id)
        cache_key = cache.generate_cache_key(
            CACHE_KEY_SPEAKER_EMBEDDING,
            embedding_id=embedding_id
        )

        await cache.delete(cache_key)
        logger.info(f"화자 캐시 무효화: speaker_id={speaker_id}")
