# 현재 시스템 누락 기능 분석 (최신)

> **분석 일자**: 2025-11-02
> **목적**: 백엔드에 구현되었으나 프론트엔드에서 미구현된 기능 최신 상태 점검
> **기준**: 오늘 구현한 회원가입 및 세션 복원 기능 반영

---

## 📊 현재 상태 요약

### 전체 Backend API: 16개

| 상태 | 개수 | 비율 |
|-----|------|------|
| ✅ 구현 완료 | 13개 | 81% |
| ❌ 미구현 | 3개 | 19% |

**오늘 구현 완료**:
- ✅ POST /api/auth/register (회원가입) - 프론트엔드 구현 완료
- ✅ GET /api/session/last (세션 복원) - 프론트엔드 구현 완료

---

## ✅ 구현 완료 (13개)

### 인증 관련 (6개)
1. ✅ `GET /` - 헬스체크
2. ✅ `POST /api/auth/register` - 회원가입 **(오늘 구현)**
3. ✅ `POST /api/auth/login` - 로그인
4. ✅ `POST /api/auth/refresh` - 토큰 갱신
5. ✅ `GET /api/auth/google` - Google OAuth
6. ✅ `GET /api/auth/google/callback` - Google OAuth 콜백
7. ✅ `GET /api/auth/kakao` - Kakao OAuth
8. ✅ `GET /api/auth/kakao/callback` - Kakao OAuth 콜백

### 채팅 관련 (1개)
9. ✅ `POST /api/chat` - 채팅 메시지 전송

### 세션 관련 (3개)
10. ✅ `GET /api/session/{session_id}` - 세션 상세 조회
11. ✅ `DELETE /api/session/{session_id}` - 세션 삭제
12. ✅ `GET /api/session/last` - 마지막 세션 조회 **(오늘 구현)**

### 시나리오 관련 (1개)
13. ✅ `GET /api/scenarios` - 시나리오 목록 조회

---

## ❌ 미구현 기능 (3개)

### 🔴 HIGH Priority

#### 1. 현재 사용자 정보 조회 (GET /api/auth/me)

**백엔드 구현**: ✅ 완료 ([api_server.py:688-708](../backend/api_server.py#L688))

```python
@app.get("/api/auth/me")
async def get_current_user(current_user: Dict = Depends(require_auth)):
    """현재 로그인한 사용자 정보 조회"""
    return {
        "user_id": current_user.get("user_id"),
        "username": current_user.get("username"),
        "email": current_user.get("email"),
        "display_name": current_user.get("display_name"),
        "provider": current_user.get("provider"),
        "created_at": current_user.get("created_at"),
        "last_login": current_user.get("last_login")
    }
```

**프론트엔드 상태**: ❌ **부분 구현 (하드코딩)**

**문제점**:
- `MyAccountModal.tsx`가 존재하지만 하드코딩된 데이터만 표시
- API 호출 없음
- `api.ts`에 `getCurrentUser()` 메서드 없음

**현재 코드 (MyAccountModal.tsx)**:
```typescript
// ❌ 하드코딩된 데이터
<div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
  <span className="text-gray-600">회원 등급</span>
  <span className="text-purple-600 font-medium">프리미엄</span>  {/* 하드코딩 */}
</div>
<div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
  <span className="text-gray-600">가입일</span>
  <span className="text-gray-800 font-medium">2024.01.15</span>  {/* 하드코딩 */}
</div>

// 최근 대화도 하드코딩
<div className="p-3 bg-gray-50 rounded-lg">
  <span className="font-medium text-gray-800">네즈코와의 대화</span>  {/* 하드코딩 */}
  <span className="text-sm text-gray-500">2시간 전</span>
</div>
```

**필요한 작업**:
1. `api.ts`에 `getCurrentUser()` 메서드 추가
   ```typescript
   async getCurrentUser(): Promise<UserInfo> {
     const response = await authenticatedApiClient.get('/api/auth/me')
     return response.data
   }
   ```

2. `MyAccountModal` 컴포넌트 수정
   - useEffect로 컴포넌트 마운트 시 사용자 정보 로드
   - 하드코딩 데이터를 실제 API 응답으로 대체
   - 로딩/에러 상태 처리

3. 실제 사용자 정보 표시
   - 사용자 ID
   - 사용자명
   - 이메일
   - 표시 이름
   - 가입 provider (email/google/kakao)
   - 가입일 (created_at)
   - 마지막 로그인 (last_login)

**예상 구현 시간**: 30분

---

### 🟡 MEDIUM Priority

#### 2. 비밀번호 재설정 요청 (POST /api/auth/password-reset/request)

**백엔드 구현**: ✅ 완료 ([api_server.py:899-969](../backend/api_server.py#L899))

```python
@app.post("/api/auth/password-reset/request")
async def request_password_reset(req: PasswordResetRequest, request: Request):
    """비밀번호 재설정 이메일 발송"""
    # 이메일로 재설정 토큰 전송
    # 토큰 유효기간: 1시간
```

**프론트엔드 상태**: ❌ **완전 없음**

**현재 문제**:
- `LoginModal`에 "비밀번호를 잊으셨나요?" 링크 없음
- 비밀번호 재설정 요청 UI 없음
- 관련 컴포넌트 없음

**필요한 작업**:
1. `LoginModal`에 "비밀번호 찾기" 링크 추가
2. `PasswordResetModal` 컴포넌트 생성
   - 이메일 입력 폼
   - "재설정 링크 보내기" 버튼
   - 성공/실패 피드백
3. `api.ts`에 메서드 추가
   ```typescript
   async requestPasswordReset(email: string): Promise<boolean>
   ```

**참고사항**:
- 백엔드에서 SMTP 설정 필요 (이메일 전송용)
- 프로덕션 환경에서는 실제 이메일 서버 필요

**예상 구현 시간**: 1시간

---

#### 3. 비밀번호 재설정 확인 (POST /api/auth/password-reset/confirm)

**백엔드 구현**: ✅ 완료 ([api_server.py:971-1021](../backend/api_server.py#L971))

```python
@app.post("/api/auth/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirm):
    """토큰 검증 후 비밀번호 업데이트"""
    # 토큰 유효성 확인
    # 새 비밀번호로 변경
```

**프론트엔드 상태**: ❌ **완전 없음**

**필요한 작업**:
1. 비밀번호 재설정 페이지 생성
   - URL: `/reset-password?token=XXX`
   - 라우팅 설정 필요
2. `PasswordResetConfirmPage` 컴포넌트
   - 새 비밀번호 입력
   - 비밀번호 확인 입력
   - 유효성 검사
   - 성공 시 로그인 페이지로 이동
3. `api.ts`에 메서드 추가
   ```typescript
   async confirmPasswordReset(token: string, newPassword: string): Promise<boolean>
   ```

**예상 구현 시간**: 1.5시간

---

## 📋 구현 우선순위 및 로드맵

### Phase 1: 사용자 정보 조회 (1순위) 🔴

**중요도**: HIGH
**긴급도**: HIGH
**예상 시간**: 30분

**이유**:
- `MyAccountModal`이 이미 존재하지만 실제 데이터를 표시하지 못함
- 사용자 경험에 직접적인 영향
- 구현이 상대적으로 간단

**작업 내용**:
```
1. api.ts에 getCurrentUser() 추가 (5분)
2. UserInfo 타입 정의 (5분)
3. MyAccountModal에 useEffect 추가 (10분)
4. 하드코딩 데이터를 실제 데이터로 교체 (10분)
```

---

### Phase 2: 비밀번호 재설정 (2순위) 🟡

**중요도**: MEDIUM
**긴급도**: LOW
**예상 시간**: 2.5시간

**이유**:
- 사용자 편의 기능
- 초기에는 관리자가 수동으로 처리 가능
- SMTP 설정 필요 (추가 인프라 작업)

**작업 내용**:
```
Phase 2-1: 비밀번호 재설정 요청 (1시간)
  1. LoginModal에 "비밀번호 찾기" 링크
  2. PasswordResetModal 컴포넌트
  3. API 연동

Phase 2-2: 비밀번호 재설정 확인 (1.5시간)
  1. /reset-password 라우트 추가
  2. PasswordResetConfirmPage 컴포넌트
  3. 폼 유효성 검사
  4. API 연동

Phase 2-3: SMTP 설정 (별도 작업)
  - 이메일 서버 설정
  - 이메일 템플릿 작성
```

---

## 📊 통계 및 진행률

### 전체 진행률

```
구현 완료: ████████████████░░░░ 81% (13/16)
미구현:     ░░░░ 19% (3/16)
```

### 우선순위별 분포

| 우선순위 | 개수 | 상태 |
|---------|------|------|
| 🔴 HIGH | 1개 | 미구현 |
| 🟡 MEDIUM | 2개 | 미구현 |

### 카테고리별 구현 상태

| 카테고리 | 전체 | 구현 | 미구현 | 완료율 |
|---------|------|------|--------|--------|
| 인증 관련 | 8개 | 5개 | 3개 | 63% |
| 채팅 관련 | 1개 | 1개 | 0개 | 100% |
| 세션 관련 | 3개 | 3개 | 0개 | 100% |
| 시나리오 | 1개 | 1개 | 0개 | 100% |
| 기타 | 3개 | 3개 | 0개 | 100% |

---

## 🎯 권장 작업 순서

### 이번 주 (HIGH Priority)

**1. GET /api/auth/me 구현**
- [ ] api.ts에 getCurrentUser() 메서드 추가
- [ ] UserInfo 타입 정의
- [ ] MyAccountModal 리팩토링
- [ ] 테스트

### 다음 주 (MEDIUM Priority)

**2. 비밀번호 재설정 (요청)**
- [ ] LoginModal에 "비밀번호 찾기" 링크
- [ ] PasswordResetModal 컴포넌트
- [ ] API 연동
- [ ] 테스트

**3. 비밀번호 재설정 (확인)**
- [ ] /reset-password 라우트 추가
- [ ] PasswordResetConfirmPage 컴포넌트
- [ ] 유효성 검사
- [ ] API 연동
- [ ] 테스트

---

## 🔍 상세 구현 가이드

### 1. GET /api/auth/me 구현

#### Step 1: api.ts 수정

```typescript
// src/services/api.ts

export interface UserInfo {
  user_id: string
  username: string
  email?: string
  display_name: string
  provider: 'email' | 'google' | 'kakao'
  created_at: string
  last_login?: string
}

class ApiClient {
  // ... 기존 메서드

  /**
   * Get current user information (with JWT authentication)
   */
  async getCurrentUser(): Promise<UserInfo> {
    try {
      const response = await authenticatedApiClient.get('/api/auth/me')
      return response.data
    } catch (error) {
      console.error('Error getting current user:', error)
      throw error
    }
  }
}
```

#### Step 2: MyAccountModal 리팩토링

```typescript
// src/components/MyAccountModal.tsx

import { useState, useEffect } from 'react'
import { useApp } from '@/contexts/AppContext'
import { apiClient, UserInfo } from '@/services/api'

export default function MyAccountModal() {
  const { isMyAccountModalOpen, closeMyAccount, logout } = useApp()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isMyAccountModalOpen) {
      loadUserInfo()
    }
  }, [isMyAccountModalOpen])

  const loadUserInfo = async () => {
    try {
      setLoading(true)
      setError('')
      const info = await apiClient.getCurrentUser()
      setUserInfo(info)
    } catch (err) {
      console.error('Failed to load user info:', err)
      setError('사용자 정보를 불러올 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (!isMyAccountModalOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-2xl w-[480px] h-[600px] shadow-2xl relative overflow-hidden">
        {/* ... 헤더 ... */}

        <div className="h-[calc(100%-48px)] overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">로딩 중...</div>
            </div>
          ) : error ? (
            <div className="text-red-500 text-center">{error}</div>
          ) : userInfo ? (
            <>
              {/* 프로필 섹션 */}
              <div className="flex items-center space-x-4 mb-8">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 text-xl font-bold">
                    {userInfo.display_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">내 계정</h2>
                  <p className="text-gray-600">{userInfo.display_name}</p>
                </div>
              </div>

              {/* 계정 정보 */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">계정 정보</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">사용자명</span>
                    <span className="text-gray-800 font-medium">{userInfo.username}</span>
                  </div>
                  {userInfo.email && (
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">이메일</span>
                      <span className="text-gray-800 font-medium">{userInfo.email}</span>
                    </div>
                  )}
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">로그인 방식</span>
                    <span className="text-purple-600 font-medium">
                      {userInfo.provider === 'email' ? '이메일' :
                       userInfo.provider === 'google' ? 'Google' : 'Kakao'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">가입일</span>
                    <span className="text-gray-800 font-medium">
                      {new Date(userInfo.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                  {userInfo.last_login && (
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-600">마지막 로그인</span>
                      <span className="text-gray-800 font-medium">
                        {new Date(userInfo.last_login).toLocaleString('ko-KR')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : null}

          {/* ... 나머지 콘텐츠 ... */}
        </div>
      </div>
    </div>
  )
}
```

#### Step 3: 테스트

```bash
# 1. 백엔드 서버 실행 확인
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/auth/me

# 2. 프론트엔드에서 테스트
# - 로그인
# - "내 계정" 클릭
# - 사용자 정보 표시 확인
```

---

## 📖 참고 문서

- [오늘 작업 로그](25_daily_work_log_2025_11_02.md)
- [회원가입 구현 완료](24_signup_feature_implementation_complete.md)
- [세션 복원 구현](22_session_restoration_implementation.md)
- [이전 Gap Analysis](23_backend_frontend_gap_analysis.md)

---

## 📌 주요 변경사항 (이전 분석 대비)

### 구현 완료 ✅
- ✅ POST /api/auth/register (회원가입)
  - LoginModal에 완전한 회원가입 기능 추가
  - 탭 전환 UI
  - 자동 로그인

- ✅ GET /api/session/last (세션 복원)
  - SessionResumeModal 컴포넌트
  - 대화 이어하기 기능
  - ChatPage 통합

### 남은 작업 ❌
- ❌ GET /api/auth/me (사용자 정보 조회) - **다음 우선순위**
- ❌ POST /api/auth/password-reset/request
- ❌ POST /api/auth/password-reset/confirm

---

**작성일**: 2025-11-02
**다음 업데이트**: GET /api/auth/me 구현 후
