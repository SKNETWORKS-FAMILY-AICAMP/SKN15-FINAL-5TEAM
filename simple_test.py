#!/usr/bin/env python3
import requests
import json
import time

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzQ5MzAwM30.syGnJgGQu5Y0tQkXmX16KXvXcpU-SECanGyMp-oRPiY"
BASE_URL = "http://localhost:8000/api/chat"
SESSION = "525160bf-9e92-43c3-8655-b6924fe589a5"

def send_and_parse(user_input):
    """Send request and parse response"""
    data = {
        "scenario_id": "mugen-train",
        "session_id": SESSION,
        "user_input": user_input,
        "user_name": "SimpleTest"
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    response = requests.post(BASE_URL, headers=headers, json=data, stream=True, timeout=30)

    stage = None
    dialogues = []

    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('data: '):
                try:
                    data = json.loads(decoded[6:])
                    if data.get('type') == 'metadata':
                        stage = data.get('current_stage')
                    elif data.get('type') == 'dialogue':
                        d = data.get('dialogue', {})
                        dialogues.append(f"{d.get('speaker')}: {d.get('text')}")
                    elif data.get('type') == 'done':
                        stage = data.get('current_stage')
                except:
                    pass

    return stage, dialogues

# Progress to ROUTE_CHOICE
for i in range(2, 7):
    print(f"\n=== Turn {i}: 계속 ===")
    stage, dialogues = send_and_parse("계속")
    print(f"Stage: {stage}")
    if dialogues:
        for d in dialogues[-2:]:  # Show last 2 dialogues
            print(f"  {d}")
    time.sleep(2)

# ROUTE_CHOICE turn
print(f"\n=== Turn 7: ROUTE_CHOICE ===")
stage, dialogues = send_and_parse("계속")
print(f"Stage: {stage}")
print("\n탄지로 대사 확인 (질문을 하는지?)")
for d in dialogues:
    if 'tanjiro' in d.lower() or '탄지로' in d:
        print(f"  → {d}")

# Save to file
with open("simple_test_result.txt", "w", encoding="utf-8") as f:
    f.write(f"Stage: {stage}\n\n")
    f.write("All dialogues:\n")
    for d in dialogues:
        f.write(f"{d}\n")

print("\n✓ Result saved to simple_test_result.txt")
