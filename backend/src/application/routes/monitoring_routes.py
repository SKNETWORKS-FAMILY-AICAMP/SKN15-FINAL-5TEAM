"""
오토 라벨링 모니터링 라우터
- 평가 통계, 비용 추적, 캐시 히트율, 에이전트별 성능을 조회하는 엔드포인트
"""

# ============================================================
# 📊 모니터링 라우터 — 오토라벨링 통계 제공
# ============================================================
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ========================================================================
# 응답 모델 정의
# ========================================================================

class LabelingStatsResponse(BaseModel):
    """Auto-labeling 통계 응답"""
    total_evaluations: int
    avg_quality_score: float
    success_rate: float
    cache_hit_rate: float
    estimated_cost: str
    cost_per_evaluation: str
    agent_stats: Dict[str, Dict[str, float]]


class ABTestResultsResponse(BaseModel):
    """A/B 테스트 결과 응답"""
    total_tests: int
    hybrid_better_count: int
    avg_rule_score: float
    avg_hybrid_score: float
    avg_score_difference: float
    recommendation: str


class FeedbackAnalysisResponse(BaseModel):
    """피드백 분석 응답"""
    low_score_count: int
    common_issues: List[Dict[str, Any]]
    recommendations: List[str]


# ========================================================================
# 데이터베이스 유틸리티
# ========================================================================

def get_db_connection():
    """DB 연결 가져오기"""
    db_url = os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"[MonitoringAPI] DB connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# ========================================================================
# API 엔드포인트 집합
# ========================================================================

@router.get("/labeling-stats", response_model=LabelingStatsResponse)
async def get_labeling_stats(days: int = Query(7, ge=1, le=30)):
    """
    Auto-labeling 통계 조회

    Args:
        days: 조회 기간 (일 단위, 기본 7일)

    Returns:
        LabelingStatsResponse: 평가 통계
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 전체 통계
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_evaluations,
                AVG(feedback_score) as avg_score,
                SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN outcome = 'failure' THEN 1 ELSE 0 END) as failure_count,
                SUM(CASE WHEN outcome_reason LIKE '%(cached)%' THEN 1 ELSE 0 END) as cached_count
            FROM training_logs
            WHERE created_at > NOW() - INTERVAL '{days} days'
                AND outcome IS NOT NULL
        """)

        row = cursor.fetchone()
        if not row or row[0] == 0:
            raise HTTPException(status_code=404, detail="No data found for the specified period")

        total_evaluations = row[0]
        avg_score = float(row[1]) if row[1] else 0.0
        success_count = row[2]
        failure_count = row[3]
        cached_count = row[4]

        success_rate = (success_count / total_evaluations * 100) if total_evaluations > 0 else 0.0
        cache_hit_rate = (cached_count / total_evaluations * 100) if total_evaluations > 0 else 0.0

        # 에이전트별 통계
        cursor.execute(f"""
            SELECT
                agent_name,
                COUNT(*) as count,
                AVG(feedback_score) as avg_score,
                SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as success_rate
            FROM training_logs
            WHERE created_at > NOW() - INTERVAL '{days} days'
                AND outcome IS NOT NULL
            GROUP BY agent_name
        """)

        agent_stats = {}
        for row in cursor.fetchall():
            agent_name = row[0]
            agent_stats[agent_name] = {
                "count": row[1],
                "avg_score": round(float(row[2]), 2) if row[2] else 0.0,
                "success_rate": round(float(row[3]), 1) if row[3] else 0.0
            }

        # 비용 계산 (GPT-4 기준 단가)
        # 캐시되지 않은 평가만 비용 발생
        llm_calls = total_evaluations - cached_count
        cost_per_call = 0.00006  # $0.00006/건
        total_cost = llm_calls * cost_per_call

        cursor.close()
        conn.close()

        return LabelingStatsResponse(
            total_evaluations=total_evaluations,
            avg_quality_score=round(avg_score, 2),
            success_rate=round(success_rate, 1),
            cache_hit_rate=round(cache_hit_rate, 1),
            estimated_cost=f"${total_cost:.2f}",
            cost_per_evaluation=f"${cost_per_call:.5f}",
            agent_stats=agent_stats
        )

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ab-test-results", response_model=ABTestResultsResponse)
async def get_ab_test_results(days: int = Query(7, ge=1, le=30)):
    """
    A/B 테스트 결과 조회

    Args:
        days: 조회 기간 (일 단위, 기본 7일)

    Returns:
        ABTestResultsResponse: A/B 테스트 결과
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # A/B 테스트 테이블 존재 확인
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'ab_test_results'
            )
        """)

        if not cursor.fetchone()[0]:
            raise HTTPException(status_code=404, detail="A/B test not enabled")

        # A/B 테스트 통계 집계
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_tests,
                SUM(CASE WHEN hybrid_score > rule_score + 0.2 THEN 1 ELSE 0 END) as hybrid_better_count,
                AVG(rule_score) as avg_rule_score,
                AVG(hybrid_score) as avg_hybrid_score,
                AVG(score_difference) as avg_score_difference
            FROM ab_test_results
            WHERE created_at > NOW() - INTERVAL '{days} days'
        """)

        row = cursor.fetchone()
        if not row or row[0] == 0:
            raise HTTPException(status_code=404, detail="No A/B test data found")

        total_tests = row[0]
        hybrid_better_count = row[1]
        avg_rule_score = float(row[2]) if row[2] else 0.0
        avg_hybrid_score = float(row[3]) if row[3] else 0.0
        avg_score_difference = float(row[4]) if row[4] else 0.0

        # 추천 메시지
        if avg_hybrid_score > avg_rule_score + 0.1:
            recommendation = "하이브리드 평가가 Rule-based보다 우수합니다. 전체 활성화를 권장합니다."
        elif avg_hybrid_score > avg_rule_score:
            recommendation = "하이브리드 평가가 소폭 우수합니다. 추가 테스트 후 결정하세요."
        else:
            recommendation = "Rule-based와 성능 차이가 미미합니다. 비용을 고려하여 결정하세요."

        cursor.close()
        conn.close()

        return ABTestResultsResponse(
            total_tests=total_tests,
            hybrid_better_count=hybrid_better_count,
            avg_rule_score=round(avg_rule_score, 2),
            avg_hybrid_score=round(avg_hybrid_score, 2),
            avg_score_difference=round(avg_score_difference, 2),
            recommendation=recommendation
        )

    except HTTPException:
        cursor.close()
        conn.close()
        raise
    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback-analysis", response_model=FeedbackAnalysisResponse)
async def analyze_low_scores(days: int = Query(7, ge=1, le=30)):
    """
    낮은 점수 패턴 분석 (피드백 루프)

    Args:
        days: 조회 기간 (일 단위, 기본 7일)

    Returns:
        FeedbackAnalysisResponse: 피드백 분석 결과
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 낮은 점수 데이터 조회 (0.5 미만)
        cursor.execute(f"""
            SELECT
                agent_name,
                outcome_reason,
                COUNT(*) as count
            FROM training_logs
            WHERE feedback_score < 0.5
                AND created_at > NOW() - INTERVAL '{days} days'
            GROUP BY agent_name, outcome_reason
            ORDER BY count DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()
        low_score_count = sum(row[2] for row in rows)

        # 공통 이슈 분류
        context_issues = []
        tone_issues = []
        routing_issues = []

        for row in rows:
            agent_name = row[0]
            reason = row[1].lower() if row[1] else ""
            count = row[2]

            issue = {
                "agent": agent_name,
                "reason": row[1],
                "count": count
            }

            if "맥락" in reason or "context" in reason:
                context_issues.append(issue)
            elif "톤" in reason or "tone" in reason or "말투" in reason:
                tone_issues.append(issue)
            elif "routing" in reason or "mismatch" in reason:
                routing_issues.append(issue)

        common_issues = []
        if context_issues:
            common_issues.append({
                "type": "맥락 이탈",
                "count": len(context_issues),
                "examples": context_issues[:3]
            })
        if tone_issues:
            common_issues.append({
                "type": "캐릭터 톤 불일치",
                "count": len(tone_issues),
                "examples": tone_issues[:3]
            })
        if routing_issues:
            common_issues.append({
                "type": "라우팅 오류",
                "count": len(routing_issues),
                "examples": routing_issues[:3]
            })

        # 개선 권장사항
        recommendations = []
        if context_issues:
            recommendations.append("프롬프트에 '갑작스러운 주제 전환은 off_topic' 명시 강화")
        if tone_issues:
            recommendations.append("캐릭터별 말투 예시를 프롬프트에 추가")
        if routing_issues:
            recommendations.append("Router 분류 로직 개선 필요")
        if len(context_issues) + len(tone_issues) + len(routing_issues) > 10:
            recommendations.append("LLM 모델 업그레이드 고려 (gpt-4o-mini → gpt-4o)")

        cursor.close()
        conn.close()

        return FeedbackAnalysisResponse(
            low_score_count=low_score_count,
            common_issues=common_issues,
            recommendations=recommendations
        )

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-stats")
async def get_cache_stats():
    """캐시 통계 조회"""
    try:
        from backend.src.tools.training_logger import get_training_logger
    except ModuleNotFoundError:
        from src.tools.training_logger import get_training_logger

    logger = get_training_logger()

    return {
        "cache_size": len(logger.evaluation_cache),
        "cache_ttl": logger.cache_ttl,
        "cache_enabled": True
    }
