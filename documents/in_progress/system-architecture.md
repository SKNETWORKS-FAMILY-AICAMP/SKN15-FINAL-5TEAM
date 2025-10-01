# [모델링 및 평가] 시스템 아키텍처

**SK Networks Family AI Camp 15기 - 데몬슬레이어팀**

---

## 📋 개요

| 항목 | 내용 |
|------|------|
| **산출물 단계** | 모델링 및 평가 |
| **평가 산출물** | 시스템 아키텍처 |
| **제출 일자** | 2025. 10. 01 |
| **깃허브 경로** | https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-TEAM |
| **작성 팀원** | [팀원 이름] |

---

## 1. LangGraph 에이전트 워크플로우

### 1-1. 전체 시스템 플로우

```mermaid
graph TD
    A[사용자 입력] --> B[Router Agent]
    B -->|on_topic| C[Guardrail Agent]
    B -->|off_topic| D[Children Agent]
    C -->|safe| E[Parent Agent]
    C -->|unsafe| F[경고 메시지]
    E --> G{게임 상태}
    G -->|컷신| H[컷신 진행]
    G -->|선택지| I[분기 처리]
    G -->|미션| J[설득 임무]
    H --> K[Children Agent]
    I --> K
    J --> K
    K --> L[State Tools]
    L --> M[Scene Tools]
    M --> N[최종 응답]
    D --> N
    F --> N
```

### 1-2. 구성 요소

```mermaid
graph TB
    subgraph "AI 에이전트"
        A1[Router Agent<br/>입력 분류]
        A2[Guardrail Agent<br/>안전성 검증]
        A3[Parent Agent<br/>게임 로직]
        A4[Children Agent<br/>대사 생성]
    end
    
    subgraph "도구 시스템"
        T1[State Tools<br/>상태 관리]
        T2[Scene Tools<br/>이미지 관리]
    end
    
    subgraph "외부 서비스"
        E1[OpenAI GPT-4<br/>LLM 분석]
        E2[이미지 저장소<br/>에셋 관리]
        E3[데이터베이스<br/>상태 저장]
    end
    
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> T1
    T1 --> T2
    
    A1 -.-> E1
    A4 -.-> E1
    T2 -.-> E2
    T1 -.-> E3
```

---

## 2. Router Agent 워크플로우

### 2-1. 입력 분류 프로세스

```mermaid
flowchart TD
    A[사용자 입력] --> B[OpenAI API 호출]
    B --> C[키워드 매칭]
    C --> D{분류 결과}
    D -->|매칭됨| E[on_topic]
    D -->|매칭 안됨| F[off_topic]
    E --> G[Guardrail Agent]
    F --> H[Children Agent]
    
    subgraph "분류 기준"
        I[게임 시나리오 관련<br/>- 캐릭터명<br/>- 액션 키워드<br/>- 선택지]
        J[일반 대화<br/>- 인사<br/>- 잡담<br/>- 질문]
    end
```

### 2-2. 처리 로직 테이블

| 분류 | 키워드 예시 | 다음 노드 | 처리 방식 |
|------|-------------|-----------|-----------|
| **on_topic** | 아카자, 렌고쿠, 전투, 구출 | Guardrail Agent | 게임 로직 처리 |
| **off_topic** | 안녕, 날씨, 취미, 일반대화 | Children Agent | 캐주얼 응답 |

---

## 3. Parent Agent 게임 로직

### 3-1. 컷신 관리 플로우

```mermaid
sequenceDiagram
    participant U as User
    participant P as Parent Agent
    participant S as State Tools
    participant SC as Scene Tools
    participant C as Children Agent
    
    U->>P: 사용자 입력
    P->>S: 현재 씬 상태 조회
    S->>P: 씬 정보 반환
    P->>SC: 컷신 이미지 요청
    SC->>P: 이미지 URL
    P->>C: 대사 생성 요청
    C->>P: 캐릭터 대사
    P->>S: 턴 증가
    P->>U: 컷신 응답
```

### 3-2. 설득 미션 처리

```mermaid
flowchart TD
    A[설득 미션 시작] --> B[대상 캐릭터 확인]
    B --> C[설득 키워드 분석]
    C --> D{키워드 매칭}
    D -->|성공| E[친밀도 증가]
    D -->|실패| F[친밀도 감소]
    E --> G[성공 응답 생성]
    F --> H[실패 응답 생성]
    G --> I[턴 소모]
    H --> I
    I --> J{미션 완료?}
    J -->|No| B
    J -->|Yes| K[결과 판정]
    
    subgraph "판정 조건"
        L[히든엔딩:<br/>- 순서 준수<br/>- 친밀도 조건<br/>- 턴 제한]
        M[일반엔딩:<br/>- 조건 미충족]
    end
    
    K --> L
    K --> M
```

---

## 4. Children Agent 대화 생성

### 4-1. 친밀도 기반 응답 시스템

```mermaid
graph TD
    A[Parent Agent 요청] --> B[활성 캐릭터 확인]
    B --> C[친밀도 레벨 조회]
    C --> D{친밀도 구간}
    D -->|Low 0-299| E[경계/조심스러운 톤]
    D -->|Mid 300-699| F[친근한 톤]
    D -->|High 700-1000| G[친밀한 톤]
    E --> H[OpenAI 대사 생성]
    F --> H
    G --> H
    H --> I[감정 상태 설정]
    I --> J[최종 응답]
```

### 4-2. 캐릭터별 특성 테이블

| 캐릭터 | 성격 특징 | 친밀도별 말투 | 특별 반응 |
|--------|-----------|---------------|-----------|
| **탄지로** | 성실하고 따뜻함 | Low: 존댓말<br/>Mid: 친근한 존댓말<br/>High: 편안한 반말 | 네즈코 관련 시 열정적 |
| **이노스케** | 거칠고 자존심 강함 | Low: 적대적<br/>Mid: 경계하는 태도<br/>High: 인정하는 태도 | 도발에 즉시 반응 |
| **젠이츠** | 겁 많지만 의리 있음 | Low: 두려워함<br/>Mid: 조심스러움<br/>High: 의지하는 태도 | 네즈코 언급 시 각성 |
| **렌고쿠** | 열정적이고 의리 있음 | 항상 격려와 조언 | 후배 보호 본능 |

---

## 5. State Tools 상태 관리

### 5-1. 게임 상태 관리 플로우

```mermaid
graph TB
    A[상태 업데이트 요청] --> B[현재 상태 로드]
    B --> C[친밀도 변경 적용]
    C --> D[턴 수 업데이트]
    D --> E[플래그 상태 확인]
    E --> F[히든엔딩 조건 검증]
    F --> G{조건 충족 여부}
    G -->|Yes| H[히든엔딩 플래그 설정]
    G -->|No| I[일반 진행]
    H --> J[DB 저장]
    I --> J
    
    subgraph "관리 데이터"
        K[게임 진행:<br/>시나리오/씬 ID<br/>턴 수/남은 턴]
        L[캐릭터 상태:<br/>친밀도/레벨<br/>활성 캐릭터]
        M[진행 플래그:<br/>선택 기록<br/>설득 결과<br/>순서 준수]
    end
```

### 5-2. 히든엔딩 조건 테이블

| 조건 항목 | 요구사항 | 검증 시점 |
|-----------|----------|-----------|
| **순서 준수** | 이노스케 → 젠이츠 순서 | 설득 완료 시 |
| **친밀도 조건** | 이노스케 350+, 젠이츠 450+ | 미션 종료 시 |
| **턴 제한** | 전체 6턴 내 완료 | 매 턴 확인 |
| **설득 성공** | 두 캐릭터 모두 성공 | 미션 완료 시 |

---

## 6. Scene Tools 리소스 관리

### 6-1. 이미지 에셋 처리 플로우

```mermaid
flowchart TD
    A[이미지 요청] --> B{에셋 타입}
    B -->|cutscene| C[컷신 이미지]
    B -->|emotion| D[감정 이미지]
    B -->|special| E[특별 이미지]
    
    C --> F[씬 ID + 턴 기반<br/>이미지 선택]
    D --> G[캐릭터 + 감정<br/>조합 매칭]
    E --> H[AI 이미지 생성<br/>또는 특별 에셋]
    
    F --> I[이미지 URL 반환]
    G --> I
    H --> I
    
    subgraph "에셋 카테고리"
        J[컷신: 씬별 배경<br/>상황 이미지]
        K[감정: 캐릭터별<br/>표정 변화]
        L[특별: 히든엔딩<br/>생성 이미지]
    end
```

---

## 7. 시나리오 확장 시스템

### 7-1. JSON 기반 시나리오 로딩

```mermaid
flowchart LR
    A[시나리오 JSON 파일] --> B[Parent Agent]
    B --> C{스테이지 타입}
    C -->|cutscene| D[컷신 모드]
    C -->|choice| E[선택지 모드]  
    C -->|mission| F[미션 모드]
    C -->|branch| G[분기 모드]
    
    D --> H[다음 스테이지]
    E --> H
    F --> H
    G --> H
    
    subgraph "확장 구조"
        I[새 시나리오:<br/>JSON 파일 추가]
        J[새 캐릭터:<br/>profiles 수정]
        K[새 룰:<br/>routing_rules 수정]
    end
```

### 7-2. 시나리오 데이터 구조

```mermaid
erDiagram
    SCENARIO {
        string scenario_id
        string title
        object stages
    }
    
    STAGE {
        string type
        int max_turns
        array dialogues
        string next_stage
    }
    
    CHARACTER {
        string name
        array keywords
        array responses
        int max_attempts
    }
    
    ENDING {
        string id
        array conditions
        string title
    }
    
    SCENARIO ||--o{ STAGE : contains
    STAGE ||--o{ CHARACTER : includes
    SCENARIO ||--o{ ENDING : defines
```

---

## 8. 전체 데이터 흐름 다이어그램

```mermaid
sequenceDiagram
    participant U as User
    participant R as Router
    participant G as Guardrail
    participant P as Parent
    participant C as Children
    participant ST as State Tools
    participant SC as Scene Tools
    participant DB as Database
    participant AI as OpenAI API
    
    Note over U,AI: 사용자 입력부터 최종 응답까지
    
    U->>R: 사용자 메시지
    R->>AI: 입력 분류 요청
    AI->>R: 분류 결과
    
    alt on_topic 경로
        R->>G: 안전성 검증
        G->>P: 게임 로직 처리
        P->>ST: 상태 조회/업데이트
        ST->>DB: 데이터 읽기/쓰기
        DB->>ST: 상태 정보
        ST->>P: 업데이트된 상태
        P->>SC: 이미지 요청
        SC->>P: 이미지 URL
        P->>C: 대사 생성 요청
        C->>AI: 캐릭터 대사 생성
        AI->>C: 생성된 대사
        C->>P: 최종 대사
        P->>U: 게임 응답
    else off_topic 경로
        R->>C: 일반 대화 처리
        C->>AI: 캐주얼 응답 생성
        AI->>C: 응답 텍스트
        C->>U: 일반 응답
    end
```

---

## 9. 기술 스택 및 성능 지표

### 9-1. 핵심 기술 스택

```mermaid
graph TB
    subgraph "AI/ML 기술"
        A1[OpenAI GPT-4<br/>입력 분류 & 대사 생성]
        A2[LangGraph<br/>멀티에이전트 워크플로우]
        A3[Python 3.12<br/>메인 개발 언어]
    end
    
    subgraph "백엔드 기술"
        B1[FastAPI<br/>REST API 서버]
        B2[WebSocket<br/>실시간 통신]
        B3[SQLite/PostgreSQL<br/>게임 상태 저장]
    end
    
    subgraph "프론트엔드 기술"
        C1[React/Vue.js<br/>사용자 인터페이스]
        C2[Socket.io<br/>실시간 클라이언트]
        C3[Material-UI<br/>UI 컴포넌트]
    end
    
    A1 --> B1
    A2 --> B1
    B1 --> C1
    B2 --> C2
```

### 9-2. 성능 목표 및 지표

| 항목 | 목표 수치 | 측정 방법 |
|------|-----------|-----------|
| **Router Agent 응답시간** | < 1초 | API 모니터링 |
| **Parent Agent 처리시간** | < 2초 | 내부 로깅 |
| **Children Agent 생성시간** | < 3초 | OpenAI API 측정 |
| **전체 응답시간** | < 5초 | End-to-End 테스트 |
| **동시 접속 지원** | 100명+ | 부하 테스트 |
| **시스템 가용성** | 99.9% | 업타임 모니터링 |

---

## 🎯 시스템 특징 및 확장성

### 주요 특징
- **모듈화된 에이전트 구조**: 각 에이전트의 독립적 개발/테스트 가능
- **확장 가능한 시나리오 시스템**: JSON 파일 기반으로 코드 수정 없이 새 시나리오 추가
- **실시간 상태 동기화**: WebSocket 기반 멀티플레이어 지원 준비
- **AI 기반 자연어 처리**: OpenAI GPT-4를 활용한 정교한 입력 분석 및 응답 생성

### 확장성 고려사항
- **마이크로서비스 전환 준비**: 각 에이전트를 독립 서비스로 분리 가능
- **다중 시나리오 지원**: 데몬슬레이어 외 다른 테마 시나리오 추가 용이
- **다국어 지원**: 캐릭터 대사 및 UI 다국어 확장 구조
- **모바일 플랫폼 확장**: React Native/Flutter 기반 모바일 앱 개발 가능

이 시스템 아키텍처는 확장 가능하고 유지보수가 용이한 구조로 설계되어, 향후 새로운 기능 추가나 플랫폼 확장 시에도 안정적으로 대응할 수 있습니다.
