#!/usr/bin/env python3
"""
Method 2: SLLM qLoRA Fine-tuning

경량화된 파인튜닝으로 Small Language Model 성능 개선
- Unsloth 사용 (2~5배 빠른 학습)
- 4-bit quantization으로 메모리 효율적
- LoRA로 파라미터 효율적 학습

장점:
  ✅ 작은 모델(1B~7B)로 빠른 추론 가능
  ✅ GPU 메모리 절약 (8GB GPU로 7B 모델 학습 가능)
  ✅ feedback_score를 sample weight로 활용
  ✅ Agent별 전문화된 모델 생성

단점:
  ⚠️  초기 학습 시간 필요 (1~2시간)
  ⚠️  데이터 1000개 이상 필요
  ⚠️  배포 복잡도 증가

추천 모델:
  - Llama-3.2-1B (빠른 추론)
  - Qwen2.5-3B (한국어 강함)
  - Gemma-2-2B (Google, 품질 우수)

사용법:
  # 1. 학습 데이터 추출
  python scripts/method2_qlora_finetuning.py --export-data --agent router

  # 2. 파인튜닝 실행 (GPU 필요)
  python scripts/method2_qlora_finetuning.py --train --agent router --model unsloth/Llama-3.2-1B-Instruct

  # 3. 추론 테스트
  python scripts/method2_qlora_finetuning.py --infer --agent router --input "이노스케 찾아줘"
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


class QLo RATrainingDataExporter:
    """qLoRA 학습 데이터 추출기"""

    def __init__(
        self,
        db_url: Optional[str] = None,
        min_score: float = 0.7,
        max_samples: int = 10000
    ):
        """
        Args:
            db_url: LogDB connection URL
            min_score: 최소 feedback_score (기본 0.7)
            max_samples: 최대 샘플 수 (기본 10000)
        """
        self.db_url = db_url or os.getenv("LOGDB_URL", os.getenv("DATABASE_URL"))
        self.min_score = min_score
        self.max_samples = max_samples

    def get_connection(self):
        """DB 연결"""
        return psycopg2.connect(self.db_url)

    def export_router_data(self, output_path: str) -> int:
        """
        Router Agent 학습 데이터 추출

        Format (JSONL):
        {
            "instruction": "시스템 프롬프트",
            "input": "사용자 입력 + 맥락",
            "output": "분류 결과 (JSON)",
            "weight": feedback_score
        }
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                user_input,
                context,
                model_output,
                feedback_score
            FROM training_logs
            WHERE agent_name = 'router'
              AND outcome IN ('success', 'partial')
              AND feedback_score >= %s
              AND created_at >= NOW() - INTERVAL '90 days'
            ORDER BY feedback_score DESC, created_at DESC
            LIMIT %s
        """, (self.min_score, self.max_samples))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # JSONL 변환
        samples = []
        for row in rows:
            user_input = row["user_input"]
            context = row["context"]
            model_output = row["model_output"]
            score = row["feedback_score"]

            # 시스템 프롬프트
            instruction = (
                "당신은 대화형 게임의 Router Agent입니다. "
                "사용자 입력을 분석하여 on_topic 또는 off_topic으로 분류하세요."
            )

            # 입력 (맥락 포함)
            recent_history = context.get("history", [])[-3:]  # 최근 3개
            history_text = "\n".join([f"- {h}" for h in recent_history]) if recent_history else "(대화 없음)"

            input_text = f"""## 최근 대화:
{history_text}

## 현재 입력:
{user_input}

다음 형식으로 출력하세요 (JSON):
{{"classification": "on_topic" 또는 "off_topic", "next_node": "라우팅 대상", "confidence": 0.0-1.0}}
"""

            # 출력
            output_json = {
                "classification": model_output.get("classification", ""),
                "next_node": model_output.get("next_node", ""),
                "confidence": model_output.get("confidence", 0.5)
            }
            output_text = json.dumps(output_json, ensure_ascii=False)

            samples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output_text,
                "weight": score
            })

        # JSONL 저장
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"✅ Router 데이터 {len(samples)}개 저장: {output_path}")
        return len(samples)

    def export_children_data(self, output_path: str) -> int:
        """
        Children Agent 학습 데이터 추출

        Format (JSONL):
        {
            "instruction": "시스템 프롬프트",
            "input": "Beats + 맥락",
            "output": "대사 리스트 (JSON)",
            "weight": feedback_score
        }
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                user_input,
                context,
                model_output,
                feedback_score
            FROM training_logs
            WHERE agent_name = 'children'
              AND outcome IN ('success', 'partial')
              AND feedback_score >= %s
              AND created_at >= NOW() - INTERVAL '90 days'
            ORDER BY feedback_score DESC, created_at DESC
            LIMIT %s
        """, (self.min_score, self.max_samples))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # JSONL 변환
        samples = []
        for row in rows:
            context = row["context"]
            model_output = row["model_output"]
            score = row["feedback_score"]

            # Beats 추출
            beats = context.get("children_ctx", {}).get("beats", [])
            if not beats:
                continue

            # 시스템 프롬프트
            instruction = (
                "당신은 귀멸의 칼날 세계관의 Children Agent입니다. "
                "Beats(행동 의도)를 받아서 캐릭터 대사를 생성하세요."
            )

            # 입력
            beats_text = "\n".join([
                f"- {b.get('character', '')}: {b.get('action', '')} (감정: {b.get('emotion', 'neutral')})"
                for b in beats
            ])

            affinity = context.get("affinity", {})
            affinity_text = "\n".join([f"- {k}: {v}" for k, v in affinity.items()])

            input_text = f"""## Beats (행동 의도):
{beats_text}

## 캐릭터 친밀도:
{affinity_text}

다음 형식으로 대사를 생성하세요 (JSON 배열):
[{{"character": "캐릭터명", "text": "대사"}}]
"""

            # 출력
            agent_responses = model_output.get("agent_responses", [])
            output_json = [
                {"character": r.get("character", ""), "text": r.get("text", "")}
                for r in agent_responses
            ]
            output_text = json.dumps(output_json, ensure_ascii=False)

            samples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output_text,
                "weight": score
            })

        # JSONL 저장
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"✅ Children 데이터 {len(samples)}개 저장: {output_path}")
        return len(samples)

    def export_parent_data(self, output_path: str) -> int:
        """
        Parent Agent 학습 데이터 추출

        Format (JSONL):
        {
            "instruction": "시스템 프롬프트",
            "input": "사용자 입력 + 스테이지 정보",
            "output": "Beats 리스트 (JSON)",
            "weight": feedback_score
        }
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                user_input,
                context,
                model_output,
                feedback_score
            FROM training_logs
            WHERE agent_name = 'parent'
              AND outcome IN ('success', 'partial')
              AND feedback_score >= %s
              AND created_at >= NOW() - INTERVAL '90 days'
            ORDER BY feedback_score DESC, created_at DESC
            LIMIT %s
        """, (self.min_score, self.max_samples))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # JSONL 변환
        samples = []
        for row in rows:
            user_input = row["user_input"]
            context = row["context"]
            model_output = row["model_output"]
            score = row["feedback_score"]

            # 시스템 프롬프트
            instruction = (
                "당신은 스토리 진행을 계획하는 Parent Agent입니다. "
                "사용자 입력을 분석하여 Beats(행동 의도)를 생성하세요."
            )

            # 입력
            current_stage = context.get("current_stage", "")
            participants = context.get("participants", [])

            input_text = f"""## 현재 스테이지:
{current_stage}

## 참여 캐릭터:
{", ".join(participants)}

## 사용자 입력:
{user_input}

다음 형식으로 Beats를 생성하세요 (JSON 배열):
[{{"character": "캐릭터명", "action": "행동", "emotion": "감정"}}]
"""

            # 출력
            agent_inputs = model_output.get("agent_inputs", {})
            beats = agent_inputs.get("children", {}).get("beats", []) if agent_inputs else []

            output_json = [
                {
                    "character": b.get("character", ""),
                    "action": b.get("action", ""),
                    "emotion": b.get("emotion", "neutral")
                }
                for b in beats
            ]
            output_text = json.dumps(output_json, ensure_ascii=False)

            if not output_json:
                continue

            samples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output_text,
                "weight": score
            })

        # JSONL 저장
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        print(f"✅ Parent 데이터 {len(samples)}개 저장: {output_path}")
        return len(samples)


def train_qlora_model(
    data_path: str,
    model_name: str,
    output_dir: str,
    max_steps: int = 1000,
    learning_rate: float = 2e-4
):
    """
    qLoRA 파인튜닝 실행

    Args:
        data_path: 학습 데이터 경로 (JSONL)
        model_name: 베이스 모델 (예: "unsloth/Llama-3.2-1B-Instruct")
        output_dir: 모델 저장 경로
        max_steps: 최대 학습 스텝
        learning_rate: 학습률
    """
    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import load_dataset
    except ImportError:
        print("❌ 필요한 패키지를 설치하세요:")
        print("   pip install unsloth trl transformers datasets")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🚀 qLoRA 파인튜닝 시작")
    print(f"{'='*70}")
    print(f"모델: {model_name}")
    print(f"데이터: {data_path}")
    print(f"출력: {output_dir}")

    # 1. 모델 로드 (4-bit quantization)
    print("\n[1/4] 모델 로딩 중...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=2048,
        dtype=None,  # Auto-detect
        load_in_4bit=True,  # 4-bit quantization
    )

    # 2. LoRA 설정
    print("[2/4] LoRA 어댑터 추가 중...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,  # LoRA rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing=True,
    )

    # 3. 데이터 로드
    print("[3/4] 학습 데이터 로딩 중...")
    dataset = load_dataset("json", data_files=data_path, split="train")

    # 데이터 포맷팅
    def formatting_func(examples):
        instructions = examples["instruction"]
        inputs = examples["input"]
        outputs = examples["output"]
        texts = []
        for instruction, input_text, output in zip(instructions, inputs, outputs):
            text = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Output:
{output}"""
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(formatting_func, batched=True)

    # Train/Val split (90/10)
    dataset = dataset.train_test_split(test_size=0.1, seed=42)

    # 4. 학습
    print(f"[4/4] 학습 시작 ({max_steps} steps)...")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            max_steps=max_steps,
            learning_rate=learning_rate,
            fp16=True,
            logging_steps=10,
            evaluation_strategy="steps",
            eval_steps=100,
            save_steps=500,
            save_total_limit=2,
            optim="adamw_8bit",
        ),
    )

    trainer.train()

    # 모델 저장
    print(f"\n✅ 학습 완료! 모델 저장 중: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"\n{'='*70}")
    print(f"🎉 qLoRA 파인튜닝 완료!")
    print(f"{'='*70}")


def infer_with_qlora(model_path: str, input_text: str):
    """
    파인튜닝된 모델로 추론

    Args:
        model_path: 모델 경로
        input_text: 입력 텍스트
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("❌ unsloth를 설치하세요: pip install unsloth")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🔮 추론 테스트")
    print(f"{'='*70}")

    # 모델 로드
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)  # 추론 모드

    # 추론
    inputs = tokenizer(input_text, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    print(f"\n입력:\n{input_text}")
    print(f"\n출력:\n{result}")
    print(f"\n{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="SLLM qLoRA Fine-tuning (Method 2)"
    )

    # 데이터 추출
    parser.add_argument(
        "--export-data",
        action="store_true",
        help="학습 데이터 추출"
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
        default="data/training",
        help="데이터 저장 경로 (기본: data/training)"
    )

    # 파인튜닝
    parser.add_argument(
        "--train",
        action="store_true",
        help="qLoRA 파인튜닝 실행 (GPU 필요)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="unsloth/Llama-3.2-1B-Instruct",
        help="베이스 모델 (기본: Llama-3.2-1B)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="최대 학습 스텝 (기본: 1000)"
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
        help="파인튜닝된 모델 경로"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="추론 입력 텍스트"
    )

    # 공통
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="최소 feedback_score (기본: 0.7)"
    )

    args = parser.parse_args()

    if args.export_data:
        if not args.agent:
            print("❌ --agent 옵션을 지정하세요 (router/parent/children)")
            sys.exit(1)

        os.makedirs(args.output, exist_ok=True)
        output_path = os.path.join(args.output, f"{args.agent}_train.jsonl")

        exporter = QLo RATrainingDataExporter(min_score=args.min_score)

        if args.agent == "router":
            count = exporter.export_router_data(output_path)
        elif args.agent == "children":
            count = exporter.export_children_data(output_path)
        elif args.agent == "parent":
            count = exporter.export_parent_data(output_path)

        print(f"\n💡 다음 명령으로 학습 시작:")
        print(f"   python scripts/method2_qlora_finetuning.py --train --agent {args.agent}")

    elif args.train:
        if not args.agent:
            print("❌ --agent 옵션을 지정하세요")
            sys.exit(1)

        data_path = os.path.join(args.output, f"{args.agent}_train.jsonl")
        if not os.path.exists(data_path):
            print(f"❌ 데이터 파일이 없습니다: {data_path}")
            print(f"먼저 --export-data를 실행하세요")
            sys.exit(1)

        output_dir = f"models/{args.agent}_qlora"
        train_qlora_model(
            data_path=data_path,
            model_name=args.model,
            output_dir=output_dir,
            max_steps=args.steps
        )

    elif args.infer:
        if not args.model_path or not args.input:
            print("❌ --model-path와 --input을 지정하세요")
            sys.exit(1)

        infer_with_qlora(args.model_path, args.input)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
