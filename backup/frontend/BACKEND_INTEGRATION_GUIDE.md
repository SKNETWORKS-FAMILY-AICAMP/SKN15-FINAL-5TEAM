# 백엔드 연동 가이드 - 배경 이미지 시스템

## 개요

프론트엔드에서 채팅 배경 이미지를 동적으로 변경할 수 있는 시스템을 구축했습니다. 백엔드에서는 API 응답에 `current_image` 필드를 포함하여 상황에 맞는 배경을 지정할 수 있습니다.

## API 응답 형식

### ChatResponse 타입

```typescript
interface ChatResponse {
  session_id: string;
  turn_count: number;
  dialogues: ChatMessage[];
  current_stage?: string;
  affinity_scores?: Record<string, number>;
  is_ended: boolean;
  has_more: boolean;
  system_message?: string;
  current_image?: string;  // 👈 배경 이미지 지정
}
```

## current_image 필드 사용법

백엔드에서 `current_image` 필드에 다음 두 가지 방식으로 값을 전달할 수 있습니다:

### 방법 1: 인덱스로 지정 (권장)

가장 간단한 방법입니다. 1~21 사이의 숫자를 문자열로 전달합니다.

```python
# Python 예시
response = {
    "session_id": session_id,
    "dialogues": dialogues,
    "current_image": "8",  # 전투 장면 1
    "has_more": False,
    # ...
}
```

```json
{
  "session_id": "abc123",
  "dialogues": [...],
  "current_image": "8",
  "has_more": false
}
```

### 방법 2: ID로 지정

더 명확한 의미 전달을 원하면 ID를 사용할 수 있습니다.

```python
# Python 예시
response = {
    "session_id": session_id,
    "dialogues": dialogues,
    "current_image": "battle_scene_01",  # 전투 장면 1
    "has_more": False,
    # ...
}
```

```json
{
  "session_id": "abc123",
  "dialogues": [...],
  "current_image": "battle_scene_01",
  "has_more": false
}
```

## 배경 이미지 목록 (무한열차 시나리오)

백엔드에서 상황에 맞게 선택할 수 있는 배경 이미지 목록:

| 인덱스 | ID | 이름 | 설명 | 주요 태그 |
|--------|-----|------|------|----------|
| **1** | `derailed_train` | 무너진 열차, 필사의 질주 | 탄지로가 열차 탈선 현장에서 필사적으로 달리는 장면 (기본값) | train, disaster, desperate, tanjiro |
| **2** | `rengoku_standing` | 염주, 렌고쿠 쿄쥬로 | 열차가 탈선 됐지만 당황하지 않고 굳건히 서 있는 렌고쿠의 모습 | rengoku, hashira, strong, flame |
| **3** | `akaza_arrival` | 상현의 등장 | 상현 3 아카자가 압도적인 기운과 함께 처음 등장하는 장면 | akaza, upper_rank, demon, arrival, threatening |
| **4** | `compass_battle` | 나침반 위의 사투 | 아카자의 술식 "파괴살: 나침" 위에서 렌고쿠와 격돌하는 장면 | battle, rengoku, akaza, technique, intense |
| **5** | `compass_technique` | 술식 전개: 파괴살 나침 | 아카자가 본격적인 전투를 위해 자세를 잡고 기술을 전개하는 장면 | akaza, technique, blood_demon_art, battle_start |
| **6** | `flame_vs_fighting_spirit` | 붉은 화염, 푸른 투기 | 렌고쿠의 화염과 아카자의 푸른 투기가 정면으로 충돌하는 모습 | battle, rengoku, akaza, clash, intense, fire |
| **7** | `hashira_vs_upper_rank` | 염주와 상현의 격돌 | 렌고쿠가 아카자의 공격을 정면으로 받아치며 싸우는 격전 | battle, rengoku, akaza, intense, clash |
| **8** | `inosuke_sharpening` | 어둠 속의 칼날갈이 | 이노스케를 만났을 때, 이노스케가 다음 전투를 준비하며 칼을 가는 장면 | inosuke, preparation, dark, beast |
| **9** | `inosuke_charge` | 짐승의 호흡, 돌격! | 이노스케를 설득했을 때 이노스케가 투지가 생긴 모습 | inosuke, beast_breathing, charge, motivated |
| **10** | `duel_flame_and_fist` | 일기토: 불꽃과 권무 | 렌고쿠와 아카자가 서로의 모든 것을 걸고 싸우는 치열한 근접전 | battle, rengoku, akaza, intense, duel, climax |
| **11** | `zenitsu_sleeping` | 고요한 열차, 잠든 번개 | 젠이츠가 파괴된 열차 안에서 잠들어 있는 모습 | zenitsu, sleeping, train, calm |
| **12** | `thunderclap_and_flash` | 벽력일섬 | 젠이츠를 설득하는데 성공했을 때 투지가 생긴 젠이츠 | zenitsu, thunder_breathing, motivated, lightning |
| **13** | `pierced_abdomen` | 최후의 일격, 꿰뚫린 복부 | 아카자의 팔이 렌고쿠의 복부를 꿰뚫은 결정적인 장면 | rengoku, akaza, critical, injury, dramatic, tragic |
| **14** | `remaining_flame` | 남겨진 불꽃 | 싸움이 끝난 후, 렌고쿠의 일륜도와 하오리만 남아있는 장면 | rengoku, aftermath, tragic, emotional, sword, haori |
| **15** | `cooperation_towards_dawn` | 새벽을 향한 공조 | 이노스케와 젠이츠가 함께 전장을 달리는 모습 | inosuke, zenitsu, cooperation, running, dawn |
| **16** | `three_united` | 삼인삼색, 합동 전선 | 탄지로, 젠이츠, 이노스케가 각자의 기술을 상징하는 형상과 함께 싸우는 모습 (히든엔딩 루트) | tanjiro, zenitsu, inosuke, trio, united, breathing, hidden_ending_route |
| **17** | `rengoku_ninth_form` | 불꽃의 호흡, 오의: 연옥 | 렌고쿠가 화룡의 형상과 함께 최후의 오의를 사용하는 장면 | rengoku, flame_breathing, ninth_form, ultimate, dragon, climax |
| **18** | `dawn_and_tears` | 여명, 그리고 패배의 눈물 | 해가 뜨고, 렌고쿠의 곁에서 오열하는 탄지로와 젠이츠, 그리고 분노하는 이노스케 | dawn, tanjiro, zenitsu, inosuke, rengoku, tears, grief, anger, tragic |
| **19** | `fulfill_duty` | 책무를 다하다 | 모든 싸움을 마치고 어머니를 떠올리며 미소 짓는 렌고쿠의 마지막 모습 | rengoku, final_moment, smile, duty, mother, tragic, emotional |
| **20** | `set_heart_ablaze` | 마음을 불태워라 | 렌고쿠가 죽기 직전, 탄지로에게 마지막 유언을 남기며 격려하는 장면 | rengoku, tanjiro, last_words, encouragement, emotional, legacy |
| **21** | `hidden_ending` | [히든 엔딩] 불꽃과 함께 맞이한 여명 | 렌고쿠가 살아남아, 탄지로 일행과 함께 폐허 속에서 떠오르는 태양을 바라보는 또 다른 결말 | hidden_ending, rengoku, tanjiro, zenitsu, inosuke, sunrise, victory, happy, alternative |

## 상황별 추천 배경

### 열차 탈선 직후
```python
# 탈선 현장
current_image = "1"  # derailed_train (기본값)

# 렌고쿠 등장
current_image = "2"  # rengoku_standing
```

### 아카자 등장 및 전투 시작
```python
# 아카자 처음 등장
current_image = "3"  # akaza_arrival

# 술식 전개
current_image = "5"  # compass_technique

# 전투 시작
current_image = "4"  # compass_battle
current_image = "6"  # flame_vs_fighting_spirit
```

### 렌고쿠 vs 아카자 전투 씬
```python
# 격렬한 전투
current_image = "7"  # hashira_vs_upper_rank

# 치열한 근접전
current_image = "10"  # duel_flame_and_fist

# 렌고쿠의 오의
current_image = "17"  # rengoku_ninth_form

# 치명상
current_image = "13"  # pierced_abdomen
```

### 동료 모집 분기
```python
# 이노스케 발견
current_image = "8"  # inosuke_sharpening

# 이노스케 합류
current_image = "9"  # inosuke_charge

# 젠이츠 발견
current_image = "11"  # zenitsu_sleeping

# 젠이츠 합류
current_image = "12"  # thunderclap_and_flash

# 둘이 함께 전장으로
current_image = "15"  # cooperation_towards_dawn

# 3인 모두 모임 (히든엔딩 루트)
current_image = "16"  # three_united
```

### 비극적 엔딩
```python
# 전투 후
current_image = "14"  # remaining_flame

# 오열하는 동료들
current_image = "18"  # dawn_and_tears

# 렌고쿠의 마지막 미소
current_image = "19"  # fulfill_duty

# 마지막 유언
current_image = "20"  # set_heart_ablaze
```

### 히든 엔딩
```python
# 렌고쿠가 살아남은 결말
current_image = "21"  # hidden_ending
```

## Python 백엔드 구현 예시

### 기본 사용

```python
class MugenTrainAgent:
    def get_background_for_situation(self, situation: str) -> str:
        """상황에 맞는 배경 인덱스 반환"""
        background_map = {
            # 초반부
            "derailed": "1",              # 탈선 현장
            "rengoku_arrival": "2",       # 렌고쿠 등장

            # 아카자 등장 및 전투
            "akaza_arrival": "3",         # 아카자 등장
            "compass_battle": "4",        # 나침반 위 사투
            "technique_deploy": "5",      # 술식 전개
            "flame_clash": "6",           # 화염 vs 투기
            "intense_battle": "7",        # 격렬한 전투
            "duel": "10",                 # 일기토

            # 동료 모집
            "find_inosuke": "8",          # 이노스케 발견
            "inosuke_join": "9",          # 이노스케 합류
            "find_zenitsu": "11",         # 젠이츠 발견
            "zenitsu_join": "12",         # 젠이츠 합류
            "cooperation": "15",          # 공조
            "trio_united": "16",          # 3인 합류 (히든엔딩 루트)

            # 클라이막스
            "ninth_form": "17",           # 오의: 연옥
            "critical_hit": "13",         # 치명상

            # 엔딩
            "aftermath": "14",            # 남겨진 불꽃
            "grief": "18",                # 오열
            "final_smile": "19",          # 마지막 미소
            "last_words": "20",           # 마지막 유언
            "hidden_ending": "21"         # 히든 엔딩
        }
        return background_map.get(situation, "1")  # 기본값: 탈선 현장

    def generate_response(self, user_input: str, session_state) -> dict:
        # ... 대화 생성 로직 ...

        # 현재 상황 판단
        current_situation = self.detect_situation(session_state)

        # 배경 이미지 선택
        background = self.get_background_for_situation(current_situation)

        return {
            "session_id": session_state.id,
            "dialogues": dialogues,
            "current_image": background,  # 👈 배경 지정
            "has_more": False,
            # ...
        }
```

### 시나리오 단계별 자동 변경

```python
class MugenTrainScenarioManager:
    """무한열차 시나리오의 단계별 배경 관리"""

    STAGE_BACKGROUNDS = {
        # Act 1: 탈선과 렌고쿠
        "derailed_scene": "1",        # 탈선 현장
        "rengoku_intro": "2",         # 렌고쿠 등장

        # Act 2: 아카자 등장
        "akaza_intro": "3",           # 아카자 등장
        "technique_start": "5",       # 술식 전개

        # Act 3: 전투 시작
        "battle_start": "4",          # 나침반 사투
        "battle_clash": "6",          # 화염 충돌
        "battle_intense": "7",        # 격렬한 전투

        # Act 4: 동료 모집 (선택 분기)
        "recruit_inosuke_find": "8",  # 이노스케 발견
        "recruit_inosuke_join": "9",  # 이노스케 합류
        "recruit_zenitsu_find": "11", # 젠이츠 발견
        "recruit_zenitsu_join": "12", # 젠이츠 합류
        "allies_move": "15",          # 동료들 이동
        "trio_formation": "16",       # 3인 합류 (히든엔딩 플래그)

        # Act 5: 클라이막스
        "battle_climax": "10",        # 일기토
        "ultimate_move": "17",        # 오의: 연옥
        "fatal_blow": "13",           # 치명상

        # Act 6: 엔딩
        "battle_end": "14",           # 남겨진 불꽃
        "mourning": "18",             # 오열
        "rengoku_final": "19",        # 렌고쿠의 마지막
        "last_message": "20",         # 마지막 유언

        # Hidden Ending
        "hidden_ending": "21"         # 렌고쿠 생존 엔딩
    }

    def get_background_for_stage(self, stage: str) -> str:
        """현재 스테이지에 맞는 배경 인덱스 반환"""
        return self.STAGE_BACKGROUNDS.get(stage, "1")

    def get_background_for_progress(self, progress_percentage: int) -> str:
        """진행률에 따른 배경 자동 선택 (0-100%)"""
        if progress_percentage < 10:
            return "1"   # 시작: 탈선
        elif progress_percentage < 20:
            return "2"   # 렌고쿠 등장
        elif progress_percentage < 30:
            return "3"   # 아카자 등장
        elif progress_percentage < 50:
            return "7"   # 전투 중
        elif progress_percentage < 70:
            return "10"  # 일기토
        elif progress_percentage < 80:
            return "17"  # 오의
        elif progress_percentage < 90:
            return "13"  # 치명상
        else:
            return "20"  # 마지막 유언
```

### 감정/대화 내용 기반 동적 변경

```python
def analyze_content_and_set_background(dialogue_content: str, speaker: str) -> str:
    """대화 내용과 화자를 분석하여 배경 선택"""

    # 화자별 특정 배경
    if speaker == "rengoku":
        if any(word in dialogue_content for word in ["오의", "연옥", "불꽃의 호흡"]):
            return "17"  # 오의: 연옥
        elif any(word in dialogue_content for word in ["마음을 불태워", "책무", "어머니"]):
            return "20"  # 마지막 유언

    elif speaker == "akaza":
        if any(word in dialogue_content for word in ["파괴살", "나침", "술식"]):
            return "5"   # 술식 전개
        elif "등장" in dialogue_content or "나타났다" in dialogue_content:
            return "3"   # 아카자 등장

    elif speaker == "inosuke":
        if "칼" in dialogue_content or "날을 간다" in dialogue_content:
            return "8"   # 칼날갈이
        elif any(word in dialogue_content for word in ["돌격", "가자", "싸우자"]):
            return "9"   # 돌격

    elif speaker == "zenitsu":
        if "잠" in dialogue_content or "자고" in dialogue_content:
            return "11"  # 잠든 젠이츠
        elif any(word in dialogue_content for word in ["벽력", "일섬", "번개"]):
            return "12"  # 벽력일섬

    # 상황 키워드 기반
    if any(word in dialogue_content for word in ["탈선", "부서진", "무너진"]):
        return "1"   # 탈선 현장

    elif any(word in dialogue_content for word in ["싸움", "전투", "공격", "막아"]):
        if "일기토" in dialogue_content or "결투" in dialogue_content:
            return "10"  # 일기토
        else:
            return "7"   # 격렬한 전투

    elif any(word in dialogue_content for word in ["꿰뚫", "관통", "치명상"]):
        return "13"  # 치명상

    elif any(word in dialogue_content for word in ["눈물", "울", "슬픔", "오열"]):
        return "18"  # 오열

    elif any(word in dialogue_content for word in ["미소", "웃음", "평온"]):
        return "19"  # 렌고쿠의 마지막 미소

    elif any(word in dialogue_content for word in ["함께", "동료", "3명", "셋이서"]):
        return "16"  # 3인 합류

    elif "여명" in dialogue_content or "해가 뜬다" in dialogue_content:
        if "살아남" in dialogue_content or "생존" in dialogue_content:
            return "21"  # 히든 엔딩
        else:
            return "18"  # 여명과 눈물

    return "1"  # 기본 배경
```

## ImageManager 통합 (백엔드)

만약 백엔드에 ImageManager가 있다면 다음과 같이 통합할 수 있습니다:

```python
# backend/src/tools/image_manager.py

class MugenTrainImageManager:
    """무한열차 시나리오 전용 이미지 관리자"""

    # 씬 타입별 배경 매핑
    SCENE_BACKGROUNDS = {
        "derailed": "1",
        "rengoku": "2",
        "akaza": "3",
        "battle_start": "4",
        "technique": "5",
        "clash": "6",
        "intense": "7",
        "inosuke_prep": "8",
        "inosuke_ready": "9",
        "duel": "10",
        "zenitsu_sleep": "11",
        "zenitsu_ready": "12",
        "critical": "13",
        "aftermath": "14",
        "cooperation": "15",
        "trio": "16",
        "ultimate": "17",
        "grief": "18",
        "final": "19",
        "legacy": "20",
        "hidden": "21"
    }

    # 화자별 기본 배경
    SPEAKER_BACKGROUNDS = {
        "rengoku": "2",
        "akaza": "3",
        "inosuke": "9",
        "zenitsu": "12",
        "tanjiro": "1"
    }

    def get_background_for_scene(self, scene_type: str) -> str:
        """씬 타입에 맞는 배경 인덱스 반환"""
        return self.SCENE_BACKGROUNDS.get(scene_type, "1")

    def get_background_for_speaker(self, speaker: str) -> str:
        """화자에 맞는 배경 반환"""
        return self.SPEAKER_BACKGROUNDS.get(speaker.lower(), "1")

    def get_background_for_dialogue(self, dialogue: dict) -> str:
        """대화 내용, 감정, 화자 등을 종합하여 배경 선택"""
        content = dialogue.get("content", "")
        speaker = dialogue.get("speaker", "")
        emotion = dialogue.get("emotion", "neutral")

        # 우선순위 1: 특정 키워드
        if "오의" in content or "연옥" in content:
            return "17"  # 렌고쿠의 오의
        elif "파괴살" in content or "나침" in content:
            return "5"   # 아카자 술식
        elif "꿰뚫" in content or "치명상" in content:
            return "13"  # 치명상
        elif "마음을 불태워" in content:
            return "20"  # 마지막 유언
        elif "살아남" in content and speaker == "rengoku":
            return "21"  # 히든 엔딩

        # 우선순위 2: 감정 기반
        emotion_map = {
            "intense": "7",      # 격렬함
            "battle": "10",      # 전투
            "sad": "18",         # 슬픔
            "peaceful": "19",    # 평온
            "threatening": "3",  # 위협적
            "determined": "17"   # 결연함
        }

        if emotion in emotion_map:
            return emotion_map[emotion]

        # 우선순위 3: 화자 기반
        return self.get_background_for_speaker(speaker)

    def get_background_transition_sequence(self, event: str) -> list[str]:
        """특정 이벤트의 배경 전환 시퀀스 반환"""
        sequences = {
            "akaza_battle": ["3", "5", "4", "6", "7", "10", "17", "13"],
            "recruit_all": ["8", "9", "11", "12", "15", "16"],
            "tragic_ending": ["13", "14", "18", "19", "20"],
            "hidden_ending": ["16", "17", "21"]
        }
        return sequences.get(event, ["1"])
```

## 주의사항

1. **인덱스 범위**: 1~21 사이의 값만 사용
2. **문자열 타입**: 숫자라도 문자열로 전달 (`"8"`, not `8`)
3. **선택적 필드**: `current_image`가 없으면 기본 배경 사용
4. **잘못된 값**: 존재하지 않는 ID나 범위 밖 인덱스는 무시됨

## 테스트 예시

```python
# 테스트용 응답
test_responses = [
    {
        "session_id": "test123",
        "dialogues": [
            {"speaker": "tanjiro", "content": "전투 준비!"}
        ],
        "current_image": "7",  # 긴장된 순간
        "has_more": True
    },
    {
        "session_id": "test123",
        "dialogues": [
            {"speaker": "rengoku", "content": "공격!"}
        ],
        "current_image": "8",  # 전투 시작
        "has_more": True
    },
    {
        "session_id": "test123",
        "dialogues": [
            {"speaker": "akaza", "content": "이게 끝이다!"}
        ],
        "current_image": "14",  # 클라이막스
        "has_more": False
    }
]
```

## 디버깅

프론트엔드 콘솔에서 배경 변경 로그 확인:

```
📥 Received 1 dialogues, has_more: false
Background changed to index: 8
```

배경이 변경되지 않으면:
1. `current_image` 값 확인
2. 1~21 범위 확인
3. 브라우저 개발자 도구 Console 탭에서 warning 메시지 확인

## 문의사항

프론트엔드 배경 시스템에 대한 자세한 내용은 `front/src/config/BACKGROUND_IMAGES_README.md` 참고
