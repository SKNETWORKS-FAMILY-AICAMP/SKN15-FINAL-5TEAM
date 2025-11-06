"""
Conversation Queries - Session 및 Dialogue 관련 SQL 쿼리

도메인: conversation 스키마
테이블: sessions, dialogues
"""


class ConversationQueries:
    """Session 및 Dialogue 관련 SQL 쿼리 집합"""

    # ============================================================
    # Session Queries
    # ============================================================

    SELECT_SESSION_BY_ID = """
        SELECT session_id, user_id, scenario_id, session_state,
               is_active, started_at, ended_at, created_at, updated_at
        FROM conversation.sessions
        WHERE session_id = %s
    """

    SELECT_ACTIVE_SESSION_BY_USER = """
        SELECT session_id, user_id, scenario_id, session_state,
               is_active, started_at, ended_at, created_at, updated_at
        FROM conversation.sessions
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY started_at DESC
        LIMIT 1
    """

    SELECT_USER_SESSIONS = """
        SELECT session_id, user_id, scenario_id, session_state,
               is_active, started_at, ended_at, created_at, updated_at
        FROM conversation.sessions
        WHERE user_id = %s
        ORDER BY started_at DESC
        LIMIT %s
    """

    INSERT_SESSION = """
        INSERT INTO conversation.sessions
        (session_id, user_id, scenario_id, session_state, is_active, started_at)
        VALUES (%s, %s, %s, %s, TRUE, NOW())
        RETURNING session_id
    """

    UPDATE_SESSION_STATE = """
        UPDATE conversation.sessions
        SET session_state = %s, updated_at = NOW()
        WHERE session_id = %s
    """

    END_SESSION = """
        UPDATE conversation.sessions
        SET is_active = FALSE, ended_at = NOW(), updated_at = NOW()
        WHERE session_id = %s
    """

    # ============================================================
    # Dialogue Queries
    # ============================================================

    INSERT_DIALOGUE = """
        INSERT INTO conversation.dialogues
        (session_id, turn_number, speaker, text, metadata, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING dialogue_id
    """

    SELECT_SESSION_DIALOGUES = """
        SELECT dialogue_id, session_id, turn_number, speaker, text, metadata, created_at
        FROM conversation.dialogues
        WHERE session_id = %s
        ORDER BY turn_number DESC
        LIMIT %s
    """

    SELECT_RECENT_DIALOGUES = """
        SELECT dialogue_id, session_id, turn_number, speaker, text, metadata, created_at
        FROM conversation.dialogues
        WHERE session_id = %s
        ORDER BY turn_number DESC
        LIMIT %s
    """

    COUNT_SESSION_DIALOGUES = """
        SELECT COUNT(*)
        FROM conversation.dialogues
        WHERE session_id = %s
    """
