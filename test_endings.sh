#!/bin/bash

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzQ5MDk4Nn0.2jlpwM_QiR1Y3Lhaz0Ipk3QqpjDK9Pr_fNCRty15TBk"

function send_chat() {
    local session=$1
    local input=$2
    local user=$3

    if [ -z "$session" ]; then
        curl -s -X POST http://localhost:8000/api/chat \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $TOKEN" \
          -d "{\"scenario_id\": \"mugen-train\", \"user_input\": \"$input\", \"user_name\": \"$user\"}"
    else
        curl -s -X POST http://localhost:8000/api/chat \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $TOKEN" \
          -d "{\"scenario_id\": \"mugen-train\", \"session_id\": \"$session\", \"user_input\": \"$input\", \"user_name\": \"$user\"}"
    fi
}

function extract_session() {
    grep -o '"session_id":"[^"]*"' | head -1 | cut -d'"' -f4
}

function extract_stage() {
    grep -o '"current_stage":"[^"]*"' | head -1 | cut -d'"' -f4
}

function extract_dialogues() {
    grep '"speaker"' | sed 's/.*"speaker":"\([^"]*\)".*/\1: /' | tr '\n' ' '
    echo
    grep '"text"' | sed 's/.*"text":"\([^"]*\)".*/  \1/' | head -3
}

echo "================================"
echo "테스트 1: 일반 엔딩 (렌고쿠 도움)"
echo "================================"

echo -e "\n[Turn 1] 시작..."
RESPONSE=$(send_chat "" "시작" "일반엔딩테스트")
SESSION=$(echo "$RESPONSE" | extract_session)
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Session: $SESSION"
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 2] 계속 진행..."
RESPONSE=$(send_chat "$SESSION" "알겠어" "일반엔딩테스트")
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 3] 렌고쿠 도움 선택..."
RESPONSE=$(send_chat "$SESSION" "렌고쿠를 도와야해" "일반엔딩테스트")
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 4-10] 계속 진행하여 엔딩까지..."
for i in {4..10}; do
    echo -e "\n[Turn $i]"
    RESPONSE=$(send_chat "$SESSION" "계속" "일반엔딩테스트")
    STAGE=$(echo "$RESPONSE" | extract_stage)
    IS_ENDED=$(echo "$RESPONSE" | grep -o '"is_ended":[^,}]*' | cut -d':' -f2)
    echo "Stage: $STAGE | Ended: $IS_ENDED"

    if [ "$IS_ENDED" = "true" ]; then
        echo -e "\n=== 엔딩 도달! ==="
        echo "$RESPONSE" | extract_dialogues
        break
    fi
    sleep 2
done

echo -e "\n\n================================"
echo "테스트 2: 히든 엔딩 (동료 모으기)"
echo "================================"

echo -e "\n[Turn 1] 시작..."
RESPONSE=$(send_chat "" "시작" "히든엔딩테스트")
SESSION=$(echo "$RESPONSE" | extract_session)
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Session: $SESSION"
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 2] 계속 진행..."
RESPONSE=$(send_chat "$SESSION" "알겠어" "히든엔딩테스트")
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 3] 동료 모으기 선택..."
RESPONSE=$(send_chat "$SESSION" "동료들을 모으자" "히든엔딩테스트")
STAGE=$(echo "$RESPONSE" | extract_stage)
echo "Stage: $STAGE"

sleep 2

echo -e "\n[Turn 4-15] 동료 영입 및 엔딩까지..."
for i in {4..15}; do
    echo -e "\n[Turn $i]"

    # 동료 영입 시도
    if [ $i -eq 4 ]; then
        INPUT="이노스케야 같이 가자"
    elif [ $i -eq 6 ]; then
        INPUT="젠이츠도 설득해야지"
    else
        INPUT="계속"
    fi

    RESPONSE=$(send_chat "$SESSION" "$INPUT" "히든엔딩테스트")
    STAGE=$(echo "$RESPONSE" | extract_stage)
    IS_ENDED=$(echo "$RESPONSE" | grep -o '"is_ended":[^,}]*' | cut -d':' -f2)
    echo "Stage: $STAGE | Ended: $IS_ENDED"

    if [ "$IS_ENDED" = "true" ]; then
        echo -e "\n=== 엔딩 도달! ==="
        echo "$RESPONSE" | extract_dialogues
        break
    fi
    sleep 2
done

echo -e "\n\n=== 테스트 완료 ==="
