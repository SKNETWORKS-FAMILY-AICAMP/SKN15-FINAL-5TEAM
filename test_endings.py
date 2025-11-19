#!/usr/bin/env python3
import requests
import json
import time

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzQ5MDk4Nn0.2jlpwM_QiR1Y3Lhaz0Ipk3QqpjDK9Pr_fNCRty15TBk"
BASE_URL = "http://localhost:8000/api/chat"

def send_chat(session_id, user_input, user_name):
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

    response = requests.post(BASE_URL, headers=headers, json=data, stream=True)

    lines = []
    for line in response.iter_lines():
        if line:
            lines.append(line.decode('utf-8'))

    return lines

def parse_response(lines):
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
                    dialogues.append({
                        "speaker": dialogue.get("speaker"),
                        "text": dialogue.get("text")
                    })

                elif data.get("type") == "done":
                    current_stage = data.get("current_stage")
                    is_ended = data.get("is_ended", False)
            except json.JSONDecodeError:
                pass

    return session_id, current_stage, is_ended, dialogues

def test_normal_ending():
    print("="*60)
    print("테스트 1: 일반 엔딩 (렌고쿠 도움)")
    print("="*60)

    conversation = []

    # Turn 1: 시작
    print("\n[Turn 1] 시작...")
    lines = send_chat(None, "시작", "일반엔딩테스트")
    session_id, stage, is_ended, dialogues = parse_response(lines)
    print(f"Session: {session_id}")
    print(f"Stage: {stage}")
    conversation.append({"turn": 1, "input": "시작", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 2: 계속
    print("\n[Turn 2] 계속 진행...")
    lines = send_chat(session_id, "알겠어", "일반엔딩테스트")
    _, stage, is_ended, dialogues = parse_response(lines)
    print(f"Stage: {stage}")
    conversation.append({"turn": 2, "input": "알겠어", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 3: 렌고쿠 도움
    print("\n[Turn 3] 렌고쿠 도움 선택...")
    lines = send_chat(session_id, "렌고쿠를 도와야해", "일반엔딩테스트")
    _, stage, is_ended, dialogues = parse_response(lines)
    print(f"Stage: {stage}")
    conversation.append({"turn": 3, "input": "렌고쿠를 도와야해", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 4-15: 엔딩까지 계속
    for i in range(4, 16):
        print(f"\n[Turn {i}]")
        lines = send_chat(session_id, "계속", "일반엔딩테스트")
        _, stage, is_ended, dialogues = parse_response(lines)
        print(f"Stage: {stage} | Ended: {is_ended}")
        conversation.append({"turn": i, "input": "계속", "stage": stage, "is_ended": is_ended, "dialogues": dialogues})

        if is_ended:
            print("\n=== 엔딩 도달! ===")
            print("마지막 대화:")
            for d in dialogues[-3:]:
                print(f"{d['speaker']}: {d['text']}")
            break
        time.sleep(2)

    return conversation

def test_hidden_ending():
    print("\n\n" + "="*60)
    print("테스트 2: 히든 엔딩 (동료 모으기)")
    print("="*60)

    conversation = []

    # Turn 1: 시작
    print("\n[Turn 1] 시작...")
    lines = send_chat(None, "시작", "히든엔딩테스트")
    session_id, stage, is_ended, dialogues = parse_response(lines)
    print(f"Session: {session_id}")
    print(f"Stage: {stage}")
    conversation.append({"turn": 1, "input": "시작", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 2: 계속
    print("\n[Turn 2] 계속 진행...")
    lines = send_chat(session_id, "알겠어", "히든엔딩테스트")
    _, stage, is_ended, dialogues = parse_response(lines)
    print(f"Stage: {stage}")
    conversation.append({"turn": 2, "input": "알겠어", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 3: 동료 모으기
    print("\n[Turn 3] 동료 모으기 선택...")
    lines = send_chat(session_id, "동료들을 모으자", "히든엔딩테스트")
    _, stage, is_ended, dialogues = parse_response(lines)
    print(f"Stage: {stage}")
    conversation.append({"turn": 3, "input": "동료들을 모으자", "stage": stage, "dialogues": dialogues})
    time.sleep(2)

    # Turn 4-20: 동료 영입 및 엔딩까지
    recruit_inputs = {
        4: "이노스케를 설득해야지",
        6: "젠이츠도 설득하자",
        8: "탄지로에게 도움 요청"
    }

    for i in range(4, 21):
        user_input = recruit_inputs.get(i, "계속")
        print(f"\n[Turn {i}] Input: {user_input}")
        lines = send_chat(session_id, user_input, "히든엔딩테스트")
        _, stage, is_ended, dialogues = parse_response(lines)
        print(f"Stage: {stage} | Ended: {is_ended}")
        conversation.append({"turn": i, "input": user_input, "stage": stage, "is_ended": is_ended, "dialogues": dialogues})

        if is_ended:
            print("\n=== 엔딩 도달! ===")
            print("마지막 대화:")
            for d in dialogues[-3:]:
                print(f"{d['speaker']}: {d['text']}")
            break
        time.sleep(2)

    return conversation

if __name__ == "__main__":
    normal_conv = test_normal_ending()
    hidden_conv = test_hidden_ending()

    # Save results
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "normal_ending": normal_conv,
            "hidden_ending": hidden_conv
        }, f, ensure_ascii=False, indent=2)

    print("\n\n=== 테스트 완료 ===")
    print("결과가 test_results.json에 저장되었습니다.")
