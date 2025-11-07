"""
PostgreSQL Character Repository Implementation

ICharacterRepository 인터페이스 구현
"""
from typing import Optional, Dict, Any, List
from psycopg2.extras import RealDictCursor

from src.core.interfaces.repositories.character_repository import ICharacterRepository
from src.infrastructure.database.connection import DatabaseConnection


class PostgresCharacterRepository(ICharacterRepository):
    """PostgreSQL 기반 캐릭터 리포지토리"""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Args:
            db_connection: 데이터베이스 연결 관리자
        """
        self._db = db_connection

    def get_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        캐릭터 ID로 캐릭터 정보 조회

        Args:
            character_id: 캐릭터 ID

        Returns:
            캐릭터 정보 딕셔너리 또는 None
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Main character data
                    cur.execute("""
                        SELECT character_id, name, description, personality, breathing_style,
                               default_affinity, appearance_hair, appearance_eyes,
                               appearance_distinctive, appearance_impression
                        FROM content.characters
                        WHERE character_id = %s
                    """, (character_id,))

                    char = cur.fetchone()
                    if not char:
                        return None

                    result = dict(char)
                    result['id'] = character_id

                    # Appearance dict
                    result['appearance'] = {
                        'hair': char['appearance_hair'],
                        'eyes': char['appearance_eyes'],
                        'distinctive': char['appearance_distinctive'],
                        'impression': char['appearance_impression']
                    }

                    # Core values
                    cur.execute("""
                        SELECT value_text
                        FROM content.character_core_values
                        WHERE character_id = %s
                        ORDER BY display_order
                    """, (character_id,))
                    result['core_values'] = [row['value_text'] for row in cur.fetchall()]

                    # Emotional triggers
                    cur.execute("""
                        SELECT emotion_type, trigger_text
                        FROM content.character_emotional_triggers
                        WHERE character_id = %s
                    """, (character_id,))
                    result['emotional_triggers'] = {
                        row['emotion_type']: row['trigger_text']
                        for row in cur.fetchall()
                    }

                    # Speaking patterns
                    cur.execute("""
                        SELECT pattern_type, pattern_text, example
                        FROM content.character_speaking_patterns
                        WHERE character_id = %s
                    """, (character_id,))
                    result['speaking_patterns'] = [dict(row) for row in cur.fetchall()]

                    return result

        except Exception as e:
            print(f"Error getting character {character_id}: {e}")
            return None

    def get_by_name(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        캐릭터 이름으로 캐릭터 정보 조회

        Args:
            character_name: 캐릭터 이름

        Returns:
            캐릭터 정보 딕셔너리 또는 None
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT character_id
                        FROM content.characters
                        WHERE name = %s
                        LIMIT 1
                    """, (character_name,))

                    row = cur.fetchone()
                    if not row:
                        return None

                    return self.get_by_id(row['character_id'])

        except Exception as e:
            print(f"Error getting character by name {character_name}: {e}")
            return None

    def get_all(self) -> List[Dict[str, Any]]:
        """
        모든 캐릭터 정보 조회

        Returns:
            캐릭터 정보 리스트
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT character_id, name, description, default_affinity
                        FROM content.characters
                        ORDER BY name
                    """)

                    characters = []
                    for row in cur.fetchall():
                        char_data = self.get_by_id(row['character_id'])
                        if char_data:
                            characters.append(char_data)

                    return characters

        except Exception as e:
            print(f"Error getting all characters: {e}")
            return []

    def get_by_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        시나리오별 캐릭터 목록 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            캐릭터 정보 리스트
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT c.character_id, c.name, c.description
                        FROM content.characters c
                        INNER JOIN content.scenario_characters sc
                            ON c.character_id = sc.character_id
                        WHERE sc.scenario_id = %s
                        ORDER BY c.name
                    """, (scenario_id,))

                    characters = []
                    for row in cur.fetchall():
                        char_data = self.get_by_id(row['character_id'])
                        if char_data:
                            characters.append(char_data)

                    return characters

        except Exception as e:
            print(f"Error getting characters for scenario {scenario_id}: {e}")
            return []
