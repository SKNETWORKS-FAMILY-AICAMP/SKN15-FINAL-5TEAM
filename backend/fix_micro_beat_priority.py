#!/usr/bin/env python3
"""
MICRO_BEAT 모드에서 "최근 대화 > 상황 요약" 우선순위 명시
"""
import yaml
from pathlib import Path

yaml_path = Path(__file__).parent / "configs" / "prompts.yaml"

# YAML 로드
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

current_prompt = data['llm_prompts']['children']['dialogue_generation']

# "대신 해야 할 것:" 섹션을 강화
old_section = """**대신 해야 할 것:**
- 최근 대화를 읽고 현재 진행 중인 대화를 이어가세요
- 사용자 입력에 자연스럽게 반응하세요 (단, 세계관 검증 먼저!)
- 상황 요약은 "배경 설정"이지 "지금 해야 할 행동"이 아닙니다"""

new_section = """**대신 해야 할 것:**
- **⚠️ 최우선: 최근 대화를 읽고 현재 진행 중인 대화를 이어가세요**
- **최근 대화 > 상황 요약** (대화 맥락이 항상 우선입니다!)
- 사용자 입력에 자연스럽게 반응하세요 (단, 세계관 검증 먼저!)
- 상황 요약은 "배경 설정"이지 "지금 해야 할 행동"이 아닙니다
- Stage가 바뀌어도 최근 대화의 맥락은 유지됩니다"""

if old_section in current_prompt:
    updated_prompt = current_prompt.replace(old_section, new_section)
    data['llm_prompts']['children']['dialogue_generation'] = updated_prompt

    # 저장
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("✅ MICRO_BEAT 모드 우선순위 규칙 강화 완료!")
    print("\n변경 사항:")
    print("1. '최근 대화 > 상황 요약' 우선순위 명시")
    print("2. Stage 전환 시에도 대화 맥락 유지 강조")
    print(f"\n프롬프트 길이: {len(updated_prompt)} characters")
else:
    print("❌ 섹션을 찾을 수 없습니다.")
    print(f"\n찾고 있는 텍스트:\n{old_section}")
