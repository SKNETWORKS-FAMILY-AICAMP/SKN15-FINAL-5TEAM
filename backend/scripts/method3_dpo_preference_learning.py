#!/usr/bin/env python3
"""
Method 3: DPO (Direct Preference Optimization)

feedback_score를 활용한 선호도 학습
- RLHF보다 간단하고 안정적
- Chosen (높은 점수) vs Rejected (낮은 점수) 쌍 생성
- 같은 입력에 대한 다른 품질의 응답 비교

장점:
  ✅ RLHF보다 구현 간단 (Reward Model 불필요)
  ✅ feedback_score를 직접 활용
  ✅ 안정적인 학습 (KL divergence로 원본 모델과 차이 제한)
  ✅ ChatGPT, Claude 등이 사용하는 최신 기법

단점:
  ⚠️  Chosen-Rejected 쌍 데이터 필요 (같은 입력에 대한 다른 응답)
  ⚠️  데이터 수집 시간 필요
  ⚠️  GPU 메모리 사용량 높음

추천 상황:
  - feedback_score가 0~1로 연속적일 때 (현재 시스템!)
  - 같은 입력에 여러 응답이 있을 때
  - 품질 차이가 명확한 데이터가 많을 때

사용법:
  # 1. Chosen-Rejected 쌍 추출
  python scripts/method3_dpo_preference_learning.py --export-pairs --agent router

  # 2. DPO 학습 실행 (GPU 필요)
  python scripts/method3_dpo_preference_learning.py --train --agent router

  # 3. 추론 테스트
  python scripts/method3_dpo_preference_learning.py --infer --model-path models/router_dpo --input "테스트"
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor


class DPOPreferencePairGenerator:
    """DPO 학습을 위한 Chosen-Rejected 쌍 생성기"""

    def __init__(
        self,
        db_url: Optional[str] = None,
        chosen_threshold: float = 0.8,
        rejected_threshold: float = 0.5,
        min_score_gap: float = 0.2
    ):
        """
        Args:
            db_url: LogDB connection URL
            chosen_threshold: Chosen 최소 점수 (기본 0.8)
            rejected_threshold: Rejected 최대 점수 (기본 0.5)
            min_score_gap: Chosen-Rejected 최소 점수 차이 (기본 0.2)
        """
        self.db_url = db_url or os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
        self.chosen_threshold = chosen_threshold
        self.rejected_threshold = rejected_threshold
        self.min_score_gap = min_score_gap

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def find_preference_pairs_by_similarity(
        self,
        agent_name: str,
        max_pairs: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        유사한 입력에 대한 Chosen-Rejected 쌍 찾기

        전략:
        1. 같은 user_input에 대한 여러 로그가 있으면 점수로 비교
        2. 비슷한 embedding을 가진 로그끼리 비교
        3. 같은 session의 유사한 턴 비교

        Returns:
            [{
                "prompt": "입력",
                "chosen": "고품질 응답",
                "rejected": "저품질 응답",
                "chosen_score": 0.9,
                "rejected_score": 0.4
            }]
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 전략 1: 정확히 같은 user_input
        print("\n[전략 1] 같은 user_input 쌍 찾기...")
        cursor.execute("""
            WITH input_groups AS (
                SELECT
                    user_input,
                    COUNT(*) as cnt
                FROM training_logs
                WHERE agent_name = %s
                  AND user_input IS NOT NULL
                  AND user_input != ''
                GROUP BY user_input
                HAVING COUNT(*) >= 2
            )
            SELECT
                t1.user_input,
                t1.context,
                t1.model_output as chosen_output,
                t1.feedback_score as chosen_score,
                t2.model_output as rejected_output,
                t2.feedback_score as rejected_score
            FROM training_logs t1
            INNER JOIN training_logs t2 ON t1.user_input = t2.user_input
            INNER JOIN input_groups ig ON t1.user_input = ig.user_input
            WHERE t1.agent_name = %s
              AND t2.agent_name = %s
              AND t1.id != t2.id
              AND t1.feedback_score >= %s
              AND t2.feedback_score <= %s
              AND (t1.feedback_score - t2.feedback_score) >= %s
            LIMIT %s
        """, (
            agent_name,
            agent_name, agent_name,
            self.chosen_threshold, self.rejected_threshold, self.min_score_gap,
            max_pairs
        ))

        exact_matches = cursor.fetchall()
        print(f"   찾은 쌍: {len(exact_matches)}개")

        pairs = []
        for row in exact_matches:
            prompt = self._format_prompt(row["user_input"], row["context"], agent_name)
            chosen = self._format_output(row["chosen_output"], agent_name)
            rejected = self._format_output(row["rejected_output"], agent_name)

            pairs.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "chosen_score": row["chosen_score"],
                "rejected_score": row["rejected_score"],
                "method": "exact_match"
            })

        # 전략 2: Embedding 유사도 기반 (exact match가 부족할 때)
        if len(pairs) < max_pairs * 0.5:
            print(f"\n[전략 2] Embedding 유사도 기반 쌍 찾기...")
            needed = max_pairs - len(pairs)

            cursor.execute("""
                SELECT
                    t1.id as chosen_id,
                    t1.user_input as chosen_input,
                    t1.context as chosen_context,
                    t1.model_output as chosen_output,
                    t1.feedback_score as chosen_score,
                    t1.embedding as chosen_embedding,
                    t2.id as rejected_id,
                    t2.user_input as rejected_input,
                    t2.model_output as rejected_output,
                    t2.feedback_score as rejected_score,
                    t2.embedding as rejected_embedding,
                    1 - (t1.embedding <=> t2.embedding) as similarity
                FROM training_logs t1
                CROSS JOIN LATERAL (
                    SELECT id, user_input, model_output, feedback_score, embedding
                    FROM training_logs t2
                    WHERE t2.agent_name = %s
                      AND t2.id != t1.id
                      AND t2.feedback_score <= %s
                      AND t2.embedding IS NOT NULL
                      AND (1 - (t1.embedding <=> t2.embedding)) >= 0.7
                    ORDER BY t1.embedding <=> t2.embedding
                    LIMIT 1
                ) t2
                WHERE t1.agent_name = %s
                  AND t1.feedback_score >= %s
                  AND t1.embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
            """, (
                agent_name, self.rejected_threshold,
                agent_name, self.chosen_threshold,
                needed
            ))

            embedding_matches = cursor.fetchall()
            print(f"   찾은 쌍: {len(embedding_matches)}개 (유사도 >= 0.7)")

            for row in embedding_matches:
                prompt = self._format_prompt(
                    row["chosen_input"],
                    row["chosen_context"],
                    agent_name
                )
                chosen = self._format_output(row["chosen_output"], agent_name)
                rejected = self._format_output(row["rejected_output"], agent_name)

                pairs.append({
                    "prompt": prompt,
                    "chosen": chosen,
                    "rejected": rejected,
                    "chosen_score": row["chosen_score"],
                    "rejected_score": row["rejected_score"],
                    "similarity": row["similarity"],
                    "method": "embedding_similarity"
                })

        cursor.close()
        conn.close()

        print(f"\n✅ 총 {len(pairs)}개 preference 쌍 생성")
        return pairs

    def _format_prompt(
        self,
        user_input: str,
        context: Dict[str, Any],
        agent_name: str
    ) -> str:
        """프롬프트 포맷팅"""
        if agent_name == "router":
            history = context.get("history", [])[-3:]
            history_text = "\n".join([f"- {h}" for h in history]) if history else "(없음)"

            return f"""## 최근 대화:
{history_text}

## 현재 입력:
{user_input}

분류하세요 (on_topic/off_topic):"""

        elif agent_name == "children":
            beats = context.get("children_ctx", {}).get("beats", [])
            beats_text = "\n".join([
                f"- {b.get('character')}: {b.get('action')}"
                for b in beats
            ]) if beats else "(없음)"

            return f"""## Beats:
{beats_text}

대사를 생성하세요:"""

        elif agent_name == "parent":
            return f"""## 입력:
{user_input}

Beats를 생성하세요:"""

        return user_input

    def _format_output(self, model_output: Dict[str, Any], agent_name: str) -> str:
        """출력 포맷팅"""
        if agent_name == "router":
            return json.dumps({
                "classification": model_output.get("classification", ""),
                "next_node": model_output.get("next_node", ""),
                "confidence": model_output.get("confidence", 0.5)
            }, ensure_ascii=False)

        elif agent_name == "children":
            responses = model_output.get("agent_responses", [])
            return json.dumps([
                {"character": r.get("character"), "text": r.get("text")}
                for r in responses
            ], ensure_ascii=False)

        elif agent_name == "parent":
            agent_inputs = model_output.get("agent_inputs", {})
            beats = agent_inputs.get("children", {}).get("beats", [])
            return json.dumps([
                {"character": b.get("character"), "action": b.get("action")}
                for b in beats
            ], ensure_ascii=False)

        return json.dumps(model_output, ensure_ascii=False)

    def export_dpo_dataset(
        self,
        pairs: List[Dict[str, Any]],
        output_path: str,
        train_split: float = 0.9
    ) -> Tuple[int, int]:
        """
        DPO 데이터셋 저장 (HuggingFace format)

        Format:
        {
            "prompt": "입력",
            "chosen": "고품질 응답",
            "rejected": "저품질 응답"
        }
        """
        # Train/Test split
        split_idx = int(len(pairs) * train_split)
        train_pairs = pairs[:split_idx]
        test_pairs = pairs[split_idx:]

        # 저장
        train_path = output_path.replace(".jsonl", "_train.jsonl")
        test_path = output_path.replace(".jsonl", "_test.jsonl")

        with open(train_path, "w", encoding="utf-8") as f:
            for pair in train_pairs:
                f.write(json.dumps({
                    "prompt": pair["prompt"],
                    "chosen": pair["chosen"],
                    "rejected": pair["rejected"]
                }, ensure_ascii=False) + "\n")

        with open(test_path, "w", encoding="utf-8") as f:
            for pair in test_pairs:
                f.write(json.dumps({
                    "prompt": pair["prompt"],
                    "chosen": pair["chosen"],
                    "rejected": pair["rejected"]
                }, ensure_ascii=False) + "\n")

        print(f"\n✅ DPO 데이터셋 저장:")
        print(f"   Train: {train_path} ({len(train_pairs)}개)")
        print(f"   Test: {test_path} ({len(test_pairs)}개)")

        return len(train_pairs), len(test_pairs)


def train_dpo_model(
    train_path: str,
    test_path: str,
    model_name: str,
    output_dir: str,
    max_steps: int = 1000,
    beta: float = 0.1
):
    """
    DPO 학습 실행

    Args:
        train_path: 학습 데이터 경로
        test_path: 검증 데이터 경로
        model_name: 베이스 모델
        output_dir: 모델 저장 경로
        max_steps: 최대 학습 스텝
        beta: DPO beta 파라미터 (KL penalty)
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from trl import DPOTrainer
        from datasets import load_dataset
    except ImportError:
        print("❌ 필요한 패키지를 설치하세요:")
        print("   pip install transformers trl datasets accelerate")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🚀 DPO 학습 시작")
    print(f"{'='*70}")
    print(f"모델: {model_name}")
    print(f"Train: {train_path}")
    print(f"Test: {test_path}")
    print(f"Beta: {beta}")

    # 1. 모델 로드
    print("\n[1/4] 모델 로딩 중...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    # 2. 데이터 로드
    print("[2/4] 데이터셋 로딩 중...")
    train_dataset = load_dataset("json", data_files=train_path, split="train")
    eval_dataset = load_dataset("json", data_files=test_path, split="train")

    # 3. DPO Trainer 설정
    print(f"[3/4] DPO Trainer 설정 중 (beta={beta})...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        learning_rate=5e-7,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_steps=500,
        save_total_limit=2,
        remove_unused_columns=False,
        fp16=True,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Auto-create reference model
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        beta=beta,  # KL penalty
        max_length=1024,
        max_prompt_length=512,
    )

    # 4. 학습
    print(f"[4/4] DPO 학습 시작...")
    trainer.train()

    # 모델 저장
    print(f"\n✅ 학습 완료! 모델 저장 중: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"\n{'='*70}")
    print(f"🎉 DPO 학습 완료!")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="DPO Preference Learning (Method 3)"
    )

    # 데이터 생성
    parser.add_argument(
        "--export-pairs",
        action="store_true",
        help="Chosen-Rejected 쌍 추출"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["router", "parent", "children"],
        help="에이전트 이름"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/dpo",
        help="데이터 저장 경로 (기본: data/dpo)"
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=5000,
        help="최대 쌍 수 (기본: 5000)"
    )

    # DPO 학습
    parser.add_argument(
        "--train",
        action="store_true",
        help="DPO 학습 실행 (GPU 필요)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="meta-llama/Llama-3.2-1B-Instruct",
        help="베이스 모델"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="최대 학습 스텝 (기본: 1000)"
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.1,
        help="DPO beta (KL penalty, 기본: 0.1)"
    )

    # 추론
    parser.add_argument(
        "--infer",
        action="store_true",
        help="추론 테스트"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        help="학습된 모델 경로"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="추론 입력"
    )

    args = parser.parse_args()

    if args.export_pairs:
        if not args.agent:
            print("❌ --agent 옵션을 지정하세요")
            sys.exit(1)

        os.makedirs(args.output, exist_ok=True)
        output_path = os.path.join(args.output, f"{args.agent}_dpo.jsonl")

        generator = DPOPreferencePairGenerator()
        pairs = generator.find_preference_pairs_by_similarity(
            agent_name=args.agent,
            max_pairs=args.max_pairs
        )

        if not pairs:
            print("❌ Preference 쌍을 찾을 수 없습니다.")
            print("💡 데이터가 부족하거나 점수 차이가 없을 수 있습니다.")
            sys.exit(1)

        train_count, test_count = generator.export_dpo_dataset(pairs, output_path)

        print(f"\n💡 다음 명령으로 DPO 학습 시작:")
        print(f"   python scripts/method3_dpo_preference_learning.py --train --agent {args.agent}")

    elif args.train:
        if not args.agent:
            print("❌ --agent 옵션을 지정하세요")
            sys.exit(1)

        train_path = os.path.join(args.output, f"{args.agent}_dpo_train.jsonl")
        test_path = os.path.join(args.output, f"{args.agent}_dpo_test.jsonl")

        if not os.path.exists(train_path):
            print(f"❌ 데이터 파일이 없습니다: {train_path}")
            print(f"먼저 --export-pairs를 실행하세요")
            sys.exit(1)

        output_dir = f"models/{args.agent}_dpo"
        train_dpo_model(
            train_path=train_path,
            test_path=test_path,
            model_name=args.model,
            output_dir=output_dir,
            max_steps=args.steps,
            beta=args.beta
        )

    elif args.infer:
        if not args.model_path or not args.input:
            print("❌ --model-path와 --input을 지정하세요")
            sys.exit(1)

        from transformers import AutoModelForCausalLM, AutoTokenizer

        model = AutoModelForCausalLM.from_pretrained(args.model_path, device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained(args.model_path)

        inputs = tokenizer(args.input, return_tensors="pt").to("cuda")
        outputs = model.generate(**inputs, max_new_tokens=256)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print(f"\n입력: {args.input}")
        print(f"출력: {result}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
