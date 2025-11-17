"""
ScenarioBuffer 모델 - 시나리오 진행 정보 임시 저장
"""
from sqlalchemy import Column, String, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app.core.db.base import Base


class ScenarioBuffer(Base):
    """시나리오 버퍼 (Scenario Buffer)

    목적: 시나리오 진행 정보 임시 저장
    - 시나리오 흐름 연결용 임시 저장소
    - LTM처럼 장기기억을 저장하지 않음
    - 시나리오 완료 시 삭제

    Schema: knowledge.scenario_buffers

    progress_data 구조:
    {
        "current_stage": "mugen_train_battle",
        "choices_made": ["help_tanjiro", "fight_demon"],
        "flags": {
            "met_rengoku": true,
            "train_departed": true
        },
        "npc_states": {
            "tanjiro": {"affinity": 75, "trust": 80},
            "rengoku": {"affinity": 60, "respect": 85}
        }
    }
    """
    __tablename__ = "scenario_buffers"
    __table_args__ = {"schema": "knowledge"}

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # Scenario Identification
    scenario_id = Column(String(100), nullable=False, comment="시나리오 ID")

    # Buffer 내용
    buffer_summary = Column(Text, nullable=True, comment="시나리오 연속성 요약")
    progress_data = Column(
        JSONB,
        nullable=True,
        default={},
        comment="진행 상황 (선택지, 진행 상황, 플래그)"
    )

    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ScenarioBuffer(id={self.id}, user_id={self.user_id}, scenario_id={self.scenario_id})>"
