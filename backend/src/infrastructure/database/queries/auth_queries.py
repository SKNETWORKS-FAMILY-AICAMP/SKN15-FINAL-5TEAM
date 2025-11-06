"""
Auth Queries - User 및 Auth 관련 SQL 쿼리

도메인: auth 스키마
테이블: users, password_reset_tokens
"""


class AuthQueries:
    """User 및 Auth 관련 SQL 쿼리 집합"""

    # ============================================================
    # User Queries
    # ============================================================

    SELECT_USER_BY_ID = """
        SELECT user_id, username, email, display_name,
               created_at, updated_at, is_active
        FROM auth.users
        WHERE user_id = %s
    """

    SELECT_USER_BY_USERNAME = """
        SELECT user_id, username, password_hash, email, display_name,
               created_at, updated_at, is_active
        FROM auth.users
        WHERE username = %s
    """

    SELECT_USER_BY_EMAIL = """
        SELECT user_id, username, email, display_name,
               created_at, updated_at, is_active
        FROM auth.users
        WHERE email = %s
    """

    INSERT_USER = """
        INSERT INTO auth.users (user_id, username, password_hash, email, display_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING user_id
    """

    UPDATE_PASSWORD = """
        UPDATE auth.users
        SET password_hash = %s, updated_at = NOW()
        WHERE user_id = %s
    """

    UPDATE_USER_PROFILE = """
        UPDATE auth.users
        SET display_name = %s, email = %s, updated_at = NOW()
        WHERE user_id = %s
    """

    # ============================================================
    # Password Reset Token Queries
    # ============================================================

    INSERT_PASSWORD_RESET_TOKEN = """
        INSERT INTO auth.password_reset_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id
    """

    SELECT_PASSWORD_RESET_TOKEN = """
        SELECT id, user_id, token, expires_at, used, created_at
        FROM auth.password_reset_tokens
        WHERE token = %s AND used = FALSE AND expires_at > NOW()
    """

    MARK_TOKEN_AS_USED = """
        UPDATE auth.password_reset_tokens
        SET used = TRUE
        WHERE token = %s
    """
