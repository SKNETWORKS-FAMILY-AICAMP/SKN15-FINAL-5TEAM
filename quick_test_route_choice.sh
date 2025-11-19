#!/bin/bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzQ5MzAwM30.syGnJgGQu5Y0tQkXmX16KXvXcpU-SECanGyMp-oRPiY"

echo "=== Turn 1: 시작 ==="
RESP1=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"scenario_id": "mugen-train", "user_input": "시작", "user_name": "빠른테스트"}')

SESSION=$(echo "$RESP1" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Session: $SESSION"

sleep 2

# Progress quickly to ROUTE_CHOICE
for i in 2 3 4 5 6; do
  echo "=== Turn $i: 계속 ==="
  curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"scenario_id\": \"mugen-train\", \"session_id\": \"$SESSION\", \"user_input\": \"계속\", \"user_name\": \"빠른테스트\"}" | grep -o '"current_stage":"[^"]*"' | head -1
  sleep 2
done

echo ""
echo "=== Turn 7: ROUTE_CHOICE 진입 - 대화 확인 ==="
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"scenario_id\": \"mugen-train\", \"session_id\": \"$SESSION\", \"user_input\": \"계속\", \"user_name\": \"빠른테스트\"}" > /tmp/route_choice_response.txt

echo "Current stage:"
grep -o '"current_stage":"[^"]*"' /tmp/route_choice_response.txt | head -1

echo ""
echo "Dialogues:"
cat /tmp/route_choice_response.txt | python3 -c "
import sys, json
for line in sys.stdin:
    if line.startswith('data: '):
        try:
            data = json.loads(line[6:])
            if data.get('type') == 'dialogue':
                d = data.get('dialogue', {})
                print(f\"{d.get('speaker')}: {d.get('text')}\")
        except: pass
"

echo ""
echo "Session ID: $SESSION"
