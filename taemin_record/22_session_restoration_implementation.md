# 세션 복원 기능 구현 가이드

## 개요

사용자가 로그인한 계정별로 마지막 대화 세션을 복원할 수 있는 기능입니다.

## 완료된 작업 (Backend + API)

### ✅ Backend Implementation

#### 1. DatabaseManager - 세션 조회 메서드 ([backend/src/database/db_manager.py](../backend/src/database/db_manager.py:424-463))

```python
def get_user_last_session(
    self,
    user_id: str,
    scenario_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    사용자의 마지막 세션 조회

    Args:
        user_id: 사용자 ID
        scenario_id: 시나리오 ID (Optional, 지정하면 해당 시나리오의 마지막 세션만 반환)

    Returns:
        Optional[Dict]: 세션 정보 or None
    """
    # SQL: SELECT * FROM sessions WHERE user_id = ? AND scenario_id = ? ORDER BY updated_at DESC LIMIT 1
```

#### 2. API Endpoint ([backend/api_server.py](../backend/api_server.py:1757-1800))

```python
@app.get("/api/session/last")
async def get_user_last_session(
    scenario_id: Optional[str] = None,
    current_user: Dict = Depends(require_auth)
):
    """
    현재 로그인한 사용자의 마지막 세션 조회 (세션 복원용)
    """
```

**Request:**
```
GET /api/session/last?scenario_id=cutscene5_llm_driven
Authorization: Bearer {jwt_token}
```

**Response (세션 있음):**
```json
{
  "has_session": true,
  "session_id": "uuid...",
  "scenario_id": "cutscene5_llm_driven",
  "current_stage": "TRAIN_PRELUDE",
  "turn_count": 5,
  "created_at": "2025-11-02T10:00:00",
  "updated_at": "2025-11-02T10:15:00",
  "conversation_summary": "렌고쿠와 무한열차에서..."
}
```

**Response (세션 없음):**
```json
{
  "has_session": false,
  "message": "저장된 세션이 없습니다"
}
```

### ✅ Frontend API Client ([front/src/services/api.ts](../front/src/services/api.ts))

```typescript
export interface LastSessionInfo {
  sessionId: string
  scenarioId: string
  currentStage?: string
  turnCount: number
  createdAt?: string
  updatedAt?: string
  conversationSummary?: string
}

// ApiClient method
async getUserLastSession(scenarioId?: string): Promise<LastSessionInfo | null> {
  const params = scenarioId ? { scenario_id: scenarioId } : {}
  const response = await authenticatedApiClient.get('/api/session/last', { params })

  if (response.data.has_session) {
    return {
      sessionId: response.data.session_id,
      scenarioId: response.data.scenario_id,
      currentStage: response.data.current_stage,
      turnCount: response.data.turn_count,
      createdAt: response.data.created_at,
      updatedAt: response.data.updated_at,
      conversationSummary: response.data.conversation_summary
    }
  }
  return null
}
```

---

## 📝 Frontend 구현 가이드 (TODO)

### Step 1: SessionResumeModal 컴포넌트 생성

**파일**: `front/src/components/SessionResumeModal.tsx`

```typescript
import { useState } from 'react'
import { LastSessionInfo } from '@/services/api'

interface SessionResumeModalProps {
  lastSession: LastSessionInfo
  onResume: (sessionId: string) => void
  onNewSession: () => void
  onClose: () => void
}

export default function SessionResumeModal({
  lastSession,
  onResume,
  onNewSession,
  onClose
}: SessionResumeModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md p-6">
        <h2 className="text-2xl font-bold mb-4">저장된 대화가 있습니다</h2>

        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600 mb-2">마지막 대화:</p>
          <p className="text-lg font-semibold">{lastSession.turnCount}턴 진행</p>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(lastSession.updatedAt!).toLocaleString('ko-KR')}
          </p>
          {lastSession.conversationSummary && (
            <p className="text-sm mt-2 text-gray-700">
              {lastSession.conversationSummary.substring(0, 100)}...
            </p>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => onResume(lastSession.sessionId)}
            className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            이어서 하기
          </button>
          <button
            onClick={onNewSession}
            className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            새로 시작
          </button>
        </div>

        <button
          onClick={onClose}
          className="mt-3 w-full text-sm text-gray-500 hover:text-gray-700"
        >
          닫기
        </button>
      </div>
    </div>
  )
}
```

---

### Step 2: ChatPage에서 마지막 세션 확인

**파일**: `front/src/pages/ChatPage.tsx`

```typescript
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, LastSessionInfo } from '@/services/api'
import SessionResumeModal from '@/components/SessionResumeModal'
import { useApp } from '@/contexts/AppContext'

export default function ChatPage() {
  const { characterId } = useParams<{ characterId: string }>()
  const { isLoggedIn } = useApp()

  const [lastSession, setLastSession] = useState<LastSessionInfo | null>(null)
  const [showResumeModal, setShowResumeModal] = useState(false)
  const [resumeSessionId, setResumeSessionId] = useState<string | undefined>(undefined)

  // 로그인 후 마지막 세션 확인
  useEffect(() => {
    if (isLoggedIn && characterId) {
      checkLastSession()
    }
  }, [isLoggedIn, characterId])

  const checkLastSession = async () => {
    const scenarioId = characterId // 또는 SCENARIO_ID_MAP 사용
    const session = await apiClient.getUserLastSession(scenarioId)

    if (session) {
      setLastSession(session)
      setShowResumeModal(true)
    }
  }

  const handleResume = (sessionId: string) => {
    setResumeSessionId(sessionId)
    setShowResumeModal(false)
    // ChatInterface에 sessionId 전달 -> 이어서 하기
  }

  const handleNewSession = () => {
    setResumeSessionId(undefined)
    setShowResumeModal(false)
    // ChatInterface에 sessionId undefined 전달 -> 새로 시작
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ChatHeader />
      <main>
        <ChatInterface
          characterId={characterId || 'ending'}
          initialSessionId={resumeSessionId}
        />
      </main>

      {showResumeModal && lastSession && (
        <SessionResumeModal
          lastSession={lastSession}
          onResume={handleResume}
          onNewSession={handleNewSession}
          onClose={() => setShowResumeModal(false)}
        />
      )}
    </div>
  )
}
```

---

### Step 3: ChatInterface에서 세션 복원 지원

**파일**: `front/src/components/ChatInterface.tsx`

```typescript
interface ChatInterfaceProps {
  characterId?: string
  initialSessionId?: string  // 추가: 복원할 세션 ID
}

export default function ChatInterface({
  characterId = 'ending',
  initialSessionId  // 추가
}: ChatInterfaceProps) {
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId)

  // initialSessionId가 변경되면 세션 복원
  useEffect(() => {
    if (initialSessionId) {
      setSessionId(initialSessionId)
      // 세션 데이터 로드 (대화 히스토리, 친밀도 등)
      loadSessionData(initialSessionId)
    }
  }, [initialSessionId])

  const loadSessionData = async (sessionId: string) => {
    try {
      // 세션 대화 히스토리 로드
      const sessionInfo = await apiClient.getSession(sessionId)

      // 메시지 복원 (backend에서 dialogues 가져오기)
      // 친밀도 복원
      // 스테이지 복원
    } catch (error) {
      console.error('Failed to load session data:', error)
    }
  }

  // 첫 메시지 전송 시 session_id 포함
  const handleSendMessage = async (userInput: string) => {
    const response = await sendChatMessage(
      backendScenarioId,
      userInput,
      sessionId,  // 세션 ID 전달 (있으면 이어서, 없으면 새로 생성)
      user_name
    )

    if (!sessionId) {
      setSessionId(response.session_id)  // 새 세션 ID 저장
    }
  }
}
```

---

## 📋 구현 체크리스트

### Backend (✅ 완료)
- [x] DatabaseManager.get_user_last_session() 메서드
- [x] /api/session/last 엔드포인트
- [x] JWT 인증 적용 (require_auth)
- [x] scenario_id 필터링 옵션

### Frontend API (✅ 완료)
- [x] LastSessionInfo 타입 정의
- [x] ApiClient.getUserLastSession() 메서드
- [x] authenticatedApiClient 사용 (JWT 자동 포함)

### Frontend UI (📝 TODO)
- [ ] SessionResumeModal 컴포넌트 생성
- [ ] ChatPage에서 마지막 세션 확인 로직
- [ ] "이어서 하기" vs "새로 시작" 선택 UI
- [ ] ChatInterface에 initialSessionId prop 추가
- [ ] 세션 데이터 복원 로직 (대화 히스토리, 친밀도)

---

## 🧪 테스트 시나리오

1. **첫 접속 사용자**:
   - 로그인 → 마지막 세션 없음 → 바로 새 대화 시작

2. **기존 세션 있는 사용자**:
   - 로그인 → 마지막 세션 감지 → SessionResumeModal 표시
   - "이어서 하기" 선택 → 이전 대화부터 계속
   - "새로 시작" 선택 → 새 세션 생성

3. **다른 시나리오 선택**:
   - 시나리오 A에서 진행 중 → 시나리오 B 선택
   - 시나리오 B의 마지막 세션 확인 → 선택

---

## 🎯 사용자 경험 (UX)

```
[사용자 로그인]
    ↓
[채팅 페이지 접속]
    ↓
[마지막 세션 확인] ← GET /api/session/last?scenario_id=...
    ↓
┌─────────────────┐
│ 세션 있음?       │
└─────────────────┘
    ↙           ↘
YES             NO
 ↓               ↓
[모달 표시]    [새 대화 시작]
 ↓
┌──────────────────────┐
│ 이어서 하기 | 새로 시작 │
└──────────────────────┘
 ↓              ↓
[세션 복원]   [새 세션]
 ↓              ↓
[대화 계속]   [처음부터]
```

---

## 📌 참고 사항

- **세션 ID 관리**: session_id를 ChatInterface state에 저장
- **대화 복원**: 백엔드가 session_id로 기존 대화 이어가기 지원
- **장기기억**: conversation_summary 필드 활용 가능
- **만료 처리**: 세션 복원 실패 시 자동으로 새 세션 생성

---

## 🚀 배포 전 확인사항

- [ ] 백엔드 API 정상 작동 확인
- [ ] JWT 토큰 인증 테스트
- [ ] 프론트엔드 모달 UI/UX 검증
- [ ] 세션 복원 로직 테스트
- [ ] 에러 처리 (세션 없음, API 실패 등)
