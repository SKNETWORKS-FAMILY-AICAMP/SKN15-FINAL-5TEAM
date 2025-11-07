"""
디버그 로깅 유틸리티
"""
import os
import sys


class DebugLogger:
    """디버그 로거 클래스"""
    def __init__(self, enabled: bool = False, verbose: bool = False):
        self.enabled = enabled or os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]
        self.verbose = verbose

    def log(self, category: str, event: str, data: dict = None):
        """로그 출력"""
        if self.enabled:
            msg = f"[{category}] {event}"
            if data and self.verbose:
                msg += f": {data}"
            print(msg, flush=True, file=sys.stderr)

    def error(self, msg: str):
        """에러 로그"""
        if self.enabled:
            print(f"[ERROR] {msg}", flush=True, file=sys.stderr)


def get_logger(enabled: bool = False, verbose: bool = False) -> DebugLogger:
    """
    디버그 로거 인스턴스 반환

    Args:
        enabled: 로깅 활성화 여부
        verbose: 상세 로깅 여부

    Returns:
        DebugLogger 인스턴스
    """
    return DebugLogger(enabled=enabled, verbose=verbose)


def debug_log(msg: str, force: bool = False):
    """
    디버그 로그 출력

    Args:
        msg: 로그 메시지
        force: True면 DEBUG 환경변수 무시하고 무조건 출력
    """
    if force or os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]:
        print(msg, flush=True, file=sys.stderr if not force else sys.stdout)
