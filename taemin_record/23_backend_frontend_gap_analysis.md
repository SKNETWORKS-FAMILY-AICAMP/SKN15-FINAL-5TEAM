# 백엔드 vs 프론트엔드 기능 격차 분석

> **분석 일자**: 2025-11-02
> **목적**: 백엔드에 구현된 API 중 프론트엔드에서 미구현된 기능 파악

---

## 📊 전체 API 엔드포인트 현황

### 백엔드 구현 현황 (총 16개 엔드포인트)

| # | Method | Endpoint | 설명 | 프론트 구현 | 우선순위 |
|---|--------|----------|------|------------|---------|
| 1 | GET | `/` | 헬스체크 | ✅ | Low |
| 2 | POST | `/api/auth/register` | **회원가입** | ❌ | **🔴 HIGH** |
| 3 | POST | `/api/auth/login` | 로그인 | ✅ | - |
| 4 | POST | `/api/auth/refresh` | 토큰 갱신 | ✅ | - |
| 5 | GET | `/api/auth/me` | **현재 사용자 정보** | ❌ | **🟡 MEDIUM** |
| 6 | GET | `/api/auth/google` | Google OAuth | ✅ | - |
| 7 | GET | `/api/auth/google/callback` | Google OAuth 콜백 | ✅ | - |
| 8 | GET | `/api/auth/kakao` | Kakao OAuth | ✅ | - |
| 9 | GET | `/api/auth/kakao/callback` | Kakao OAuth 콜백 | ✅ | - |
| 10 | POST | `/api/auth/password-reset/request` | **비밀번호 재설정 요청** | ❌ | **🟡 MEDIUM** |
| 11 | POST | `/api/auth/password-reset/confirm` | **비밀번호 재설정 확인** | ❌ | **🟡 MEDIUM** |
| 12 | POST | `/api/chat` | 채팅 | ✅ | - |
| 13 | GET | `/api/session/{session_id}` | 세션 조회 | ✅ | - |
| 14 | DELETE | `/api/session/{session_id}` | 세션 삭제 | ✅ | - |
| 15 | GET | `/api/session/last` | 마지막 세션 조회 | ✅ | - |
| 16 | GET | `/api/scenarios` | 시나리오 목록 | ✅ | - |

---

## ❌ 프론트엔드 미구현 기능 (4개)

### 🔴 HIGH Priority

#### 1. 회원가입 (POST /api/auth/register)

**백엔드 구현**: ✅ 완벽 ([api_server.py:522-602](../backend/api_server.py:522))

**기능**:
- 사용자명 중복 체크
- 이메일 중복 체크
- bcrypt 비밀번호 해싱
- 자동 JWT 토큰 발급
- 에러 처리

**Request**:
```json
{
  "username": "new_user",
  "password": "password123",
  "email": "user@example.com",  // optional
  "display_name": "표시이름"     // optional
}
```

**Response**:
```json
{
  "success": true,
  "message": "회원가입이 완료되었습니다.",
  "user_id": "uuid...",
  "username": "new_user",
  "display_name": "표시이름",
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

**프론트엔드 상태**: ❌ **완전히 없음**
- LoginModal에 회원가입 UI 없음
- 회원가입 버튼/링크 없음
- API 호출 로직 없음

**필요한 작업**:
1. LoginModal에 "회원가입" 탭 또는 모드 추가
2. 회원가입 폼 구현 (username, password, email, display_name)
3. `/api/auth/register` API 호출 로직
4. 성공 시 자동 로그인 처리

---

### 🟡 MEDIUM Priority

#### 2. 현재 사용자 정보 조회 (GET /api/auth/me)

**백엔드 구현**: ✅ ([api_server.py:688-708](../backend/api_server.py:688))

**기능**:
- JWT 토큰으로 현재 로그인한 사용자 정보 반환
- 인증 필수 (require_auth)

**Response**:
```json
{
  "user_id": "uuid...",
  "username": "tanjiro",
  "email": "tanjiro@example.com",
  "display_name": "탄지로",
  "provider": "email",
  "created_at": "2025-11-01T...",
  "last_login": "2025-11-02T..."
}
```

**프론트엔드 상태**: ❌ **없음**

**사용 사례**:
- 마이페이지/내 정보 페이지
- 프로필 표시
- 사용자 설정 페이지

**필요한 작업**:
1. `api.ts`에 `getCurrentUser()` 메서드 추가
2. MyAccountModal에서 사용자 정보 표시
3. 로그인 후 사용자 정보 자동 로드

---

#### 3. 비밀번호 재설정 요청 (POST /api/auth/password-reset/request)

**백엔드 구현**: ✅ ([api_server.py:899-969](../backend/api_server.py:899))

**기능**:
- 이메일로 재설정 토큰 전송
- 토큰 유효기간: 1시간
- 이메일 전송 (SMTP 설정 필요)

**Request**:
```json
{
  "email": "user@example.com"
}
```

**Response**:
```json
{
  "success": true,
  "message": "비밀번호 재설정 링크가 이메일로 전송되었습니다."
}
```

**프론트엔드 상태**: ❌ **없음**

**필요한 작업**:
1. "비밀번호를 잊으셨나요?" 링크 추가
2. 비밀번호 재설정 요청 모달
3. 이메일 입력 폼

---

#### 4. 비밀번호 재설정 확인 (POST /api/auth/password-reset/confirm)

**백엔드 구현**: ✅ ([api_server.py:971-1021](../backend/api_server.py:971))

**기능**:
- 토큰 검증
- 새 비밀번호로 업데이트
- 토큰 사용 처리

**Request**:
```json
{
  "token": "reset-token-here",
  "new_password": "new-password123"
}
```

**프론트엔드 상태**: ❌ **없음**

**필요한 작업**:
1. 비밀번호 재설정 페이지 (/reset-password?token=...)
2. 새 비밀번호 입력 폼
3. 비밀번호 확인 필드
4. API 호출 및 성공 처리

---

## ✅ 구현된 기능 (12개)

### 인증 관련
- ✅ 로그인 (POST /api/auth/login)
- ✅ 토큰 갱신 (POST /api/auth/refresh)
- ✅ Google OAuth (GET /api/auth/google)
- ✅ Kakao OAuth (GET /api/auth/kakao)

### 채팅 관련
- ✅ 채팅 메시지 전송 (POST /api/chat)

### 세션 관련
- ✅ 세션 조회 (GET /api/session/{session_id})
- ✅ 세션 삭제 (DELETE /api/session/{session_id})
- ✅ 마지막 세션 조회 (GET /api/session/last)

### 기타
- ✅ 헬스체크 (GET /)
- ✅ 시나리오 목록 (GET /api/scenarios)

---

## 📋 구현 우선순위

### 🔴 Immediate (즉시 구현 필요)

1. **회원가입 UI**
   - 현재 신규 사용자가 계정을 만들 수 없음!
   - 테스트 계정만 사용 가능한 상태
   - **가장 시급한 이슈**

### 🟡 High (높은 우선순위)

2. **현재 사용자 정보 조회**
   - 마이페이지 기능 구현을 위해 필요
   - 사용자 경험 개선

### 🟢 Medium (중간 우선순위)

3. **비밀번호 재설정**
   - 사용자 편의 기능
   - SMTP 설정도 필요

---

## 🎯 권장 구현 순서

### Phase 1: 회원가입 (필수)
```
1. LoginModal에 "회원가입" 탭 추가
2. 회원가입 폼 구현
3. API 연동
4. 성공 시 자동 로그인
```

### Phase 2: 사용자 정보
```
1. api.ts에 getCurrentUser() 추가
2. MyAccountModal에서 사용자 정보 표시
3. 프로필 편집 기능 (선택)
```

### Phase 3: 비밀번호 재설정 (선택)
```
1. "비밀번호를 잊으셨나요?" 링크
2. 재설정 요청 모달
3. 재설정 확인 페이지
4. SMTP 설정 (백엔드)
```

---

## 📊 통계 요약

- **총 백엔드 API**: 16개
- **프론트엔드 구현**: 12개 (75%)
- **미구현**: 4개 (25%)
- **핵심 누락**: 회원가입 (신규 사용자 가입 불가!)

---

## 🚨 즉시 조치 필요

**현재 상태**: 신규 사용자가 계정을 만들 수 없습니다!

백엔드에는 완벽한 회원가입 API가 있지만, 프론트엔드에 UI가 없어서:
- 테스트 계정(tanjiro, zenitsu 등)만 사용 가능
- 실제 서비스 출시 불가능
- 사용자 확장 불가능

**해결 방법**: LoginModal에 회원가입 기능 추가 (30분 작업)

---

## 📖 관련 문서

- 백엔드 API: [backend/api_server.py](../backend/api_server.py)
- 프론트엔드 API Client: [front/src/services/api.ts](../front/src/services/api.ts)
- 로그인 모달: [front/src/components/LoginModal.tsx](../front/src/components/LoginModal.tsx)
- 인증 시스템: [taemin_record/21_authentication_required_chat_implementation.md](21_authentication_required_chat_implementation.md)
