-- ============================================================
-- KIME Chat Database Schema - User Credits (Bubble System)
-- Version: 1.0
-- Description: 사용자 크레딧(버블) 시스템 구현
-- ============================================================

-- ============================================================
-- StateDB Schema: User Credits 테이블 추가
-- ============================================================

-- ------------------------------------------------------------
-- 1. user_credits: 사용자 크레딧(버블) 정보
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.user_credits (
    user_id UUID PRIMARY KEY REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    bubble_count INTEGER NOT NULL DEFAULT 200,
    total_purchased INTEGER NOT NULL DEFAULT 200,
    total_consumed INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT positive_bubble_count CHECK (bubble_count >= 0),
    CONSTRAINT positive_totals CHECK (total_purchased >= 0 AND total_consumed >= 0)
);

CREATE INDEX idx_user_credits_user ON statedb.user_credits(user_id);
CREATE INDEX idx_user_credits_updated ON statedb.user_credits(last_updated DESC);

COMMENT ON TABLE statedb.user_credits IS '사용자 크레딧(버블) 정보';
COMMENT ON COLUMN statedb.user_credits.user_id IS '사용자 ID (외래키)';
COMMENT ON COLUMN statedb.user_credits.bubble_count IS '현재 보유 버블 수';
COMMENT ON COLUMN statedb.user_credits.total_purchased IS '총 구매한 버블 수';
COMMENT ON COLUMN statedb.user_credits.total_consumed IS '총 소비한 버블 수';
COMMENT ON COLUMN statedb.user_credits.last_updated IS '마지막 업데이트 시간';

-- ------------------------------------------------------------
-- 2. credit_transactions: 크레딧 트랜잭션 히스토리
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.credit_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_transaction_type CHECK (
        transaction_type IN ('purchase', 'consume', 'refund', 'bonus', 'initial')
    )
);

CREATE INDEX idx_credit_trans_user ON statedb.credit_transactions(user_id);
CREATE INDEX idx_credit_trans_created ON statedb.credit_transactions(created_at DESC);
CREATE INDEX idx_credit_trans_type ON statedb.credit_transactions(transaction_type);

COMMENT ON TABLE statedb.credit_transactions IS '크레딧 트랜잭션 히스토리';
COMMENT ON COLUMN statedb.credit_transactions.transaction_id IS '트랜잭션 고유 ID';
COMMENT ON COLUMN statedb.credit_transactions.user_id IS '사용자 ID';
COMMENT ON COLUMN statedb.credit_transactions.amount IS '변경 금액 (양수: 추가, 음수: 차감)';
COMMENT ON COLUMN statedb.credit_transactions.transaction_type IS '트랜잭션 유형';
COMMENT ON COLUMN statedb.credit_transactions.balance_after IS '트랜잭션 후 잔액';
COMMENT ON COLUMN statedb.credit_transactions.description IS '트랜잭션 설명';

-- ------------------------------------------------------------
-- 3. 신규 가입자 초기 크레딧 자동 생성 트리거
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_initial_credits()
RETURNS TRIGGER AS $$
BEGIN
    -- 신규 사용자에게 200 버블 지급
    INSERT INTO statedb.user_credits (user_id, bubble_count, total_purchased, total_consumed)
    VALUES (NEW.user_id, 200, 200, 0);

    -- 초기 지급 트랜잭션 기록
    INSERT INTO statedb.credit_transactions (user_id, amount, transaction_type, balance_after, description)
    VALUES (NEW.user_id, 200, 'initial', 200, '신규 가입 환영 버블');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 기존 트리거가 있으면 삭제 후 재생성
DROP TRIGGER IF EXISTS trigger_create_credits ON statedb.users;

CREATE TRIGGER trigger_create_credits
AFTER INSERT ON statedb.users
FOR EACH ROW EXECUTE FUNCTION create_initial_credits();

COMMENT ON FUNCTION create_initial_credits() IS '신규 사용자 가입 시 초기 크레딧(200 버블) 자동 생성';

-- ------------------------------------------------------------
-- 4. 기존 사용자에게 초기 크레딧 추가
-- ------------------------------------------------------------
-- 기존 users 테이블에 있는 사용자들에게 크레딧 생성
INSERT INTO statedb.user_credits (user_id, bubble_count, total_purchased, total_consumed)
SELECT
    user_id,
    100 as bubble_count,
    100 as total_purchased,
    0 as total_consumed
FROM statedb.users
WHERE user_id NOT IN (SELECT user_id FROM statedb.user_credits)
ON CONFLICT (user_id) DO NOTHING;

-- 기존 사용자들의 초기 트랜잭션 기록
INSERT INTO statedb.credit_transactions (user_id, amount, transaction_type, balance_after, description)
SELECT
    uc.user_id,
    100 as amount,
    'initial' as transaction_type,
    uc.bubble_count as balance_after,
    '기존 사용자 크레딧 부여' as description
FROM statedb.user_credits uc
WHERE NOT EXISTS (
    SELECT 1 FROM statedb.credit_transactions ct
    WHERE ct.user_id = uc.user_id AND ct.transaction_type = 'initial'
);

-- ------------------------------------------------------------
-- 5. 인덱스 통계 업데이트
-- ------------------------------------------------------------
ANALYZE statedb.user_credits;
ANALYZE statedb.credit_transactions;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'User Credits System Created Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - statedb.user_credits (사용자 크레딧)';
    RAISE NOTICE '  - statedb.credit_transactions (트랜잭션 히스토리)';
    RAISE NOTICE '';
    RAISE NOTICE 'Triggers created:';
    RAISE NOTICE '  - trigger_create_credits (신규 가입 시 100 버블 자동 지급)';
    RAISE NOTICE '';
    RAISE NOTICE 'Initial credits:';
    RAISE NOTICE '  - All users granted 100 bubbles';
    RAISE NOTICE '============================================================';
END $$;
