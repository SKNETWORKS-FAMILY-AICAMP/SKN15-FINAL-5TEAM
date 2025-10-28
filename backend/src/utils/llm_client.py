"""
LLM 클라이언트 모듈 - OpenAI/Anthropic API를 이용한 통합 클라이언트
- 모든 에이전트에서 공통으로 사용
- config_loader를 통한 동적 provider 설정
- 프롬프트 템플릿 관리
- 응답 파싱 및 에러 처리
"""

import os
import threading
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# config_loader import (optional)
try:
    from src.utils.config_loader import ConfigLoader
    _config_available = True
except ImportError:
    _config_available = False


# Thread-safe global variable lock
_global_lock = threading.Lock()


import time
from collections import deque

class RateLimiter:
    """API Rate Limiter"""
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = threading.Lock()

    def acquire(self):
        """요청 허가 획득 (필요시 대기)"""
        with self._lock:
            now = time.time()

            # 오래된 요청 제거
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            # Rate limit 체크
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    return self.acquire()

            self.requests.append(now)

# Global rate limiter instance
_llm_rate_limiter = RateLimiter(max_requests=60, time_window=60)


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 provider: Optional[str] = None, enable_caching: bool = True):
        """
        LLM 클라이언트 초기화

        Args:
            api_key: API 키 (없으면 환경변수에서 가져옴)
            model: 사용할 모델 (없으면 config에서 가져옴, 기본: gpt-4o-mini)
            provider: LLM 공급자 ("openai" or "anthropic", 없으면 config에서 가져옴)
            enable_caching: 응답 캐싱 활성화 (기본: True)
        """
        # config_loader에서 설정 읽기 (가능한 경우)
        agent_configs: Dict[str, Dict[str, Any]] = {}
        default_temperature: Optional[float] = None
        default_max_tokens: Optional[int] = None

        if _config_available and (provider is None or model is None):
            try:
                config = ConfigLoader()
                settings = config.get_settings()
                llm_config = settings.get("llm_client", {})
                if provider is None:
                    provider = llm_config.get("provider", "openai")
                if model is None:
                    model = llm_config.get("default_model", "gpt-4o-mini")
                default_temperature = llm_config.get("temperature")
                default_max_tokens = llm_config.get("max_tokens")

                raw_agent_cfg = llm_config.get("agent_configs") or llm_config.get("agent_models") or {}
                if isinstance(raw_agent_cfg, dict):
                    for agent_key, cfg in raw_agent_cfg.items():
                        if not isinstance(agent_key, str):
                            continue
                        agent_name = agent_key.strip()
                        if not agent_name:
                            continue

                        if isinstance(cfg, dict):
                            agent_configs[agent_name] = dict(cfg)
                        elif isinstance(cfg, str):
                            if cfg.strip():
                                agent_configs[agent_name] = {"model": cfg.strip()}
                        else:
                            continue
            except Exception:
                # config 로드 실패 시 기본값 사용
                provider = provider or "openai"
                model = model or "gpt-4o-mini"
                agent_configs = {}
                default_temperature = None
                default_max_tokens = None
        else:
            provider = provider or "openai"
            model = model or "gpt-4o-mini"
            agent_configs = {}
            default_temperature = None
            default_max_tokens = None

        self.provider = provider
        self.model = model
        self.agent_configs = agent_configs
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

        # OpenAI 클라이언트 초기화
        if self.provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. 환경변수 또는 초기화 시 전달하세요.")
            self.client = OpenAI(api_key=self.api_key)
        else:
            raise ValueError(f"지원하지 않는 LLM 공급자입니다: {self.provider}")

        self.enable_caching = enable_caching
        self.cache: Dict[str, str] = {}  # 프롬프트 해시 -> 응답 캐시
        self.call_count = 0  # LLM 호출 횟수

    def _get_cache_key(self, system_prompt: str, user_prompt: str, temperature: float, model: str) -> str:
        """캐시 키 생성"""
        import hashlib
        cache_str = f"{system_prompt}|{user_prompt}|{temperature}|{model}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get_agent_setting(self, agent: str, key: str, default: Any = None) -> Any:
        cfg = self.agent_configs.get(agent, {}) if agent else {}
        if key in cfg:
            return cfg[key]
        if key == "temperature" and self.default_temperature is not None:
            return self.default_temperature
        if key == "max_tokens" and self.default_max_tokens is not None:
            return self.default_max_tokens
        if key == "model" and cfg.get("model"):
            return cfg["model"]
        return default

    def _resolve_model(self, agent: Optional[str], explicit_model: Optional[str]) -> str:
        if isinstance(explicit_model, str) and explicit_model.strip():
            return explicit_model.strip()
        if agent:
            cfg = self.agent_configs.get(agent, {})
            model_override = cfg.get("model")
            if isinstance(model_override, str) and model_override.strip():
                return model_override.strip()
        return self.model

    def _resolve_temperature(self, agent: Optional[str], explicit_temperature: Optional[float]) -> float:
        if explicit_temperature is not None:
            return float(explicit_temperature)
        if agent:
            cfg_temp = self.agent_configs.get(agent, {}).get("temperature")
            if isinstance(cfg_temp, (int, float)):
                return float(cfg_temp)
        if isinstance(self.default_temperature, (int, float)):
            return float(self.default_temperature)
        return 0.7

    def _resolve_max_tokens(self, agent: Optional[str], explicit_max_tokens: Optional[int]) -> Optional[int]:
        if explicit_max_tokens is not None:
            return int(explicit_max_tokens)
        if agent:
            cfg_tokens = self.agent_configs.get(agent, {}).get("max_tokens")
            if isinstance(cfg_tokens, int):
                return cfg_tokens
        if isinstance(self.default_max_tokens, int):
            return self.default_max_tokens
        return None

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        use_cache: bool = True,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        LLM 호출 (일반 텍스트 응답)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 창의성 조절 (0.0~1.0)
            max_tokens: 최대 토큰 수
            response_format: 응답 포맷 (예: {"type": "json_object"})
            use_cache: 캐시 사용 여부 (기본: True)

        Returns:
            LLM 응답 텍스트
        """
        target_model = self._resolve_model(agent, model)
        resolved_temperature = self._resolve_temperature(agent, temperature)
        resolved_max_tokens = self._resolve_max_tokens(agent, max_tokens)

        # 캐시 확인
        if self.enable_caching and use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temperature, target_model)
            if cache_key in self.cache:
                return self.cache[cache_key]

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": resolved_temperature,
            }

            if resolved_max_tokens is not None:
                kwargs["max_tokens"] = resolved_max_tokens

            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            result = response.choices[0].message.content

            # 호출 횟수 증가
            self.call_count += 1

            # 캐시 저장
            if self.enable_caching and use_cache:
                cache_key = self._get_cache_key(system_prompt, user_prompt, resolved_temperature, target_model)
                self.cache[cache_key] = result

            return result

        except Exception as e:
            print(f"LLM 호출 중 오류 발생: {str(e)}")
            raise

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        LLM 호출 (JSON 응답)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 창의성 조절
            max_tokens: 최대 토큰 수

        Returns:
            파싱된 JSON 딕셔너리
        """
        try:
            response_text = self.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                agent=agent,
                model=model,
            )

            # JSON 파싱
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {str(e)}")
            print(f"응답 텍스트: {response_text}")
            raise
        except Exception as e:
            print(f"LLM JSON 호출 중 오류 발생: {str(e)}")
            raise

    def call_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_response: Any,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Any:
        """
        LLM 호출 (실패 시 폴백 응답 반환)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            fallback_response: 실패 시 반환할 기본값
            temperature: 창의성 조절
            max_tokens: 최대 토큰 수

        Returns:
            LLM 응답 또는 폴백 응답
        """
        try:
            return self.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                agent=agent,
                model=model,
            )
        except Exception as e:
            print(f"LLM 호출 실패, 폴백 응답 사용: {str(e)}")
            return fallback_response


# 전역 LLM 클라이언트 인스턴스 (싱글톤 패턴)
_llm_client_instance: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    """
    전역 LLM 클라이언트 인스턴스 가져오기 (싱글톤, Thread-safe)
    """
    global _llm_client_instance

    with _global_lock:
        if _llm_client_instance is None:
            _llm_client_instance = LLMClient()

    return _llm_client_instance

def set_llm_client(client: LLMClient):
    """
    전역 LLM 클라이언트 인스턴스 설정 (Thread-safe)
    """
    global _llm_client_instance

    with _global_lock:
        _llm_client_instance = client


# 테스트용 함수
def test_llm_client():
    """LLM 클라이언트 테스트"""
    print("=== LLM 클라이언트 테스트 ===")

    # 환경변수에서 API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("export OPENAI_API_KEY='your-api-key' 를 실행하세요.")
        return

    try:
        client = get_llm_client()

        # 테스트 1: 일반 텍스트 응답
        print("\n테스트 1: 일반 텍스트 응답")
        response1 = client.call(
            system_prompt="너는 친근한 AI 어시스턴트야.",
            user_prompt="안녕! 간단히 인사해줘.",
            temperature=0.7,
            max_tokens=50
        )
        print(f"응답: {response1}")

        # 테스트 2: JSON 응답
        print("\n테스트 2: JSON 응답")
        response2 = client.call_json(
            system_prompt="당신은 사용자 입력을 분석하는 AI입니다. JSON 형식으로만 응답하세요.",
            user_prompt="""
다음 텍스트를 분석하세요:
"혈귀가 나타났다! 함께 싸우자!"

다음 JSON 형식으로 응답하세요:
{
  "classification": "on_topic 또는 off_topic",
  "intent": "game_action 또는 casual_chat",
  "confidence": 0.0~1.0 사이의 숫자
}
""",
            temperature=0.3
        )
        print(f"JSON 응답: {json.dumps(response2, ensure_ascii=False, indent=2)}")

        # 테스트 3: 폴백 응답
        print("\n테스트 3: 폴백 응답 (정상 작동)")
        response3 = client.call_with_fallback(
            system_prompt="너는 게임 캐릭터야.",
            user_prompt="간단히 대사 한 줄만 해줘.",
            fallback_response="기본 대사입니다.",
            temperature=0.8,
            max_tokens=30
        )
        print(f"응답: {response3}")

        print("\n=== 모든 테스트 완료 ===")

    except Exception as e:
        print(f"테스트 실패: {str(e)}")


if __name__ == "__main__":
    test_llm_client()
