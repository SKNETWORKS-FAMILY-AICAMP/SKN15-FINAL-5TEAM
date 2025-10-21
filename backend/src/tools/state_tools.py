# 6. State Tools 구현 (상태 관리 및 DB 연동)

"""
State Tools - 게임 상태 관리 및 데이터베이스 연동
- 상태 업데이트 및 검증
- 친밀도 관리
- 히든엔딩 조건 체크
- 데이터베이스 저장/로드
"""

from typing import Dict, List, Optional, Tuple
import json
import sqlite3
from datetime import datetime
from src.core.graph_state import AgentState, StateToolRequest, StateToolResponse

class StateTools:
    def __init__(self, db_path: str = "data/game_state.db"):
        """State Tools 초기화"""
        self.db_path = db_path
        self._initialize_database()
        
        # 히든엔딩 조건 규칙
        self.hidden_ending_rules = {
            "required_order": ["inosuke_first"],  # 이노스케 먼저 대화
            "required_flags": ["inosuke_recruited", "zenitsu_recruited"],
            "min_total_turns_remaining": 1,
            "min_character_turns": {"inosuke": 1, "zenitsu": 1},
            "min_affinity": {"inosuke": 350, "zenitsu": 450}
        }
    
    def _initialize_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 게임 세션 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_sessions (
                    session_id TEXT PRIMARY KEY,
                    scenario_id TEXT,
                    scene_id TEXT,
                    turn INTEGER,
                    total_remaining_turns INTEGER,
                    flags TEXT,  -- JSON string
                    character_remaining_turns TEXT,  -- JSON string
                    user_choice TEXT,
                    last_action TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 캐릭터 친밀도 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_affinity (
                    session_id TEXT,
                    character_id TEXT,
                    affinity INTEGER,
                    affinity_level TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, character_id)
                )
            ''')
            
            # 메시지 히스토리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message_type TEXT,
                    speaker TEXT,
                    content TEXT,
                    metadata TEXT,  -- JSON string
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 게임 이벤트 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT,
                    event_data TEXT,  -- JSON string
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def process_request(self, state: AgentState) -> AgentState:
        """State Tools 요청 처리"""
        if not state.state_tool_request:
            return state
        
        request = state.state_tool_request
        action = request.action
        
        try:
            if action == "get_state":
                response = self._get_state(request, state)
            elif action == "update_state":
                response = self._update_state(request, state)
            elif action == "save_checkpoint":
                response = self._save_checkpoint(request, state)
            else:
                response = StateToolResponse(
                    status="error",
                    validation_errors=[f"지원하지 않는 액션: {action}"]
                )
        except Exception as e:
            response = StateToolResponse(
                status="error",
                validation_errors=[f"State Tools 처리 오류: {str(e)}"]
            )
        
        state.state_tool_response = response
        
        # 성공적으로 처리된 경우 상태 반영
        if response.status == "success" and response.updated_state:
            self._apply_state_updates(state, response.updated_state)
        
        return state
    
    def _get_state(self, request: StateToolRequest, state: AgentState) -> StateToolResponse:
        """저장된 상태 조회"""
        session_id = state.meta.session_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 게임 상태 조회
            cursor.execute('''
                SELECT scenario_id, scene_id, turn, total_remaining_turns, 
                       flags, character_remaining_turns, user_choice, last_action
                FROM game_sessions 
                WHERE session_id = ?
            ''', (session_id,))
            
            game_row = cursor.fetchone()
            if not game_row:
                return StateToolResponse(
                    status="error",
                    validation_errors=["세션을 찾을 수 없습니다"]
                )
            
            # 친밀도 정보 조회
            cursor.execute('''
                SELECT character_id, affinity, affinity_level
                FROM character_affinity
                WHERE session_id = ?
            ''', (session_id,))
            
            affinity_rows = cursor.fetchall()
            
            # 상태 구성
            loaded_state = {
                "scenario_id": game_row[0],
                "scene_id": game_row[1],
                "turn": game_row[2],
                "total_remaining_turns": game_row[3],
                "flags": json.loads(game_row[4]) if game_row[4] else [],
                "character_remaining_turns": json.loads(game_row[5]) if game_row[5] else {},
                "user_choice": game_row[6],
                "last_action": game_row[7],
                "affinity": {row[0]: row[1] for row in affinity_rows},
                "affinity_levels": {row[0]: row[2] for row in affinity_rows}
            }
            
            return StateToolResponse(
                status="success",
                updated_state=loaded_state
            )
    
    def _update_state(self, request: StateToolRequest, state: AgentState) -> StateToolResponse:
        """상태 업데이트"""
        session_id = state.meta.session_id
        updates = request.updates
        character_updates = request.character_updates
        
        validation_errors = []
        
        # 상태 검증
        validation_errors.extend(self._validate_state_updates(state, updates))
        validation_errors.extend(self._validate_character_updates(state, character_updates))
        
        if validation_errors:
            return StateToolResponse(
                status="error",
                validation_errors=validation_errors
            )
        
        # 데이터베이스 업데이트
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 게임 상태 업데이트
            if updates:
                self._update_game_state_db(cursor, session_id, state, updates)
            
            # 친밀도 업데이트
            if character_updates:
                self._update_character_affinity_db(cursor, session_id, character_updates)
            
            conn.commit()
        
        # 히든엔딩 조건 체크
        hidden_ending_triggered, ending_type = self._check_ending_conditions(state)
        
        # 업데이트된 상태 구성
        updated_state = self._build_updated_state(state, updates, character_updates)
        
        return StateToolResponse(
            status="success",
            updated_state=updated_state,
            validation_errors=[],
            hidden_ending_triggered=hidden_ending_triggered,
            ending_type=ending_type
        )
    
    def _save_checkpoint(self, request: StateToolRequest, state: AgentState) -> StateToolResponse:
        """체크포인트 저장"""
        session_id = state.meta.session_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 현재 상태 전체 저장
            cursor.execute('''
                INSERT OR REPLACE INTO game_sessions 
                (session_id, scenario_id, scene_id, turn, total_remaining_turns,
                 flags, character_remaining_turns, user_choice, last_action, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                state.game.scenario_id,
                state.game.scene_id,
                state.game.turn,
                state.game.total_remaining_turns,
                json.dumps(state.game.flags),
                json.dumps(state.game.character_remaining_turns),
                state.game.user_choice,
                state.game.last_action,
                datetime.now().isoformat()
            ))
            
            # 친밀도 저장
            for character_id, affinity in state.characters.affinity.items():
                affinity_level = state.characters.affinity_levels.get(character_id, "low")
                cursor.execute('''
                    INSERT OR REPLACE INTO character_affinity
                    (session_id, character_id, affinity, affinity_level, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, character_id, affinity, affinity_level, datetime.now().isoformat()))
            
            # 메시지 히스토리 저장 (최근 5개)
            recent_messages = state.message_history.messages[-5:]
            for msg in recent_messages:
                cursor.execute('''
                    INSERT INTO message_history
                    (session_id, message_type, speaker, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    msg["type"],
                    msg["speaker"],
                    msg["content"],
                    json.dumps(msg.get("metadata", {})),
                    msg["timestamp"]
                ))
            
            # 게임 이벤트 로그
            event_data = {
                "checkpoint_saved": True,
                "scene": state.game.scene_id,
                "turn": state.game.turn,
                "flags": state.game.flags
            }
            
            cursor.execute('''
                INSERT INTO game_events
                (session_id, event_type, event_data)
                VALUES (?, ?, ?)
            ''', (session_id, "checkpoint_saved", json.dumps(event_data)))
            
            conn.commit()
        
        return StateToolResponse(
            status="success",
            updated_state={"checkpoint_saved": True}
        )
    
    def _validate_state_updates(self, state: AgentState, updates: Dict) -> List[str]:
        """상태 업데이트 검증"""
        errors = []
        
        # 턴 검증
        if "turn" in updates:
            new_turn = updates["turn"]
            if not isinstance(new_turn, int) or new_turn < 0:
                errors.append("턴은 0 이상의 정수여야 합니다")
            elif new_turn > state.game.max_turns:
                errors.append(f"턴이 최대값({state.game.max_turns})을 초과했습니다")
        
        # 전체 남은 턴 검증
        if "total_remaining_turns" in updates:
            remaining = updates["total_remaining_turns"]
            if not isinstance(remaining, int) or remaining < 0:
                errors.append("남은 턴은 0 이상의 정수여야 합니다")
        
        return errors
    
    def _validate_character_updates(self, state: AgentState, character_updates: Dict) -> List[str]:
        """캐릭터 업데이트 검증"""
        errors = []
        
        for character_id, change in character_updates.items():
            current_affinity = state.characters.affinity.get(character_id, 0)
            new_affinity = current_affinity + change
            
            if new_affinity < 0 or new_affinity > 1000:
                errors.append(f"{character_id}의 친밀도가 범위(0-1000)를 벗어남: {new_affinity}")
        
        return errors
    
    def _update_game_state_db(self, cursor, session_id: str, state: AgentState, updates: Dict):
        """데이터베이스에 게임 상태 업데이트"""
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ["turn", "total_remaining_turns", "user_choice", "last_action"]:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if set_clauses:
            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(session_id)
            
            query = f"UPDATE game_sessions SET {', '.join(set_clauses)} WHERE session_id = ?"
            cursor.execute(query, values)
    
    def _update_character_affinity_db(self, cursor, session_id: str, character_updates: Dict):
        """데이터베이스에 캐릭터 친밀도 업데이트"""
        for character_id, change in character_updates.items():
            # 현재 친밀도 조회
            cursor.execute('''
                SELECT affinity FROM character_affinity 
                WHERE session_id = ? AND character_id = ?
            ''', (session_id, character_id))
            
            row = cursor.fetchone()
            current_affinity = row[0] if row else 0
            new_affinity = max(0, min(1000, current_affinity + change))
            
            # 친밀도 레벨 계산
            if new_affinity < 300:
                affinity_level = "low"
            elif new_affinity < 700:
                affinity_level = "mid" 
            else:
                affinity_level = "high"
            
            # 업데이트
            cursor.execute('''
                INSERT OR REPLACE INTO character_affinity
                (session_id, character_id, affinity, affinity_level, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, character_id, new_affinity, affinity_level, datetime.now().isoformat()))
    
    def _check_ending_conditions(self, state: AgentState) -> Tuple[bool, Optional[str]]:
        """엔딩 조건 체크"""
        rules = self.hidden_ending_rules

        # 히든엔딩 조건을 개별적으로 확인 (unhashable 오류 방지)
        # 1. 순서 체크 (이노스케 먼저)
        condition1 = all(flag in state.game.flags for flag in rules["required_order"])

        # 2. 필요한 플래그들 체크
        condition2 = all(flag in state.game.flags for flag in rules["required_flags"])

        # 3. 턴 제한 체크
        condition3 = state.game.total_remaining_turns >= rules["min_total_turns_remaining"]

        # 4. 캐릭터별 턴 체크
        condition4 = True
        for char, min_turns in rules["min_character_turns"].items():
            if state.game.character_remaining_turns.get(char, 0) < min_turns:
                condition4 = False
                break

        # 5. 친밀도 체크
        condition5 = True
        for char, min_affinity in rules["min_affinity"].items():
            if state.characters.affinity.get(char, 0) < min_affinity:
                condition5 = False
                break

        if all([condition1, condition2, condition3, condition4, condition5]):
            return True, "hidden_ending"

        # 실패 조건 체크
        if state.game.total_remaining_turns <= 0:
            return True, "original_ending"

        # 캐릭터별 턴이 모두 0인지 확인
        all_turns_zero = True
        for turns in state.game.character_remaining_turns.values():
            if turns > 0:
                all_turns_zero = False
                break

        if all_turns_zero:
            return True, "original_ending"

        return False, None
    
    def _build_updated_state(self, state: AgentState, updates: Dict, character_updates: Dict) -> Dict:
        """업데이트된 상태 구성"""
        updated = {}
        
        # 게임 상태 업데이트
        for key, value in updates.items():
            updated[key] = value
        
        # 친밀도 업데이트
        if character_updates:
            updated["affinity"] = state.characters.affinity.copy()
            updated["affinity_levels"] = state.characters.affinity_levels.copy()
            
            for character_id, change in character_updates.items():
                current = updated["affinity"].get(character_id, 0)
                new_affinity = max(0, min(1000, current + change))
                updated["affinity"][character_id] = new_affinity
                
                # 레벨 업데이트
                if new_affinity < 300:
                    updated["affinity_levels"][character_id] = "low"
                elif new_affinity < 700:
                    updated["affinity_levels"][character_id] = "mid"
                else:
                    updated["affinity_levels"][character_id] = "high"
        
        return updated
    
    def _apply_state_updates(self, state: AgentState, updated_state: Dict):
        """상태 업데이트 적용"""
        # 게임 상태 적용
        for key, value in updated_state.items():
            if hasattr(state.game, key):
                setattr(state.game, key, value)
        
        # 친밀도 적용
        if "affinity" in updated_state:
            state.characters.affinity.update(updated_state["affinity"])
        if "affinity_levels" in updated_state:
            state.characters.affinity_levels.update(updated_state["affinity_levels"])

def run_state_tools(state: AgentState) -> AgentState:
    """State Tools 실행 함수"""
    tools = StateTools()
    return tools.process_request(state)

# 테스트용 함수
def test_state_tools():
    from src.core.graph_state import create_enhanced_initial_state, StateToolRequest
    
    # 테스트: 상태 업데이트
    state = create_enhanced_initial_state("test_state", scene_id="scene5_recruit_mission")
    state.state_tool_request = StateToolRequest(
        action="update_state",
        updates={
            "turn": 3,
            "total_remaining_turns": 7,
            "last_action": "user_persuaded_inosuke"
        },
        character_updates={
            "inosuke": 30,
            "tanjiro": 10
        }
    )
    
    result_state = run_state_tools(state)
    
    print("=== State Tools 테스트 결과 ===")
    print(f"상태: {result_state.state_tool_response.status}")
    print(f"검증 오류: {result_state.state_tool_response.validation_errors}")
    print(f"히든엔딩 트리거: {result_state.state_tool_response.hidden_ending_triggered}")
    print(f"엔딩 타입: {result_state.state_tool_response.ending_type}")
    print(f"업데이트된 턴: {result_state.game.turn}")
    print(f"업데이트된 친밀도: {result_state.characters.affinity}")

if __name__ == "__main__":
    test_state_tools()