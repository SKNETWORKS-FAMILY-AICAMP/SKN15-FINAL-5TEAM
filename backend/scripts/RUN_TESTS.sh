#!/bin/bash
# 테스트 실행 스크립트

echo "======================================"
echo "🧪 Kime Chat Agent 테스트 실행"
echo "======================================"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📍 작업 디렉토리: $SCRIPT_DIR"
echo ""

# 1. 유닛 테스트
echo "========================================"
echo "1️⃣  유닛 테스트 (개별 에이전트)"
echo "========================================"
python tests/test_agents.py
if [ $? -eq 0 ]; then
    echo "✅ 유닛 테스트 통과"
else
    echo "❌ 유닛 테스트 실패"
fi
echo ""

# 2. 통합 테스트
echo "========================================"
echo "2️⃣  통합 테스트 (워크플로우, DB)"
echo "========================================"
python tests/test_integration.py
if [ $? -eq 0 ]; then
    echo "✅ 통합 테스트 통과"
else
    echo "❌ 통합 테스트 실패"
fi
echo ""

# 3. Scene Tools 테스트
echo "========================================"
echo "3️⃣  Scene Tools 테스트"
echo "========================================"
python tests/test_scene_tools.py
if [ $? -eq 0 ]; then
    echo "✅ Scene Tools 테스트 통과"
else
    echo "❌ Scene Tools 테스트 실패"
fi
echo ""

echo "======================================"
echo "🎉 모든 테스트 완료!"
echo "======================================"
