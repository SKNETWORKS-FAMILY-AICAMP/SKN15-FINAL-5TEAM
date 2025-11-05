# 🔧 Troubleshooting Guide

## 자주 발생하는 문제와 해결 방법

---

## 1️⃣ Chrome 콘솔에 `ERR_FILE_NOT_FOUND` 에러가 발생해요

### 증상
```
Failed to load resource: net::ERR_FILE_NOT_FOUND
- utils.js:1
- extensionState.js:1
- heuristicsRedefinitions.js:1
```

### 원인
**이것은 Chrome Extension (브라우저 확장 프로그램) 에러입니다.**
- 프론트엔드 앱 자체의 문제가 아닙니다 ✅
- 설치된 Chrome 확장 프로그램이 로드하려는 파일이 없어서 발생하는 경고입니다
- **앱의 동작에는 전혀 영향을 주지 않습니다**

### 해결 방법

#### 방법 1: 콘솔 필터 설정 (추천!)

Chrome DevTools에서:
1. **Console 탭** 열기
2. **Filter** 입력창에 다음 입력:
   ```
   -utils.js -extensionState.js -heuristicsRedefinitions.js
   ```
3. **필터를 저장**하면 이후에도 에러가 숨겨집니다

#### 방법 2: 시크릿 모드 사용

```
Mac: Cmd + Shift + N
Windows: Ctrl + Shift + N
```

시크릿 모드에서는 확장 프로그램이 비활성화되어 에러가 사라집니다.

#### 방법 3: Chrome 확장 프로그램 비활성화

1. Chrome 주소창에 입력: `chrome://extensions/`
2. 의심되는 확장 프로그램을 **비활성화**

---

## 2️⃣ API 응답이 느려요 (30초 이상)

### 확인 사항

1. **백엔드 서버 로그 확인**
   ```bash
   # 서버 로그에서 ⏱️ 표시 찾기
   ⏱️ [parent_agent] duration=6,500ms
   ⏱️ [children_agent] duration=11,200ms
   ```

2. **네트워크 탭 확인**
   - Chrome DevTools → Network 탭
   - `/api/chat` 요청의 실제 소요 시간 확인

3. **OpenAI API 키 확인**
   ```bash
   # backend/.env 파일 확인
   OPENAI_API_KEY=sk-...
   ```

### 최적화 팁

최근 최적화 적용 후 예상 성능:
- parent_agent: 13-14초 → **6-8초**
- children_agent: 16-20초 → **10-13초**
- 전체: 30-35초 → **18-23초** (40% 빠름)

---

## 3️⃣ 프론트엔드가 실행되지 않아요

### 해결 방법

```bash
cd front
npm install
npm run dev
```

**예상 출력**:
```
VITE v5.4.21  ready in 277 ms
➜  Local:   http://localhost:3000/
```

---

## 4️⃣ 백엔드가 실행되지 않아요

### 확인 사항

1. **Python 환경 확인**
   ```bash
   which python
   # 또는
   /Users/jtm427/miniconda3/envs/openai/bin/python --version
   ```

2. **의존성 설치**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **데이터베이스 연결 확인**
   ```bash
   # PostgreSQL이 실행 중인지 확인
   psql -h localhost -p 5433 -U kime -d kimedb
   ```

4. **포트 충돌 확인**
   ```bash
   lsof -ti:8000
   # 포트가 사용 중이면
   lsof -ti:8000 | xargs kill -9
   ```

---

## 5️⃣ CORS 에러가 발생해요

### 증상
```
Access to fetch at 'http://localhost:8000/api/chat' from origin
'http://localhost:3000' has been blocked by CORS policy
```

### 해결 방법

백엔드 `api_server.py`에서 CORS 설정 확인:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 6️⃣ 시나리오가 로드되지 않아요

### 확인 사항

1. **시나리오 파일 존재 확인**
   ```bash
   ls backend/data/scenarios/*.json
   ```

2. **시나리오 DB 확인**
   ```bash
   psql -h localhost -p 5433 -U kime -d kimedb
   SELECT * FROM scenarios;
   ```

3. **서버 로그 확인**
   ```
   ⏱️ [scenario_loader] Loaded 'train' in 1.15ms
   ```

---

## 📚 추가 도움이 필요하신가요?

- GitHub Issues에 질문 남기기
- 서버 로그 전체를 첨부해주세요
- 브라우저 콘솔 에러 스크린샷 포함

---

**마지막 업데이트**: 2025-11-05
