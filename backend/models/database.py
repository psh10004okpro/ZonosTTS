"""
데이터베이스 모델 정의
SQLAlchemy를 사용한 ORM 모델 및 Pydantic 스키마
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field

# SQLAlchemy Base
Base = declarative_base()

# ==================== SQLAlchemy 모델 ====================

class AudioFile(Base):
    """생성된 음성 파일 테이블"""
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    speaker_id = Column(Integer, ForeignKey("speakers.id"), nullable=True)
    language = Column(String, default="en-us")
    speaking_rate = Column(Float, default=1.0)
    pitch_shift = Column(Float, default=0.0)
    emotion = Column(String, default="neutral")
    duration = Column(Float)  # 재생 시간 (초)
    file_size = Column(Integer)  # 파일 크기 (바이트)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    speaker = relationship("Speaker", back_populates="audio_files")


class Speaker(Base):
    """화자 샘플 테이블"""
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    sample_path = Column(String, nullable=False)  # 원본 오디오 샘플 경로
    embedding_path = Column(String)  # 임베딩 파일 경로 (.pt 파일)
    language = Column(String, default="en-us")
    duration = Column(Float)  # 샘플 재생 시간
    usage_count = Column(Integer, default=0)  # 사용 횟수
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    audio_files = relationship("AudioFile", back_populates="speaker")


# ==================== Pydantic 스키마 ====================

class SpeakerBase(BaseModel):
    """화자 기본 스키마"""
    name: str
    language: Optional[str] = "en-us"


class SpeakerCreate(SpeakerBase):
    """화자 생성 요청"""
    pass


class SpeakerResponse(SpeakerBase):
    """화자 응답"""
    id: int
    sample_path: str
    duration: Optional[float] = None
    usage_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AudioFileBase(BaseModel):
    """오디오 파일 기본 스키마"""
    text: str = Field(..., max_length=5000, description="생성할 텍스트 (최대 5000자)")
    speaker_id: Optional[int] = None
    language: str = Field(default="en-us", description="언어 (en-us, ja, zh, fr, de)")
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="말하기 속도")
    pitch_shift: float = Field(default=0.0, ge=-12.0, le=12.0, description="피치 조절 (반음)")
    emotion: str = Field(default="neutral", description="감정 (neutral, happy, sad, angry, fear)")


class AudioFileCreate(AudioFileBase):
    """오디오 파일 생성 요청"""
    pass


class AudioFileResponse(AudioFileBase):
    """오디오 파일 응답"""
    id: int
    filename: str
    duration: Optional[float] = None
    file_size: Optional[int] = None
    created_at: datetime
    speaker: Optional[SpeakerResponse] = None

    class Config:
        from_attributes = True


class TTSStreamRequest(BaseModel):
    """실시간 스트리밍 TTS 요청"""
    text: str = Field(..., max_length=5000)
    speaker_id: Optional[int] = None
    language: str = "en-us"
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch_shift: float = Field(default=0.0, ge=-12.0, le=12.0)
    emotion: str = "neutral"


class TTSGenerateRequest(BaseModel):
    """음성 파일 생성 요청"""
    text: str = Field(..., max_length=5000)
    speaker_id: Optional[int] = None
    language: str = "en-us"
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch_shift: float = Field(default=0.0, ge=-12.0, le=12.0)
    emotion: str = "neutral"
    save_to_db: bool = Field(default=True, description="DB에 저장 여부")


class AudioListResponse(BaseModel):
    """오디오 파일 목록 응답"""
    total: int
    page: int
    page_size: int
    items: list[AudioFileResponse]


class DashboardStats(BaseModel):
    """대시보드 통계"""
    total_audio_files: int
    total_speakers: int
    total_duration_seconds: float
    total_storage_mb: float


# ==================== 데이터베이스 설정 ====================

class Database:
    """데이터베이스 연결 및 세션 관리"""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./zonos_tts.db"):
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """테이블 생성"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """세션 반환"""
        async with self.async_session() as session:
            yield session

    async def close(self):
        """연결 종료"""
        await self.engine.dispose()


# 전역 데이터베이스 인스턴스
db_instance = Database()


async def get_db() -> AsyncSession:
    """FastAPI 의존성 주입용 데이터베이스 세션"""
    async with db_instance.async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
