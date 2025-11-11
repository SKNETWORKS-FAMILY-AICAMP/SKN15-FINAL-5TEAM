"""
LoggingRepository - 시스템 로그 저장/조회
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import SystemLog


class LoggingRepository:
    """시스템 로그 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        log_level: str,
        message: str,
        logger_name: str,
        module: Optional[str] = None,
        function: Optional[str] = None,
        line_number: Optional[int] = None,
        extra_data: Optional[dict] = None
    ) -> SystemLog:
        """로그 생성"""
        log = SystemLog(
            log_level=log_level,
            message=message,
            logger_name=logger_name,
            module=module,
            function=function,
            line_number=line_number,
            extra_data=extra_data or {}
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_logs(
        self,
        log_level: Optional[str] = None,
        limit: int = 100
    ) -> List[SystemLog]:
        """로그 조회"""
        query = select(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit)

        if log_level:
            query = query.where(SystemLog.log_level == log_level)

        result = await self.db.execute(query)
        return result.scalars().all()
