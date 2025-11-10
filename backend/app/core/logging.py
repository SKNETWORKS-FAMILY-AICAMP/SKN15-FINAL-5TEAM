"""
[Core] 구조화된 로깅 시스템 모듈

이 모듈은 애플리케이션 전반에 걸쳐 일관되고 구조화된 로그를 남기기 위한
다양한 유틸리티와 클래스를 제공합니다.

- LayerLogger: 아키텍처 계층(Layer)과 기능(Feature)별로 컨텍스트를 부여하는 로거
- 팩토리 함수: 각 계층에 맞는 로거를 쉽게 생성하는 헬퍼 함수
- 성능 측정 데코레이터: 함수의 실행 시간을 자동으로 측정하고 로깅
- 개발용 헬퍼: 개발 시 디버깅을 돕는 컬러 콘솔 출력 함수
"""
import logging
import sys
from typing import Optional, Dict, Any
import time
from functools import wraps

# ============================================================
# 전역 로깅 기본 설정
# ============================================================
def setup_logging(log_level: str = "INFO"):
    """
    Python의 내장 `logging` 모듈에 대한 전역 설정을 초기화합니다.
    애플리케이션 시작 시 한 번만 호출되어야 합니다.

    Args:
        log_level (str): 전역 로그 레벨 ("DEBUG", "INFO", "WARNING", "ERROR").
                         이 레벨보다 낮은 로그는 무시됩니다.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # 로그를 콘솔(stdout)으로 출력
        ]
    )


# ============================================================
# 계층형 컨텍스트 로거 (Layered Context Logger)
# ============================================================
class LayerLogger:
    """
    아키텍처 계층(Layer)과 기능(Feature) 컨텍스트를 포함하는 구조화된 로거입니다.
    로그 메시지에 `[계층] [기능] [함수명]`과 같은 접두사를 자동으로 추가하여
    로그 추적을 용이하게 합니다.

    Attributes:
        layer (str): 로거가 속한 아키텍처 계층 (예: "CONTROLLER", "USECASE").
        feature (str): 로거가 속한 기능 (예: "Chat", "Auth").
        logger (logging.Logger): 실제 로깅을 수행하는 표준 로거 인스턴스.
    """

    def __init__(self, layer: str, feature: str):
        """
        LayerLogger를 초기화합니다.

        Args:
            layer (str): "CONTROLLER", "USECASE", "REPOSITORY" 등 계층 이름.
            feature (str): "Chat", "User" 등 기능 또는 도메인 이름.
        """
        self.layer = layer
        self.feature = feature
        self.logger = logging.getLogger(f"{layer}.{feature}")

    def _format_message(self, function: str, message: str, **kwargs) -> str:
        """
        로그 메시지에 컨텍스트 정보와 추가 인자를 결합하여 최종 로그 문자열을 생성합니다.
        """
        base = f"[{self.layer}] [{self.feature}] [{function}] {message}"
        if kwargs:
            # 추가 컨텍스트 정보(kwargs)를 'key=value' 형태로 덧붙입니다.
            context = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
            return base + context
        return base

    def debug(self, function: str, message: str, **kwargs):
        """디버그 레벨의 로그를 기록합니다."""
        msg = self._format_message(function, message, **kwargs)
        self.logger.debug(msg)

    def info(self, function: str, message: str, **kwargs):
        """정보 레벨의 로그를 기록합니다."""
        msg = self._format_message(function, message, **kwargs)
        self.logger.info(msg)

    def warning(self, function: str, message: str, **kwargs):
        """경고 레벨의 로그를 기록합니다."""
        msg = self._format_message(function, message, **kwargs)
        self.logger.warning(msg)

    def error(self, function: str, message: str, **kwargs):
        """에러 레벨의 로그를 기록합니다."""
        msg = self._format_message(function, message, **kwargs)
        self.logger.error(msg)

    def exception(self, function: str, message: str, exc: Exception, **kwargs):
        """예외 정보를 스택 트레이스와 함께 기록합니다."""
        msg = self._format_message(function, message, error=str(exc), **kwargs)
        self.logger.exception(msg)


# ============================================================
# 로거 팩토리 함수 (Logger Factory Functions)
# ============================================================
# 각 아키텍처 계층별로 LayerLogger를 쉽게 생성할 수 있도록 돕는 헬퍼 함수들입니다.
def get_controller_logger(feature: str) -> LayerLogger:
    """Controller 계층용 로거를 반환합니다."""
    return LayerLogger("CONTROLLER", feature)

def get_usecase_logger(feature: str) -> LayerLogger:
    """UseCase 계층용 로거를 반환합니다."""
    return LayerLogger("USECASE", feature)

def get_parent_logger(feature: str) -> LayerLogger:
    """Core 또는 Shared 등 상위 계층용 로거를 반환합니다."""
    return LayerLogger("PARENT", feature)

def get_agent_logger(feature: str, agent_name: str) -> LayerLogger:
    """Agent 계층용 로거를 반환합니다."""
    return LayerLogger(f"AGENT.{agent_name.upper()}", feature)

def get_stage_logger(feature: str, stage_name: str) -> LayerLogger:
    """Stage 계층용 로거를 반환합니다."""
    return LayerLogger(f"STAGE.{stage_name.upper()}", feature)

def get_repository_logger(feature: str) -> LayerLogger:
    """Repository 계층용 로거를 반환합니다."""
    return LayerLogger("REPOSITORY", feature)


# ============================================================
# 함수 실행 시간 측정 데코레이터
# ============================================================
def log_execution_time(logger: LayerLogger, function_name: str):
    """
    함수(동기/비동기 모두)의 실행 시간을 측정하고 자동으로 로그를 남기는 데코레이터입니다.

    Args:
        logger (LayerLogger): 시간을 기록할 로거 인스턴스.
        function_name (str): 로그에 표시될 함수 이름.

    Usage:
        @log_execution_time(logger, "my_function")
        async def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000  # ms 단위로 변환
                logger.info(function_name, "Completed", elapsed_ms=f"{elapsed:.2f}")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(function_name, "Failed", elapsed_ms=f"{elapsed:.2f}", error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(function_name, "Completed", elapsed_ms=f"{elapsed:.2f}")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(function_name, "Failed", elapsed_ms=f"{elapsed:.2f}", error=str(e))
                raise

        # 데코레이팅된 함수가 비동기 함수인지 확인하여 적절한 wrapper를 반환합니다.
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x100: # CO_COROUTINE 플래그 확인
            return async_wrapper
        return sync_wrapper
    return decorator


# ============================================================
# 개발용 디버그 프린트 헬퍼
# ============================================================
class Colors:
    """터미널 출력에 사용할 ANSI 컬러 코드입니다."""
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
    개발 환경에서 디버깅 편의를 위해 계층별로 색상을 입혀 콘솔에 출력합니다.

    NOTE: 이 함수는 `print`를 직접 사용하므로, 정식 로깅 시스템을 우회합니다.
          프로덕션 코드에서는 사용을 지양하고, `LayerLogger`를 사용해야 합니다.
    """
    color_map = {
        "CONTROLLER": Colors.BLUE,
        "USECASE": Colors.GREEN,
        "PARENT": Colors.YELLOW,
        "AGENT": Colors.CYAN,
        "STAGE": Colors.HEADER,
        "REPOSITORY": Colors.RED,
    }
    color = color_map.get(layer.split('.')[0], Colors.ENDC)
    base = f"{color}[{layer}]{Colors.ENDC} [{feature}] [{function}] {message}"

    if kwargs:
        context = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
        print(base + context, flush=True)
    else:
        print(base, flush=True)
