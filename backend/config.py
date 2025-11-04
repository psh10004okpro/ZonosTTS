"""
애플리케이션 설정 및 상수
"""

import os
from typing import Set

# ==================== 서버 설정 ====================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEVICE = os.getenv("DEVICE", "cuda" if os.path.exists("/dev/nvidia0") else "cpu")

# ==================== 모델 설정 ====================
ZONOS_MODEL = os.getenv("ZONOS_MODEL", "Zyphra/Zonos-v0.1-transformer")
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", None)

# ==================== 데이터베이스 설정 ====================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./zonos_tts.db")

# ==================== 파일 업로드 보안 설정 ====================

# 파일 크기 제한 (바이트)
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TEXT_LENGTH = 5000  # 최대 텍스트 길이

# 허용된 오디오 MIME 타입
ALLOWED_AUDIO_MIME_TYPES: Set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "audio/x-flac",
    "audio/ogg",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
}

# 허용된 파일 확장자
ALLOWED_AUDIO_EXTENSIONS: Set[str] = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
}

# 화자 샘플 오디오 길이 제한 (초)
MIN_SPEAKER_DURATION = 5.0
MAX_SPEAKER_DURATION = 30.0

# ==================== 디렉토리 설정 ====================
UPLOAD_DIR = "uploads"
SPEAKER_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "speakers")
GENERATED_AUDIO_DIR = os.path.join(UPLOAD_DIR, "generated")
EMBEDDING_DIR = os.path.join(UPLOAD_DIR, "embeddings")

# ==================== TTS 설정 ====================
DEFAULT_LANGUAGE = "en-us"
SUPPORTED_LANGUAGES = ["en-us", "ja", "zh", "fr", "de"]
SUPPORTED_EMOTIONS = ["neutral", "happy", "sad", "angry", "fear"]

# 말하기 속도 범위
MIN_SPEAKING_RATE = 0.5
MAX_SPEAKING_RATE = 2.0

# 피치 조절 범위 (반음)
MIN_PITCH_SHIFT = -12.0
MAX_PITCH_SHIFT = 12.0

# ==================== 스트리밍 설정 ====================
STREAMING_CHUNK_SIZE = 100  # 문자 수
STREAMING_SAMPLE_RATE = 44100

# ==================== 동시성 제어 설정 ====================
# GPU 메모리 부족 방지를 위한 동시 실행 제한
MAX_CONCURRENT_TTS = int(os.getenv("MAX_CONCURRENT_TTS", 2))  # 동시 TTS 생성 수
MAX_CONCURRENT_EMBEDDING = int(os.getenv("MAX_CONCURRENT_EMBEDDING", 1))  # 동시 임베딩 생성 수
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", 10))  # 최대 대기 큐 크기
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 300.0))  # 요청 타임아웃 (초)

# ==================== 보안 설정 ====================
# 파일명 생성 시 사용할 안전한 문자
SAFE_FILENAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"

# API 속도 제한 (선택사항)
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_PER_HOUR = 1000

# ==================== 로깅 설정 ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
