# children.py
from __future__ import annotations
import json
from typing import Any, Dict

# ------------------------------
# 1) 공통: Children 인터페이스
# ------------------------------
class ChildrenBase:
    """
    ParentAgent가 기대하는 호출 인터페이스:
      __call__(prompt_json_str: str) -> str(JSON 문자열)
    """
    def __call__(self, prompt_json_str: str) -> str:
        raise NotImplementedError


# ------------------------------
# 2) MockChildren (로컬 테스트용)
#    - LLM 없이도 E2E 확인 가능
# ------------------------------
class MockChildren(ChildrenBase):
    def __call__(self, prompt_json_str: str) -> str:
        req = json.loads(prompt_json_str)

        # 입력에서 필요한 정보만 사용
        sys_spec   = req.get("system", {})
        scene_beats = sys_spec.get("beats", {})
        allowed = [s for s in sys_spec.get("allowed_speakers", []) if s] or ["tanjiro"]
        choice_spec = sys_spec.get("choice_spec", []) or []

        # 간단한 더미 내레이션/대사 생성 (허용 화자만)
        narration = scene_beats.get("intro") or "상황이 긴박하다."
        lines = [{"speaker": allowed[0], "text": "결정을 내려야 해. 어떻게 할래?"}]

        # Children은 분기 결정을 하지 않는다(Parent 규칙). 선택지는 그대로 회신.
        choices = []
        for ch in choice_spec:
            # Parent가 검증할 것이므로 id/text/value만 그대로 복사
            choices.append({
                "id": ch.get("id",""),
                "text": ch.get("text",""),
                "value": ch.get("value")
            })

        # 상태 패치는 아주 보수적으로 (예: 턴 +1만)
        state_patch = {"turn": {"$inc": 1}}

        resp = {
            "narration": narration,
            "lines": lines,
            "choices": choices,
            "state_patch": state_patch,
            # "image_resource_id": "optional_id"
        }
        return json.dumps(resp, ensure_ascii=False)


# ------------------------------
# 3) OpenAI 백엔드 예시
#    - 실제 LLM 붙일 때 사용
#    - 환경변수 OPENAI_API_KEY 필요
# ------------------------------
class OpenAIChildren(ChildrenBase):
    """
    OpenAI Chat Completions(혹은 Responses)로 Children 구현 예시.
    - 모델에게: "반드시 JSON만" 반환하도록 강하게 지시
    - 실패 시 1회 재시도 + 간단한 JSON 복구
    """
    def __init__(self, client, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

        # 시스템 프롬프트: 절대 JSON 외 형식 금지
        self.system_msg = (
            "You are a dialogue writer for a story game. "
            "You MUST output ONLY a single JSON object that exactly matches the provided schema. "
            "Do NOT add commentary, markdown, or extra keys."
        )

    def __call__(self, prompt_json_str: str) -> str:
        prompt = prompt_json_str

        # 1) LLM 호출
        content = [
            {"role": "system", "content": self.system_msg},
            {"role": "user", "content": prompt},
        ]
        raw = self.client.chat.completions.create(
            model=self.model,
            messages=content,
            temperature=0.7,
        )

        txt = raw.choices[0].message.content.strip()

        # 2) JSON 강제 파싱 & 1회 복구 시도
        try:
            data = json.loads(txt)
        except Exception:
            # 재요청(엄격 지시)
            content.append({"role":"system","content":"Return ONLY valid JSON. No prose. No markdown."})
            raw2 = self.client.chat.completions.create(
                model=self.model,
                messages=content,
                temperature=0.2,
            )
            txt = raw2.choices[0].message.content.strip()
            # 마지막으로 억지 파싱 시도 (중괄호만 추출)
            start = txt.find("{")
            end   = txt.rfind("}")
            if start >= 0 and end > start:
                txt = txt[start:end+1]
            # 실패해도 그대로 반환(Parent에서 pydantic이 걸러줌)
        return txt
