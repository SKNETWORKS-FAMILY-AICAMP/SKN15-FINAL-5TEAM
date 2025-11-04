# LLM Streaming 구현 가이드

**작성일**: 2025-11-04
**상태**: 구현 준비 완료
**예상 효과**: 사용자 체감 속도 90% 향상

---

## 개요

LLM Streaming은 AI 응답을 실시간으로 전송하여 사용자 대기 시간을 대폭 줄입니다.

### 현재 vs Streaming

| 구분 | 현재 (일괄 응답) | Streaming |
|------|-----------------|-----------|
| 첫 응답 | 5-15초 후 | 0.5-1초 후 |
| 사용자 경험 | 빈 화면 대기 | 타이핑 효과 |
| 타임아웃 위험 | 있음 | 없음 |

---

## Backend 구현

### 1. Streaming 엔드포인트 추가

`backend/api_server.py`에 추가:

```python
from fastapi.responses import StreamingResponse
import asyncio

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    스트리밍 채팅 엔드포인트 (Server-Sent Events)
    """
    async def generate_response():
        try:
            # 초기 상태 생성
            initial_state = create_initial_graph_state(
                scenario_id=req.scenario_id,
                user_input=req.user_input,
                user_name=req.user_name or "익명",
                user_id=req.user_id,
                session_id=req.session_id
            )

            # 워크플로우 생성
            workflow = create_workflow()
            graph = workflow.compile()

            # Streaming 실행
            async for event in graph.astream(initial_state):
                # AI 응답 추출
                if "messages" in event:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content'):
                        chunk_data = {
                            "type": "message",
                            "content": last_message.content,
                            "speaker": getattr(last_message, 'name', 'AI')
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\\n\\n"
                        await asyncio.sleep(0)  # 이벤트 루프 양보

            # 완료 신호
            yield f"data: {json.dumps({'type': 'done'})}\\n\\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_data)}\\n\\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
            "Connection": "keep-alive"
        }
    )
```

### 2. 기존 /api/chat 유지

기존 엔드포인트는 호환성을 위해 유지하고, 새로운 `/api/chat/stream`을 추가하는 방식입니다.

---

## Frontend 구현

### 1. API 클라이언트 함수

`front/src/services/api.ts`에 추가:

```typescript
export interface StreamCallbacks {
  onMessage: (content: string, speaker: string) => void
  onError: (error: string) => void
  onComplete: () => void
}

export function chatStream(
  scenarioId: string,
  userInput: string,
  userName: string,
  callbacks: StreamCallbacks
): EventSource {
  const url = new URL(`${API_URL}/api/chat/stream`)

  const params = new URLSearchParams({
    scenario_id: scenarioId,
    user_input: userInput,
    user_name: userName
  })

  const eventSource = new EventSource(`${url}?${params}`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'message':
          callbacks.onMessage(data.content, data.speaker)
          break
        case 'done':
          eventSource.close()
          callbacks.onComplete()
          break
        case 'error':
          eventSource.close()
          callbacks.onError(data.message)
          break
      }
    } catch (error) {
      console.error('Failed to parse SSE data:', error)
    }
  }

  eventSource.onerror = (error) => {
    console.error('EventSource error:', error)
    eventSource.close()
    callbacks.onError('Connection error')
  }

  return eventSource
}
```

### 2. React Component 수정

`front/src/components/ChatInterface.tsx`:

```typescript
import { useState, useRef } from 'react'
import { chatStream } from '../services/api'

function ChatInterface() {
  const [streamedMessage, setStreamedMessage] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const handleSendMessage = (message: string) => {
    setStreamedMessage('')  // 초기화
    setIsStreaming(true)

    eventSourceRef.current = chatStream(
      scenarioId,
      message,
      userName,
      {
        // onMessage: 실시간으로 메시지 누적
        onMessage: (content, speaker) => {
          setStreamedMessage(prev => prev + content)
        },

        // onError: 에러 처리
        onError: (error) => {
          console.error('Stream error:', error)
          setIsStreaming(false)
          setError(error)
        },

        // onComplete: 완료 처리
        onComplete: () => {
          setIsStreaming(false)
          console.log('Stream complete')
          // 최종 메시지 저장, UI 업데이트 등
        }
      }
    )
  }

  const handleCancelStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      setIsStreaming(false)
    }
  }

  return (
    <div>
      {/* 스트리밍 메시지 표시 */}
      {isStreaming && (
        <div className="streaming-message">
          {streamedMessage}
          <span className="cursor-blink">▊</span>
        </div>
      )}

      {/* 취소 버튼 */}
      {isStreaming && (
        <button onClick={handleCancelStream}>
          Stop Generation
        </button>
      )}
    </div>
  )
}
```

---

## 테스트 방법

### 1. curl 테스트

```bash
curl -N http://localhost:8000/api/chat/stream?scenario_id=train&user_input=안녕&user_name=테스트

# 출력 예시:
# data: {"type":"message","content":"안녕하세요","speaker":"AI"}
#
# data: {"type":"message","content":" 반갑습니다","speaker":"AI"}
#
# data: {"type":"done"}
```

### 2. 브라우저 DevTools

Network 탭에서 `event-stream` 타입 확인

### 3. 성능 비교

```bash
# Before (일괄 응답)
time curl -X POST http://localhost:8000/api/chat ...
# 응답: 12.5초

# After (Streaming)
time curl -N http://localhost:8000/api/chat/stream ...
# 첫 청크: 0.8초
```

---

## 주의사항

### 1. CORS 설정

```python
# api_server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # SSE 헤더 노출 필요
)
```

### 2. Nginx 설정 (프로덕션)

```nginx
location /api/chat/stream {
    proxy_pass http://backend;
    proxy_buffering off;  # 중요!
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

### 3. 타임아웃 설정

```python
# Uvicorn 시작 시
uvicorn api_server:app --timeout-keep-alive 300
```

---

## 예상 효과

### 사용자 경험

| 지표 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 첫 응답 시간 | 5-15초 | 0.5-1초 | **93% ↓** |
| 체감 대기감 | 매우 높음 | 낮음 | **대폭 개선** |
| 타임아웃 발생 | 있음 | 없음 | **완전 제거** |

### 기술적 이점

- Connection 유지로 재연결 오버헤드 감소
- 부분 응답으로 사용자 피드백 빠름
- 장시간 응답에도 안정적

---

## 구현 우선순위

### Phase 1 (1주)
1. Backend `/api/chat/stream` 엔드포인트 구현
2. 기본 Streaming 로직 테스트

### Phase 2 (1주)
3. Frontend API 클라이언트 함수
4. React Component 통합

### Phase 3 (1주)
5. 에러 처리 강화
6. UI/UX 개선 (타이핑 효과, 취소 버튼)

---

## 체크리스트

구현 전 확인:

- [ ] 기존 `/api/chat` 정상 작동 확인
- [ ] LangGraph astream 지원 확인
- [ ] Redis/DB 세션 저장 로직 검토
- [ ] 백업 브랜치 생성

구현 후 확인:

- [ ] curl 테스트 성공
- [ ] 브라우저 EventSource 연결 확인
- [ ] 긴 응답 타임아웃 없이 완료
- [ ] 에러 처리 정상 작동

---

## 참고 자료

- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Server-Sent Events (SSE) MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [LangGraph Streaming](https://langchain-ai.github.io/langgraph/how-tos/streaming/)

---

**작성자**: Claude Code
**완료 일시**: 2025-11-04 16:00 KST
**상태**: 구현 가이드 완료, 실제 구현 대기 중
**예상 소요 기간**: 3주
