"""
Training Data Export Script
대화 데이터를 CSV/JSON 형식으로 추출하여 LLM Fine-tuning에 사용
"""
import asyncio
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import AsyncSessionLocal
from app.features.chat.models import DialogueTurn, UserInput


async def export_training_data(
    output_dir: str = "/tmp/training_data",
    scenario_id: str = None,
    format: str = "jsonl"  # "jsonl", "csv", "both"
):
    """
    대화 데이터를 훈련용 형식으로 추출

    Args:
        output_dir: 출력 디렉토리
        scenario_id: 특정 시나리오만 추출 (None이면 전체)
        format: 출력 형식 ("jsonl", "csv", "both")
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        print("🔍 Fetching dialogue data from database...")

        # 1. Dialogues 조회
        dialogue_query = select(DialogueTurn).order_by(
            DialogueTurn.session_id,
            DialogueTurn.turn_number,
            DialogueTurn.order_index
        )

        if scenario_id:
            dialogue_query = dialogue_query.where(DialogueTurn.scenario_id == scenario_id)

        dialogue_result = await db.execute(dialogue_query)
        all_dialogues = list(dialogue_result.scalars().all())

        # 2. User Inputs 조회
        user_input_query = select(UserInput).order_by(
            UserInput.session_id,
            UserInput.turn_number
        )

        user_input_result = await db.execute(user_input_query)
        all_user_inputs = list(user_input_result.scalars().all())

        print(f"✅ Loaded {len(all_dialogues)} dialogues and {len(all_user_inputs)} user inputs")

        # 3. 턴별로 그룹화
        # (session_id, turn_number) → [dialogues]
        turn_dialogues: Dict[tuple, List[DialogueTurn]] = {}
        for dlg in all_dialogues:
            key = (str(dlg.session_id), dlg.turn_number)
            if key not in turn_dialogues:
                turn_dialogues[key] = []
            turn_dialogues[key].append(dlg)

        # (session_id, turn_number) → user_input
        turn_user_inputs: Dict[tuple, str] = {}
        for ui in all_user_inputs:
            key = (str(ui.session_id), ui.turn_number)
            turn_user_inputs[key] = ui.user_input

        # 4. 훈련 샘플 생성
        training_samples = []

        for (session_id, turn_number), dialogues in turn_dialogues.items():
            user_input = turn_user_inputs.get((session_id, turn_number), "")

            # 턴 1 (prologue)은 스킵 (user_input 없음)
            if not user_input or turn_number == 1:
                continue

            # NPC 응답 결합
            npc_responses = []
            for dlg in sorted(dialogues, key=lambda d: d.order_index or 0):
                npc_responses.append({
                    "speaker": dlg.speaker,
                    "text": dlg.content,
                    "emotion": dlg.emotion or "neutral"
                })

            # 샘플 생성
            sample = {
                "session_id": session_id,
                "turn_number": turn_number,
                "scenario_id": dialogues[0].scenario_id if dialogues else None,
                "stage_tag": dialogues[0].stage_tag if dialogues else None,
                "user_input": user_input,
                "npc_responses": npc_responses,
                "response_count": len(npc_responses)
            }

            training_samples.append(sample)

        print(f"✅ Generated {len(training_samples)} training samples")

        # 5. 출력 형식별 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_suffix = f"_{scenario_id}" if scenario_id else "_all"

        if format in ["jsonl", "both"]:
            # JSONL 형식 (OpenAI Fine-tuning 호환)
            jsonl_path = f"{output_dir}/training_data{scenario_suffix}_{timestamp}.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for sample in training_samples:
                    # OpenAI Chat Completion 형식
                    messages = [
                        {
                            "role": "system",
                            "content": f"You are a character in a {sample['scenario_id']} scenario. Current stage: {sample['stage_tag'] or 'unknown'}. Respond in character with appropriate emotion."
                        },
                        {
                            "role": "user",
                            "content": sample["user_input"]
                        },
                        {
                            "role": "assistant",
                            "content": json.dumps(sample["npc_responses"], ensure_ascii=False)
                        }
                    ]

                    f.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")

            print(f"✅ Saved JSONL to: {jsonl_path}")

        if format in ["csv", "both"]:
            # CSV 형식 (분석용)
            csv_path = f"{output_dir}/training_data{scenario_suffix}_{timestamp}.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "session_id", "turn_number", "scenario_id", "stage_tag",
                    "user_input", "npc_responses", "response_count"
                ])
                writer.writeheader()

                for sample in training_samples:
                    sample["npc_responses"] = json.dumps(sample["npc_responses"], ensure_ascii=False)
                    writer.writerow(sample)

            print(f"✅ Saved CSV to: {csv_path}")

        # 6. 통계 출력
        print("\n📊 Training Data Statistics:")
        print(f"   Total samples: {len(training_samples)}")

        # 시나리오별 분포
        scenario_counts = {}
        for sample in training_samples:
            sid = sample["scenario_id"]
            scenario_counts[sid] = scenario_counts.get(sid, 0) + 1

        print(f"   By scenario:")
        for sid, count in sorted(scenario_counts.items(), key=lambda x: -x[1]):
            print(f"     - {sid}: {count} samples")

        # 응답 개수 분포
        response_count_dist = {}
        for sample in training_samples:
            count = sample["response_count"]
            response_count_dist[count] = response_count_dist.get(count, 0) + 1

        print(f"   By response count:")
        for count, num_samples in sorted(response_count_dist.items()):
            print(f"     - {count} responses: {num_samples} samples")

        return training_samples


async def export_by_scenario():
    """각 시나리오별로 개별 파일 생성"""
    print("=" * 80)
    print("🎯 Exporting Training Data by Scenario")
    print("=" * 80)

    # mugen-train
    print("\n1️⃣ Exporting mugen-train...")
    await export_training_data(
        output_dir="/tmp/training_data",
        scenario_id="mugen-train",
        format="both"
    )

    # counseling
    print("\n2️⃣ Exporting counseling...")
    await export_training_data(
        output_dir="/tmp/training_data",
        scenario_id="counseling",
        format="both"
    )

    # 전체
    print("\n3️⃣ Exporting all scenarios...")
    await export_training_data(
        output_dir="/tmp/training_data",
        scenario_id=None,
        format="both"
    )

    print("\n" + "=" * 80)
    print("✅ All training data exported successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(export_by_scenario())
