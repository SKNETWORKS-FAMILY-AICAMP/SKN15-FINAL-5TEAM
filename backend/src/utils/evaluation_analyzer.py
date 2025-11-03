"""
Evaluation Analyzer for Auto-labeling Feedback Loop

주기적으로 낮은 점수 데이터를 분석하여 프롬프트 개선 제안
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import psycopg2


class EvaluationAnalyzer:
    """평가 결과 분석 및 피드백 생성"""

    def __init__(self):
        self.db_url = os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def analyze_low_scores(self, days: int = 7, threshold: float = 0.5) -> Dict:
        """
        최근 N일간 낮은 점수 패턴 분석

        Args:
            days: 분석 기간 (일)
            threshold: 낮은 점수 기준 (기본 0.5)

        Returns:
            분석 결과 딕셔너리
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 낮은 점수 데이터 조회
        cursor.execute(f"""
            SELECT
                agent_name,
                user_input,
                outcome,
                outcome_reason,
                feedback_score,
                context
            FROM training_logs
            WHERE feedback_score < %s
              AND created_at > NOW() - INTERVAL '{days} days'
            ORDER BY feedback_score ASC
            LIMIT 100
        """, (threshold,))

        rows = cursor.fetchall()

        # 패턴 분석
        patterns = self._find_common_patterns(rows)

        # 개선 보고서 생성
        report = self._generate_improvement_report(patterns, days, threshold)

        cursor.close()
        conn.close()

        return {
            "analysis_period_days": days,
            "threshold": threshold,
            "total_low_scores": len(rows),
            "patterns": patterns,
            "report": report
        }

    def _find_common_patterns(self, data: List[tuple]) -> Dict[str, List]:
        """공통 패턴 추출"""
        patterns = {
            "context_break": [],      # 맥락 이탈
            "tone_mismatch": [],       # 톤 불일치
            "routing_errors": [],      # 라우팅 오류
            "beat_issues": [],         # Beat 문제
            "other": []
        }

        for row in data:
            agent_name = row[0]
            user_input = row[1]
            outcome = row[2]
            reason = row[3].lower() if row[3] else ""
            score = row[4]

            issue = {
                "agent": agent_name,
                "input": user_input,
                "outcome": outcome,
                "reason": row[3],
                "score": score
            }

            # 패턴 분류
            if "맥락" in reason or "context" in reason or "이탈" in reason:
                patterns["context_break"].append(issue)
            elif "톤" in reason or "tone" in reason or "말투" in reason or "캐릭터" in reason:
                patterns["tone_mismatch"].append(issue)
            elif "routing" in reason or "mismatch" in reason or "불일치" in reason:
                patterns["routing_errors"].append(issue)
            elif "beat" in reason or "의도" in reason:
                patterns["beat_issues"].append(issue)
            else:
                patterns["other"].append(issue)

        return patterns

    def _generate_improvement_report(
        self,
        patterns: Dict[str, List],
        days: int,
        threshold: float
    ) -> str:
        """개선 보고서 작성"""
        report_lines = []

        report_lines.append("# Auto-labeling 개선 보고서")
        report_lines.append("")
        report_lines.append(f"**분석 기간**: 최근 {days}일")
        report_lines.append(f"**점수 기준**: {threshold} 미만")
        report_lines.append("")

        # 1. 맥락 이탈 문제
        if patterns["context_break"]:
            count = len(patterns["context_break"])
            report_lines.append(f"## 1. 맥락 이탈 문제 ({count}건)")
            report_lines.append("")
            report_lines.append("**가장 많은 실패 원인:**")
            report_lines.append("- 갑작스러운 주제 전환을 감지 못함")
            report_lines.append("- 세계관 외부 질문을 on_topic으로 오분류")
            report_lines.append("")
            report_lines.append("**개선 방안:**")
            report_lines.append("- 프롬프트에 '갑작스러운 주제 전환은 off_topic' 명시 강화")
            report_lines.append("- 세계관 관련 질문 목록 예시 추가")
            report_lines.append("")
            report_lines.append("**예시:**")
            for i, issue in enumerate(patterns["context_break"][:3], 1):
                report_lines.append(f"{i}. Agent: {issue['agent']}, Score: {issue['score']:.2f}")
                report_lines.append(f"   Input: \"{issue['input']}\"")
                report_lines.append(f"   Reason: {issue['reason']}")
                report_lines.append("")

        # 2. 캐릭터 톤 불일치
        if patterns["tone_mismatch"]:
            count = len(patterns["tone_mismatch"])
            report_lines.append(f"## 2. 캐릭터 톤 불일치 ({count}건)")
            report_lines.append("")
            report_lines.append("**가장 많은 실패 원인:**")
            report_lines.append("- 대사가 캐릭터 성격과 맞지 않음")
            report_lines.append("- 친밀도를 고려하지 않은 반응")
            report_lines.append("")
            report_lines.append("**개선 방안:**")
            report_lines.append("- 캐릭터별 말투 예시 추가")
            report_lines.append("- 친밀도별 대사 톤 가이드 제공")
            report_lines.append("")

        # 3. 라우팅 오류
        if patterns["routing_errors"]:
            count = len(patterns["routing_errors"])
            report_lines.append(f"## 3. 라우팅 오류 ({count}건)")
            report_lines.append("")
            report_lines.append("**개선 방안:**")
            report_lines.append("- Router Agent 분류 로직 개선")
            report_lines.append("- Confidence 임계값 조정")
            report_lines.append("")

        # 4. Beat 문제
        if patterns["beat_issues"]:
            count = len(patterns["beat_issues"])
            report_lines.append(f"## 4. Beat 의도 표현 문제 ({count}건)")
            report_lines.append("")
            report_lines.append("**개선 방안:**")
            report_lines.append("- Beat action/emotion을 더 명확히 정의")
            report_lines.append("- 예시 대사를 프롬프트에 포함")
            report_lines.append("")

        # 5. 전체 권장사항
        report_lines.append("## 5. 전체 권장사항")
        report_lines.append("")

        total_issues = sum(len(v) for v in patterns.values())
        if total_issues > 50:
            report_lines.append("- ⚠️  **심각**: 낮은 점수 건수가 많습니다. 즉시 조치 필요")
            report_lines.append("- LLM 모델 업그레이드 고려 (gpt-4o-mini → gpt-4o)")
        elif total_issues > 20:
            report_lines.append("- ⚡ **주의**: 프롬프트 개선 권장")
        else:
            report_lines.append("- ✅ **양호**: 현재 시스템이 잘 작동 중")

        if len(patterns["context_break"]) > 10:
            report_lines.append("- 맥락 이해 개선 우선 필요")
        if len(patterns["tone_mismatch"]) > 10:
            report_lines.append("- 캐릭터 톤 평가 강화 필요")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append(f"**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(report_lines)

    def get_improvement_suggestions(self, days: int = 7) -> List[str]:
        """
        개선 제안 목록 생성

        Returns:
            개선 제안 문자열 리스트
        """
        analysis = self.analyze_low_scores(days=days)
        patterns = analysis["patterns"]

        suggestions = []

        # 맥락 이탈 문제
        if len(patterns["context_break"]) > 5:
            suggestions.append(
                "Router 프롬프트에 '갑작스러운 주제 전환은 off_topic으로 판단' 추가"
            )
            suggestions.append(
                "세계관 관련 질문 예시 목록 확대 (호흡법, 훈련, 미션 등)"
            )

        # 톤 불일치
        if len(patterns["tone_mismatch"]) > 5:
            suggestions.append(
                "Children 프롬프트에 캐릭터별 대표 대사 예시 3개씩 추가"
            )
            suggestions.append(
                "친밀도별 대사 톤 가이드라인 명시 (낯설음/보통/친밀)"
            )

        # 라우팅 오류
        if len(patterns["routing_errors"]) > 5:
            suggestions.append(
                "Router Confidence 임계값 재조정 (현재 0.3/0.8 → 0.4/0.7)"
            )

        # Beat 문제
        if len(patterns["beat_issues"]) > 5:
            suggestions.append(
                "Parent 프롬프트에 Beat action/emotion 예시 추가"
            )

        # 전체적으로 점수가 낮으면
        if analysis["total_low_scores"] > 50:
            suggestions.append(
                "LLM 모델 업그레이드 고려 (gpt-4o-mini → gpt-4o)"
            )
            suggestions.append(
                "Rule + LLM 가중치 조정 (40:60 → 30:70)"
            )

        return suggestions


# Singleton
_analyzer: Optional[EvaluationAnalyzer] = None


def get_evaluation_analyzer() -> EvaluationAnalyzer:
    """Analyzer 싱글톤 가져오기"""
    global _analyzer
    if _analyzer is None:
        _analyzer = EvaluationAnalyzer()
    return _analyzer


# CLI용 실행 함수
if __name__ == "__main__":
    """
    사용 예시:
    python -m backend.src.utils.evaluation_analyzer
    """
    analyzer = get_evaluation_analyzer()

    # 최근 7일간 분석
    result = analyzer.analyze_low_scores(days=7)

    print(result["report"])
    print("\n\n=== 개선 제안 ===")
    for i, suggestion in enumerate(analyzer.get_improvement_suggestions(), 1):
        print(f"{i}. {suggestion}")
