#!/usr/bin/env python3
"""
dialogue_generation 프롬프트에 맥락 유지 규칙 강화
- Stage 전환 시에도 이전 대화 맥락을 유지하도록 명시
"""
import yaml
from pathlib import Path

yaml_path = Path(__file__).parent / "configs" / "prompts.yaml"

# YAML 로드
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

current_prompt = data['llm_prompts']['children']['dialogue_generation']

# "3. **최근 대화 맥락을 참고하세요**" 섹션을 강화
old_rule_3 = """3. **최근 대화 맥락을 참고하세요**
   - 캐릭터가 방금 질문했다면, 사용자의 대답을 받아들이는 반응을 하세요
   - 이전 대화의 감정과 톤을 유지하세요
   - 대화가 자연스럽게 이어지도록 하세요"""

new_rule_3 = """3. **⚠️ CRITICAL: 최근 대화 맥락을 반드시 참고하세요**
   - **최근 대화는 Stage가 바뀌어도 유효합니다!** 절대 무시하지 마세요
   - 캐릭터가 방금 질문했다면, 사용자의 대답을 받아들이는 반응을 하세요
   - 이전 대화에서 언급된 주제(도시락, 어머니, 임무 등)를 기억하세요
   - 사용자가 이전 대화를 이어가는 말을 하면 자연스럽게 응답하세요
   - 예시:
     * 최근 대화: "렌고쿠: 너도 먹어보지 않겠나?"
     * 사용자: "다음에 한번 같이 드시죠"
     * ✅ 올바름: "하하! 그렇게 하지! 다음에는 꼭 함께 먹도록 하자!"
     * ❌ 틀림: "무엇을 드시겠다고?" (이전 도시락 얘기를 잊음)"""

if old_rule_3 in current_prompt:
    updated_prompt = current_prompt.replace(old_rule_3, new_rule_3)
    data['llm_prompts']['children']['dialogue_generation'] = updated_prompt

    # 저장
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("✅ dialogue_generation 프롬프트에 맥락 유지 규칙 강화 완료!")
    print("\n변경 사항:")
    print("1. 규칙 3을 CRITICAL로 강화")
    print("2. Stage 전환 시에도 최근 대화 맥락 유지하도록 명시")
    print("3. 구체적인 예시 추가 (도시락 맥락 유지)")
    print(f"\n프롬프트 길이: {len(updated_prompt)} characters")
else:
    print("❌ 규칙 3을 찾을 수 없습니다.")
    print(f"\n찾고 있는 텍스트:\n{old_rule_3}")
