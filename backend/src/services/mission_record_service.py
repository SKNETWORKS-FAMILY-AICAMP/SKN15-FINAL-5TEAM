"""
============================================================
📊 Mission Record Service — 미션 기록 저장
============================================================
미션 진행 기록과 게임 이벤트를 DB에 저장합니다.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from src.utils.logger import log


class MissionRecordService:
    """
    미션 기록 서비스

    책임:
    - 미션 기록 DB 저장
    - 게임 이벤트 저장 (캐릭터 합류 등)
    """

    CHARACTER_NAMES_KR = {
        "inosuke": "이노스케",
        "zenitsu": "젠이츠",
        "tanjiro": "탄지로",
        "nezuko": "네즈코",
    }

    def save_recruit_result(
        self,
        state: Dict[str, Any],
        character: str,
        success: bool,
        attempts: int,
    ) -> None:
        """
        설득 결과를 DB에 저장

        Args:
            state: 전체 state 객체
            character: 타겟 캐릭터 ID
            success: 설득 성공 여부
            attempts: 시도 횟수
        """
        try:
            from src.database.db_manager import DatabaseManager

            db_manager = DatabaseManager(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                dbname=os.getenv('DB_NAME', 'kimedb'),
                user=os.getenv('DB_USER', 'kime'),
                password=os.getenv('DB_PASSWORD', 'dev123'),
                min_conn=1,
                max_conn=2
            )

            session_id = state.get("session_id")
            turn_count = state.get("turn_count", 0)

            if not session_id:
                log("mission_record", "⚠️ No session_id, skipping DB save")
                return

            # 미션 기록 저장
            db_manager.save_mission_record(
                session_id=session_id,
                mission_type="recruit",
                target_character=character,
                attempt_count=attempts,
                success=success
            )
            log("mission_record", f"🎮 Mission record saved: {character} ({'SUCCESS' if success else 'FAIL'}, attempt {attempts})")

            # 🎉 게임 이벤트 저장: 캐릭터 합류 성공
            if success:
                db_manager.save_game_event(
                    session_id=session_id,
                    turn_number=turn_count,
                    event_type="character_recruited",
                    event_data={
                        "character": character,
                        "character_display": self.CHARACTER_NAMES_KR.get(character, character),
                        "mission_type": "recruit",
                        "attempts": attempts
                    }
                )
                log("mission_record", f"🎉 Game event saved: character_recruited ({character})")

        except Exception as e:
            log("mission_record", f"⚠️ Failed to save mission/game records: {e}", level=40)


__all__ = ["MissionRecordService"]
