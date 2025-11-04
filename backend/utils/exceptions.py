"""
커스텀 예외 클래스
세분화된 에러 처리를 위한 예외 정의
"""

from typing import Optional


class ZonosTTSException(Exception):
    """Base exception for Zonos TTS system"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# ==================== 모델 관련 예외 ====================

class ModelException(ZonosTTSException):
    """모델 관련 예외 베이스"""
    pass


class ModelLoadError(ModelException):
    """모델 로드 실패"""
    pass


class ModelNotLoadedError(ModelException):
    """모델이 로드되지 않음"""
    pass


class ModelInferenceError(ModelException):
    """모델 추론 실패"""
    pass


class ModelOutOfMemoryError(ModelException):
    """GPU/CPU 메모리 부족"""
    pass


# ==================== 파일 관련 예외 ====================

class FileException(ZonosTTSException):
    """파일 관련 예외 베이스"""
    pass


class FileValidationError(FileException):
    """파일 검증 실패"""
    pass


class FileSizeTooLargeError(FileValidationError):
    """파일 크기 초과"""
    pass


class InvalidFileTypeError(FileValidationError):
    """잘못된 파일 타입"""
    pass


class AudioDurationError(FileValidationError):
    """오디오 길이 오류"""
    pass


class FileNotFoundError(FileException):
    """파일을 찾을 수 없음"""
    pass


class FileIOError(FileException):
    """파일 읽기/쓰기 실패"""
    pass


# ==================== 동시성 관련 예외 ====================

class ConcurrencyException(ZonosTTSException):
    """동시성 제어 관련 예외 베이스"""
    pass


class QueueFullError(ConcurrencyException):
    """대기 큐가 가득 참"""
    pass


class RequestTimeoutError(ConcurrencyException):
    """요청 타임아웃"""
    pass


class ResourceUnavailableError(ConcurrencyException):
    """리소스 사용 불가"""
    pass


# ==================== 데이터베이스 관련 예외 ====================

class DatabaseException(ZonosTTSException):
    """데이터베이스 관련 예외 베이스"""
    pass


class RecordNotFoundError(DatabaseException):
    """레코드를 찾을 수 없음"""
    pass


class DatabaseConnectionError(DatabaseException):
    """데이터베이스 연결 실패"""
    pass


# ==================== API 관련 예외 ====================

class APIException(ZonosTTSException):
    """API 관련 예외 베이스"""
    pass


class InvalidInputError(APIException):
    """잘못된 입력 파라미터"""
    pass


class RateLimitExceededError(APIException):
    """API 요청 한도 초과"""
    pass


class AuthenticationError(APIException):
    """인증 실패"""
    pass


# ==================== 오디오 처리 관련 예외 ====================

class AudioException(ZonosTTSException):
    """오디오 처리 관련 예외 베이스"""
    pass


class AudioProcessingError(AudioException):
    """오디오 처리 실패"""
    pass


class AudioFormatError(AudioException):
    """지원하지 않는 오디오 포맷"""
    pass


class SpeakerEmbeddingError(AudioException):
    """화자 임베딩 생성 실패"""
    pass


# ==================== 유틸리티 함수 ====================

def get_http_status_code(exception: Exception) -> int:
    """예외에 맞는 HTTP 상태 코드 반환"""

    status_map = {
        # 400 Bad Request
        FileValidationError: 400,
        InvalidFileTypeError: 400,
        AudioDurationError: 400,
        InvalidInputError: 400,
        AudioFormatError: 400,

        # 401 Unauthorized
        AuthenticationError: 401,

        # 404 Not Found
        FileNotFoundError: 404,
        RecordNotFoundError: 404,

        # 413 Payload Too Large
        FileSizeTooLargeError: 413,

        # 429 Too Many Requests
        RateLimitExceededError: 429,
        QueueFullError: 429,

        # 500 Internal Server Error
        ModelLoadError: 500,
        ModelNotLoadedError: 500,
        ModelInferenceError: 500,
        ModelOutOfMemoryError: 500,
        FileIOError: 500,
        DatabaseException: 500,
        AudioProcessingError: 500,
        SpeakerEmbeddingError: 500,

        # 503 Service Unavailable
        RequestTimeoutError: 503,
        ResourceUnavailableError: 503,
        DatabaseConnectionError: 503,
    }

    # 예외 클래스 체크 (상속 고려)
    for exc_class, status_code in status_map.items():
        if isinstance(exception, exc_class):
            return status_code

    # 기본값
    return 500


def format_error_response(exception: Exception) -> dict:
    """예외를 API 응답 형식으로 변환"""

    if isinstance(exception, ZonosTTSException):
        return {
            "error": exception.error_code,
            "message": exception.message,
            "details": exception.details
        }
    else:
        return {
            "error": "InternalError",
            "message": str(exception),
            "details": {}
        }
