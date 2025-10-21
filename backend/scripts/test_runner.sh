#!/bin/bash
# 통합 테스트 실행 스크립트

set -e  # 오류 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경변수 설정
export USE_LLM=false
export DEBUG=false

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                          ║${NC}"
echo -e "${BLUE}║  🧪 Kime Chat Agent - 백엔드 테스트 실행                   ║${NC}"
echo -e "${BLUE}║                                                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 함수 정의
run_test() {
    local name=$1
    local cmd=$2

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if eval $cmd; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

# 메인 메뉴
if [ "$1" == "all" ] || [ "$1" == "" ]; then
    echo -e "${GREEN}전체 테스트 실행 모드${NC}"
    echo ""

    # 핵심 백엔드 로직
    run_test "1️⃣ 턴 시스템 (8 tests)" \
        "pytest tests/test_turn_system.py -q"

    run_test "2️⃣ 친밀도 시스템 (18 tests)" \
        "pytest tests/test_affinity.py -q"

    run_test "3️⃣ 프로세스 깊이 (3 tests)" \
        "pytest tests/test_process_depth.py -q"

    # 엣지케이스
    run_test "4️⃣ 친밀도 경계값 (35 tests)" \
        "pytest tests/test_affinity_edge_cases.py -q"

    run_test "5️⃣ 미션 관리자 종합 (17 tests)" \
        "pytest tests/test_mission_manager_comprehensive.py -q"

    run_test "6️⃣ 친밀도 시스템 종합 (24 tests)" \
        "pytest tests/test_affinity_system_comprehensive.py -q"

    run_test "7️⃣ 미커버 경로 테스트 (12 tests)" \
        "pytest tests/test_uncovered_paths.py -q"

    # 커버리지
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ 📊 커버리지 리포트${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    pytest tests/test_turn_system.py \
           tests/test_affinity.py \
           tests/test_process_depth.py \
           tests/test_affinity_edge_cases.py \
           tests/test_mission_manager_comprehensive.py \
           tests/test_affinity_system_comprehensive.py \
           tests/test_uncovered_paths.py \
           --cov=affinity_system \
           --cov=mission_manager \
           --cov=agent_state_enhanced \
           --cov-report=term \
           --cov-report=html \
           -q

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ 전체 테스트 완료!                                      ║${NC}"
    echo -e "${GREEN}║  📁 HTML 리포트: htmlcov/index.html                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

elif [ "$1" == "core" ]; then
    echo -e "${GREEN}핵심 로직 테스트만 실행 (29 tests)${NC}"
    pytest tests/test_turn_system.py \
           tests/test_affinity.py \
           tests/test_process_depth.py \
           -v

elif [ "$1" == "edge" ]; then
    echo -e "${GREEN}엣지케이스 테스트만 실행 (76 tests)${NC}"
    pytest tests/test_affinity_edge_cases.py \
           tests/test_mission_manager_comprehensive.py \
           tests/test_affinity_system_comprehensive.py \
           -v

elif [ "$1" == "coverage" ]; then
    echo -e "${GREEN}커버리지 리포트 생성${NC}"
    pytest tests/test_turn_system.py \
           tests/test_affinity.py \
           tests/test_process_depth.py \
           tests/test_affinity_edge_cases.py \
           tests/test_mission_manager_comprehensive.py \
           tests/test_affinity_system_comprehensive.py \
           --cov=affinity_system \
           --cov=mission_manager \
           --cov=agent_state_enhanced \
           --cov-report=html \
           --cov-report=term

    echo ""
    echo -e "${GREEN}📁 HTML 리포트: htmlcov/index.html${NC}"

elif [ "$1" == "quick" ]; then
    echo -e "${GREEN}빠른 검증 (핵심 로직만)${NC}"
    pytest tests/test_turn_system.py \
           tests/test_affinity.py \
           tests/test_process_depth.py \
           -q

elif [ "$1" == "verbose" ]; then
    echo -e "${GREEN}상세 모드 실행${NC}"
    pytest tests/test_turn_system.py \
           tests/test_affinity.py \
           tests/test_process_depth.py \
           tests/test_affinity_edge_cases.py \
           tests/test_mission_manager_comprehensive.py \
           tests/test_affinity_system_comprehensive.py \
           -vv

elif [ "$1" == "help" ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo -e "${BLUE}사용법:${NC}"
    echo "  ./test_runner.sh [옵션]"
    echo ""
    echo -e "${YELLOW}옵션:${NC}"
    echo "  all       - 전체 테스트 + 커버리지 (기본값)"
    echo "  core      - 핵심 로직만 (29 tests)"
    echo "  edge      - 엣지케이스만 (76 tests)"
    echo "  coverage  - 커버리지 리포트만"
    echo "  quick     - 빠른 검증 (핵심만)"
    echo "  verbose   - 상세 출력"
    echo "  help      - 이 도움말"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo "  ./test_runner.sh           # 전체 실행"
    echo "  ./test_runner.sh core      # 핵심만"
    echo "  ./test_runner.sh coverage  # 커버리지만"

else
    echo -e "${RED}알 수 없는 옵션: $1${NC}"
    echo "도움말: ./test_runner.sh help"
    exit 1
fi
