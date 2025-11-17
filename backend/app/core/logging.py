"""
Core Logging System
레이어별, Feature별 구조화된 로깅
"""
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json

# ============================================================
# 로깅 설정
# ============================================================

def setup_logging(log_level: str = "INFO"):
    """
    애플리케이션 전역 로깅 설정

    Args:
        log_level: "DEBUG", "INFO", "WARNING", "ERROR"
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


# ============================================================
# 레이어별 로거
# ============================================================

class LayerLogger:
    """
    레이어별 구조화된 로거

    Usage:
        logger = LayerLogger("CONTROLLER", "Chat")
        logger.info("create_chat", "Request received", session_id="abc123")
    """

    def __init__(self, layer: str, feature: str):
        """
        Args:
            layer: "CONTROLLER", "USECASE", "PARENT", "AGENT", "STAGE", "REPOSITORY"
            feature: "Chat", "Session", "User" etc.
        """
        self.layer = layer
        self.feature = feature
        self.logger = logging.getLogger(f"{layer}.{feature}")

    def _format_message(
        self,
        function: str,
        message: str,
        **kwargs
    ) -> str:
        """로그 메시지 포맷팅"""
        base = f"[{self.layer}] [{self.feature}] [{function}] {message}"

        if kwargs:
            # 추가 컨텍스트를 JSON으로 포맷
            context = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
            return base + context

        return base

    def debug(self, function: str, message: str, **kwargs):
        """디버그 레벨 로그"""
        msg = self._format_message(function, message, **kwargs)
        self.logger.debug(msg)

    def info(self, function: str, message: str, **kwargs):
        """정보 레벨 로그"""
        msg = self._format_message(function, message, **kwargs)
        self.logger.info(msg)

    def warning(self, function: str, message: str, **kwargs):
        """경고 레벨 로그"""
        msg = self._format_message(function, message, **kwargs)
        self.logger.warning(msg)

    def error(self, function: str, message: str, **kwargs):
        """에러 레벨 로그"""
        msg = self._format_message(function, message, **kwargs)
        self.logger.error(msg)

    def exception(self, function: str, message: str, exc: Exception, **kwargs):
        """예외 로그 (스택 트레이스 포함)"""
        msg = self._format_message(function, message, error=str(exc), **kwargs)
        self.logger.exception(msg)


# ============================================================
# 레이어별 로거 팩토리
# ============================================================

def get_controller_logger(feature: str) -> LayerLogger:
    """Controller 레이어 로거"""
    return LayerLogger("CONTROLLER", feature)


def get_usecase_logger(feature: str) -> LayerLogger:
    """UseCase 레이어 로거"""
    return LayerLogger("USECASE", feature)


def get_parent_logger(feature: str) -> LayerLogger:
    """Parent 레이어 로거"""
    return LayerLogger("PARENT", feature)


def get_agent_logger(feature: str, agent_name: str) -> LayerLogger:
    """Agent 레이어 로거 (Guardrail, Router, Children)"""
    return LayerLogger(f"AGENT.{agent_name.upper()}", feature)


def get_stage_logger(feature: str, stage_name: str) -> LayerLogger:
    """Stage 레이어 로거 (Mission, Scene, Narrative)"""
    return LayerLogger(f"STAGE.{stage_name.upper()}", feature)


def get_repository_logger(feature: str) -> LayerLogger:
    """Repository 레이어 로거"""
    return LayerLogger("REPOSITORY", feature)


def get_logger(name: str) -> LayerLogger:
    """
    범용 로거 (기존 코드 호환성)

    Args:
        name: 로거 이름 (보통 __name__)

    Returns:
        LayerLogger 인스턴스
    """
    # name이 모듈 경로인 경우 (예: app.features.chat.middleware.mode_guard)
    # 마지막 부분을 feature로 사용
    parts = name.split('.')
    if len(parts) > 1:
        feature = parts[-1]
    else:
        feature = name

    return LayerLogger("GENERAL", feature)


# ============================================================
# 성능 측정 데코레이터
# ============================================================

import time
from functools import wraps

def log_execution_time(logger: LayerLogger, function_name: str):
    """
    함수 실행 시간 측정 및 로깅

    Usage:
        @log_execution_time(logger, "create_dialogue")
        async def create_dialogue(self, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(function_name, f"Completed", elapsed_ms=f"{elapsed:.2f}")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(function_name, f"Failed", elapsed_ms=f"{elapsed:.2f}", error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(function_name, f"Completed", elapsed_ms=f"{elapsed:.2f}")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(function_name, f"Failed", elapsed_ms=f"{elapsed:.2f}", error=str(e))
                raise

        # async 함수면 async_wrapper, 아니면 sync_wrapper
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x100:
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================
# 개발용 프린트 헬퍼 (컬러)
# ============================================================

class Colors:
    """터미널 컬러 코드"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_layer_debug(layer: str, feature: str, function: str, message: str, **kwargs):
    """
    개발용 컬러 프린트 (디버깅 편의)

    레이어별 색상:
    - CONTROLLER: 파란색
    - USECASE: 초록색
    - PARENT: 노란색
    - AGENT: 시안색
    - STAGE: 마젠타색
    - REPOSITORY: 빨간색
    """
    color_map = {
        "CONTROLLER": Colors.BLUE,
        "USECASE": Colors.GREEN,
        "PARENT": Colors.YELLOW,
        "AGENT": Colors.CYAN,
        "STAGE": Colors.HEADER,
        "REPOSITORY": Colors.RED,
    }

    color = color_map.get(layer, Colors.ENDC)

    base = f"{color}[{layer}]{Colors.ENDC} [{feature}] [{function}] {message}"

    if kwargs:
        context = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
        print(base + context, flush=True)
    else:
        print(base, flush=True)
