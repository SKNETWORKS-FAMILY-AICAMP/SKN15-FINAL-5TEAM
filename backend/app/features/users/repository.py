"""
Users Repository
사용자 데이터 액세스 계층
Layer 4: Repository
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_parent_logger
from app.features.auth.models import CreditTransaction

logger = get_parent_logger("UserRepository")


class UserRepository:
    """
    사용자 데이터 액세스
    Layer 4: Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 ID로 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 정보 또는 None
        """
        query = text("""
            SELECT
                user_id, username, display_name, email,
                is_active, is_verified, role,
                total_sessions, total_bubbles,
                last_login, created_at, updated_at
            FROM auth.users
            WHERE user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_user_by_id", "User not found", user_id=user_id)
            return None

        return {
            "user_id": str(row.user_id),
            "username": row.username,
            "display_name": row.display_name,
            "email": row.email,
            "is_active": row.is_active,
            "is_verified": row.is_verified,
            "role": row.role,
            "total_sessions": row.total_sessions or 0,
            "total_bubbles": row.total_bubbles or 0,
            "last_login": row.last_login.isoformat() if row.last_login else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> bool:
        """
        사용자 프로필 업데이트

        Args:
            user_id: 사용자 ID
            display_name: 표시 이름 (선택)
            email: 이메일 (선택)

        Returns:
            성공 여부
        """
        # 업데이트할 필드 구성
        updates = []
        params = {"user_id": user_id, "updated_at": datetime.utcnow()}

        if display_name is not None:
            updates.append("display_name = :display_name")
            params["display_name"] = display_name

        if email is not None:
            updates.append("email = :email")
            params["email"] = email

        if not updates:
            return True  # 업데이트할 것이 없음

        updates.append("updated_at = :updated_at")

        query = text(f"""
            UPDATE auth.users
            SET {', '.join(updates)}
            WHERE user_id = :user_id
        """)

        await self.db.execute(query, params)
        await self.db.commit()

        logger.info("update_user_profile", "Profile updated", user_id=user_id)
        return True

    async def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 통계 정보
        """
        query = text("""
            SELECT
                u.total_sessions,
                u.total_bubbles,
                uc.current_credits,
                COUNT(DISTINCT s.session_id) as active_sessions,
                MAX(s.created_at) as last_session_at
            FROM auth.users u
            LEFT JOIN user_credits uc ON u.user_id = uc.user_id
            LEFT JOIN sessions s ON u.user_id = s.user_id
            WHERE u.user_id = :user_id
            GROUP BY u.user_id, u.total_sessions, u.total_bubbles, uc.current_credits
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "total_sessions": row.total_sessions or 0,
            "total_bubbles": row.total_bubbles or 0,
            "current_credits": row.current_credits or 0,
            "active_sessions": row.active_sessions or 0,
            "last_session_at": row.last_session_at.isoformat() if row.last_session_at else None,
        }

    async def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 크레딧 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 정보
        """
        query = text("""
            SELECT
                COALESCE(bubble_count, 0) as bubble_count,
                COALESCE(total_purchased, 0) as total_purchased,
                COALESCE(total_consumed, 0) as total_consumed
            FROM auth.user_credits
            WHERE user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            # 크레딧 레코드가 없으면 기본값 반환
            return {
                "bubble_count": 0,
                "total_purchased": 0,
                "total_consumed": 0
            }

        return {
            "bubble_count": row.bubble_count,
            "total_purchased": row.total_purchased,
            "total_consumed": row.total_consumed,
        }

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> bool:
        """
        크레딧 소비

        Args:
            user_id: 사용자 ID
            amount: 소비할 양
            description: 사용 목적

        Returns:
            성공 여부
        """
        # 현재 크레딧 확인
        check_query = text("""
            SELECT bubble_count
            FROM auth.user_credits
            WHERE user_id = :user_id
        """)
        result = await self.db.execute(check_query, {"user_id": user_id})
        row = result.fetchone()

        if not row or row.bubble_count < amount:
            logger.warning(
                "consume_credits",
                "Insufficient credits",
                user_id=user_id,
                required=amount,
                available=row.bubble_count if row else 0
            )
            return False

        # 변동 전 잔액 저장
        balance_before = row.bubble_count

        # 크레딧 차감
        update_query = text("""
            UPDATE user_credits
            SET
                bubble_count = bubble_count - :amount,
                total_consumed = total_consumed + :amount,
                last_updated = :updated_at
            WHERE user_id = :user_id
        """)

        await self.db.execute(update_query, {
            "user_id": user_id,
            "amount": amount,
            "updated_at": datetime.utcnow()
        })

        # 변동 후 잔액
        balance_after = balance_before - amount

        # 크레딧 트랜잭션 로깅
        await self._log_credit_transaction(
            user_id=user_id,
            amount=-amount,  # 소비는 음수
            transaction_type="consume",
            balance_after=balance_after,
            description=description
        )

        await self.db.commit()

        logger.info(
            "consume_credits",
            "Credits consumed",
            user_id=user_id,
            amount=amount,
            description=description
        )
        return True

    async def add_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: str,
        description: Optional[str] = None
    ) -> bool:
        """
        크레딧 추가 (purchase, bonus, initial, refund)

        Args:
            user_id: 사용자 ID
            amount: 추가할 양
            transaction_type: 거래 유형 (purchase, bonus, initial, refund)
            description: 설명

        Returns:
            성공 여부
        """
        # 현재 크레딧 확인
        check_query = text("""
            SELECT bubble_count
            FROM auth.user_credits
            WHERE user_id = :user_id
        """)
        result = await self.db.execute(check_query, {"user_id": user_id})
        row = result.fetchone()

        # 잔액 계산
        balance_before = row.bubble_count if row else 0

        # 크레딧 추가
        if row:
            # 기존 레코드 업데이트
            update_query = text("""
                UPDATE user_credits
                SET
                    bubble_count = bubble_count + :amount,
                    total_purchased = total_purchased + :amount,
                    last_updated = :updated_at
                WHERE user_id = :user_id
            """)
            await self.db.execute(update_query, {
                "user_id": user_id,
                "amount": amount,
                "updated_at": datetime.utcnow()
            })
        else:
            # 새 레코드 생성
            insert_query = text("""
                INSERT INTO user_credits (user_id, bubble_count, total_purchased, total_consumed, last_updated)
                VALUES (:user_id, :amount, :amount, 0, :updated_at)
            """)
            await self.db.execute(insert_query, {
                "user_id": user_id,
                "amount": amount,
                "updated_at": datetime.utcnow()
            })

        # 변동 후 잔액
        balance_after = balance_before + amount

        # 크레딧 트랜잭션 로깅
        await self._log_credit_transaction(
            user_id=user_id,
            amount=amount,  # 추가는 양수
            transaction_type=transaction_type,
            balance_after=balance_after,
            description=description
        )

        await self.db.commit()

        logger.info(
            "add_credits",
            "Credits added",
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            description=description
        )
        return True

    async def _log_credit_transaction(
        self,
        user_id: str,
        amount: int,
        transaction_type: str,
        balance_after: int,
        description: Optional[str] = None
    ) -> CreditTransaction:
        """
        크레딧 트랜잭션 로깅 (내부 메서드)

        Args:
            user_id: 사용자 ID
            amount: 변동량 (양수: 획득, 음수: 소비)
            transaction_type: 거래 유형
            balance_after: 변동 후 잔액
            description: 설명

        Returns:
            CreditTransaction 객체
        """
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            balance_after=balance_after,
            description=description
        )

        self.db.add(transaction)
        # commit은 호출하는 쪽에서 처리
        return transaction

    async def get_credit_transactions(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        크레딧 트랜잭션 내역 조회

        Args:
            user_id: 사용자 ID
            transaction_type: 거래 유형 필터 (선택)
            limit: 조회 개수
            offset: 오프셋

        Returns:
            트랜잭션 목록
        """
        base_query = """
            SELECT
                transaction_id, user_id, amount, transaction_type,
                balance_after, description, created_at
            FROM credit_transactions
            WHERE user_id = :user_id
        """

        params = {"user_id": user_id, "limit": limit, "offset": offset}

        if transaction_type:
            base_query += " AND transaction_type = :transaction_type"
            params["transaction_type"] = transaction_type

        base_query += """
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """

        query = text(base_query)
        result = await self.db.execute(query, params)
        rows = result.fetchall()

        transactions = []
        for row in rows:
            transactions.append({
                "transaction_id": str(row.transaction_id),
                "user_id": str(row.user_id),
                "amount": row.amount,
                "transaction_type": row.transaction_type,
                "balance_after": row.balance_after,
                "description": row.description,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })

        return transactions

    async def get_credit_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        크레딧 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 통계 정보
        """
        query = text("""
            SELECT
                transaction_type,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MAX(created_at) as last_transaction_at
            FROM credit_transactions
            WHERE user_id = :user_id
            GROUP BY transaction_type
            ORDER BY transaction_type
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        rows = result.fetchall()

        statistics = {
            "by_type": [],
            "total_transactions": 0,
            "net_change": 0
        }

        for row in rows:
            type_stat = {
                "transaction_type": row.transaction_type,
                "count": row.count,
                "total_amount": row.total_amount,
                "avg_amount": float(row.avg_amount) if row.avg_amount else 0,
                "last_transaction_at": row.last_transaction_at.isoformat() if row.last_transaction_at else None
            }
            statistics["by_type"].append(type_stat)
            statistics["total_transactions"] += row.count
            statistics["net_change"] += row.total_amount

        return statistics

    async def get_progression_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 진행도 조회 (progression.user_progression + content.rank_definitions JOIN)

        Args:
            user_id: 사용자 ID

        Returns:
            진행도 정보
            {
                "user_id": str,
                "rank_code": str,
                "rank_name_ko": str,
                "rank_name_en": str,
                "rank_name_ja": str,
                "icon_emoji": str,
                "level": int,
                "experience_points": int,
                "total_messages": int,
                "total_sessions": int,
                "total_play_minutes": int,
                "scenarios_completed": int,
                "achievements_count": int,
                "min_xp": int,  # 현재 계급의 최소 XP
                "description_ko": str
            }
        """
        query = text("""
            SELECT
                up.user_id,
                up.rank_code,
                rd.rank_name_ko,
                rd.rank_name_en,
                rd.rank_name_ja,
                rd.icon_emoji,
                up.level,
                up.experience_points,
                up.total_messages,
                up.total_sessions,
                up.total_play_minutes,
                up.scenarios_completed,
                up.achievements_count,
                rd.min_xp,
                rd.description_ko,
                up.created_at,
                up.updated_at
            FROM progression.user_progression up
            LEFT JOIN content.rank_definitions rd ON up.rank_code = rd.rank_code
            WHERE up.user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_progression_by_user_id", "Progression not found", user_id=user_id)
            return None

        return {
            "user_id": str(row.user_id),
            "rank_code": row.rank_code,
            "rank_name_ko": row.rank_name_ko,
            "rank_name_en": row.rank_name_en,
            "rank_name_ja": row.rank_name_ja,
            "icon_emoji": row.icon_emoji,
            "level": row.level,
            "experience_points": row.experience_points,
            "total_messages": row.total_messages or 0,
            "total_sessions": row.total_sessions or 0,
            "total_play_minutes": row.total_play_minutes or 0,
            "scenarios_completed": row.scenarios_completed or 0,
            "achievements_count": row.achievements_count or 0,
            "min_xp": row.min_xp,
            "description_ko": row.description_ko,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None
        }

    async def get_settings_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 설정 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 설정 정보 또는 None
        """
        query = text("""
            SELECT
                user_id, sound_enabled, bgm_volume, sfx_volume,
                language, updated_at
            FROM auth.user_settings
            WHERE user_id = :user_id
        """)

        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_settings_by_user_id", "Settings not found", user_id=user_id)
            return None

        return {
            "user_id": str(row.user_id),
            "sound_enabled": row.sound_enabled,
            "bgm_volume": row.bgm_volume,
            "sfx_volume": row.sfx_volume,
            "language": row.language,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def upsert_user_settings(
        self,
        user_id: str,
        settings_data: Dict[str, Any]
    ) -> bool:
        """
        사용자 설정 생성 또는 업데이트 (UPSERT)

        Args:
            user_id: 사용자 ID
            settings_data: 설정 데이터

        Returns:
            성공 여부
        """
        # 업데이트할 필드 구성
        params = {"user_id": user_id, "updated_at": datetime.utcnow()}

        # settings_data에서 None이 아닌 필드만 추가
        set_fields = []
        insert_fields = ["user_id"]
        insert_values = [":user_id"]

        for key, value in settings_data.items():
            if value is not None:
                params[key] = value
                set_fields.append(f"{key} = :{key}")
                insert_fields.append(key)
                insert_values.append(f":{key}")

        # updated_at 추가
        set_fields.append("updated_at = :updated_at")
        insert_fields.append("updated_at")
        insert_values.append(":updated_at")

        # INSERT ... ON CONFLICT DO UPDATE 쿼리
        query = text(f"""
            INSERT INTO auth.user_settings ({', '.join(insert_fields)})
            VALUES ({', '.join(insert_values)})
            ON CONFLICT (user_id)
            DO UPDATE SET {', '.join(set_fields)}
        """)

        await self.db.execute(query, params)
        await self.db.commit()

        logger.info("upsert_user_settings", "Settings upserted", user_id=user_id)
        return True

    # ========================================
    # XP 관련 메서드 (progression에서 이동)
    # ========================================

    async def add_xp(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        XP 추가 + 트랜잭션 로그

        Args:
            user_id: 사용자 ID
            xp_amount: XP 양 (양수: 획득, 음수: 소비)
            xp_type: XP 타입 (message, scenario_complete, achievement)
            session_id: 세션 ID (선택)
            metadata: 추가 메타데이터

        Returns:
            XPTransaction dict
        """
        from app.features.users.models.xp_transaction import XPTransaction

        # 사용자 조회
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 레벨 계산 (현재)
        level_before = self._calculate_level(user.get("total_xp", 0))

        # XP 업데이트
        new_xp = user.get("total_xp", 0) + xp_amount

        # 레벨 계산 (업데이트 후)
        level_after = self._calculate_level(new_xp)
        did_level_up = level_after > level_before

        # 사용자 테이블 XP 업데이트
        update_query = text("""
            UPDATE auth.users
            SET total_xp = :new_xp, updated_at = :updated_at
            WHERE user_id = :user_id
        """)
        await self.db.execute(update_query, {
            "new_xp": new_xp,
            "updated_at": datetime.utcnow(),
            "user_id": user_id
        })

        # 트랜잭션 로그 생성
        import uuid
        transaction_id = str(uuid.uuid4())
        insert_query = text("""
            INSERT INTO xp_transactions (
                transaction_id, user_id, session_id,
                xp_amount, xp_type, xp_balance_after,
                level_before, level_after, did_level_up,
                extra_metadata, created_at
            ) VALUES (
                :transaction_id, :user_id, :session_id,
                :xp_amount, :xp_type, :xp_balance_after,
                :level_before, :level_after, :did_level_up,
                :extra_metadata, :created_at
            )
        """)

        await self.db.execute(insert_query, {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "session_id": session_id,
            "xp_amount": xp_amount,
            "xp_type": xp_type,
            "xp_balance_after": new_xp,
            "level_before": level_before,
            "level_after": level_after,
            "did_level_up": did_level_up,
            "extra_metadata": metadata or {},
            "created_at": datetime.utcnow()
        })

        await self.db.commit()

        return {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "xp_amount": xp_amount,
            "xp_balance_after": new_xp,
            "level_before": level_before,
            "level_after": level_after,
            "did_level_up": did_level_up
        }

    def _calculate_level(self, xp: int) -> int:
        """XP로부터 레벨 계산"""
        import math
        return math.floor(math.sqrt(xp / 100))

    async def get_xp_transactions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """XP 트랜잭션 조회"""
        query = text("""
            SELECT
                transaction_id, user_id, session_id,
                xp_amount, xp_type, xp_balance_after,
                level_before, level_after, did_level_up,
                extra_metadata, created_at
            FROM progression.xp_transactions
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = await self.db.execute(query, {"user_id": user_id, "limit": limit})
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]
