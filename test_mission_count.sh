#!/bin/bash

# Test mission count decrements properly
# Expected: 남은 시도 should go from 3 → 2 → 1 → 0

SESSION_ID="test-mission-count-$(date +%s)"
USER_ID="00000000-0000-0000-0000-000000000001"

echo "=== Testing Mission Count (Session: $SESSION_ID) ==="
echo ""

# Test 1: Start mission
echo "1️⃣ Starting mission with '이노스케'"
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"scenario_id\": \"mugen-train\",
    \"user_name\": \"츠구코\",
    \"message\": \"이노스케\"
  }" | jq -r '.dialogues[] | "\(.speaker): \(.text)"' | grep -E "미션|남은"

echo ""
sleep 2

# Test 2: First persuasion attempt (will fail)
echo "2️⃣ First attempt: '가자 이노스케' (Expected: 남은 시도 2회)"
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"scenario_id\": \"mugen-train\",
    \"user_name\": \"츠구코\",
    \"message\": \"가자 이노스케\"
  }" | jq -r '.dialogues[] | "\(.speaker): \(.text)"' | grep -E "설득|남은|시도"

echo ""
sleep 2

# Test 3: Second persuasion attempt (will fail)
echo "3️⃣ Second attempt: '같이 가자' (Expected: 남은 시도 1회)"
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"scenario_id\": \"mugen-train\",
    \"user_name\": \"츠구코\",
    \"message\": \"같이 가자\"
  }" | jq -r '.dialogues[] | "\(.speaker): \(.text)"' | grep -E "설득|남은|시도"

echo ""
sleep 2

# Test 4: Third persuasion attempt (will fail)
echo "4️⃣ Third attempt: '제발' (Expected: 모든 시도를 소진)"
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_id\": \"$USER_ID\",
    \"scenario_id\": \"mugen-train\",
    \"user_name\": \"츠구코\",
    \"message\": \"제발\"
  }" | jq -r '.dialogues[] | "\(.speaker): \(.text)"' | grep -E "설득|남은|시도|소진"

echo ""
echo "=== Test Complete ==="
