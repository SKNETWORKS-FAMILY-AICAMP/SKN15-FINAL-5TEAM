#!/usr/bin/env python3
"""
시나리오 JSON 자동 변환 도구
dialogues (하드코딩 대사) → situations (상황 설명) 형식으로 변환

사용법:
    python scripts/convert_to_situations.py input.json output.json
"""

import json
import sys
import os
from pathlib import Path


def convert_dialogue_to_situation(dialogue_data, stage_name):
    """
    기존 dialogue 형식을 situation 형식으로 변환

    Args:
        dialogue_data: 기존 dialogue 객체
        stage_name: 스테이지 이름 (컨텍스트 생성용)

    Returns:
        situation 객체
    """
    speakers = dialogue_data.get("speakers", [])
    contents = dialogue_data.get("contents", [])
    emotions = dialogue_data.get("emotions", [])
    turn = dialogue_data.get("turn", 0)
    user_prompt = dialogue_data.get("user_prompt", "")

    # 모든 대사를 scene_description으로 통합
    scene_parts = []
    for i, content in enumerate(contents):
        speaker = speakers[i] if i < len(speakers) else "unknown"
        if speaker in ["system", "System", "시스템"]:
            # 시스템 나레이션은 그대로 사용
            scene_parts.append(content)
        else:
            # 캐릭터 대사는 간접 화법으로 변환
            scene_parts.append(f"{speaker}가 말한다: {content}")

    scene_description = " ".join(scene_parts)

    # 각 캐릭터별 정보 생성
    characters = []
    for idx, speaker in enumerate(speakers):
        if speaker in ["system", "System", "시스템"]:
            characters.append({
                "id": "system",
                "order": idx,
                "role": "나레이터",
                "emotion": emotions[idx] if idx < len(emotions) else "neutral",
                "situation": contents[idx] if idx < len(contents) else "",
                "context": f"{stage_name} 스테이지의 상황 설명"
            })
        else:
            characters.append({
                "id": speaker,
                "order": idx,
                "role": f"TODO: {speaker}의 역할을 정의하세요",
                "emotion": emotions[idx] if idx < len(emotions) else "neutral",
                "motivation": f"TODO: {speaker}의 동기를 정의하세요",
                "context": f"TODO: {speaker}의 상황 컨텍스트를 정의하세요",
                "original_dialogue": contents[idx] if idx < len(contents) else ""
            })

    return {
        "turn": turn,
        "scene_description": scene_description,
        "characters": characters,
        "user_prompt": user_prompt,
        "_conversion_note": "자동 변환됨. role, motivation, context를 수동으로 보완하세요."
    }


def analyze_character_context(stage_name, stage_type, speakers, contents):
    """
    스테이지 정보를 바탕으로 캐릭터 컨텍스트 추론
    """
    context_hints = {
        "intro": "시작 부분, 상황 파악 중",
        "fork": "선택의 순간, 결정을 내려야 함",
        "recruit_mission": "동료를 설득하는 중",
        "ending": "결말 부분",
        "cutscene": "중요한 장면 전개 중"
    }

    return context_hints.get(stage_type, "상황 전개 중")


def convert_stage(stage_name, stage_data):
    """
    스테이지 데이터 변환
    """
    if "dialogues" not in stage_data:
        print(f"  ⏭️  {stage_name}: dialogues 없음 (변환 스킵)")
        return stage_data

    print(f"  🔄 {stage_name}: dialogues → situations 변환 중...")

    situations = []
    for dialogue in stage_data["dialogues"]:
        situation = convert_dialogue_to_situation(dialogue, stage_name)
        situations.append(situation)

    # 새 데이터 생성
    new_stage_data = stage_data.copy()
    new_stage_data["situations"] = situations

    # 기존 dialogues는 백업으로 남김
    new_stage_data["_original_dialogues"] = stage_data["dialogues"]
    del new_stage_data["dialogues"]

    print(f"  ✅ {stage_name}: {len(situations)}개 situation 생성")

    return new_stage_data


def convert_scenario(input_file, output_file):
    """
    시나리오 JSON 파일 변환
    """
    print(f"\n{'='*60}")
    print(f"시나리오 변환 시작")
    print(f"{'='*60}")
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print()

    # JSON 로드
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 오류: 파일을 찾을 수 없습니다: {input_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 오류: JSON 파싱 실패: {e}")
        return False

    # 메타데이터 확인
    scenario_id = data.get("scenario_id", "unknown")
    title = data.get("title", "제목 없음")
    print(f"📋 시나리오: {title} ({scenario_id})")
    print()

    # 스테이지 변환
    stages = data.get("stages", {})
    if not stages:
        print("⚠️  경고: stages가 비어있습니다.")
        return False

    print(f"📂 총 {len(stages)}개 스테이지 발견")
    print()

    converted_stages = {}
    for stage_name, stage_data in stages.items():
        converted_stages[stage_name] = convert_stage(stage_name, stage_data)

    # 새 데이터 구성
    new_data = data.copy()
    new_data["stages"] = converted_stages
    new_data["metadata"]["version"] = new_data.get("metadata", {}).get("version", "1.0") + "_llm_driven"
    new_data["_conversion_info"] = {
        "converted_from": input_file,
        "conversion_tool": "convert_to_situations.py",
        "manual_review_required": True,
        "notes": [
            "role, motivation, context를 수동으로 보완해야 합니다",
            "original_dialogue를 참고하여 캐릭터의 의도를 파악하세요",
            "_original_dialogues 백업을 참고할 수 있습니다"
        ]
    }

    # JSON 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 오류: 파일 저장 실패: {e}")
        return False

    print()
    print(f"{'='*60}")
    print(f"✅ 변환 완료!")
    print(f"{'='*60}")
    print(f"출력: {output_file}")
    print()
    print("⚠️  중요: 다음 작업이 필요합니다:")
    print("  1. 각 캐릭터의 'role' 필드 작성")
    print("  2. 각 캐릭터의 'motivation' 필드 작성")
    print("  3. 각 캐릭터의 'context' 필드 작성")
    print("  4. 'original_dialogue'를 참고하여 의도 파악")
    print("  5. '_conversion_note' 및 '_original_dialogues' 제거 (선택)")
    print()

    return True


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python scripts/convert_to_situations.py <input.json> [output.json]")
        print()
        print("예제:")
        print("  python scripts/convert_to_situations.py data/scenarios/cutscene5_simple.json")
        print("  python scripts/convert_to_situations.py cutscene5_simple.json cutscene5_llm_driven.json")
        sys.exit(1)

    input_file = sys.argv[1]

    # 출력 파일명 자동 생성
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # input.json → input_llm_driven.json
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_llm_driven{input_path.suffix}")

    # 변환 실행
    success = convert_scenario(input_file, output_file)

    if success:
        print(f"🎉 다음 단계: {output_file}을 열어서 TODO 항목을 수정하세요!")
        sys.exit(0)
    else:
        print("❌ 변환 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
