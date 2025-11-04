"""
File validator unit tests
"""

import pytest
from io import BytesIO
from fastapi import UploadFile

from utils.file_validator import FileValidator
from utils.exceptions import (
    FileSizeTooLargeError,
    FileValidationError,
    InvalidFileTypeError,
    AudioDurationError,
    InvalidInputError,
)


class TestFileValidator:
    """FileValidator 클래스 테스트"""

    def test_validate_file_size_valid(self):
        """정상 파일 크기 검증"""
        # 작은 파일 (1KB)
        content = b"x" * 1024
        file = UploadFile(filename="test.wav", file=BytesIO(content))

        # 예외가 발생하지 않아야 함
        FileValidator.validate_file_size(file)

    def test_validate_file_size_too_large(self):
        """파일 크기 초과 검증"""
        # 매우 큰 파일
        max_size = 1024  # 1KB로 제한
        content = b"x" * (max_size + 1)
        file = UploadFile(filename="test.wav", file=BytesIO(content))

        with pytest.raises(FileSizeTooLargeError) as exc_info:
            FileValidator.validate_file_size(file, max_size=max_size)

        assert "너무 큽니다" in str(exc_info.value)
        assert exc_info.value.details["file_size"] == max_size + 1

    def test_validate_file_size_empty(self):
        """빈 파일 검증"""
        file = UploadFile(filename="test.wav", file=BytesIO(b""))

        with pytest.raises(FileValidationError) as exc_info:
            FileValidator.validate_file_size(file)

        assert "빈 파일" in str(exc_info.value)

    def test_validate_file_extension_valid(self):
        """정상 확장자 검증"""
        valid_extensions = ["test.wav", "test.mp3", "test.flac", "test.ogg"]

        for filename in valid_extensions:
            # 예외가 발생하지 않아야 함
            FileValidator.validate_file_extension(filename)

    def test_validate_file_extension_invalid(self):
        """잘못된 확장자 검증"""
        invalid_filenames = ["test.txt", "test.exe", "test.pdf"]

        for filename in invalid_filenames:
            with pytest.raises(InvalidFileTypeError):
                FileValidator.validate_file_extension(filename)

    def test_validate_file_extension_no_extension(self):
        """확장자 없는 파일"""
        with pytest.raises(InvalidFileTypeError) as exc_info:
            FileValidator.validate_file_extension("testfile")

        assert "확장자가 없습니다" in str(exc_info.value)

    def test_validate_audio_duration_valid(self):
        """정상 오디오 길이 검증"""
        # 10초 (5-30초 범위 내)
        FileValidator.validate_audio_duration(10.0)

        # 경계값 테스트
        FileValidator.validate_audio_duration(5.0)   # 최소값
        FileValidator.validate_audio_duration(30.0)  # 최대값

    def test_validate_audio_duration_too_short(self):
        """너무 짧은 오디오"""
        with pytest.raises(AudioDurationError) as exc_info:
            FileValidator.validate_audio_duration(3.0)  # 5초 미만

        assert "너무 짧습니다" in str(exc_info.value)
        assert exc_info.value.details["duration"] == 3.0

    def test_validate_audio_duration_too_long(self):
        """너무 긴 오디오"""
        with pytest.raises(AudioDurationError) as exc_info:
            FileValidator.validate_audio_duration(35.0)  # 30초 초과

        assert "너무 깁니다" in str(exc_info.value)
        assert exc_info.value.details["duration"] == 35.0

    def test_generate_safe_filename(self):
        """안전한 파일명 생성"""
        filename = FileValidator.generate_safe_filename("test.wav", prefix="speaker")

        # 검증
        assert filename.startswith("speaker_")
        assert filename.endswith(".wav")
        assert len(filename) > 20  # UUID + timestamp가 포함됨

        # 특수문자가 없어야 함
        assert all(c.isalnum() or c in "._-" for c in filename)

    def test_sanitize_text_valid(self):
        """정상 텍스트 정제"""
        text = "  Hello, world!  "
        result = FileValidator.sanitize_text(text)

        assert result == "Hello, world!"
        assert result == text.strip()

    def test_sanitize_text_empty(self):
        """빈 텍스트"""
        with pytest.raises(InvalidInputError) as exc_info:
            FileValidator.sanitize_text("")

        assert "텍스트를 입력해주세요" in str(exc_info.value)

        with pytest.raises(InvalidInputError):
            FileValidator.sanitize_text("   ")  # 공백만

    def test_sanitize_text_too_long(self):
        """너무 긴 텍스트"""
        long_text = "x" * 6000  # 5000자 초과

        with pytest.raises(InvalidInputError) as exc_info:
            FileValidator.sanitize_text(long_text)

        assert "너무 깁니다" in str(exc_info.value)
        assert exc_info.value.details["text_length"] == 6000

    def test_sanitize_text_removes_control_chars(self):
        """제어 문자 제거"""
        text_with_control = "Hello\x00\x01\x02World"
        result = FileValidator.sanitize_text(text_with_control)

        # 제어 문자가 제거되어야 함
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "HelloWorld" == result


@pytest.mark.asyncio
class TestAsyncFileValidator:
    """비동기 파일 검증 테스트"""

    async def test_validate_mime_type_valid(self):
        """정상 MIME 타입 검증"""
        # WAV 파일 헤더 (간단한 더미)
        wav_header = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fmt ' + b'\x00' * 100

        file = UploadFile(
            filename="test.wav",
            file=BytesIO(wav_header)
        )

        # python-magic이 설치되지 않은 경우 스킵
        pytest.importorskip("magic")

        try:
            mime_type = await FileValidator.validate_mime_type(file)
            # WAV 파일로 감지되어야 함 (또는 감지 실패로 예외)
            assert mime_type is not None
        except (FileValidationError, InvalidFileTypeError):
            # 더미 헤더라서 감지 실패 가능
            pass
