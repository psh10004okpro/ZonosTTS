"""
데이터베이스 마이그레이션 스크립트: 인덱스 추가
Phase 5: 데이터베이스 최적화

이 스크립트는 기존 데이터베이스에 성능 최적화를 위한 인덱스를 추가합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from loguru import logger
from config import DATABASE_URL


async def create_indexes():
    """
    인덱스 생성 (이미 존재하면 무시)
    """
    engine = create_async_engine(DATABASE_URL, echo=False)

    # 생성할 인덱스 목록
    indexes = [
        # AudioFile 테이블
        ("ix_audio_files_speaker_id", "audio_files", "speaker_id"),
        ("ix_audio_files_language", "audio_files", "language"),
        ("ix_audio_files_created_at", "audio_files", "created_at"),
        ("ix_audio_files_speaker_created", "audio_files", "speaker_id, created_at"),
        ("ix_audio_files_language_created", "audio_files", "language, created_at"),

        # Speaker 테이블
        ("ix_speakers_name", "speakers", "name"),
        ("ix_speakers_language", "speakers", "language"),
        ("ix_speakers_usage_count", "speakers", "usage_count"),
        ("ix_speakers_created_at", "speakers", "created_at"),
        ("ix_speakers_language_usage", "speakers", "language, usage_count"),

        # Job 테이블
        ("ix_jobs_job_id", "jobs", "job_id"),
        ("ix_jobs_job_type", "jobs", "job_type"),
        ("ix_jobs_status", "jobs", "status"),
        ("ix_jobs_created_at", "jobs", "created_at"),
        ("ix_jobs_completed_at", "jobs", "completed_at"),
        ("ix_jobs_result_audio_id", "jobs", "result_audio_id"),
        ("ix_jobs_result_speaker_id", "jobs", "result_speaker_id"),
        ("ix_jobs_error_type", "jobs", "error_type"),
        ("ix_jobs_status_created", "jobs", "status, created_at"),
        ("ix_jobs_type_status", "jobs", "job_type, status"),
        ("ix_jobs_status_completed", "jobs", "status, completed_at"),
    ]

    try:
        async with engine.begin() as conn:
            logger.info("인덱스 생성 시작...")

            for index_name, table_name, columns in indexes:
                try:
                    # SQLite는 CREATE INDEX IF NOT EXISTS 지원
                    await conn.execute(
                        text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})")
                    )
                    logger.info(f"✓ 인덱스 생성: {index_name} ON {table_name}({columns})")
                except Exception as e:
                    logger.warning(f"⚠ 인덱스 생성 실패 (이미 존재할 수 있음): {index_name} - {e}")

            logger.info("✓ 인덱스 생성 완료!")

    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")
        raise
    finally:
        await engine.dispose()


async def analyze_database():
    """
    데이터베이스 분석 및 통계 정보 출력
    """
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            logger.info("\n데이터베이스 통계:")

            # 테이블별 행 수
            tables = ["audio_files", "speakers", "jobs"]
            for table in tables:
                result = await conn.execute(
                    text(f"SELECT COUNT(*) as count FROM {table}")
                )
                count = result.scalar()
                logger.info(f"  - {table}: {count:,} rows")

            # 인덱스 목록
            logger.info("\n생성된 인덱스:")
            result = await conn.execute(
                text("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
            )
            for row in result:
                if row[0] and not row[0].startswith("sqlite_"):
                    logger.info(f"  - {row[1]}.{row[0]}")

    except Exception as e:
        logger.error(f"분석 실패: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """메인 실행 함수"""
    logger.info("="*60)
    logger.info("데이터베이스 마이그레이션: 인덱스 추가")
    logger.info("="*60)

    try:
        # 1. 인덱스 생성
        await create_indexes()

        # 2. 데이터베이스 분석
        await analyze_database()

        logger.info("\n✓ 마이그레이션 성공!")
        logger.info("\n주의: 데이터베이스를 재생성하려면 기존 .db 파일을 삭제하고 애플리케이션을 재시작하세요.")

    except Exception as e:
        logger.error(f"\n✗ 마이그레이션 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
