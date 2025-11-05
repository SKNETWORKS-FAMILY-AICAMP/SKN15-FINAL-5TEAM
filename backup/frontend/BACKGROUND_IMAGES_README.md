# 배경 이미지 관리 시스템

채팅 인터페이스의 배경 이미지를 동적으로 관리하기 위한 시스템입니다.

## 📁 폴더 구조

```
front/
├── public/
│   └── images/
│       └── backgrounds/
│           ├── mugen_train/        # 무한열차 시나리오 이미지
│           │   ├── 1.png
│           │   ├── 2.png
│           │   └── ... (21개)
│           ├── train_station/      # (예시) 다른 시나리오 추가 가능
│           └── demon_slayer_hq/    # (예시) 다른 시나리오 추가 가능
└── src/
    ├── config/
    │   └── backgroundImages.ts     # 배경 이미지 설정 파일
    └── hooks/
        └── useBackgroundImage.ts   # 배경 이미지 관리 Hook
```

## 🎨 배경 이미지 설정

### 1. 이미지 파일 추가

새로운 배경 이미지를 추가하려면:

1. `front/public/images/backgrounds/[시나리오명]/` 폴더에 이미지 파일 추가
2. 파일명은 숫자.확장자 형식 권장 (예: `1.png`, `2.jpg`)

### 2. 설정 파일 업데이트

`front/src/config/backgroundImages.ts` 파일에서 배경 이미지 메타데이터 설정:

```typescript
export const mugenTrainBackgrounds: ScenarioBackgrounds = {
  scenarioId: 'mugen_train',
  scenarioName: '무한열차',
  defaultBackground: 'train_interior_01', // 기본 배경 ID
  backgrounds: [
    {
      id: 'train_interior_01',        // 고유 ID
      index: 1,                        // 인덱스 (백엔드에서 참조)
      fileName: '1.png',               // 실제 파일명
      name: '열차 내부 - 일반 객실',   // 설명용 이름
      description: '무한열차의 일반적인 객실 내부',
      tags: ['interior', 'normal', 'default'] // 검색용 태그
    },
    // ... 더 많은 배경 추가
  ]
};
```

### 3. 새로운 시나리오 추가

다른 시나리오의 배경을 추가하려면:

```typescript
// 1. 새로운 시나리오 설정 생성
export const trainStationBackgrounds: ScenarioBackgrounds = {
  scenarioId: 'train_station',
  scenarioName: '기차역',
  defaultBackground: 'station_platform',
  backgrounds: [
    {
      id: 'station_platform',
      index: 1,
      fileName: '1.png',
      name: '역 플랫폼',
      description: '기차역 플랫폼',
      tags: ['station', 'platform']
    },
    // ... 더 많은 배경
  ]
};

// 2. allScenarioBackgrounds 배열에 추가
export const allScenarioBackgrounds: ScenarioBackgrounds[] = [
  mugenTrainBackgrounds,
  trainStationBackgrounds, // 새로 추가
];
```

## 🔧 사용 방법

### React 컴포넌트에서 사용

```typescript
import { useBackgroundImage } from '@/hooks/useBackgroundImage';

function MyComponent() {
  const {
    currentBackground,      // 현재 배경 정보
    backgroundImageUrl,     // 현재 배경 이미지 URL
    setBackgroundById,      // ID로 배경 변경
    setBackgroundByIndex,   // 인덱스로 배경 변경
    setBackgroundByTag,     // 태그로 배경 변경
    resetToDefault,         // 기본 배경으로 리셋
    preloadImages          // 모든 이미지 미리 로드
  } = useBackgroundImage('mugen_train');

  // 배경 이미지 적용
  return (
    <div
      style={{
        backgroundImage: `url(${backgroundImageUrl})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}
    >
      {/* 콘텐츠 */}
    </div>
  );
}
```

### 배경 변경 예시

```typescript
// ID로 변경
setBackgroundById('battle_scene_01');

// 인덱스로 변경 (백엔드에서 숫자만 보내는 경우)
setBackgroundByIndex(8);

// 태그로 변경 (해당 태그의 첫 번째 이미지)
setBackgroundByTag('battle');

// 태그로 변경 (해당 태그의 두 번째 이미지)
setBackgroundByTag('battle', 1);

// 기본 배경으로 리셋
resetToDefault();
```

## 🔄 백엔드 연동

백엔드 API 응답에서 `current_image` 필드로 배경을 제어할 수 있습니다:

### 방법 1: 인덱스로 전송 (권장)

```json
{
  "current_image": "8",
  "dialogues": [...]
}
```

프론트엔드에서 자동으로 인덱스 8번 배경으로 변경됩니다.

### 방법 2: ID로 전송

```json
{
  "current_image": "battle_scene_01",
  "dialogues": [...]
}
```

프론트엔드에서 ID가 `battle_scene_01`인 배경으로 변경됩니다.

### ChatInterface에서의 처리

```typescript
// 백엔드 응답 처리
const handleBackgroundChange = (currentImage: string | null) => {
  if (!currentImage) return;

  // 숫자인 경우 인덱스로 처리
  const indexNum = parseInt(currentImage, 10);
  if (!isNaN(indexNum)) {
    setBackgroundByIndex(indexNum);
    return;
  }

  // 문자열인 경우 ID로 처리
  setBackgroundById(currentImage);
};
```

## 📋 배경 이미지 목록 (무한열차)

| 인덱스 | ID | 파일명 | 이름 | 설명 |
|--------|-----|--------|------|------|
| 1 | derailed_train | 1.png | 무너진 열차, 필사의 질주 | 탄지로가 열차 탈선 현장에서 필사적으로 달리는 장면 |
| 2 | rengoku_standing | 2.png | 염주, 렌고쿠 쿄쥬로 | 열차가 탈선 됐지만 당황하지 않고 굳건히 서 있는 렌고쿠의 모습 |
| 3 | akaza_arrival | 3.png | 상현의 등장 | 상현 3 아카자가 압도적인 기운과 함께 처음 등장하는 장면 |
| 4 | compass_battle | 4.png | 나침반 위의 사투 | 아카자의 술식 "파괴살: 나침" 위에서 렌고쿠와 격돌하는 장면 |
| 5 | compass_technique | 5.png | 술식 전개: 파괴살 나침 | 아카자가 본격적인 전투를 위해 자세를 잡고 기술을 전개하는 장면 |
| 6 | flame_vs_fighting_spirit | 6.png | 붉은 화염, 푸른 투기 | 렌고쿠의 화염과 아카자의 푸른 투기가 정면으로 충돌하는 모습 |
| 7 | hashira_vs_upper_rank | 7.png | 염주와 상현의 격돌 | 렌고쿠가 아카자의 공격을 정면으로 받아치며 싸우는 격전 |
| 8 | inosuke_sharpening | 8.png | 어둠 속의 칼날갈이 | 이노스케를 만났을 때, 이노스케가 다음 전투를 준비하며 칼을 가는 장면 |
| 9 | inosuke_charge | 9.png | 짐승의 호흡, 돌격! | 이노스케를 설득했을 때 이노스케가 투지가 생긴 모습 |
| 10 | duel_flame_and_fist | 10.jpg | 일기토: 불꽃과 권무 | 렌고쿠와 아카자가 서로의 모든 것을 걸고 싸우는 치열한 근접전 |
| 11 | zenitsu_sleeping | 11.png | 고요한 열차, 잠든 번개 | 젠이츠가 파괴된 열차 안에서 잠들어 있는 모습 |
| 12 | thunderclap_and_flash | 12.png | 벽력일섬 | 젠이츠를 설득하는데 성공했을 때 투지가 생긴 젠이츠 |
| 13 | pierced_abdomen | 13.png | 최후의 일격, 꿰뚫린 복부 | 아카자의 팔이 렌고쿠의 복부를 꿰뚫은 결정적인 장면 |
| 14 | remaining_flame | 14.png | 남겨진 불꽃 | 싸움이 끝난 후, 렌고쿠의 일륜도와 하오리만 남아있는 장면 |
| 15 | cooperation_towards_dawn | 15.png | 새벽을 향한 공조 | 이노스케와 젠이츠가 함께 전장을 달리는 모습 |
| 16 | three_united | 16.png | 삼인삼색, 합동 전선 | 탄지로, 젠이츠, 이노스케가 각자의 기술을 상징하는 형상과 함께 싸우는 모습 |
| 17 | rengoku_ninth_form | 17.png | 불꽃의 호흡, 오의: 연옥 | 렌고쿠가 화룡의 형상과 함께 최후의 오의를 사용하는 장면 |
| 18 | dawn_and_tears | 18.png | 여명, 그리고 패배의 눈물 | 해가 뜨고, 렌고쿠의 곁에서 오열하는 탄지로와 젠이츠, 그리고 분노하는 이노스케 |
| 19 | fulfill_duty | 19.jpg | 책무를 다하다 | 모든 싸움을 마치고 어머니를 떠올리며 미소 짓는 렌고쿠의 마지막 모습 |
| 20 | set_heart_ablaze | 20.png | 마음을 불태워라 | 렌고쿠가 죽기 직전, 탄지로에게 마지막 유언을 남기며 격려하는 장면 |
| 21 | hidden_ending | 21.png | [히든 엔딩] 불꽃과 함께 맞이한 여명 | 렌고쿠가 살아남아, 탄지로 일행과 함께 폐허 속에서 떠오르는 태양을 바라보는 결말 |

## 🎯 사용 시나리오 예시

### 렌고쿠 vs 아카자 전투 씬

```typescript
// 아카자 등장
setBackgroundById('akaza_arrival');  // 3번

// 술식 전개
setBackgroundById('compass_technique'); // 5번

// 격렬한 전투
setBackgroundById('hashira_vs_upper_rank'); // 7번

// 치열한 일기토
setBackgroundById('duel_flame_and_fist'); // 10번

// 렌고쿠의 오의
setBackgroundById('rengoku_ninth_form'); // 17번

// 치명상
setBackgroundById('pierced_abdomen'); // 13번
```

### 동료 모집 분기

```typescript
// 이노스케 발견
setBackgroundById('inosuke_sharpening'); // 8번

// 이노스케 합류
setBackgroundById('inosuke_charge'); // 9번

// 젠이츠 발견
setBackgroundById('zenitsu_sleeping'); // 11번

// 젠이츠 합류
setBackgroundById('thunderclap_and_flash'); // 12번

// 공동 작전
setBackgroundById('cooperation_towards_dawn'); // 15번

// 3인 모두 합류 (히든 엔딩 플래그)
setBackgroundById('three_united'); // 16번
```

### 비극적 엔딩

```typescript
// 전투 종료
setBackgroundById('remaining_flame'); // 14번

// 오열하는 동료들
setBackgroundById('dawn_and_tears'); // 18번

// 렌고쿠의 마지막 미소
setBackgroundById('fulfill_duty'); // 19번

// 마지막 유언
setBackgroundById('set_heart_ablaze'); // 20번
```

### 히든 엔딩

```typescript
// 렌고쿠가 살아남은 결말
setBackgroundById('hidden_ending'); // 21번
```

## ⚡ 성능 최적화

### 이미지 미리 로드

```typescript
useEffect(() => {
  // 컴포넌트 마운트 시 모든 이미지 미리 로드
  preloadImages();
}, [preloadImages]);
```

이렇게 하면 배경 전환이 부드럽게 진행됩니다.

## 🐛 문제 해결

### 배경이 표시되지 않는 경우

1. 이미지 파일 경로 확인: `front/public/images/backgrounds/[시나리오명]/`
2. 파일명이 설정과 일치하는지 확인
3. 브라우저 콘솔에서 에러 메시지 확인

### 배경 전환이 느린 경우

1. `preloadImages()` 호출 확인
2. 이미지 파일 크기 최적화 (권장: 1MB 이하)
3. WebP 포맷 사용 고려

## 📝 TODO

- [ ] 페이드 인/아웃 전환 효과 추가
- [ ] 이미지 lazy loading 구현
- [ ] 다크 모드 지원
- [ ] 모바일 최적화 이미지 별도 관리
