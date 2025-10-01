# [모델링 및 평가] 시스템 아키텍처

**SK Networks Family AI Camp 15기 - 데몬슬레이어팀**  
**GitHub**: https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM  
**작성자**: 권도원, 이준원, 조태민  
**제출 일자**: 2025.10.01  

---

## 1. LangGraph 에이전트 워크플로우

```mermaid
flowchart TD
  subgraph Client
    U[User 입력]
  end
  subgraph Agents
    R[Router Agent]
    G[Guardrail Agent]
    P[Parent Agent]
    C[Children Agent]
    D[Dialogue Agent]
  end
  subgraph Tools
    ST[State Tools]
    SC[Scene Tools]
  end
  subgraph AI
    OAI[OpenAI GPT-4/3.5]
    NB[나노바나나]
  end
  subgraph DB
    PG[PostgreSQL]
    RD[Redis]
    FS[파일 시스템]
  end

  U --> R
  R -->|on_topic| G
  R -->|off_topic| C

  G -->|심각 위반| GW[경고 창]
  G -->|경미 위반| C
  G -->|안전| P

  P <--> ST
  P -->|컷신/특별 이미지| SC
  P -->|대화| C

  C <--> ST
  C --> D

  SC --> NB
  SC --> FS
  NB --> SC

  D --> U

  R -.-> OAI
  C -.-> OAI
  D -.-> OAI
```  

---

## 2. Router Agent

```mermaid
flowchart LR
  U[User 입력] --> R[Router Agent]
  R -->|on_topic| G[Guardrail Agent]
  R -->|off_topic| C[Children Agent]
```  

| 분류     | 기준                     | 다음 노드       |
|----------|--------------------------|-----------------|
| on_topic | 시나리오 키워드 포함     | Guardrail Agent |
| off_topic| 일반 대화               | Children Agent  |

---

## 3. Guardrail Agent

```mermaid
flowchart TD
  R --> G
  G -->|심각| GW[경고 창]
  G -->|경미| C
  G -->|안전| P
```  

---

## 4. Parent Agent & State Tools

```mermaid
sequenceDiagram
  participant U as User
  participant P as Parent Agent
  participant ST as State Tools
  participant SC as Scene Tools
  participant C as Children Agent
  participant D as Dialogue Agent

  U->>P: 시작 또는 입력
  P->>ST: 이전 상태 로드
  ST->>PG: DB 조회
  PG->>ST: 상태 반환
  ST->>P: 상태 정보

  alt 이미지 필요
    P->>SC: 컷신/특별 이미지 요청
    SC->>FS: 사전 저장 이미지 로드
    SC-->>P: 이미지 전달
  else 대화 필요
    P->>C: 대사 요청
    C->>ST: 상태 확인
    ST->>C: 캐릭터 정보
    C->>OAI: 대사 생성
    OAI->>C: 대사 반환
    C-->>P: 대사 전달
  end

  P->>D: 검증 요청
  D->>OAI: 품질 검증
  OAI->>D: 검증 결과
  D-->>P: 검증된 대사
  P-->>U: 최종 응답
  P->>ST: 상태 업데이트
  ST->>PG: DB 저장
```  

---

## 5. Scene Tools & 이미지 처리

```mermaid
flowchart TB
  P -->|컷신 이미지 요청| SC
  C -->|감정 이미지 요청| SC

  subgraph StoredImages
    SC --> FS
  end

  subgraph SpecialImage
    P -->|특별 이미지 요청| SC
    SC -->|대화 히스토리 요청| ST
    ST -->|히스토리 조회| PG
    PG -->|대화 요약 생성| ST
    ST -->|요약 기반 이미지 생성| NB
    NB -->|특별 이미지 전달| SC
  end

  SC -->|컷신 이미지| P
  SC -->|감정 이미지| C
  SC -->|특별 이미지| P


```  

---

## 6. Children & Dialogue Agent

```mermaid
flowchart LR
  P --> C
  C --> ST
  ST --> C
  C --> D
  D --> OAI
  OAI --> D
  D --> P
```  

---

## 7. 기술 스택

```mermaid
graph LR
  subgraph Backend
    DJ[Django]
    GN[Gunicorn]
    NG[Nginx]
  end
  subgraph Frontend
    RE[React + HTML/CSS]
    WS[WebSocket]
  end
  subgraph AI
    OA[OpenAI GPT]
    NB[나노바나나]
  end
  subgraph Data
    PG[PostgreSQL]
    RD[Redis]
    FS[파일 시스템]
  end

  RE --> NG
  NG --> DJ
  DJ --> GN
  DJ --> PG
  DJ --> RD
  SC --> NB
  C --> OA
```  

---

## 8. 요약

- **on/off topic** 분류만 수행  
- **Guardrail**: 심각/경미/안전 대응  
- **Parent → Scene/Children → Dialogue** 에이전트 분리  
- **State Tools**: DB 상태 로드/업데이트  
- **Scene Tools**: 이미지 로드 및 실시간 생성  
- **나노바나나**: 특별 이미지 실시간 생성  
