# [모델 배포] 시스템 구성도

**SK Networks Family AI Camp 15기 - 데몬슬레이어팀**

---

## 📋 개요

| 항목 | 내용 |
|------|------|
| **산출물 단계** | 모델 배포 |  
| **평가 산출물** | 시스템 구성도 |
| **제출 일자** | 2025. 10. 01 |
| **깃허브 경로** | https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM |
| **작성 팀원** | 권도원, 이준원, 조태민 |

---

## 1. 전체 시스템 인프라 구성

### 1-1. 전체 아키텍처 다이어그램

```mermaid
graph TB
    subgraph "클라이언트 계층"
        C1[웹 브라우저<br/>React + HTML/CSS]
        C2[모바일 웹<br/>반응형 디자인]
        C3[관리자 대시보드<br/>Django Admin]
    end
    
    subgraph "웹 서버 계층"
        WS[Nginx<br/>리버스 프록시 & 정적 파일]
    end
    
    subgraph "애플리케이션 서버"
        AS[Gunicorn + Django<br/>WSGI 애플리케이션 서버]
    end
    
    subgraph "LangGraph 에이전트 엔진"
        A1[Router Agent]
        A2[Guardrail Agent] 
        A3[Parent Agent]
        A4[Children Agent]
        A5[Dialogue Agent]
        T1[State Tools]
        T2[Scene Tools]
    end
    
    subgraph "외부 AI 서비스"
        E1[OpenAI API<br/>GPT-4/3.5]
        E2[나노바나나<br/>이미지 생성]
    end
    
    subgraph "데이터 저장소"
        D1[PostgreSQL<br/>게임 상태 DB]
        D2[Redis<br/>세션 & 캐시]
        D3[파일 시스템<br/>이미지 저장소]
    end
    
    C1 --> WS
    C2 --> WS
    C3 --> WS
    WS --> AS
    AS --> A1
    
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    A3 <--> T1
    A4 <--> T1
    
    A3 --> T2
    A4 --> T2
    
    A1 -.-> E1
    A4 -.-> E1
    A5 -.-> E1
    T2 -.-> E2
    
    T1 --> D1
    AS --> D2
    T2 --> D3
```

---

## 2. 웹 서버 및 애플리케이션 구성

### 2-1. Django + Gunicorn + Nginx 스택

```mermaid
graph TB
    subgraph "Nginx 웹 서버"
        N1[정적 파일 서빙<br/>CSS, JS, 이미지]
        N2[리버스 프록시<br/>동적 요청 전달]
        N3[SSL/TLS 처리<br/>HTTPS 암호화]
        N4[로드 밸런싱<br/>다중 인스턴스]
    end
    
    subgraph "Gunicorn WSGI"
        G1[워커 프로세스 관리<br/>멀티프로세싱]
        G2[Django 앱 실행<br/>웹 애플리케이션]
        G3[요청/응답 처리<br/>HTTP 통신]
    end
    
    subgraph "Django 프레임워크"
        D1[URL 라우팅<br/>endpoints 관리]
        D2[뷰 함수<br/>비즈니스 로직]
        D3[템플릿 엔진<br/>HTML 렌더링]
        D4[ORM<br/>데이터베이스 연동]
        D5[WebSocket<br/>실시간 통신]
    end
    
    N2 --> G1
    G1 --> G2
    G2 --> D1
    D1 --> D2
    D2 --> D3
    D2 --> D4
    D2 --> D5
```

### 2-2. Django 애플리케이션 구조

```mermaid
graph TD
    subgraph "Django 프로젝트"
        M[manage.py<br/>메인 관리 스크립트]
        S[settings.py<br/>설정 파일]
        U[urls.py<br/>URL 구성]
        W[wsgi.py<br/>WSGI 설정]
    end
    
    subgraph "게임 앱 (game/)"
        V1[views.py<br/>게임 로직 뷰]
        M1[models.py<br/>데이터 모델]
        U1[urls.py<br/>게임 URL]
        T1[templates/<br/>HTML 템플릿]
        S1[static/<br/>CSS/JS 파일]
    end
    
    subgraph "에이전트 앱 (agents/)"
        V2[views.py<br/>에이전트 API]
        A1[router.py<br/>Router Agent]
        A2[guardrail.py<br/>Guardrail Agent]
        A3[parent.py<br/>Parent Agent]
        A4[children.py<br/>Children Agent]
        A5[dialogue.py<br/>Dialogue Agent]
    end
    
    subgraph "도구 앱 (tools/)"
        T2[state_tools.py<br/>상태 관리]
        T3[scene_tools.py<br/>이미지 생성]
        T4[utils.py<br/>유틸리티]
    end
    
    M --> S
    S --> U
    U --> V1
    V1 --> A1
    A1 --> T2
```

---

## 3. 클라이언트 구성

### 3-1. React + HTML 프론트엔드

```mermaid
graph LR
    subgraph "React 컴포넌트"
        R1[App.js<br/>메인 애플리케이션]
        R2[ChatInterface<br/>채팅 UI]
        R3[GameState<br/>게임 상태 표시]
        R4[CharacterPanel<br/>캐릭터 정보]
        R5[ImageViewer<br/>이미지 표시]
    end
    
    subgraph "HTML/CSS"
        H1[index.html<br/>메인 페이지]
        H2[game.css<br/>게임 스타일]
        H3[character.css<br/>캐릭터 스타일]
        H4[responsive.css<br/>반응형 디자인]
    end
    
    subgraph "JavaScript"
        J1[websocket.js<br/>실시간 통신]
        J2[api.js<br/>REST API 호출]
        J3[utils.js<br/>유틸리티 함수]
    end
    
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> R5
    
    R1 --> H1
    R2 --> H2
    R4 --> H3
    H1 --> H4
    
    R2 --> J1
    R3 --> J2
    R5 --> J3
```

### 3-2. 클라이언트 기술 스택

| 구성 요소 | 기술 | 역할 | 특징 |
|-----------|------|------|------|
| **UI 프레임워크** | React 18 | 컴포넌트 기반 UI | 상태 관리, 재사용성 |
| **스타일링** | HTML/CSS | 디자인 & 레이아웃 | 반응형, 애니메이션 |
| **실시간 통신** | WebSocket | 게임 상태 동기화 | 양방향 통신 |
| **HTTP 통신** | Fetch API | REST API 호출 | 비동기 데이터 처리 |

---

## 4. 데이터베이스 구성

### 4-1. PostgreSQL 스키마 설계

```mermaid
erDiagram
    GAME_SESSIONS {
        varchar session_id PK
        varchar user_id
        varchar current_scene
        int current_turn
        int total_remaining_turns
        json game_flags
        json character_affinity
        timestamp created_at
        timestamp updated_at
        boolean is_active
    }
    
    DIALOGUE_HISTORY {
        bigint id PK
        varchar session_id FK
        varchar speaker
        text content
        varchar emotion
        timestamp created_at
        int turn_number
    }
    
    SCENE_PROGRESS {
        varchar session_id PK
        varchar scene_id PK
        int completed_turns
        json scene_data
        boolean is_completed
        timestamp last_updated
    }
    
    CHARACTER_STATUS {
        varchar session_id PK
        varchar character_name PK
        int affinity_score
        varchar affinity_level
        json interaction_history
        timestamp last_interaction
    }
    
    IMAGE_CACHE {
        varchar image_id PK
        varchar image_type
        varchar prompt_hash
        varchar file_path
        timestamp created_at
        boolean is_generated
    }
    
    GAME_SESSIONS ||--o{ DIALOGUE_HISTORY : contains
    GAME_SESSIONS ||--o{ SCENE_PROGRESS : tracks
    GAME_SESSIONS ||--o{ CHARACTER_STATUS : manages
    SCENE_PROGRESS ||--o{ IMAGE_CACHE : uses
```

### 4-2. Redis 캐시 구조

```mermaid
flowchart TB
    subgraph "Redis 키 구조"
        R1["session:게임상태캐시"]
        R2["session:동시성제어"]
        R3["user:활성세션"]
        R4["image:URL캐시"]
        R5["agent:작업큐"]
    end
    
    subgraph "캐시 전략"
        C1["게임 상태: 15분 TTL"]
        C2["이미지 URL: 1시간 TTL"]
        C3["세션 락: 30초 TTL"]
        C4["사용자 활성: 24시간 TTL"]
    end
    
    R1 --> C1
    R4 --> C2
    R2 --> C3
    R3 --> C4
```

---

## 5. Scene Tools 이미지 관리 시스템

### 5-1. 이미지 처리 플로우

```mermaid
flowchart TD
    A[이미지 요청] --> B{이미지 타입}
    
    B -->|컷신 이미지| C[Parent Agent 요청]
    B -->|감정 이미지| D[Children Agent 요청]
    B -->|특별 이미지| E[Parent Agent 요청]
    
    C --> F[미리 저장된<br/>컷신 이미지 로드]
    D --> G[미리 저장된<br/>감정 이미지 로드]
    E --> H[채팅 히스토리 요약]
    
    F --> I[Parent Agent에 전달]
    G --> J[Children Agent에 전달]
    H --> K[나노바나나 API 호출]
    
    K --> L[실시간 이미지 생성]
    L --> M[Parent Agent에 전달]
    
    I --> N[컷신 표시]
    J --> O[채팅에 감정 이미지]
    M --> P[특별 이미지 표시]
```

### 5-2. 이미지 처리 방식

| 이미지 타입 | 처리 방식 | 요청 에이전트 | 전달 대상 | 저장 방식 |
|-------------|-----------|---------------|-----------|-----------|
| **컷신 이미지** | 미리 저장된 이미지 로드 | Parent Agent | Parent Agent | 사전 저장 |
| **감정 이미지** | 미리 저장된 이미지 로드 | Children Agent | Children Agent | 사전 저장 |
| **특별 이미지** | 실시간 생성 (나노바나나) | Parent Agent | Parent Agent | 실시간 생성 |

### 5-3. 특별 이미지 생성 과정

```mermaid
sequenceDiagram
    participant P as Parent Agent
    participant ST as Scene Tools
    participant DB as Database
    participant NB as NanoBanana
    
    Note over P,NB: 시나리오 클리어 시
    P->>ST: 특별 이미지 생성 요청
    ST->>DB: 전체 채팅 히스토리 조회
    DB->>ST: 컷신 전체 대화 내역
    ST->>ST: 대화 내용 요약
    ST->>NB: 요약 기반 프롬프트 생성
    NB->>ST: 커스텀 이미지 생성
    ST->>P: 생성된 특별 이미지
    P->>P: 엔딩 이미지로 표시
```

---

## 6. 외부 서비스 연동

### 6-1. OpenAI API 통합

```mermaid
graph TB
    subgraph "OpenAI 서비스 활용"
        O1[GPT-4<br/>복잡한 분석 & 품질검증]
        O2[GPT-3.5 Turbo<br/>빠른 분류 & 일반 대화]
    end
    
    subgraph "API 관리 시스템"
        A1[API 키 순환<br/>rate limit 방지]
        A2[요청 큐잉<br/>동시 요청 제한]
        A3[응답 캐싱<br/>중복 요청 방지]
        A4[오류 재시도<br/>지수 백오프]
    end
    
    subgraph "사용 패턴"
        U1[Router: GPT-3.5<br/>빠른 분류]
        U2[Children: GPT-4<br/>고품질 대사]
        U3[Dialogue: GPT-4<br/>품질 검증]
        U4[Guardrail: GPT-3.5<br/>안전성 검사]
    end
    
    O1 --> A1
    O2 --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    
    A4 --> U1
    A4 --> U2
    A4 --> U3
    A4 --> U4
```

### 6-2. 나노바나나 이미지 생성

```mermaid
flowchart TD
    A[특별 이미지 요청] --> B[채팅 히스토리 수집]
    B --> C[대화 내용 요약]
    C --> D[프롬프트 최적화]
    D --> E[나노바나나 API 호출]
    E --> F[생성 대기]
    F --> G{생성 결과}
    
    G -->|성공| H[이미지 다운로드]
    G -->|실패| I[기본 엔딩 이미지]
    G -->|큐 대기| J[재시도 스케줄링]
    
    H --> K[로컬 저장]
    I --> K
    J --> E
    
    K --> L[Parent Agent 전달]
    
    subgraph "나노바나나 설정"
        M[모델: Stable Diffusion XL]
        N[스타일: Anime/Manga]
        O[해상도: 1024x1024]
        P[품질: Premium]
        Q[프롬프트: 히스토리 요약]
    end
```

---

## 7. 배포 및 컨테이너 구성

### 7-1. Docker 컨테이너 구성

```mermaid
graph TB
    subgraph "Docker Compose 구성"
        D1[nginx<br/>웹 서버 컨테이너]
        D2[django-app<br/>메인 애플리케이션]
        D3[postgres<br/>데이터베이스]
        D4[redis<br/>캐시 서버]
        D5[celery<br/>백그라운드 작업]
    end
    
    subgraph "볼륨 마운트"
        V1[postgres_data<br/>DB 영구 저장]
        V2[media_files<br/>업로드 파일]
        V3[static_files<br/>정적 파일]
        V4[logs<br/>로그 파일]
    end
    
    subgraph "네트워크"
        N1[app-network<br/>내부 통신]
        N2[db-network<br/>DB 전용]
    end
    
    D1 --> V3
    D2 --> V2
    D2 --> V4
    D3 --> V1
    
    D1 -.-> N1
    D2 -.-> N1
    D3 -.-> N2
    D4 -.-> N1
    D5 -.-> N1
```

### 7-2. Docker Compose 설정

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_files:/var/www/static
    depends_on:
      - django-app

  django-app:
    build: .
    command: gunicorn --bind 0.0.0.0:8000 --workers 4 config.wsgi:application
    volumes:
      - media_files:/app/media
      - static_files:/app/static
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/gamedb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: gamedb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  media_files:
  static_files:
```

---

## 8. 환경별 배포 구성

### 8-1. 환경 구성

```mermaid
graph LR
    subgraph "개발 환경"
        DEV1[로컬 개발<br/>Django runserver]
        DEV2[SQLite DB<br/>개발 편의성]
        DEV3[Debug Mode<br/>상세 오류 표시]
        DEV4[Mock APIs<br/>외부 서비스 모킹]
    end
    
    subgraph "스테이징 환경"
        STG1[Docker Compose<br/>운영 환경 시뮬레이션]
        STG2[PostgreSQL<br/>운영 DB와 동일]
        STG3[Nginx + Gunicorn<br/>운영 스택]
        STG4[Real APIs<br/>제한된 사용량]
    end
    
    subgraph "운영 환경"
        PROD1[Kubernetes/ECS<br/>컨테이너 오케스트레이션]
        PROD2[RDS PostgreSQL<br/>관리형 DB 서비스]
        PROD3[CloudFront<br/>CDN 가속]
        PROD4[Full APIs<br/>전체 기능]
    end
    
    DEV1 --> STG1
    STG1 --> PROD1
```

### 8-2. 환경별 설정

| 환경 | 웹서버 | 데이터베이스 | 캐시 | 외부 서비스 |
|------|--------|---------------|------|-------------|
| **개발** | runserver | SQLite | 메모리 | Mock/Sandbox |
| **스테이징** | Nginx+Gunicorn | PostgreSQL | Redis | 제한된 API |
| **운영** | 로드밸런서+CDN | RDS PostgreSQL | ElastiCache | 전체 API |

---

## 9. 모니터링 및 보안

### 9-1. 모니터링 시스템

```mermaid
graph TB
    subgraph "로그 수집"
        L1[Django 로그<br/>애플리케이션 로그]
        L2[Nginx 로그<br/>액세스 로그]
        L3[Gunicorn 로그<br/>WSGI 서버 로그]
        L4[PostgreSQL 로그<br/>쿼리 로그]
        L5[에이전트 로그<br/>AI 처리 로그]
    end
    
    subgraph "메트릭 수집"
        M1[시스템 메트릭<br/>CPU/메모리/디스크]
        M2[애플리케이션 메트릭<br/>응답시간/처리량]
        M3[데이터베이스 메트릭<br/>쿼리 성능]
        M4[외부 API 메트릭<br/>호출 횟수/지연시간]
    end
    
    subgraph "알림 시스템"
        A1[Slack 알림<br/>장애 발생]
        A2[Email 알림<br/>일일/주간 리포트]
        A3[SMS 알림<br/>긴급 장애]
    end
    
    L1 --> A1
    M1 --> A1
    M2 --> A2
    M4 --> A3
```

### 9-2. 보안 구성

```mermaid
graph TB
    subgraph "네트워크 보안"
        S1[HTTPS 강제<br/>SSL/TLS 암호화]
        S2[CORS 설정<br/>허용 도메인 제한]
        S3[Rate Limiting<br/>API 호출 제한]
        S4[DDoS 방어<br/>트래픽 분석]
    end
    
    subgraph "애플리케이션 보안"
        S5[Django Security<br/>CSRF/XSS 방어]
        S6[Input Validation<br/>입력 데이터 검증]
        S7[SQL Injection 방어<br/>ORM 사용]
        S8[Authentication<br/>사용자 인증]
    end
    
    subgraph "데이터 보안"
        S9[환경 변수<br/>민감 정보 암호화]
        S10[DB 암호화<br/>중요 데이터 보호]
        S11[API 키 순환<br/>정기적 갱신]
        S12[백업 암호화<br/>데이터 복구 보안]
    end
    
    subgraph "인프라 보안"
        S13[컨테이너 보안<br/>이미지 스캔]
        S14[네트워크 격리<br/>VPC/방화벽]
        S15[접근 제어<br/>IAM 역할 기반]
        S16[보안 패치<br/>정기 업데이트]
    end
```

---

## 10. 성능 최적화

### 10-1. 성능 최적화 전략

| 최적화 영역 | 기술/방법 | 목표 | 측정 방법 |
|-------------|-----------|------|-----------|
| **프론트엔드** | React 메모이제이션, 코드 스플리팅 | 초기 로딩 < 3초 | 브라우저 개발자 도구 |
| **백엔드** | Django ORM 최적화, 쿼리 캐싱 | API 응답 < 2초 | APM 도구 |
| **데이터베이스** | 인덱스 최적화, 커넥션 풀링 | 쿼리 < 100ms | DB 모니터링 |
| **캐시** | Redis 캐싱, CDN 활용 | 캐시 히트율 > 80% | Redis 모니터링 |
| **이미지** | 이미지 압축, 지연 로딩 | 이미지 로딩 < 1초 | 네트워크 분석 |

### 10-2. 확장성 계획

```mermaid
graph TB
    subgraph "단계 1: 수직 확장"
        V1[서버 사양 업그레이드<br/>CPU/메모리 증설]
        V2[데이터베이스 성능 향상<br/>더 큰 인스턴스]
    end
    
    subgraph "단계 2: 수평 확장"
        H1[로드 밸런서<br/>다중 애플리케이션 서버]
        H2[DB 읽기 복제본<br/>읽기 분산]
        H3[Redis 클러스터<br/>캐시 분산]
    end
    
    subgraph "단계 3: 마이크로서비스"
        M1[에이전트 분리<br/>독립 서비스]
        M2[API 게이트웨이<br/>서비스 라우팅]
        M3[메시지 큐<br/>비동기 처리]
    end
    
    subgraph "단계 4: 클라우드 네이티브"
        C1[컨테이너 오케스트레이션<br/>Kubernetes]
        C2[서비스 메시<br/>Istio]
        C3[오토 스케일링<br/>자동 확장]
    end
    
    V1 --> H1
    H1 --> M1
    M1 --> C1
```

---

## 11. 운영 및 유지보수

### 11-1. CI/CD 파이프라인

```mermaid
graph LR
    subgraph "소스 코드"
        SC1[Git Repository<br/>코드 저장소]
        SC2[Feature Branch<br/>기능 개발]
        SC3[Pull Request<br/>코드 리뷰]
    end
    
    subgraph "지속 통합 (CI)"
        CI1[Code Lint<br/>코드 품질 검사]
        CI2[Unit Test<br/>단위 테스트]
        CI3[Integration Test<br/>통합 테스트]
        CI4[Security Scan<br/>보안 스캔]
        CI5[Docker Build<br/>이미지 빌드]
    end
    
    subgraph "지속 배포 (CD)"
        CD1[Staging Deploy<br/>스테이징 배포]
        CD2[E2E Test<br/>엔드투엔드 테스트]
        CD3[Production Deploy<br/>운영 배포]
        CD4[Health Check<br/>배포 검증]
    end
    
    SC3 --> CI1
    CI1 --> CI2
    CI2 --> CI3
    CI3 --> CI4
    CI4 --> CI5
    CI5 --> CD1
    CD1 --> CD2
    CD2 --> CD3
    CD3 --> CD4
```

### 11-2. 백업 및 복구

| 대상 | 백업 주기 | 보관 기간 | 복구 시간 목표 |
|------|-----------|-----------|----------------|
| **PostgreSQL** | 매일 02:00 | 30일 | 1시간 |
| **Redis 상태** | 실시간 복제 | 7일 | 5분 |
| **업로드 파일** | 주 단위 | 90일 | 30분 |
| **애플리케이션** | Git 태그 | 영구 | 10분 |
| **설정 파일** | 변경 시마다 | 1년 | 5분 |

---

## 🎯 시스템 구성 특징

### 주요 특징
- **전통적이고 안정적인 스택**: Django + Gunicorn + Nginx의 검증된 조합
- **React 기반 모던 UI**: 사용자 친화적인 인터페이스와 실시간 상호작용
- **확장 가능한 데이터베이스**: PostgreSQL + Redis 조합으로 성능과 확장성 확보
- **AI 서비스 통합**: OpenAI와 나노바나나를 활용한 지능형 콘텐츠 생성
- **컨테이너 기반 배포**: Docker를 활용한 일관된 배포 환경

### 이미지 처리 특징
- **효율적인 이미지 관리**: 컷신/감정 이미지는 사전 저장, 특별 이미지만 실시간 생성
- **적응형 이미지 시스템**: Parent Agent(컷신/특별), Children Agent(감정) 역할 분리
- **개인화된 엔딩**: 전체 플레이 히스토리를 바탕으로 한 커스텀 이미지 생성

### 운영 고려사항
- **모니터링**: 포괄적인 로그 수집과 메트릭 모니터링
- **보안**: 다층 보안 체계로 안전한 서비스 운영  
- **성능**: 캐싱과 최적화를 통한 빠른 응답 속도
- **확장성**: 단계적 확장 계획으로 성장에 대비

