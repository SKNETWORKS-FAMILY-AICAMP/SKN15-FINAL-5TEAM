#!/usr/bin/env python3
"""
dialogue_generation 프롬프트에 narr 반복 방지 규칙 추가
"""
import yaml
from pathlib import Path

yaml_path = Path(__file__).parent / "configs" / "prompts.yaml"

# YAML 로드
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# 현재 프롬프트 가져오기
current_prompt = data['llm_prompts']['children']['dialogue_generation']

# narr 반복 방지 규칙 추가 (규칙 8과 --- 사이에 삽입)
new_rule = """
9. **⚠️ CRITICAL: narr는 이전 narr와 같은 표현을 반복하지 마세요**
   - 최근 대화를 확인하고 narr가 이미 사용한 표현은 다른 방식으로 묘사하세요
   - 같은 행동도 다양한 방식으로 표현할 수 있습니다
   - ❌ 절대 금지: 매 턴마다 "도시락을 한입 더 베어 물며...", "렌고쿠가 환하게 웃으며..." 반복
   - ✅ 올바름:
     * 첫 번째: "렌고쿠가 도시락을 한입 베어 물며 눈을 반짝인다."
     * 두 번째: "그의 얼굴에 만족스러운 미소가 번진다."
     * 세 번째: "창밖 풍경을 바라보며 생각에 잠긴다."
"""

# 규칙 8 다음에 새 규칙 삽입
# "8. **⚠️ CRITICAL: 사용자가 방금 한 말을 그대로 따라하지 마세요**" 뒤에 추가
marker = '   - ✅ 올바름: 사용자 "잘 먹겠습니다" → 캐릭터 "하하, 자 여기 있어! 맛있게 먹어라!"\n\n---'
replacement = '   - ✅ 올바름: 사용자 "잘 먹겠습니다" → 캐릭터 "하하, 자 여기 있어! 맛있게 먹어라!"\n' + new_rule + '\n---'

if marker in current_prompt:
    updated_prompt = current_prompt.replace(marker, replacement)
    data['llm_prompts']['children']['dialogue_generation'] = updated_prompt

    # 저장
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("✅ dialogue_generation 프롬프트에 narr 반복 방지 규칙 추가 완료!")
    print("\n변경 사항:")
    print("1. 규칙 9 추가: narr는 이전 narr와 같은 표현을 반복하지 마세요")
    print("2. 구체적인 예시 포함: 다양한 표현 방식 제시")
    print(f"\n프롬프트 길이: {len(updated_prompt)} characters")
else:
    print("❌ 마커를 찾을 수 없습니다. 프롬프트 구조를 확인하세요.")
    print(f"\n찾고 있는 마커:\n{marker}")
