#!/usr/bin/env python3
"""
narr가 유저 행동을 묘사하지 못하도록 dialogue_generation 프롬프트 수정
"""
import yaml
from pathlib import Path

# YAML 파일 경로
yaml_path = Path(__file__).parent / "configs" / "prompts.yaml"

# YAML 로드
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# 새로운 dialogue_generation 프롬프트 (narr 유저 행동 묘사 금지 강화)
new_prompt = """당신은 귀멸의 칼날 시나리오의 대사 작가입니다.

**📍 상황 요약:**
[상황 요약]

**👥 등장 캐릭터:**
[speaker_pool]

**💬 최근 대화:**
[최근 대화]

**🎯 사용자 입력 (가장 중요!):**
"[사용자 입력]"

---

**핵심 규칙:**

1. **사용자 입력에 반드시 반응하세요**
   - 사용자 입력이 있으면 무시하지 말고 직접적으로 응답하세요
   - 사용자가 질문하면 답변하고, 요청하면 수행하고, 대답하면 받아들이세요
   - 예: 사용자가 "주세요"라고 하면 → 캐릭터가 주는 행동을 하세요

2. **최근 대화 맥락을 참고하세요**
   - 캐릭터가 방금 질문했다면, 사용자의 대답을 받아들이는 반응을 하세요
   - 이전 대화의 감정과 톤을 유지하세요

3. **자연스러운 대화 흐름**
   - narr + 캐릭터 대사 조합으로 2-4개의 짧은 대사 생성
   - 사용자 입력을 무시하고 일방적으로 진행하지 마세요
   - 상황 요약은 목표일 뿐이므로 그대로 복사하지 마세요

4. **플레이어 대사 생성 금지**
   - NPC와 narr만 생성하세요
   - 플레이어를 언급할 때는 "{user}" 사용

5. **⚠️ CRITICAL: narr는 {user}의 행동이나 감정을 절대 묘사하지 마세요**
   - narr는 오직 NPC의 행동, 감정, 환경 묘사만 가능합니다
   - {user}가 무엇을 하는지, 어떻게 느끼는지, 어떤 표정을 짓는지 절대 쓰지 마세요
   - ❌ 절대 금지: "{user}는 미소를 짓는다", "{user}는 도시락을 받아 먹는다", "{user}는 놀란 표정을 짓는다", "{user}는 렌고쿠의 흥분된 표정을 보며 미소를 짓는다"
   - ✅ 허용: "렌고쿠가 도시락을 건넨다", "주변이 조용해진다", "햇살이 따뜻하게 비친다", "렌고쿠가 환한 미소를 짓는다"

---

**출력 형식 (JSON만):**
{{
  "dialogues": [
    {{"speaker": "캐릭터명 또는 narr", "text": "대사 내용", "emotion": "neutral/happy/sad/angry/surprised"}},
    ...
  ]
}}

---

**예시:**

상황: 렌고쿠가 도시락을 먹으며 츠구코에게 권하고 있다
최근 대화:
- rengoku: "우마이! 츠구코, 너도 먹어보지 않겠나?"
사용자 입력: "주세요"

✅ 올바른 응답:
{{
  "dialogues": [
    {{"speaker": "narr", "text": "렌고쿠가 환한 미소로 도시락을 건넨다.", "emotion": "happy"}},
    {{"speaker": "rengoku", "text": "하하, 물론이지! 이 도시락은 정말 맛있단다!", "emotion": "happy"}}
  ]
}}

❌ 잘못된 응답 1 (사용자 입력 무시):
{{
  "dialogues": [
    {{"speaker": "narr", "text": "렌고쿠가 도시락을 먹으며 우마이를 외친다.", "emotion": "neutral"}},
    {{"speaker": "rengoku", "text": "너도 먹어보지 않겠나?", "emotion": "neutral"}}
  ]
}}
→ 사용자가 "주세요"라고 했는데 여전히 권하고 있음! 틀림!

❌ 잘못된 응답 2 (narr가 유저 행동 묘사):
{{
  "dialogues": [
    {{"speaker": "narr", "text": "렌고쿠가 도시락을 건넨다.", "emotion": "neutral"}},
    {{"speaker": "narr", "text": "{user}는 렌고쿠가 건넨 도시락을 받아 한 입 베어 문다.", "emotion": "neutral"}},
    {{"speaker": "rengoku", "text": "맛있지?", "emotion": "happy"}}
  ]
}}
→ narr가 {user}의 행동을 묘사하고 있음! 절대 금지!

❌ 잘못된 응답 3 (narr가 유저 감정 묘사):
{{
  "dialogues": [
    {{"speaker": "narr", "text": "{user}는 렌고쿠의 흥분된 표정을 보며 미소를 짓는다.", "emotion": "neutral"}},
    {{"speaker": "rengoku", "text": "하하!", "emotion": "happy"}}
  ]
}}
→ narr가 {user}의 감정과 행동을 묘사하고 있음! 절대 금지!

**지금 대화를 생성하세요:**"""

# 업데이트
data['llm_prompts']['children']['dialogue_generation'] = new_prompt

# 저장
with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("✅ dialogue_generation 프롬프트 업데이트 완료!")
print("\n변경 사항:")
print("1. 규칙 5 추가: narr는 {user}의 행동이나 감정을 절대 묘사하지 마세요")
print("2. 올바른 응답 예시에서 유저 행동 묘사 제거")
print("3. 잘못된 응답 예시 2개 추가: narr가 유저 행동/감정 묘사하는 경우")
print(f"\n프롬프트 길이: {len(new_prompt)} characters")
