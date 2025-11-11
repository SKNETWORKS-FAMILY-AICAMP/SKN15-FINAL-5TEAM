# 채팅 UI 복구 가이드 (tm_work → 현재 브랜치)

> 3개 Claude 창에서 병렬로 작업하기
> 작성일: 2025-11-11

---

## 🎯 전체 개요

### 작업 분리 전략
```
창 2 → ChatPage.tsx (세션 복원, 로그인 가드)
창 3 → ChatInterface.tsx (메시지 처리, 타이핑 효과)
창 4 → Hooks + Utils (useBackgroundImage, useSoundEffects, 타입 정의)
```

### ⚠️ 중요: 작업 순서
1. **창 4 먼저 시작** (hooks/utils가 다른 창의 의존성)
2. **창 2, 3 병렬 실행** (파일 충돌 없음)
3. **모든 창 완료 후** → 통합 테스트

---

## 창 4: Hooks + Utils + Types 🔥

**담당 파일:**
- `front/src/hooks/useBackgroundImage.ts`
- `front/src/hooks/useSoundEffects.ts`
- `front/src/services/api.ts` (타입 추가)
- `front/src/types/chat.ts` (신규 생성)

**목표:**
- ChatInterface가 의존하는 커스텀 훅 구현
- 타입 정의 추가
- API 클라이언트 확장

### STEP 4-1: 타입 정의 생성

```bash
cd /Users/jtm427/Desktop/workspace

# types/chat.ts 생성
cat > front/src/types/chat.ts << 'EOF'
/**
 * Chat Types
 * 채팅 관련 타입 정의
 */

export interface Message {
  id: number;
  text: string;
  isUser: boolean;
  timestamp: Date;
  characterId?: string; // 메시지를 보낸 캐릭터 ID
  isSystemMessage?: boolean; // 시스템/에이전트 메시지 여부
  imageIndex?: string; // 이 메시지가 표시될 때 변경할 배경 이미지 인덱스
}

export interface BackgroundImage {
  index: string;
  fileName: string;
  url: string;
}

export interface ChatResponse {
  session_id: string;
  dialogues: Dialogue[];
  has_more?: boolean;
  agent_messages?: Array<{ text: string }>;
  stage_id?: string;
  invited_characters?: string[];
  affinity_changes?: Record<string, number>;
  image_index?: string;
  is_ended?: boolean;
  ending_summary?: string;
}

export interface Dialogue {
  speaker: string;
  text: string;
  emotion?: string;
}

export interface AffinityScore {
  characterId: string;
  score: number;
  level: number;
}
EOF
```

### STEP 4-2: useBackgroundImage hook 생성

```bash
cat > front/src/hooks/useBackgroundImage.ts << 'EOF'
import { useState, useCallback } from 'react';

interface BackgroundImage {
  index: string;
  fileName: string;
  url: string;
}

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

// 시나리오별 배경 이미지 매핑
const SCENARIO_BACKGROUNDS: Record<string, BackgroundImage[]> = {
  mugen_train_full: [
    { index: '0', fileName: 'mugen_train_bg1.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg1.jpg` },
    { index: '1', fileName: 'mugen_train_bg2.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg2.jpg` },
    { index: '2', fileName: 'mugen_train_bg3.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg3.jpg` },
  ],
  cutscene5_llm_driven: [
    { index: '0', fileName: 'ending_bg1.jpg', url: `${CDN_URL}/scenarios/ending/ending_bg1.jpg` },
    { index: '1', fileName: 'ending_bg2.jpg', url: `${CDN_URL}/scenarios/ending/ending_bg2.jpg` },
  ],
};

export function useBackgroundImage(scenarioId: string) {
  const backgrounds = SCENARIO_BACKGROUNDS[scenarioId] || [];
  const [currentBackground, setCurrentBackground] = useState<BackgroundImage>(
    backgrounds[0] || { index: '0', fileName: '', url: '' }
  );

  const setBackgroundById = useCallback((id: string) => {
    const bg = backgrounds.find(b => b.index === id);
    if (bg) {
      setCurrentBackground(bg);
    }
  }, [backgrounds]);

  const setBackgroundByIndex = useCallback((index: number) => {
    if (backgrounds[index]) {
      setCurrentBackground(backgrounds[index]);
    }
  }, [backgrounds]);

  const preloadImages = useCallback(() => {
    backgrounds.forEach(bg => {
      const img = new Image();
      img.src = bg.url;
    });
  }, [backgrounds]);

  return {
    currentBackground,
    backgroundImageUrl: currentBackground.url,
    setBackgroundById,
    setBackgroundByIndex,
    preloadImages,
  };
}
EOF
```

### STEP 4-3: useSoundEffects hook 생성

```bash
cat > front/src/hooks/useSoundEffects.ts << 'EOF'
import { useCallback, useRef, useEffect } from 'react';

const SOUND_URLS = {
  message: '/sounds/message.mp3',
  system: '/sounds/system.mp3',
  typingStart: '/sounds/typing.mp3',
};

export function useSoundEffects() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const isUnlockedRef = useRef(false);

  useEffect(() => {
    // AudioContext 초기화
    if (typeof window !== 'undefined' && 'AudioContext' in window) {
      audioContextRef.current = new AudioContext();
    }
  }, []);

  const unlockAudio = useCallback(() => {
    if (!isUnlockedRef.current && audioContextRef.current) {
      audioContextRef.current.resume();
      isUnlockedRef.current = true;
    }
  }, []);

  const playSound = useCallback((soundUrl: string) => {
    try {
      const audio = new Audio(soundUrl);
      audio.volume = 0.3;
      audio.play().catch(err => {
        console.warn('Failed to play sound:', err);
      });
    } catch (err) {
      console.warn('Sound playback error:', err);
    }
  }, []);

  const playMessageSound = useCallback(() => {
    playSound(SOUND_URLS.message);
  }, [playSound]);

  const playSystemSound = useCallback(() => {
    playSound(SOUND_URLS.system);
  }, [playSound]);

  const playTypingStartSound = useCallback(() => {
    playSound(SOUND_URLS.typingStart);
  }, [playSound]);

  return {
    playMessageSound,
    playSystemSound,
    playTypingStartSound,
    unlockAudio,
  };
}
EOF
```

### STEP 4-4: API 클라이언트 타입 추가

```bash
# api.ts에 타입 추가 (기존 파일에 병합 필요)
# ScenarioCard 타입이 있는지 확인
grep -n "export interface ScenarioCard" front/src/services/api.ts

# 없으면 추가
cat >> front/src/services/api.ts << 'EOF'

// Scenario API types
export interface ScenarioCard {
  id: string;
  title: string;
  description: string;
  image: string;
  thumbnail?: string;
  tags?: string[];
  implemented: boolean;
}

// Scenario API
export const getScenario = async (scenarioId: string): Promise<ScenarioCard> => {
  const response = await fetch(`${API_URL}/scenarios/${scenarioId}`);
  if (!response.ok) throw new Error('Failed to fetch scenario');
  return response.json();
};
EOF
```

### ✅ 창 4 완료 체크리스트

- [ ] types/chat.ts 생성
- [ ] useBackgroundImage.ts 생성
- [ ] useSoundEffects.ts 생성
- [ ] api.ts에 ScenarioCard 타입 추가
- [ ] api.ts에 getScenario 함수 추가

---

## 창 2: ChatPage.tsx 복구 🔥

**담당 파일:**
- `front/src/pages/ChatPage.tsx`

**목표:**
- tm_work의 ChatPage.tsx 로직 복구
- 세션 복원 기능
- 로그인 가드
- 시나리오 로딩

### STEP 2-1: ChatPage.tsx 백업

```bash
cd /Users/jtm427/Desktop/workspace

cp front/src/pages/ChatPage.tsx front/src/pages/ChatPage.tsx.backup
```

### STEP 2-2: tm_work ChatPage.tsx 복사

```bash
git show tm_work:front/src/pages/ChatPage.tsx > front/src/pages/ChatPage.tsx
```

### STEP 2-3: import 경로 확인 및 수정

```bash
# ChatPage.tsx의 import 확인
grep "^import" front/src/pages/ChatPage.tsx

# 필요시 수정 (현재 프로젝트 구조에 맞게)
# 예: ScenarioCard가 api.ts가 아닌 다른 곳에 정의되어 있다면 수정
```

### STEP 2-4: SCENARIO_ID_MAP 확인

```bash
# SCENARIO_ID_MAP이 올바른지 확인
grep -A 5 "SCENARIO_ID_MAP" front/src/pages/ChatPage.tsx

# 현재 프로젝트의 시나리오 ID와 일치하는지 확인
cat front/src/data/scenarios.json | jq '.[].id'
```

### STEP 2-5: 컴포넌트 의존성 확인

```bash
# 필요한 컴포넌트들이 모두 존재하는지 확인
ls -1 front/src/components/ | grep -E "ChatInterface|ChatHeader|LoginModal|SessionResumeModal"
```

### ✅ 창 2 완료 체크리스트

- [ ] ChatPage.tsx 백업 완료
- [ ] tm_work 버전으로 교체
- [ ] import 경로 수정
- [ ] SCENARIO_ID_MAP 확인
- [ ] 컴포넌트 의존성 확인
- [ ] TypeScript 에러 없음

---

## 창 3: ChatInterface.tsx 복구 🔥

**담당 파일:**
- `front/src/components/ChatInterface.tsx`

**목표:**
- tm_work의 ChatInterface.tsx 로직 복구
- 메시지 처리
- 타이핑 효과
- 자동 요청
- 배경 변경

### STEP 3-1: ChatInterface.tsx 백업

```bash
cd /Users/jtm427/Desktop/workspace

cp front/src/components/ChatInterface.tsx front/src/components/ChatInterface.tsx.backup
```

### STEP 3-2: tm_work ChatInterface.tsx 복사

```bash
git show tm_work:front/src/components/ChatInterface.tsx > front/src/components/ChatInterface.tsx
```

### STEP 3-3: import 경로 확인

```bash
# import 확인
grep "^import" front/src/components/ChatInterface.tsx | head -20

# hooks 경로 확인 (창 4에서 만든 hooks 사용)
grep "useBackgroundImage\|useSoundEffects" front/src/components/ChatInterface.tsx
```

### STEP 3-4: 타입 import 수정

```bash
# Message 타입을 types/chat.ts에서 import하도록 수정
# 기존: 컴포넌트 내부에 정의
# 변경: import { Message } from '@/types/chat';

# sed로 수정 가능
sed -i '' 's/interface Message {/\/\/ Message type moved to @\/types\/chat\n\/\/ interface Message {/' front/src/components/ChatInterface.tsx
```

### STEP 3-5: API 응답 타입 확인

```bash
# ChatResponse 타입이 api.ts에 정의되어 있는지 확인
grep "ChatResponse" front/src/services/api.ts

# 없으면 types/chat.ts에서 import
```

### STEP 3-6: 의존 컴포넌트 확인

```bash
# CharacterSelectionModal, BubbleCounter, AffinityPanel 존재 확인
ls -1 front/src/components/ | grep -E "CharacterSelectionModal|BubbleCounter|AffinityPanel"
```

### ✅ 창 3 완료 체크리스트

- [ ] ChatInterface.tsx 백업 완료
- [ ] tm_work 버전으로 교체
- [ ] import 경로 수정 (hooks, types)
- [ ] Message 타입 import 수정
- [ ] 의존 컴포넌트 확인
- [ ] TypeScript 에러 없음

---

## 🔄 모든 창 완료 후: 통합 테스트

### STEP 5-1: TypeScript 컴파일 체크

```bash
cd front

# TypeScript 타입 체크
npm run type-check
# 또는
npx tsc --noEmit
```

### STEP 5-2: 개발 서버 시작

```bash
# 프론트엔드 dev 서버
npm run dev

# 백엔드가 실행 중인지 확인
curl http://localhost:8000/health
```

### STEP 5-3: 기능 테스트

1. **로그인 테스트**
   - 로그인하지 않은 상태에서 ChatPage 접근
   - 로그인 모달 자동 표시 확인

2. **세션 복원 테스트**
   - 이전 세션이 있는 경우 복원 모달 표시 확인
   - 새 세션 시작 / 이전 세션 이어하기 선택

3. **채팅 기능 테스트**
   - 메시지 전송
   - AI 응답 타이핑 효과
   - 배경 이미지 변경
   - 소리 효과

4. **자동 요청 테스트**
   - has_more=true일 때 자동 요청 확인
   - 사용자 중단 기능 (스페이스바, ESC)

### STEP 5-4: 에러 핸들링 확인

```bash
# 브라우저 콘솔에서 에러 확인
# Network 탭에서 API 요청 확인
```

---

## ✅ 최종 검증 체크리스트

### 파일 구조 검증
- [ ] `types/chat.ts` 존재
- [ ] `hooks/useBackgroundImage.ts` 존재
- [ ] `hooks/useSoundEffects.ts` 존재
- [ ] `pages/ChatPage.tsx` 업데이트
- [ ] `components/ChatInterface.tsx` 업데이트
- [ ] `.backup` 파일들 존재 (롤백용)

### 기능 검증
- [ ] 로그인 가드 정상 작동
- [ ] 세션 복원 모달 정상 표시
- [ ] 메시지 전송/수신 정상
- [ ] 타이핑 효과 정상
- [ ] 배경 변경 정상
- [ ] 소리 효과 정상 (선택적)
- [ ] 자동 요청 정상 (has_more)
- [ ] Skip 기능 정상 (타이핑 스킵)

### TypeScript 검증
```bash
# 컴파일 에러 없음
npx tsc --noEmit

# ESLint 경고 확인 (선택적)
npm run lint
```

---

## 🎯 요약

### 창 4 - Hooks + Utils
- useBackgroundImage, useSoundEffects 구현
- 타입 정의 (types/chat.ts)
- **소요 시간: 10-15분**

### 창 2 - ChatPage
- tm_work ChatPage.tsx 복구
- 세션 복원, 로그인 가드
- **소요 시간: 10-15분**

### 창 3 - ChatInterface
- tm_work ChatInterface.tsx 복구
- 메시지 처리, 타이핑 효과
- **소요 시간: 15-20분**

### 총 예상 시간
**병렬 작업: 15-20분** (가장 긴 창 기준)
**순차 작업: 35-50분**

---

## 🚨 주의사항

1. **창 4를 먼저 완료하세요**
   - 창 2, 3이 의존하는 hooks와 타입이 창 4에 있음

2. **백업 파일 보관**
   - 각 파일 수정 전 .backup 생성
   - 문제 발생 시 롤백 가능

3. **TypeScript 에러 즉시 해결**
   - 각 단계마다 타입 에러 확인
   - import 경로 오류 주의

4. **브라우저 캐시 클리어**
   - 변경 사항이 반영되지 않으면 Hard Refresh (Cmd+Shift+R)

---

**작성자:** Claude (Sonnet 4.5)
**마지막 업데이트:** 2025-11-11
