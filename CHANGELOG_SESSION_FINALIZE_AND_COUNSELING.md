# 변경사항 요약 (2025-11-13)

## 📋 작업 개요
이번 세션에서는 **장기 메모리 시스템 개선**, **세션 종료 API 구현**, **귀칼 상담소 시나리오 추가** 작업을 완료했습니다.

---

## 🎯 주요 변경사항

### 1. 대화 개수 기반 메모리 추출 시스템 (5개 대화마다 자동 추출)

**문제점:**
- 기존: 턴(사용자 입력) 기반으로 메모리 추출 (10턴마다)
- 스토리 모드(무한열차 등)에서는 사용자 입력 없이 AI 대화만 진행되는 경우가 있어 메모리가 저장되지 않음

**해결:**
- 턴 대신 **대화 개수** 기반으로 변경
- **5개 대화마다** 자동으로 메모리 추출 및 저장
- 모든 시나리오 유형에서 정상 작동

**변경 파일:**
- `backend/app/features/chat/services/extractors/conversation_summarizer.py`
  - Line 23: `SUMMARY_TRIGGER_DIALOGUE_COUNT = 5` (기존 TURN_COUNT → DIALOGUE_COUNT)
  - Lines 47-62: `should_create_summary()` 메서드 수정

- `backend/app/features/chat/usecase.py`
  - Lines 683-686: `total_dialogue_count` 추적 로직 추가
  - Lines 780-782: `summary_dialogue_count` 업데이트

- `backend/app/features/chat/repositories/session_repository.py`
  - Lines 36-37, 54-55: DB에서 대화 개수 컬럼 로드
  - Lines 93-94, 110-111, 127-128: 대화 개수 저장

**데이터베이스 변경:**
```sql
ALTER TABLE conversation.sessions ADD COLUMN total_dialogue_count INTEGER DEFAULT 0;
ALTER TABLE conversation.sessions ADD COLUMN summary_dialogue_count INTEGER DEFAULT 0;
```

**테스트 결과:**
```
✅ 5개 메시지 전송 → 자동 메모리 추출 발동
✅ 5개 메모리 생성 (24 → 29)
✅ 대화 개수 정확히 추적: 1 → 2 → 3 → 4 → 5
```

---

### 2. 세션 종료 API 구현 (수동 메모리 추출)

**목적:**
- 사용자가 채팅을 나갈 때 (5개 미만의 대화도) 메모리로 저장
- 세션을 명시적으로 종료하고 비활성화

**구현 내용:**

#### 백엔드 API
**파일:** `backend/app/features/chat/controller.py`
- Lines 253-303: 새 엔드포인트 추가
```python
POST /api/chat/{session_id}/finalize
```

**응답 형식:**
```json
{
  "success": true,
  "message": "Session finalized successfully",
  "memories_created": 3
}
```

**파일:** `backend/app/features/chat/usecase.py`
- Lines 1367-1528: `finalize_session()` 메서드 구현
  - 세션 상태 및 최근 대화 조회
  - 남은 대화를 강제로 요약
  - 요약에서 메모리 추출
  - 세션 비활성화 (is_active = false)

**메모리 키 중복 방지:**
- `backend/app/features/chat/repositories/memory_repository.py` (Lines 56-60)
```python
unique_id = str(uuid.uuid4())[:8]
memory_key = f"{memory_type}_{timestamp}_{unique_id}"
```

#### 프론트엔드 연동
**파일:** `front/src/services/api.ts`
- Lines 513-530: `finalizeSession()` 메서드 추가

**파일:** `front/src/pages/ChatPage.tsx`
- Lines 35-36: `currentSessionId` 상태 추가
- Lines 159-179: 뒤로가기 시 세션 종료 호출
```typescript
if (currentSessionId) {
  const result = await apiClient.finalizeSession(currentSessionId);
  console.log('[ChatPage] Session finalized:', result);
}
```

**파일:** `front/src/components/ChatInterface.tsx`
- Line 31: `onSessionStart` prop 추가
- Lines 891, 1301: 세션 생성/변경 시 부모에게 알림

**테스트 결과:**
```
✅ 3개 메시지 전송 (자동 추출 미발동)
✅ 수동 finalize API 호출
✅ 3개 메모리 생성 (29 → 32)
✅ 세션 비활성화 확인 (is_active = false)
```

---

### 3. 귀칼 상담소 시나리오 구현

**새로운 시나리오 추가:**
- 힐링 및 상담 중심 AU 시나리오
- 7명의 상담원이 각자의 전문 분야로 사용자를 지원

#### 백엔드 시나리오 파일
**파일:** `data/scenarios/counseling.json`
- 버전: 2.0 (1.0에서 대폭 업그레이드)
- 5단계 스테이지 구조:
  1. INTRO - 상담소 방문
  2. MAIN_COUNSELING - 고민 상담
  3. HEALING_ACTIVITY - 힐링 활동
  4. GROUP_SUPPORT - 모두의 응원
  5. CONCLUSION - 따뜻한 마무리

**상담원 및 전문 분야:**
```
탄지로: 공감과 경청, 따뜻한 위로
렌고쿠: 목표 설정, 열정 회복, 긍정 에너지
시노부: 스트레스 관리, 감정 조절, 미소 요법
기유: 조용한 위로, 인간관계 조언
젠이츠: 연애 고민, 자존감, 불안 해소
이노스케: 자신감 회복, 도전 용기
네즈코: 비언어적 지지, 따뜻한 존재감
```

**힐링 활동 목록:**
- 함께 산책하기
- 명상과 호흡 연습
- 따뜻한 차 마시며 이야기하기
- 간단한 요리 함께 하기
- 스트레칭이나 가벼운 운동
- 일기 쓰기 안내
- 감사 노트 작성
- 음악 듣기
- 그림이나 만들기 활동

**Global Rules:**
- 상담원들은 항상 따뜻하고 공감적인 태도 유지
- 사용자의 고민을 절대 판단하지 않음
- 각 캐릭터의 성격을 살린 위로와 조언
- 필요시 전문적인 도움 권유 가능
- 상담소 분위기는 항상 평화롭고 안전

#### 프론트엔드 설정
**파일:** `front/src/data/scenarios.json`
- Lines 144-217: counseling 시나리오 설정
- `implemented: true`로 변경 (플레이 가능)
- `image: "/images/scenarios/counseling.jpg"` 설정
- 7명의 캐릭터 정보 추가 (프로필 이미지, 인사말, 상태)

**이미지:**
- 기존 `/images/scenarios/counseling.jpg` 사용
- 썸네일: `/images/scenarios/counseling_thumb.jpg`

**접속 경로:**
- URL: `http://localhost/character/counseling`
- 홈페이지에서 "💬 귀칼 상담소 AU" 카드 클릭

---

## 📊 통합 테스트 결과

**테스트 스크립트:** `/tmp/test_integration_finalize.sh`

### Test Case 1: 자동 메모리 추출 (5개 대화)
```
입력: 5개 메시지
결과: ✅ 자동 메모리 추출 발동
메모리 증가: 24 → 29 (+5)
```

### Test Case 2: 수동 세션 종료 (3개 대화)
```
입력: 3개 메시지 (자동 추출 미발동)
수동 종료: /api/chat/{session_id}/finalize
결과: ✅ 메모리 추출 성공
메모리 증가: 29 → 32 (+3)
세션 상태: is_active = false
```

### Test Case 3: 귀칼 상담소 시나리오
```
시나리오: counseling
입력: 5개 메시지
대화 생성: 14개 (평균 2-3 AI 응답/입력)
세션 종료: ✅ 4개 메모리 생성
```

**전체 결과:**
```
✅ INTEGRATION TEST PASSED

- 자동 추출 (5개 대화): 정상 작동 ✓
- 수동 종료 (< 5개 대화): 정상 작동 ✓
- 귀칼 상담소 시나리오: 플레이 가능 ✓
```

---

## 🗂️ 파일 변경 목록

### Backend
```
✏️ Modified:
- app/features/chat/services/extractors/conversation_summarizer.py
- app/features/chat/usecase.py
- app/features/chat/repositories/session_repository.py
- app/features/chat/repositories/memory_repository.py
- app/features/chat/controller.py

📄 Added:
- data/scenarios/counseling.json (새 시나리오)
```

### Frontend
```
✏️ Modified:
- src/services/api.ts
- src/pages/ChatPage.tsx
- src/components/ChatInterface.tsx
- src/data/scenarios.json

📦 Rebuilt:
- dist/ (새 빌드)
```

### Database
```
🗄️ Schema Changes:
- conversation.sessions 테이블
  - ADD COLUMN total_dialogue_count INTEGER DEFAULT 0
  - ADD COLUMN summary_dialogue_count INTEGER DEFAULT 0
```

### Test Scripts
```
✅ Created:
- /tmp/test_integration_finalize.sh (통합 테스트)
- /tmp/test_counseling_scenario.sh (상담소 테스트)
- /tmp/test_counseling_simple.sh (간단 테스트)
```

---

## 🔄 장기 메모리 시스템 동작 방식

### 자동 메모리 추출
```
대화 5개 쌓임 → 자동 요약 생성 → 메모리 추출 → 임베딩 저장
```
- 대화 카운트: `total_dialogue_count` (세션 전체)
- 마지막 요약: `summary_dialogue_count` (마지막 요약 시점)
- 트리거 조건: `(total_dialogue_count - summary_dialogue_count) >= 5`

### 수동 세션 종료
```
사용자 나가기 → finalize API 호출 → 남은 대화 요약 → 메모리 추출 → 세션 비활성화
```
- API: `POST /api/chat/{session_id}/finalize`
- 세션 상태: `is_active = false`로 변경
- 5개 미만의 대화도 메모리로 저장

### 메모리 타입
```
fact: 사실 정보
event: 경험/사건
relationship: 관계
preference: 선호도
```

### 메모리 로딩
```
세션 시작 시 → Top 5 관련 메모리 로드 → LLM 프롬프트에 추가
```

---

## 🚀 사용 방법

### 1. 서비스 재시작 (필요시)
```bash
docker-compose restart backend frontend
```

### 2. 귀칼 상담소 플레이
1. 브라우저에서 http://localhost 접속
2. "💬 귀칼 상담소 AU" 카드 클릭
3. "이 시나리오로 대화 시작" 버튼 클릭
4. 고민 상담 시작!

### 3. 메모리 확인
```bash
# 사용자의 장기 메모리 조회
curl -s -X GET "http://localhost/api/users/me/long-term-memories?limit=100" \
  -H "Authorization: Bearer {TOKEN}" | jq '.'
```

### 4. 세션 상태 확인
```bash
docker-compose exec postgres psql -U kime -d kimedb -c "
  SELECT session_id, scenario_id, current_stage, turn_count,
         total_dialogue_count, summary_dialogue_count
  FROM conversation.sessions
  WHERE session_id = '{SESSION_ID}';"
```

---

## 📝 주의사항

1. **브라우저 캐시 클리어**: 프론트엔드 변경 후 반드시 Cmd+Shift+R (완전 새로고침) 필요
2. **로그인 필수**: 세션 종료 API는 인증 필요
3. **대화 개수**: 5개 대화마다 자동 추출 (턴이 아님!)
4. **메모리 키 중복**: UUID 추가로 해결됨
5. **세션 비활성화**: finalize 후 세션은 재사용 불가 (is_active = false)

---

## 🐛 해결된 버그

### 1. 세션 상태 미저장 문제
**문제:** 대화 개수가 계속 1로 표시됨
**원인:** `get_session()`에서 `total_dialogue_count`, `summary_dialogue_count` 컬럼 누락
**해결:** SQL SELECT 및 state dict에 컬럼 추가

### 2. 메모리 키 중복 오류
**문제:** `UniqueViolationError: duplicate key value`
**원인:** 타임스탬프만 사용해서 같은 초에 생성된 메모리가 충돌
**해결:** UUID 추가로 고유성 보장 (`fact_20251113_171916_a3f2b891`)

### 3. 프론트엔드 시나리오 미활성화
**문제:** "백엔드 API 연결 후 채팅 기능이 활성화됩니다" 메시지
**원인:** `scenarios.json`에서 `implemented: false`
**해결:** `implemented: true`로 변경 및 이미지 경로 수정

---

## 🎉 완료된 기능

- ✅ 대화 개수 기반 메모리 추출 (5개마다)
- ✅ 세션 종료 API 및 프론트엔드 연동
- ✅ 귀칼 상담소 시나리오 (7명 상담원)
- ✅ 메모리 키 중복 방지
- ✅ 통합 테스트 통과
- ✅ 프론트엔드 빌드 및 배포

---

## 📞 문의사항

궁금한 점이나 버그 발견 시 팀 채널로 문의해주세요!

**작성자:** Claude Code Assistant
**작성일:** 2025-11-13
**브랜치:** tm-merge-all-logic
