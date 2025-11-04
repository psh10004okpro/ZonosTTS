"""
파일 검증 유틸리티
업로드된 파일의 보안 검증 및 유효성 검사
"""

import os
import re
import uuid
import magic
import mimetypes
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
from loguru import logger

from config import (
    MAX_AUDIO_FILE_SIZE,
    ALLOWED_AUDIO_MIME_TYPES,
    ALLOWED_AUDIO_EXTENSIONS,
    MIN_SPEAKER_DURATION,
    MAX_SPEAKER_DURATION,
    SAFE_FILENAME_CHARS,
)


class FileValidator:
    """파일 검증 클래스"""

    @staticmethod
    def validate_file_size(file: UploadFile, max_size: int = MAX_AUDIO_FILE_SIZE) -> None:
        """
        파일 크기 검증

        Args:
            file: 업로드된 파일
            max_size: 최대 파일 크기 (바이트)

        Raises:
            HTTPException: 파일이 너무 큰 경우
        """
        # 파일 크기를 확인하기 위해 끝까지 읽기
        file.file.seek(0, 2)  # 파일 끝으로 이동
        file_size = file.file.tell()
        file.file.seek(0)  # 다시 처음으로

        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"파일이 너무 큽니다. (현재: {size_mb:.2f}MB, 최대: {max_mb:.2f}MB)"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="빈 파일은 업로드할 수 없습니다"
            )

        logger.info(f"파일 크기 검증 통과: {file_size / 1024:.2f}KB")

    @staticmethod
    def validate_file_extension(filename: str) -> None:
        """
        파일 확장자 검증

        Args:
            filename: 파일명

        Raises:
            HTTPException: 허용되지 않은 확장자
        """
        ext = Path(filename).suffix.lower()

        if not ext:
            raise HTTPException(
                status_code=400,
                detail="파일 확장자가 없습니다"
            )

        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
            )

        logger.info(f"파일 확장자 검증 통과: {ext}")

    @staticmethod
    async def validate_mime_type(file: UploadFile) -> str:
        """
        MIME 타입 검증 (실제 파일 내용 검사)

        Args:
            file: 업로드된 파일

        Returns:
            검증된 MIME 타입

        Raises:
            HTTPException: 허용되지 않은 MIME 타입
        """
        # 파일 시작 부분 읽기 (Magic bytes 확인)
        content = await file.read(2048)
        file.file.seek(0)  # 다시 처음으로

        # python-magic을 사용하여 실제 MIME 타입 확인
        try:
            mime_type = magic.from_buffer(content, mime=True)
        except Exception as e:
            logger.error(f"MIME 타입 감지 실패: {e}")
            raise HTTPException(
                status_code=400,
                detail="파일 형식을 확인할 수 없습니다"
            )

        # MIME 타입 검증
        if mime_type not in ALLOWED_AUDIO_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 오디오 형식입니다. (감지된 타입: {mime_type})"
            )

        logger.info(f"MIME 타입 검증 통과: {mime_type}")
        return mime_type

    @staticmethod
    def validate_audio_duration(
        duration: float,
        min_duration: float = MIN_SPEAKER_DURATION,
        max_duration: float = MAX_SPEAKER_DURATION
    ) -> None:
        """
        오디오 길이 검증

        Args:
            duration: 오디오 길이 (초)
            min_duration: 최소 길이
            max_duration: 최대 길이

        Raises:
            HTTPException: 길이가 범위를 벗어난 경우
        """
        if duration < min_duration:
            raise HTTPException(
                status_code=400,
                detail=f"오디오가 너무 짧습니다. (현재: {duration:.1f}초, 최소: {min_duration:.1f}초)"
            )

        if duration > max_duration:
            raise HTTPException(
                status_code=400,
                detail=f"오디오가 너무 깁니다. (현재: {duration:.1f}초, 최대: {max_duration:.1f}초)"
            )

        logger.info(f"오디오 길이 검증 통과: {duration:.1f}초")

    @staticmethod
    def generate_safe_filename(original_filename: str, prefix: str = "") -> str:
        """
        안전한 파일명 생성

        Args:
            original_filename: 원본 파일명
            prefix: 파일명 접두사

        Returns:
            안전한 파일명
        """
        # 확장자 추출
        ext = Path(original_filename).suffix.lower()

        # UUID 생성
        unique_id = uuid.uuid4().hex[:12]

        # 타임스탬프
        import time
        timestamp = int(time.time())

        # 안전한 파일명 생성
        if prefix:
            filename = f"{prefix}_{unique_id}_{timestamp}{ext}"
        else:
            filename = f"{unique_id}_{timestamp}{ext}"

        # 안전한 문자만 사용
        safe_filename = "".join(c for c in filename if c in SAFE_FILENAME_CHARS or c == ".")

        return safe_filename

    @staticmethod
    def sanitize_text(text: str, max_length: int = 5000) -> str:
        """
        텍스트 입력 검증 및 정제

        Args:
            text: 입력 텍스트
            max_length: 최대 길이

        Returns:
            정제된 텍스트

        Raises:
            HTTPException: 텍스트가 너무 긴 경우
        """
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="텍스트를 입력해주세요"
            )

        text = text.strip()

        if len(text) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"텍스트가 너무 깁니다. (현재: {len(text)}자, 최대: {max_length}자)"
            )

        # 제어 문자 제거 (개행 제외)
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

        return text


async def validate_audio_file(file: UploadFile) -> Tuple[str, int]:
    """
    오디오 파일 전체 검증 (원스톱 검증)

    Args:
        file: 업로드된 파일

    Returns:
        (MIME 타입, 파일 크기) 튜플

    Raises:
        HTTPException: 검증 실패 시
    """
    validator = FileValidator()

    # 1. 파일명 검증
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다")

    # 2. 확장자 검증
    validator.validate_file_extension(file.filename)

    # 3. 파일 크기 검증
    validator.validate_file_size(file)

    # 4. MIME 타입 검증 (실제 파일 내용)
    mime_type = await validator.validate_mime_type(file)

    # 파일 크기 반환
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    logger.info(f"✓ 파일 검증 완료: {file.filename} ({mime_type}, {file_size / 1024:.2f}KB)")

    return mime_type, file_size
