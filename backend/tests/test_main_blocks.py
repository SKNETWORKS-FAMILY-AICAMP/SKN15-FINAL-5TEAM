#!/usr/bin/env python3
"""
__main__ 블록 테스트 - Coverage 향상용

affinity_system.py, mission_manager.py의 __main__ 블록 커버리지를 높이기 위한 테스트
"""
import subprocess
import sys


class TestMainBlocks:
    """__main__ 블록 실행 테스트"""

    def test_affinity_system_main_block(self):
        """affinity_system.py의 __main__ 블록 실행"""
        result = subprocess.run(
            [sys.executable, "affinity_system.py"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 정상 실행 확인
        assert result.returncode == 0

        # 예상 출력 확인
        assert "친밀도 시스템 테스트" in result.stdout
        assert "탄지로 초기 친밀도" in result.stdout
        assert "이노스케 초기 친밀도" in result.stdout

    def test_mission_manager_main_block(self):
        """mission_manager.py의 __main__ 블록 실행"""
        result = subprocess.run(
            [sys.executable, "mission_manager.py"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # 정상 실행 확인
        assert result.returncode == 0

        # 예상 출력 확인
        assert "미션 관리자 테스트" in result.stdout
        assert "올바른 순서" in result.stdout
        assert "inosuke" in result.stdout
        assert "zenitsu" in result.stdout
