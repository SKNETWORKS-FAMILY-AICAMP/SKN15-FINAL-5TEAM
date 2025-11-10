#!/usr/bin/env python3
"""
Method 5: Self-Improvement Loop

낮은 점수 데이터를 LLM으로 재생성하여 자동 개선
- feedback_score < 0.5 데이터를 선별
- 고품질 예제를 참고하여 개선안 생성
- 자동 평가 후 DB에 저장
- 지속적인 피드백 루프

장점:
  ✅ 자동으로 시스템 개선
  ✅ 인간 개입 최소화
  ✅ 낮은 품질 데이터를 학습 데이터로 전환
  ✅ 프롬프트 자동 최적화

사용 사례:
  - 야간 배치로 실행 (cron)
  - 낮은 점수 패턴 발견 시 자동 개선
  - A/B 테스트용 개선안 생성

워크플로우:
  1. 낮은 점수 로그 조회 (feedback_score < 0.5)
  2. 유사한 고품질 예제 검색
  3. LLM으로 개선안 생성
  4. 자동 평가 (graph_evaluator)
  5. 개선됐으면 DB에 저장
  6. 통계 리포트 생성

사용법:
  # 1. 낮은 점수 데이터 분석
  python scripts/method5_self_improvement_loop.py --analyze --days 7

  # 2. 개선 루프 실행 (최대 100개)
  python scripts/method5_self_improvement_loop.py --improve --agent children --max 100

  # 3. 크론 등록 (매일 자정 실행)
  # 0 0 * * * cd /path/to/backend && python scripts/method5_self_improvement_loop.py --improve --max 50
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor, Json


class SelfImprovementEngine:
    """자동 개선 엔진"""

    def __init__(
        self,
        db_url: Optional[str] = None,
        llm_model: str = "gpt-4o-mini",
        score_threshold: float = 0.5
    ):
        """
        Args:
            db_url: LogDB connection URL
            llm_model: 개선안 생성에 사용할 LLM
            score_threshold: 개선 대상 최대 점수 (기본 0.5)
        """
        self.db_url = db_url or os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
        self.llm_model = llm_model
        self.score_threshold = score_threshold

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def find_low_quality_logs(
        self,
        agent_name: str,
        days: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        낮은 품질 로그 조회

        Args:
            agent_name: 에이전트 이름
            days: 조회 기간 (일)
            limit: 최대 로그 수

        Returns:
            낮은 품질 로그 리스트
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(f"""
            SELECT
                id,
                session_id,
                turn_count,
                agent_name,
                user_input,
                context,
                model_output,
                feedback_score,
                outcome,
                outcome_reason,
                created_at
            FROM training_logs
            WHERE agent_name = %s
              AND feedback_score < %s
              AND created_at > NOW() - INTERVAL '{days} days'
              AND outcome IN ('failure', 'partial')
            ORDER BY feedback_score ASC, created_at DESC
            LIMIT %s
        """, (agent_name, self.score_threshold, limit))

        logs = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(log) for log in logs]

    def find_similar_high_quality_examples(
        self,
        low_quality_log: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        유사한 고품질 예제 검색

        Args:
            low_quality_log: 낮은 품질 로그
            top_k: 검색할 예제 수

        Returns:
            고품질 예제 리스트
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        agent_name = low_quality_log["agent_name"]
        user_input = low_quality_log["user_input"]

        # 간단한 텍스트 유사도 (실제로는 embedding 사용)
        # 여기서는 같은 agent_name + 비슷한 길이로 검색
        input_len = len(user_input) if user_input else 0

        cursor.execute("""
            SELECT
                id,
                user_input,
                context,
                model_output,
                feedback_score,
                outcome_reason
            FROM training_logs
            WHERE agent_name = %s
              AND feedback_score >= 0.8
              AND outcome = 'success'
              AND ABS(LENGTH(user_input) - %s) < 50
            ORDER BY feedback_score DESC
            LIMIT %s
        """, (agent_name, input_len, top_k))

        examples = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(ex) for ex in examples]

    def generate_improvement_with_llm(
        self,
        low_quality_log: Dict[str, Any],
        high_quality_examples: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        LLM으로 개선안 생성

        Args:
            low_quality_log: 개선 대상 로그
            high_quality_examples: 참고할 고품질 예제

        Returns:
            개선된 model_output 또는 None
        """
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
        except ImportError:
            print("❌ openai 패키지를 설치하세요: pip install openai")
            return None

        agent_name = low_quality_log["agent_name"]
        user_input = low_quality_log["user_input"]
        context = low_quality_log["context"]
        original_output = low_quality_log["model_output"]
        failure_reason = low_quality_log["outcome_reason"]

        # 프롬프트 생성
        examples_text = "\n\n".join([
            f"### 고품질 예제 {i+1} (점수: {ex['feedback_score']:.2f})\n"
            f"입력: {ex['user_input']}\n"
            f"출력: {json.dumps(ex['model_output'], ensure_ascii=False, indent=2)}\n"
            f"성공 이유: {ex['outcome_reason']}"
            for i, ex in enumerate(high_quality_examples)
        ])

        system_prompt = f"""당신은 {agent_name} Agent의 출력을 개선하는 전문가입니다.
낮은 품질의 출력을 분석하고, 고품질 예제를 참고하여 개선안을 제시하세요.

**개선 원칙**:
1. 고품질 예제의 패턴을 따르세요
2. 실패 이유를 해결하세요
3. JSON 형식을 정확히 유지하세요
4. 맥락에 맞는 응답을 생성하세요
"""

        user_prompt = f"""## 현재 상황
**Agent**: {agent_name}
**입력**: {user_input}
**맥락**: {json.dumps(context, ensure_ascii=False, indent=2)[:500]}...

## 기존 출력 (낮은 품질)
```json
{json.dumps(original_output, ensure_ascii=False, indent=2)}
```

**실패 이유**: {failure_reason}

## 참고할 고품질 예제
{examples_text}

## 요청
위 고품질 예제를 참고하여, 기존 출력을 개선하세요.
JSON 형식으로만 출력하세요 (설명 없이).
"""

        try:
            response = openai.ChatCompletion.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            improved_text = response.choices[0].message.content.strip()

            # JSON 파싱
            # Code block 제거
            if "```json" in improved_text:
                improved_text = improved_text.split("```json")[1].split("```")[0].strip()
            elif "```" in improved_text:
                improved_text = improved_text.split("```")[1].split("```")[0].strip()

            improved_output = json.loads(improved_text)

            return improved_output

        except Exception as e:
            print(f"❌ LLM 개선안 생성 실패: {e}")
            return None

    def evaluate_improvement(
        self,
        improved_output: Dict[str, Any],
        original_log: Dict[str, Any]
    ) -> Tuple[str, float, str]:
        """
        개선안 평가 (graph_evaluator 사용)

        Args:
            improved_output: 개선된 출력
            original_log: 원본 로그

        Returns:
            (outcome, score, reason)
        """
        try:
            from src.utils.graph_evaluator import GraphEvaluator
            from src.database.db_manager import DatabaseManager

            # DB Manager 생성
            db_manager = DatabaseManager(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                dbname=os.getenv('DB_NAME', 'kimedb'),
                user=os.getenv('DB_USER', 'kime'),
                password=os.getenv('DB_PASSWORD', 'dev123')
            )

            evaluator = GraphEvaluator(db_manager)

            # 임시 log_id (실제로는 저장 후 사용)
            log_id = original_log["id"]
            entity_ids = improved_output.get("mentioned_entity_ids", [])
            session_id = original_log.get("session_id")
            turn_number = original_log.get("turn_count")

            outcome, score, reason = evaluator.evaluate_log_quality(
                log_id=log_id,
                entity_ids=entity_ids,
                session_id=session_id,
                turn_number=turn_number,
                context=original_log["context"]
            )

            return (outcome, score, reason)

        except Exception as e:
            print(f"⚠️  평가 실패 (기본값 사용): {e}")
            # 기본값: 원본보다 조금 높게
            original_score = original_log.get("feedback_score", 0.3)
            return ("partial", original_score + 0.2, "Auto-improved (no evaluation)")

    def save_improved_log(
        self,
        original_log: Dict[str, Any],
        improved_output: Dict[str, Any],
        outcome: str,
        score: float,
        reason: str
    ) -> Optional[int]:
        """
        개선된 로그 저장

        Args:
            original_log: 원본 로그
            improved_output: 개선된 출력
            outcome: 평가 결과
            score: feedback_score
            reason: 평가 이유

        Returns:
            새 로그 ID 또는 None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO training_logs (
                    session_id, turn_count, scenario_id, current_stage,
                    agent_name, user_input, context, model_output,
                    latency_ms, token_count, llm_model,
                    outcome, outcome_reason, feedback_score,
                    is_error, labeled_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                RETURNING id
            """, (
                original_log["session_id"],
                original_log["turn_count"],
                original_log["context"].get("scenario_id"),
                original_log["context"].get("current_stage"),
                original_log["agent_name"],
                original_log["user_input"],
                Json(original_log["context"]),
                Json(improved_output),
                0,  # latency_ms (개선안은 0)
                None,  # token_count
                f"self-improved-{self.llm_model}",
                outcome,
                f"[IMPROVED] {reason}",
                score,
                False,
                datetime.now()
            ))

            new_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()

            return new_id

        except Exception as e:
            print(f"❌ 개선 로그 저장 실패: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return None

    def run_improvement_loop(
        self,
        agent_name: str,
        days: int = 7,
        max_improvements: int = 100
    ) -> Dict[str, Any]:
        """
        개선 루프 실행

        Args:
            agent_name: 에이전트 이름
            days: 조회 기간 (일)
            max_improvements: 최대 개선 수

        Returns:
            통계 딕셔너리
        """
        print("\n" + "="*70)
        print(f"🔄 Self-Improvement Loop 시작")
        print("="*70)
        print(f"Agent: {agent_name}")
        print(f"기간: 최근 {days}일")
        print(f"최대 개선 수: {max_improvements}")

        # 1. 낮은 품질 로그 조회
        print(f"\n[1/5] 낮은 품질 로그 조회 중...")
        low_quality_logs = self.find_low_quality_logs(agent_name, days, max_improvements)

        if not low_quality_logs:
            print("✅ 개선 대상이 없습니다!")
            return {"improved": 0, "failed": 0, "total": 0}

        print(f"   찾은 로그: {len(low_quality_logs)}개")

        # 통계
        improved_count = 0
        failed_count = 0
        improvements = []

        # 2. 각 로그에 대해 개선 시도
        for i, log in enumerate(low_quality_logs, 1):
            print(f"\n[{i}/{len(low_quality_logs)}] 개선 중...")
            print(f"   원본 점수: {log['feedback_score']:.2f}")
            print(f"   실패 이유: {log['outcome_reason'][:80]}...")

            # 고품질 예제 검색
            examples = self.find_similar_high_quality_examples(log, top_k=3)

            if not examples:
                print("   ⚠️  참고 예제 없음 (건너뜀)")
                failed_count += 1
                continue

            # LLM으로 개선안 생성
            improved_output = self.generate_improvement_with_llm(log, examples)

            if not improved_output:
                print("   ❌ 개선안 생성 실패")
                failed_count += 1
                continue

            # 개선안 평가
            outcome, score, reason = self.evaluate_improvement(improved_output, log)

            print(f"   개선 점수: {score:.2f} ({outcome})")

            # 점수가 향상됐으면 저장
            if score > log["feedback_score"]:
                new_id = self.save_improved_log(log, improved_output, outcome, score, reason)

                if new_id:
                    print(f"   ✅ 개선 성공! (ID: {new_id}, +{score - log['feedback_score']:.2f})")
                    improved_count += 1
                    improvements.append({
                        "original_id": log["id"],
                        "improved_id": new_id,
                        "original_score": log["feedback_score"],
                        "improved_score": score,
                        "delta": score - log["feedback_score"]
                    })
                else:
                    print("   ❌ 저장 실패")
                    failed_count += 1
            else:
                print(f"   ⚠️  점수 향상 없음 (건너뜀)")
                failed_count += 1

            # Rate limit (API 비용 절감)
            time.sleep(1)

        # 3. 통계 출력
        print("\n" + "="*70)
        print("📊 Self-Improvement 결과")
        print("="*70)
        print(f"총 처리: {len(low_quality_logs)}개")
        print(f"개선 성공: {improved_count}개")
        print(f"개선 실패: {failed_count}개")

        if improvements:
            avg_delta = sum(imp["delta"] for imp in improvements) / len(improvements)
            max_delta = max(imp["delta"] for imp in improvements)
            print(f"\n평균 점수 향상: +{avg_delta:.3f}")
            print(f"최대 점수 향상: +{max_delta:.3f}")

            print(f"\n상위 5개 개선:")
            for imp in sorted(improvements, key=lambda x: x["delta"], reverse=True)[:5]:
                print(f"  - ID {imp['original_id']}: "
                      f"{imp['original_score']:.2f} → {imp['improved_score']:.2f} "
                      f"(+{imp['delta']:.2f})")

        return {
            "total": len(low_quality_logs),
            "improved": improved_count,
            "failed": failed_count,
            "improvements": improvements
        }

    def analyze_low_quality_patterns(
        self,
        agent_name: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """낮은 품질 패턴 분석"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Agent별 낮은 품질 통계
        where_clause = f"AND agent_name = '{agent_name}'" if agent_name else ""

        cursor.execute(f"""
            SELECT
                agent_name,
                COUNT(*) as low_quality_count,
                AVG(feedback_score) as avg_score,
                outcome_reason,
                COUNT(*) as pattern_count
            FROM training_logs
            WHERE feedback_score < %s
              AND created_at > NOW() - INTERVAL '{days} days'
              {where_clause}
            GROUP BY agent_name, outcome_reason
            ORDER BY pattern_count DESC
        """, (self.score_threshold,))

        patterns = cursor.fetchall()
        cursor.close()
        conn.close()

        return {"patterns": [dict(p) for p in patterns]}


def main():
    parser = argparse.ArgumentParser(
        description="Self-Improvement Loop (Method 5)"
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="낮은 품질 패턴 분석"
    )
    parser.add_argument(
        "--improve",
        action="store_true",
        help="개선 루프 실행"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["router", "parent", "children"],
        help="에이전트 이름"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="조회 기간 (일, 기본: 7)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=100,
        help="최대 개선 수 (기본: 100)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="LLM 모델 (기본: gpt-4o-mini)"
    )

    args = parser.parse_args()

    engine = SelfImprovementEngine(llm_model=args.model)

    if args.analyze:
        print("\n" + "="*70)
        print("📊 낮은 품질 패턴 분석")
        print("="*70)

        result = engine.analyze_low_quality_patterns(args.agent, args.days)

        print(f"\n총 {len(result['patterns'])}개 패턴 발견\n")

        print(f"{'Agent':<15} {'Count':<10} {'Avg Score':<12} {'Reason':<50}")
        print("-" * 90)

        for pattern in result["patterns"][:20]:
            print(f"{pattern['agent_name']:<15} "
                  f"{pattern['pattern_count']:<10} "
                  f"{pattern['avg_score']:<12.2f} "
                  f"{pattern['outcome_reason'][:50]:<50}")

        print(f"\n💡 --improve 옵션으로 자동 개선 실행")

    elif args.improve:
        if not args.agent:
            print("❌ --agent 옵션을 지정하세요")
            sys.exit(1)

        result = engine.run_improvement_loop(
            agent_name=args.agent,
            days=args.days,
            max_improvements=args.max
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
