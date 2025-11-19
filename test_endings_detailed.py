#!/usr/bin/env python3
"""
엔딩 테스트 스크립트 - 상세 버전
- 일반 엔딩 (렌고쿠 도움)
- 히든 엔딩 (동료 모으기)
- 모든 NPC 대사와 사용자 입력 저장
"""
import requests
import json
import time
from datetime import datetime

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzQ5MzAwM30.syGnJgGQu5Y0tQkXmX16KXvXcpU-SECanGyMp-oRPiY"
BASE_URL = "http://localhost:8000/api/chat"

def send_chat(session_id, user_input, user_name):
    """채팅 API 호출"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    data = {
        "scenario_id": "mugen-train",
        "user_input": user_input,
        "user_name": user_name
    }

    if session_id:
        data["session_id"] = session_id

    print(f"\n>>> User ({user_name}): {user_input}")

    response = requests.post(BASE_URL, headers=headers, json=data, stream=True)

    lines = []
    for line in response.iter_lines():
        if line:
            lines.append(line.decode('utf-8'))

    return lines

def parse_response(lines):
    """응답 파싱"""
    session_id = None
    current_stage = None
    is_ended = False
    dialogues = []

    for line in lines:
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])

                if data.get("type") == "metadata":
                    session_id = data.get("session_id")
                    current_stage = data.get("current_stage")
                    is_ended = data.get("is_ended", False)

                elif data.get("type") == "dialogue":
                    dialogue = data.get("dialogue", {})
                    speaker = dialogue.get("speaker")
                    text = dialogue.get("text")
                    print(f"  {speaker}: {text}")
                    dialogues.append({
                        "speaker": speaker,
                        "text": text
                    })

                elif data.get("type") == "done":
                    current_stage = data.get("current_stage")
                    is_ended = data.get("is_ended", False)
            except json.JSONDecodeError:
                pass

    return session_id, current_stage, is_ended, dialogues

def save_to_file(filename, content):
    """파일 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Saved: {filename}")

def test_normal_ending():
    """테스트 1: 일반 엔딩 (렌고쿠 도움)"""
    print("="*80)
    print("테스트 1: 일반 엔딩 (렌고쿠 도움)")
    print("="*80)

    conversation = []
    npc_outputs = []
    user_inputs = []

    # Turn 1: 시작
    print("\n[Turn 1] 시작...")
    user_input = "시작"
    user_inputs.append(f"[Turn 1] {user_input}")

    lines = send_chat(None, user_input, "일반엔딩테스트")
    session_id, stage, is_ended, dialogues = parse_response(lines)

    print(f"→ Session: {session_id}")
    print(f"→ Stage: {stage}")

    npc_outputs.append(f"\n[Turn 1] Stage: {stage}")
    for d in dialogues:
        npc_outputs.append(f"{d['speaker']}: {d['text']}")

    conversation.append({
        "turn": 1,
        "user_input": user_input,
        "stage": stage,
        "is_ended": is_ended,
        "dialogues": dialogues
    })
    time.sleep(3)

    # Turn 2-20: ROUTE_CHOICE 나올 때까지 진행, 나오면 선택
    for i in range(2, 21):
        print(f"\n[Turn {i}]")

        # ROUTE_CHOICE 감지: 이전 턴에서 ROUTE_CHOICE 나왔으면 선택
        if i > 2 and conversation[-1]["stage"] == "ROUTE_CHOICE":
            user_input = "렌고쿠를 도와야해"
            print(f"  *** ROUTE_CHOICE 감지! 렌고쿠 도움 선택 ***")
        else:
            user_input = "계속"

        user_inputs.append(f"[Turn {i}] {user_input}")

        lines = send_chat(session_id, user_input, "일반엔딩테스트")
        _, stage, is_ended, dialogues = parse_response(lines)

        print(f"→ Stage: {stage} | Ended: {is_ended}")

        npc_outputs.append(f"\n[Turn {i}] Stage: {stage} | Ended: {is_ended}")
        for d in dialogues:
            npc_outputs.append(f"{d['speaker']}: {d['text']}")

        conversation.append({
            "turn": i,
            "user_input": user_input,
            "stage": stage,
            "is_ended": is_ended,
            "dialogues": dialogues
        })

        if is_ended:
            print("\n=== 일반 엔딩 도달! ===")
            print("마지막 대화:")
            for d in dialogues[-3:]:
                print(f"  {d['speaker']}: {d['text']}")
            break
        time.sleep(3)

    # 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_to_file(f"normal_ending_npc_{timestamp}.txt", "\n".join(npc_outputs))
    save_to_file(f"normal_ending_user_{timestamp}.txt", "\n".join(user_inputs))
    save_to_file(f"normal_ending_full_{timestamp}.json", json.dumps(conversation, ensure_ascii=False, indent=2))

    return conversation

def test_hidden_ending():
    """테스트 2: 히든 엔딩 (동료 모으기)"""
    print("\n\n" + "="*80)
    print("테스트 2: 히든 엔딩 (동료 모으기)")
    print("="*80)

    conversation = []
    npc_outputs = []
    user_inputs = []

    # Turn 1: 시작
    print("\n[Turn 1] 시작...")
    user_input = "시작"
    user_inputs.append(f"[Turn 1] {user_input}")

    lines = send_chat(None, user_input, "히든엔딩테스트")
    session_id, stage, is_ended, dialogues = parse_response(lines)

    print(f"→ Session: {session_id}")
    print(f"→ Stage: {stage}")

    npc_outputs.append(f"\n[Turn 1] Stage: {stage}")
    for d in dialogues:
        npc_outputs.append(f"{d['speaker']}: {d['text']}")

    conversation.append({
        "turn": 1,
        "user_input": user_input,
        "stage": stage,
        "is_ended": is_ended,
        "dialogues": dialogues
    })
    time.sleep(3)

    # Turn 2-30: 동적 진행 (ROUTE_CHOICE -> RECRUIT -> Ending)
    recruit_attempts = 0  # RECRUIT에서 몇 번 대답했는지 카운트

    for i in range(2, 31):
        print(f"\n[Turn {i}]")

        # 이전 stage 확인
        prev_stage = conversation[-1]["stage"] if conversation else None

        # 입력 결정
        if prev_stage == "ROUTE_CHOICE":
            user_input = "동료들을 모으자"
            print(f"  *** ROUTE_CHOICE 감지! 동료 모으기 선택 ***")
        elif prev_stage == "RECRUIT":
            # RECRUIT 스테이지에서는 매 turn마다 다양한 대답
            recruit_responses = [
                "이노스케야, 같이 가자!",
                "겁쟁이는 아니잖아?",
                "함께 싸우자!",
                "젠이츠야, 네즈코가 위험해!",
                "같이 가야 해!",
                "네즈코를 지키자!",
                "힘을 합치자!",
                "알았어!"
            ]
            user_input = recruit_responses[recruit_attempts % len(recruit_responses)]
            recruit_attempts += 1
            print(f"  *** RECRUIT 스테이지 - 설득 시도 {recruit_attempts} ***")
        else:
            user_input = "계속"

        user_inputs.append(f"[Turn {i}] {user_input}")

        lines = send_chat(session_id, user_input, "히든엔딩테스트")
        _, stage, is_ended, dialogues = parse_response(lines)

        print(f"→ Stage: {stage} | Ended: {is_ended}")

        npc_outputs.append(f"\n[Turn {i}] Stage: {stage} | Ended: {is_ended}")
        for d in dialogues:
            npc_outputs.append(f"{d['speaker']}: {d['text']}")

        conversation.append({
            "turn": i,
            "user_input": user_input,
            "stage": stage,
            "is_ended": is_ended,
            "dialogues": dialogues
        })

        if is_ended:
            print("\n=== 히든 엔딩 도달! ===")
            print("마지막 대화:")
            for d in dialogues[-3:]:
                print(f"  {d['speaker']}: {d['text']}")
            break
        time.sleep(3)

    # 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_to_file(f"hidden_ending_npc_{timestamp}.txt", "\n".join(npc_outputs))
    save_to_file(f"hidden_ending_user_{timestamp}.txt", "\n".join(user_inputs))
    save_to_file(f"hidden_ending_full_{timestamp}.json", json.dumps(conversation, ensure_ascii=False, indent=2))

    return conversation

if __name__ == "__main__":
    print("엔딩 테스트 시작...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 일반 엔딩 테스트
    normal_conv = test_normal_ending()

    print("\n\n" + "="*80)
    print("잠시 대기 (5초)...")
    print("="*80)
    time.sleep(5)

    # 히든 엔딩 테스트
    hidden_conv = test_hidden_ending()

    print("\n\n" + "="*80)
    print("=== 테스트 완료 ===")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("\n파일이 저장되었습니다:")
    print("  - normal_ending_npc_*.txt")
    print("  - normal_ending_user_*.txt")
    print("  - normal_ending_full_*.json")
    print("  - hidden_ending_npc_*.txt")
    print("  - hidden_ending_user_*.txt")
    print("  - hidden_ending_full_*.json")
