"""
데이터베이스 모델 정의
SQLAlchemy를 사용한 ORM 모델 및 Pydantic 스키마
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
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
    speaker_id = Column(Integer, ForeignKey("speakers.id"), nullable=True, index=True)
    language = Column(String, default="en-us", index=True)
    speaking_rate = Column(Float, default=1.0)
    pitch_shift = Column(Float, default=0.0)
    emotion = Column(String, default="neutral")
    duration = Column(Float)  # 재생 시간 (초)
    file_size = Column(Integer)  # 파일 크기 (바이트)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    speaker = relationship("Speaker", back_populates="audio_files")

    # Indexes
    __table_args__ = (
        Index('ix_audio_files_speaker_created', 'speaker_id', 'created_at'),
        Index('ix_audio_files_language_created', 'language', 'created_at'),
    )


class Speaker(Base):
    """화자 샘플 테이블"""
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    sample_path = Column(String, nullable=False)  # 원본 오디오 샘플 경로
    embedding_path = Column(String)  # 임베딩 파일 경로 (.pt 파일)
    language = Column(String, default="en-us", index=True)
    duration = Column(Float)  # 샘플 재생 시간
    usage_count = Column(Integer, default=0, index=True)  # 사용 횟수 (정렬용)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    audio_files = relationship("AudioFile", back_populates="speaker")

    # Indexes
    __table_args__ = (
        Index('ix_speakers_language_usage', 'language', 'usage_count'),
    )


class Job(Base):
    """비동기 작업 추적 테이블"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, nullable=False, index=True)  # Celery task ID
    job_type = Column(String, nullable=False, index=True)  # "tts", "embedding"
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100

    # 요청 파라미터 (JSON)
    request_params = Column(Text)  # JSON string

    # 결과
    result_audio_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True, index=True)
    result_speaker_id = Column(Integer, ForeignKey("speakers.id"), nullable=True, index=True)
    result_data = Column(Text, nullable=True)  # JSON string for additional data

    # 에러 정보
    error_message = Column(Text, nullable=True)
    error_type = Column(String, nullable=True, index=True)

    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True, index=True)

    # 관계
    result_audio = relationship("AudioFile", foreign_keys=[result_audio_id])
    result_speaker = relationship("Speaker", foreign_keys=[result_speaker_id])

    # Indexes (복합 인덱스)
    __table_args__ = (
        Index('ix_jobs_status_created', 'status', 'created_at'),
        Index('ix_jobs_type_status', 'job_type', 'status'),
        Index('ix_jobs_status_completed', 'status', 'completed_at'),
    )


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


class JobCreate(BaseModel):
    """작업 생성 요청"""
    job_type: str  # "tts", "embedding"
    request_params: dict


class JobResponse(BaseModel):
    """작업 상태 응답"""
    id: int
    job_id: str
    job_type: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    request_params: Optional[dict] = None
    result_data: Optional[dict] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_audio_id: Optional[int] = None
    result_speaker_id: Optional[int] = None

    class Config:
        from_attributes = True


class AsyncTTSRequest(BaseModel):
    """비동기 TTS 생성 요청"""
    text: str = Field(..., max_length=5000)
    speaker_id: Optional[int] = None
    language: str = "en-us"
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch_shift: float = Field(default=0.0, ge=-12.0, le=12.0)
    emotion: str = "neutral"
    priority: int = Field(default=5, ge=1, le=10, description="작업 우선순위 (1-10)")


class AsyncTTSResponse(BaseModel):
    """비동기 TTS 생성 응답"""
    job_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = None


# ==================== 데이터베이스 설정 ====================

class Database:
    """데이터베이스 연결 및 세션 관리 (최적화된 연결 풀링)"""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./zonos_tts.db"):
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            # 연결 풀 설정 (SQLite는 단일 writer이므로 적절히 제한)
            pool_size=20,  # 연결 풀 크기
            max_overflow=10,  # 풀 초과 시 추가 연결 수
            pool_pre_ping=True,  # 연결 유효성 검사
            pool_recycle=3600,  # 1시간마다 연결 재활용
            # 쿼리 실행 설정
            connect_args={
                "timeout": 30,  # SQLite 락 대기 시간 (초)
                "check_same_thread": False,
            }
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
