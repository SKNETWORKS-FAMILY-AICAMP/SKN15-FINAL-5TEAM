# 멘토링 데모 SQL 쿼리 가이드

## 📁 파일 구성

```
demo_queries/
├── 01_session_check.sql          # 세션 생성 확인
├── 02_dialogues_check.sql         # 대화 저장 확인
├── 03_training_logs_check.sql     # AI 학습 로그 확인
├── 04_entities_check.sql          # 엔티티 추출 확인
├── 05_entity_mentions_check.sql   # 엔티티 멘션 상세
├── 06_conversation_summary_check.sql  # ⭐ 대화 요약 (하이라이트!)
├── 07_overall_stats.sql           # 전체 데이터 현황
├── 08_performance_analysis.sql    # 성능 분석
├── 09_user_memories.sql           # 장기 기억 (임베딩)
└── README.md                      # 이 파일
```

---

## 🚀 빠른 시작

### 1단계: DBeaver 연결 설정

```
Host: 127.0.0.1
Port: 5433
Database: kimedb
Username: kime
Password: dev123
```

### 2단계: 데모 시나리오

1. **첫 번째 채팅 후** → `01_session_check.sql` 실행
   - 새 세션 ID 복사!

2. **세션 ID를 모든 쿼리에 붙여넣기**
   - 각 SQL 파일에서 `'여기에_세션_ID_붙여넣기'` 부분을 실제 세션 ID로 변경

3. **채팅 3번 후** → `02_dialogues_check.sql`, `03_training_logs_check.sql` 실행

4. **채팅 5번 후** → `04_entities_check.sql`, `05_entity_mentions_check.sql` 실행

5. **채팅 10번 후 (하이라이트!)** → `06_conversation_summary_check.sql` 실행
   - **"요약이 자동으로 생성되었습니다!"** 강조

6. **데모 종료 시** → `07_overall_stats.sql`, `08_performance_analysis.sql` 실행

---

## 🎬 데모 스크립트

### 오프닝 (30초)
"안녕하세요. 오늘은 제가 만든 AI 채팅 시스템의 데이터 파이프라인을 실시간으로 보여드리겠습니다."

**화면 구성:**
- 왼쪽: 브라우저 (채팅창)
- 오른쪽: DBeaver (SQL 쿼리)

---

### Demo 1: 세션 생성 (1분)

**채팅 입력:**
```
"안녕하세요"
```

**실행할 쿼리:** `01_session_check.sql`

**말할 내용:**
"지금 '안녕하세요'라고 입력했습니다. 이 쿼리를 실행하면..."

**예상 결과:**
```
session_id: uuid-123...
turn_count: 1
scenario_id: train
```

**세션 ID를 복사하세요!**

---

### Demo 2: 대화 저장 (2분)

**채팅 계속:**
```
"무한열차에 대해 알려주세요"
"렌고쿠는 어떤 사람인가요?"
```

**실행할 쿼리:** `02_dialogues_check.sql` (세션 ID 붙여넣기 필수!)

**말할 내용:**
"보시는 것처럼 방금 입력한 대화가 데이터베이스에 저장되었습니다. 사용자 입력뿐만 아니라 AI의 응답(narr, rengoku, tanjiro)도 모두 저장되고 있습니다."

**예상 결과:**
```
Turn 1: user → "안녕하세요"
Turn 1: tanjiro → "지금은 임무에 집중..."
Turn 3: user → "무한열차에 대해..."
Turn 3: narr → "무한열차의 내부는..."
Turn 3: rengoku → "무한열차는 전설적인..."
```

---

### Demo 3: AI 학습 로그 (1분)

**실행할 쿼리:** `03_training_logs_check.sql`

**말할 내용:**
"각 AI 에이전트의 실행 기록도 모두 저장됩니다. 보시면 guardrail은 입력 검증, router는 의도 분석, parent_agent는 메인 로직, children_agent는 대화 생성을 담당합니다."

**예상 결과:**
```
guardrail: 2501ms
router: 2796ms
parent_agent: 7253ms
children_agent: 1062ms
dialogue_agent: 0.1ms (매우 빠름!)
```

---

### Demo 4: 엔티티 추출 (2분)

**채팅 계속:**
```
"아카자와 싸워야 하나요?"
"불의 호흡을 배우고 싶어요"
```

**실행할 쿼리:** `04_entities_check.sql`

**말할 내용:**
"NLP 기반으로 대화에서 자동으로 엔티티를 추출합니다. '아카자', '불의 호흡', '렌고쿠' 등이 자동으로 인식되었네요."

**예상 결과:**
```
아카자 (character): 언급 3회
불의 호흡 (skill): 언급 2회
렌고쿠 (character): 언급 2회
```

**추가 쿼리:** `05_entity_mentions_check.sql` (어떤 문맥에서 언급되었는지)

---

### Demo 5: 대화 요약 자동 생성 ⭐ (3분, 하이라이트!)

**채팅 계속 (10턴까지):**
```
"히노카미 카구라는 무엇인가요?"
"우리는 어디로 가야 하나요?"
"승객들이 이상해요"
"이 상황을 어떻게 해결해야 할까요?"
"모두를 지켜야 해요"
```

**실행할 쿼리:** `06_conversation_summary_check.sql`

**말할 내용 (천천히, 강조하면서):**
"이제 10번째 대화를 입력했습니다. 여기서 특별한 일이 일어나는데요..."

*쿼리 실행*

"보세요! 지금까지의 대화가 자동으로 요약되었습니다! LLM이 주요 이벤트, 캐릭터 관계, 게임 목표를 모두 파악했네요!"

**예상 결과:**
```
turn_count: 19
summary_turn_count: 11
summary_length: 441자
conversation_summary: "현재 스테이지는 TRAIN_PRELUDE이며, 주요 캐릭터는 Tanjiro와 Rengoku입니다. Tanjiro는 임무에 집중해야 한다고 강조하며, 대화는 무한열차에 대한 조사로 이어집니다..."
```

**이 부분에서 잠시 멈추고 요약 내용을 읽어주세요!**

---

### Demo 6: 전체 데이터 현황 (1분)

**실행할 쿼리:** `07_overall_stats.sql`

**말할 내용:**
"보시는 것처럼 한 번의 대화로 8개 테이블에 데이터가 저장되었습니다! 이 모든 것이 자동으로 수집되어, AI 학습과 개인화에 활용됩니다!"

**예상 결과:**
```
Sessions: 1
Dialogues: 48
Training Logs: 60
Entities: 8
Entity Mentions: 12
User Memories: 17
...
```

---

### Demo 7: 성능 분석 (1분, 선택사항)

**실행할 쿼리:** `08_performance_analysis.sql`

**말할 내용:**
"parent_agent가 가장 느린 이유는 LLM을 호출하기 때문입니다. dialogue_agent는 단순 형식 정리라서 0.1ms로 매우 빠릅니다."

---

### 클로징 (30초)

**핵심 메시지:**
"실시간 채팅이 → 6가지 데이터로 → 자동 저장됩니다"

1. 💬 대화 (Dialogues)
2. 📊 학습 로그 (Training Logs)
3. 🏷️ 엔티티 (Entities)
4. 📌 엔티티 멘션 (Entity Mentions)
5. 🧠 세션 상태 (Sessions)
6. 📝 **대화 요약 (Conversation Summary)** ← 하이라이트!

---

## 💡 팁

### DBeaver 설정

1. **SQL 에디터 설정**
   - Font Size: 14pt 이상 (화면 공유 시 잘 보임)
   - Line Numbers: 활성화
   - Result Grid: Auto-refresh 비활성화

2. **단축키**
   - `Ctrl+Enter` (Mac: `Cmd+Enter`): 현재 쿼리 실행
   - `Ctrl+\` (Mac: `Cmd+\`): 결과 창 전환

### 데모 준비

1. **사전에 한 번 리허설 해보기**
2. **세션 ID를 빠르게 복사할 수 있도록 준비**
3. **모든 쿼리를 DBeaver에 미리 열어두기** (탭으로)
4. **화면 레이아웃 미리 설정**

### 예상 질문 & 답변

**Q: "왜 Turn이 1, 3, 5로 증가하나요?"**
A: "각 턴마다 사용자 입력(+1)과 에이전트 응답(+1)이 있어서 내부적으로 2씩 증가합니다."

**Q: "실시간으로 요약이 생성되나요?"**
A: "네, 10턴마다 자동으로 생성됩니다. 약 2-3초 정도 소요되며, gpt-4o-mini 모델을 사용합니다."

**Q: "데이터베이스 성능은 어떤가요?"**
A: "PostgreSQL을 사용하고 있으며, 인덱싱과 파티셔닝으로 최적화했습니다."

**Q: "임베딩은 어떻게 사용하나요?"**
A: "pgvector 확장을 사용해서 의미 기반 검색을 합니다. 예를 들어 '불의 호흡'과 유사한 기억을 찾을 수 있습니다."

---

## ⚠️ 주의사항

1. **세션 ID 복사 필수!**
   - 01번 쿼리 실행 후 session_id를 바로 복사
   - 02-09번 쿼리의 `'여기에_세션_ID_붙여넣기'`를 실제 값으로 변경

2. **Turn Count 이해**
   - Turn 1, 3, 5, 7, 9, 11... (2씩 증가)
   - Turn 10+ 에서 요약 생성
   - Turn 11 또는 13에서 요약 확인

3. **LLM 응답 시간**
   - 각 채팅마다 2-5초 소요
   - 인내심을 가지고 기다리기

4. **백업 계획**
   - 만약 실시간 데모가 안되면, 미리 준비한 세션 ID 사용
   - 예: `5bf5a121-c9c8-4f70-9658-60b8cba99fa2`

---

## 🎯 타이밍 가이드 (총 10분)

| 시간 | 활동 | 쿼리 | 중요도 |
|------|------|------|--------|
| 0:00-0:30 | 오프닝 | - | - |
| 0:30-1:30 | 세션 생성 | 01 | ★★ |
| 1:30-3:30 | 대화 저장 | 02 | ★★★ |
| 3:30-4:30 | 학습 로그 | 03 | ★★ |
| 4:30-6:30 | 엔티티 추출 | 04, 05 | ★★★ |
| 6:30-9:30 | **대화 요약** | **06** | **★★★★★** |
| 9:30-10:00 | 전체 요약 | 07, 08 | ★★ |

---

## ✅ 체크리스트

**데모 전:**
- [ ] PostgreSQL 실행 확인 (port 5433)
- [ ] API 서버 실행 확인 (port 8000)
- [ ] DBeaver 연결 확인
- [ ] 모든 SQL 파일을 DBeaver에 열어두기
- [ ] 화면 레이아웃 설정 (브라우저 | DBeaver)
- [ ] 폰트 크기 조정 (화면 공유 시 잘 보이게)

**데모 중:**
- [ ] 01번 실행 → 세션 ID 복사
- [ ] 02-09번에 세션 ID 붙여넣기
- [ ] 채팅 입력 → 쿼리 실행 → 설명
- [ ] 06번 (대화 요약) 강조!

**데모 후:**
- [ ] 질문 받기
- [ ] README.md 링크 공유
- [ ] 세션 데이터 보존

---

## 🔗 참고 링크

- 프로젝트 README: `/Users/jtm427/Desktop/workspace/taemin_record/README.md`
- 데모 전략 문서: `/Users/jtm427/Desktop/workspace/taemin_record/99_mentoring_demo_strategy.md`
- 데이터베이스 스키마: `/Users/jtm427/Desktop/workspace/backend/database/migrations/`

---

## 🎉 Good Luck!

**핵심 메시지를 잊지 마세요:**
"실시간 채팅이 → 6가지 데이터로 → 자동 저장됩니다!"

특히 **06번 대화 요약**이 가장 인상적인 부분입니다!
