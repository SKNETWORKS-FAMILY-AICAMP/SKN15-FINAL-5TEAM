# INTRO 스테이지 수정 사항 정리

> 작성자: 태민
> 작성일: 2025-10-19
> 목적: INTRO 대화를 6개 → 10개 이상으로 확장, 스토리 흐름 개선

---

## 📋 수정 개요

### 목표
- INTRO 대화 개수: 6개 → **10개 이상** 확장
- 나레이션: **맨 처음 1회만** 출력
- 아카자: **마지막 1회만** 등장
- 비유 제거: "철의 뱀" → "열차" (직접적 표현)
- 아카자 등장 **지연**: 구호 활동 후 등장

### 결과
- ✅ 대화 개수: **14개** 생성 (목표 달성)
- ✅ 스토리 흐름: 탈선 → 구호 → 아카자 등장 → 전투 선언
- ✅ ROUTE_CHOICE로 자연스럽게 연결

---

## 🔧 수정 파일 및 내용

### 1. JSON 파일: `cutscene5_llm_driven.json`

**파일 경로**: `SKN15-FINAL-5TEAM/data/scenarios/cutscene5_llm_driven.json`

**수정 위치**: Line 156-204 (`beats_intro` 배열만)

#### 변경 전 (6개 beats)
```json
"beats_intro": [
  {
    "goal": "【비유적 묘사】엔무라는 거대한 괴물이 쓰러지자, 철의 뱀(열차)은 균형을 잃고...",
    "speaker_hint": ["narr"],
    "fx": "..."
  },
  // ... 총 6개
]
```

#### 변경 후 (10개 beats)
```json
"beats_intro": [
  {
    "goal": "【상황 설명】열차가 격렬하게 흔들리더니 탈선했다. 브레이크가 비명을 지르며 금속이 갈리는 소리가 울려퍼진다. 유리창이 깨지고 파편이 날아다닌다. 자욱한 먼지와 연기가 객차 안을 가득 채우며 시야를 가린다. 승객들의 신음 소리가 여기저기서 들려온다",
    "speaker_hint": ["narr"],
    "fx": "brake_screech|ash_wind|ground_fissure"
  },
  {
    "goal": "{user}가 천천히 정신을 차리고 주변을 살핀다. 탄지로가 다급하게 달려와 {user}의 안전을 확인하며 안도한다",
    "speaker_hint": ["tanjiro"]
  },
  {
    "goal": "탄지로가 '엔무를 쓰러뜨렸지만 열차가 완전히 망가졌다'고 설명한다. 주변에 부상자가 많아 빨리 구조해야 한다고 말한다",
    "speaker_hint": ["tanjiro"],
    "fx": "ember_fall"
  },
  {
    "goal": "탄지로가 고통스럽게 옆구리를 붙잡으며 복부 출혈이 심각함을 토로한다. 전집중 호흡으로 출혈을 막아야 한다고 {user}에게 알린다",
    "speaker_hint": ["tanjiro"]
  },
  {
    "goal": "렌고쿠가 등장하여 {user}와 탄지로를 '훌륭하다! 잘 버텼다!'며 칭찬한다. 탄지로에게 출혈 치료에 집중하라고 격려한다",
    "speaker_hint": ["rengoku"],
    "fx": "ember_swirl"
  },
  {
    "goal": "렌고쿠가 승객들의 상태를 확인하고 {user}에게 부상자 구조를 도와달라고 요청한다. 탄지로도 움직일 수 있는 사람들을 안전한 곳으로 대피시키자고 제안한다",
    "speaker_hint": ["rengoku", "tanjiro"]
  },
  {
    "goal": "갑자기 강력한 충격이 지면을 흔든다. 섬뜩한 살기가 느껴지며 공기가 차갑게 식는다. 렌고쿠의 표정이 굳어지며 경계 태세를 취한다",
    "speaker_hint": ["rengoku"],
    "fx": "ground_fissure|pulse_boom|air_freeze"
  },
  {
    "goal": "먼지 속에서 아카자가 모습을 드러낸다. 상현 삼의 눈동자가 섬뜩하게 빛나며 렌고쿠를 '지주(柱)인가'라고 파악한다",
    "speaker_hint": ["akaza", "rengoku"],
    "fx": "kanji_flash"
  },
  {
    "goal": "아카자가 순식간에 움직여 부상당한 탄지로 앞에 나타난다. 렌고쿠가 번개처럼 탄지로를 밀쳐내고 검을 뽑아 막아선다. 칼날과 주먹이 격돌하며 불꽃이 터진다",
    "speaker_hint": ["akaza", "rengoku"],
    "fx": "blink_dash|shockwave_snap|flame_ignition"
  },
  {
    "goal": "아카자가 '혈귀가 되어 영원히 강해지라'고 제안하지만 렌고쿠는 단호히 거절한다. 아카자가 '혈귀가 되지 않겠다면 죽일 수밖에'라고 선언하며 술식을 전개한다(파괴살・나침!). 발밑으로 눈꽃 모양의 진이 펼쳐지며 공기가 얼어붙는다",
    "speaker_hint": ["akaza", "rengoku", "tanjiro"],
    "fx": "heart_drop|pulse_boom"
  }
]
```

#### 주요 변경점
- Beat 개수: 6개 → **10개**
- Beat 1: 비유("철의 뱀") 제거, 직접적 표현("열차 탈선") 사용
- 아카자 등장 시점: Beat 5 → **Beat 8**로 지연
- 스토리 구조:
  - Beat 1: 나레이션 (탈선 상황)
  - Beat 2-6: 구호 활동 (탄지로, 렌고쿠)
  - Beat 7-10: 아카자 등장 및 전투 선언

**⚠️ 중요**: `beats_intro` 배열만 수정, 다른 설정(constraints, speaker_pool, 다른 스테이지)은 건드리지 않음

---

### 2. Parent Agent: `parent_agent.py`

**파일 경로**: `SKN15-FINAL-5TEAM/src/agents/parent_agent.py`

**수정 위치**: Line 197-212

#### 추가된 코드
```python
# INTRO 스테이지에서만 beats를 턴마다 slice하여 점진적으로 전달
if stage_tag.upper() == "INTRO" and len(beats_all) > 3:
    turn_count = state.get("turn_count", 0)
    beat_index = min(turn_count, len(beats_all) - 1)
    beats_slice = [beats_all[beat_index]]

    # INTRO에서는 전체 speaker_pool 사용 (대사 자유도 증가)
    # speaker_hint는 사용하지 않음 - children_agent에서 필터링 처리
    speakers = _speaker_pool_for_stage(stage)
else:
    beats_slice = beats_all
    speakers = _speaker_pool_for_stage(stage)
```

#### 기존 코드 (참고)
```python
beats_slice = beats_all
speakers = _speaker_pool_for_stage(stage)
```

#### 주요 변경점
- **INTRO 스테이지만** `if stage_tag.upper() == "INTRO"` 조건으로 분기
- INTRO: beats를 턴마다 1개씩 slice (점진적 스토리 전개)
- INTRO: 전체 speaker_pool 사용 (대사 자유도 증가)
- **다른 스테이지**: `else` 블록에서 기존 로직 그대로 유지

**⚠️ 중요**: `if` 조건문으로 INTRO만 특별 처리, 다른 스테이지 영향 없음

---

### 3. Children Agent: `children_agent.py`

**파일 경로**: `SKN15-FINAL-5TEAM/src/agents/children_agent.py`

#### 3-1. 프롬프트 수정 (Line 317-365)

**변경 전**
```python
dialogue_rule = "**자유로운 연출**: 발화자, 대사 순서, 대화량(2~4명)을 자유롭게 결정"

system_prompt = f"""당신은 귀멸의 칼날 스토리 게임의 **연출가이자 배우**입니다.
...
1. {dialogue_rule}
...
"""

user_prompt = f'사용자 입력: "{user_input}"\n위 상황을 반영하여 캐릭터별 대사를 생성하세요.\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}}]}}'
```

**변경 후**
```python
# INTRO 스테이지에서는 더 많은 대화를 생성
if stage_tag.upper() == "INTRO":
    dialogue_rule = """**풍부한 연출**: 인트로 씬이므로 **최소 10개 이상**의 대화를 생성하여 상황을 충분히 전달
   - 각 상황 설명마다 1-2개씩 대사를 배치하여 스토리를 순차적으로 전개
   - narr는 맨 처음 1회만, akaza는 마지막에 1회만 등장
   - tanjiro와 rengoku가 주로 대화를 이끌어가며 상황을 설명"""
else:
    dialogue_rule = "**자유로운 연출**: 발화자, 대사 순서, 대화량(2~4명)을 자유롭게 결정"

system_prompt = f"""당신은 귀멸의 칼날 스토리 게임의 **연출가이자 배우**입니다.
...
1. {dialogue_rule}
...
"""

# INTRO에서는 최소 10개 대화 생성 요구
if stage_tag.upper() == "INTRO":
    user_prompt = f'사용자 입력: "{user_input}"\n\n위 "현재 상황"의 각 단계를 **순서대로** 반영하여 **최소 10개 이상**의 캐릭터 대사를 생성하세요.\n- narr는 맨 처음 1회만\n- akaza는 마지막 상황에서 1회만\n- 나머지는 tanjiro, rengoku가 상황을 설명하며 대화\n\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}},{{"speaker":"...","text":"..."}},...]}}'
else:
    user_prompt = f'사용자 입력: "{user_input}"\n위 상황을 반영하여 캐릭터별 대사를 생성하세요.\nJSON: {{"dialogues":[{{"speaker":"...","text":"..."}}]}}'
```

**주요 변경점**
- **INTRO만** `if stage_tag.upper() == "INTRO"` 조건으로 분기
- INTRO: "최소 10개 이상", "narr 1회", "akaza 1회", "순차적 전개" 명시
- **다른 스테이지**: 기존 프롬프트 그대로 유지 (`else` 블록)

#### 3-2. 나레이션 필터링 추가 (Line 375-398)

**변경 전**
```python
for it in items:
    sp = _normalize_speaker(it.get("speaker", ""))
    tx = _normalize_text(it.get("text", ""))
    if not sp or not tx:
        continue

    # INTRO 스테이지에서는 speaker_pool을 엄격하게 필터링
    if stage_tag.upper() == "INTRO":
        # speaker_pool에 없는 캐릭터는 제외
        if sp not in speakers:
            logger.info(f"[INTRO] Skipping speaker '{sp}' not in speaker_pool: {speakers}")
            continue
```

**변경 후**
```python
# INTRO에서 narr가 이미 나왔는지 추적
narr_already_output = False

for it in items:
    sp = _normalize_speaker(it.get("speaker", ""))
    tx = _normalize_text(it.get("text", ""))
    if not sp or not tx:
        continue

    # INTRO 스테이지에서는 speaker_pool을 엄격하게 필터링
    if stage_tag.upper() == "INTRO":
        # speaker_pool에 없는 캐릭터는 제외
        if sp not in speakers:
            logger.info(f"[INTRO] Skipping speaker '{sp}' not in speaker_pool: {speakers}")
            continue

        # 나레이션은 맨 처음 딱 한 번만 허용
        turn_idx = int(_state_get(state, "turn_index", 0) or 0)
        if sp == "narr":
            # turn 0이 아니거나, 이미 narr가 출력되었으면 스킵
            if turn_idx > 0 or narr_already_output:
                logger.info(f"[INTRO] Skipping narr - turn_idx={turn_idx}, already_output={narr_already_output}")
                continue
            narr_already_output = True
```

**주요 변경점**
- **INTRO만** 나레이션 필터링 로직 추가
- `narr_already_output` 플래그로 narr가 1회만 출력되도록 제어
- turn_idx > 0이면 narr 스킵
- **다른 스테이지**: 영향 없음

---

## 🔒 다른 조원 작업과의 충돌 방지

### ✅ 안전한 이유

#### 1. JSON 수정
- 오직 `beats_intro` 배열만 수정
- `beats_route_choice`, `beats_intervene`, `beats_recruit` 등 **다른 스테이지 beats 건드리지 않음**
- `constraints`, `speaker_pool`, `affinity_thresholds` 등 **전역 설정 건드리지 않음**

#### 2. Parent Agent
- `if stage_tag.upper() == "INTRO"`로 조건 분기
- INTRO만 특별 처리
- 다른 스테이지는 `else` 블록에서 **기존 로직 그대로 실행**

#### 3. Children Agent
- `if stage_tag.upper() == "INTRO"`로 조건 분기
- INTRO만 프롬프트 변경 및 필터링 적용
- 다른 스테이지는 `else` 블록에서 **기존 프롬프트 및 로직 유지**

### ⚠️ 주의사항

다음 파일들을 다른 조원이 수정했다면 충돌 가능:
- `cutscene5_llm_driven.json`의 `beats_intro` (Line 156-204)
- `parent_agent.py` (Line 197-212)
- `children_agent.py` (Line 317-398)

**해결 방법**: Git에서 확인 후 조원과 상의
```bash
cd SKN15-FINAL-5TEAM
git status
git diff
```

---

## 📊 수정 요약표

| 파일 | 라인 | 변경 내용 | 영향 범위 |
|------|------|-----------|----------|
| `cutscene5_llm_driven.json` | 156-204 | beats_intro 6개→10개, 비유 제거, 아카자 지연 | **INTRO만** |
| `parent_agent.py` | 197-212 | INTRO만 beats slice, speaker_pool 전체 사용 | **INTRO만** (`if` 분기) |
| `children_agent.py` | 317-365 | INTRO만 프롬프트 변경 (10개 이상, narr/akaza 1회) | **INTRO만** (`if` 분기) |
| `children_agent.py` | 375-398 | INTRO만 narr 필터링 추가 | **INTRO만** (`if` 분기) |

---

## 🎯 테스트 결과

### 실행 방법
```bash
cd SKN15-FINAL-5TEAM
source venv/bin/activate  # 또는: venv
echo -e "\n태민\n시작" | ./venv/bin/python play.py
```

### 결과 (14개 대화 생성)
```
[narr]: 열차가 갑자기 격렬하게 흔들리기 시작하며 레일을 벗어나 비명과 함께 무너져 내린다.

[rengoku]: 모두, 침착하게! 지금은 안전을 최우선으로 생각해야 할 때입니다.

[tanjiro]: 네, 렌고쿠 선배님! 주변을 둘러보겠습니다. 여기 계신 분들, 다치신 곳은 없으신가요?

[tanjiro]: 유리 파편이 많이 흩어져 있어요. 발을 다치지 않게 조심하세요!

[rengoku]: 탄지로, 그쪽은 내가 볼게. 너는 다른 칸으로 가서 승객들을 도와줘.

[tanjiro]: 알겠습니다! 빠르게 움직이겠습니다.

[rengoku]: 여기 계신 분들, 제 말에 귀 기울여 주세요. 안전한 곳으로 모이시면 응급 처치를 도와드리겠습니다!

[tanjiro]: 이쪽도 사람들이 많이 다쳤어요. 누구든지 걸을 수 있다면 도와주세요. 부상자를 안전한 곳으로 옮겨야 합니다.

[rengoku]: 천천히 여러분, 패닉에 빠지지 마세요. 호흡을 깊게 하시고, 제 지시를 따라 주십시오.

[tanjiro]: 여기 어린 아이가 다쳤어요! 빠르게 의료 팀을 부탁드립니다, 렌고쿠 선배님!

[rengoku]: 알겠어, 탄지로! 의료 팀을 즉시 호출하겠어. 그 동안 안전한 곳으로 아이를 옮겨라.

[rengoku]: 우리의 도움을 필요로 하는 사람들이 많습니다. 모두의 안전을 확보하면서 차근차근 해결해 나가야 해.

[tanjiro]: 네, 모두를 위해 최선을 다하겠습니다. 다친 이들을 돕고, 희망을 잃지 않게 하겠습니다!

[akaza]: 흥, 인간들의 연약함이란... 하지만 렌고쿠 쿄쥬로, 너와의 싸움을 기대하고 있다. 준비가 되면 맞서 봐라.
```

### 분석
- ✅ 대화 개수: **14개** (목표 10개 초과)
- ✅ narr: 맨 처음 1회만
- ✅ akaza: 마지막 1회만
- ✅ 스토리 흐름: 탈선 → 구호 → 아카자 도전
- ✅ 캐릭터 균형: tanjiro(6회), rengoku(7회), narr(1회), akaza(1회)

---

## 📝 결론

모든 수정은 **INTRO 스테이지에만** 적용되며, 다른 스테이지(ROUTE_CHOICE, INTERVENE, RECRUIT 등)는 **전혀 영향받지 않습니다**!

조원들의 작업(도원, 준원)과 충돌 없이 안전하게 적용 가능합니다.
