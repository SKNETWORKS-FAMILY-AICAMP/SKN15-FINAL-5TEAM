# 이미지 CDN 마이그레이션 가이드

## 📋 목차
1. [문제 발견](#문제-발견)
2. [해결 전략](#해결-전략)
3. [수정 파일 목록](#수정-파일-목록)
4. [상세 수정 내역](#상세-수정-내역)
5. [환경별 설정](#환경별-설정)
6. [테스트 방법](#테스트-방법)

---

## 문제 발견

### 배경
AWS S3 + CloudFront CDN으로 이미지를 제공하기 위한 준비 단계에서 문제를 발견했습니다.

### 발견된 문제
프론트엔드 코드에 **이미지 경로가 하드코딩**되어 있어, AWS 배포 시 이미지를 불러올 수 없는 상황:

```typescript
// ❌ 문제가 있는 코드
profileImage: '/images/프로필_탄지로.png'
backgroundImage: "url('/images/홈배경.jpg')"
```

### 영향 범위
- **9개 파일**
- **총 43개 이미지 경로** 하드코딩 발견
  - 프로필 이미지: 27개
  - 배경 이미지: 8개
  - 시나리오 카드: 6개
  - onError fallback: 2개

---

## 해결 전략

### 환경 변수 기반 CDN URL 설정

**핵심 아이디어:**
- 로컬: `/images` (기존 경로 유지)
- AWS: `https://d1a2b3c4d5e6f7.cloudfront.net` (CloudFront URL)

**구현 방법:**
```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';
const imagePath = `${CDN_URL}/프로필_탄지로.png`;
```

### Vite 환경 변수

Vite는 `VITE_` 접두사가 붙은 환경 변수만 클라이언트에 노출합니다:
- `VITE_API_URL` ✅ 클라이언트에서 사용 가능
- `API_URL` ❌ 클라이언트에서 사용 불가

---

## 수정 파일 목록

### ✅ 완료된 수정 (9개 파일)

| # | 파일 경로 | 수정 항목 | 경로 수 |
|---|----------|----------|--------|
| 1 | `front/.env` | 환경 변수 파일 생성 | 3개 변수 |
| 2 | `front/.env.production` | 프로덕션 환경 변수 | 3개 변수 |
| 3 | `front/src/vite-env.d.ts` | TypeScript 타입 정의 | - |
| 4 | `front/src/config/backgroundImages.ts` | 배경 이미지 경로 함수 | 1개 함수 |
| 5 | `front/src/components/AffinityPanel.tsx` | 캐릭터 프로필 이미지 | 4개 |
| 6 | `front/src/components/CharacterSelectionModal.tsx` | 캐릭터/친구 프로필 | 10개 |
| 7 | `front/src/components/ChatInterface.tsx` | 대화 프로필 이미지 | 19개 |
| 8 | `front/src/pages/HomePage.tsx` | 시나리오 카드 + 배경 | 7개 |
| 9 | `front/src/components/SettingsSidebar.tsx` | onError fallback | 1개 |
| 10 | `front/src/styles/globals.css` | CSS 주석 추가 | 2개 (미사용) |

**총계:** 9개 파일, **43개 이미지 경로** 수정 완료

---

## 상세 수정 내역

### 1. 환경 변수 파일 생성

#### front/.env (로컬 개발)
```bash
VITE_API_URL=http://localhost:8000
VITE_CDN_URL=/images
VITE_ENVIRONMENT=development
```

#### front/.env.production (AWS 프로덕션)
```bash
VITE_API_URL=http://kime-alb-xxxxx.ap-northeast-2.elb.amazonaws.com
VITE_CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net
VITE_ENVIRONMENT=production
```

⚠️ **주의:** AWS 배포 후 실제 ALB URL과 CloudFront URL로 업데이트 필요!

### 2. TypeScript 타입 정의

#### front/src/vite-env.d.ts
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_CDN_URL: string
  readonly VITE_ENVIRONMENT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

**이유:** TypeScript에서 `import.meta.env` 사용 시 타입 에러 방지

### 3. backgroundImages.ts

**수정 전:**
```typescript
export function getBackgroundImagePath(scenarioId: string, fileName: string): string {
  return `/images/backgrounds/${scenarioId}/${fileName}`;
}
```

**수정 후:**
```typescript
export function getBackgroundImagePath(scenarioId: string, fileName: string): string {
  const cdnUrl = import.meta.env.VITE_CDN_URL || '/images';
  return `${cdnUrl}/backgrounds/${scenarioId}/${fileName}`;
}
```

### 4. AffinityPanel.tsx

**수정 내용:** 4개 캐릭터 프로필 이미지

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const CHARACTERS: CharacterInfo[] = [
  {
    id: 'tanjiro',
    profileImage: `${CDN_URL}/프로필_탄지로.png`,  // ✅
  },
  // ... 3개 더
];
```

### 5. CharacterSelectionModal.tsx

**수정 내용:** 10개 이미지 경로
- 캐릭터 6개
- 친구 2개
- onError fallback 2개

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const characters: Character[] = [
  {
    id: 'tanjiro',
    profileImage: `${CDN_URL}/프로필_탄지로.png`,
  },
  // ... 5개 더
];

const friends: Friend[] = [
  {
    id: 'friend1',
    profileImage: `${CDN_URL}/프로필_탄지로.png`,
  },
  // ... 1개 더
];

// onError 핸들러도 수정
onError={(e) => {
  (e.target as HTMLImageElement).src = `${CDN_URL}/프로필_탄지로.png`;
}}
```

### 6. ChatInterface.tsx (최대 수정)

**수정 내용:** 19개 이미지 경로
- `getCharacterProfile()` 함수 내 17개 캐릭터
- onError 핸들러 2개

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const getCharacterProfile = (charId: string) => {
  const lowerCharId = charId.toLowerCase();

  // 주요 캐릭터 (9명)
  if (lowerCharId.includes('tanjiro')) {
    return `${CDN_URL}/프로필_탄지로.png`;
  }
  if (lowerCharId.includes('rengoku')) {
    return `${CDN_URL}/프로필_렌고쿠.png`;
  }
  // ... 7개 더

  // 시스템 캐릭터
  if (lowerCharId.includes('user')) {
    return `${CDN_URL}/기본이미지.png`;
  }
  // ... 4개 더

  // NPC
  if (lowerCharId.includes('역무원')) {
    return `${CDN_URL}/역무원.jpg`;
  }
  if (lowerCharId.includes('woman')) {
    return `${CDN_URL}/일반인_여성.png`;
  }
  if (lowerCharId.includes('man')) {
    return `${CDN_URL}/일반인_남성.png`;
  }

  return `${CDN_URL}/기본이미지.png`;  // 기본 폴백
};
```

### 7. HomePage.tsx

**수정 내용:** 7개 이미지 경로
- 시나리오 카드 6개
- 홈 배경 이미지 1개

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const characters: CharacterCard[] = [
  {
    id: 'tanjiro',
    image: `${CDN_URL}/편의점탄지로.png`,
  },
  {
    id: 'train',
    image: `${CDN_URL}/무한열차.jpeg`,
  },
  // ... 4개 더
];

// 배경 이미지 (인라인 스타일)
<main
  style={{
    backgroundImage: `url('${CDN_URL}/홈배경.jpg')`,
  }}
>
```

### 8. SettingsSidebar.tsx

**수정 내용:** 1개 onError fallback

```typescript
const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

onError={(e) => {
  const target = e.target as HTMLImageElement;
  target.src = `${CDN_URL}/tanjiro.png`;
}}
```

### 9. globals.css (특수 처리)

**문제:** CSS는 JavaScript 환경 변수를 사용할 수 없음

**해결:** 주석 추가 + 향후 사용 시 인라인 스타일 권장

```css
/* 배경 이미지 클래스
 * ⚠️ 주의: 현재 사용되지 않음.
 * CSS는 환경 변수를 직접 사용할 수 없으므로,
 * S3+CloudFront 배포 시 이 클래스 대신 인라인 스타일을 사용하세요.
 *
 * 예시:
 * const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';
 * style={{ backgroundImage: `url('${CDN_URL}/엔딩이후.png')` }}
 */
.bg-ending-default {
  background-image: url('/images/엔딩이후.png');
}
```

---

## 환경별 설정

### 로컬 개발 환경

**빌드 명령어:**
```bash
cd front
npm run dev
```

**환경 변수 로드:**
- `.env` 파일 자동 로드
- `VITE_CDN_URL=/images`
- 기존 로컬 이미지 경로 유지

### AWS 프로덕션 환경

**빌드 명령어:**
```bash
cd front
npm run build
```

**환경 변수 로드:**
- `.env.production` 파일 자동 로드
- `VITE_CDN_URL=https://d1a2b3c4d5e6f7.cloudfront.net`
- CloudFront CDN에서 이미지 로드

### 환경 확인 방법

```typescript
// 콘솔에서 확인
console.log('CDN URL:', import.meta.env.VITE_CDN_URL);
console.log('Environment:', import.meta.env.VITE_ENVIRONMENT);
```

---

## 테스트 방법

### 1. 로컬 환경 테스트

```bash
# 1. 프론트엔드 시작
cd front
npm run dev

# 2. 브라우저 개발자 도구 열기
# 3. Network 탭 확인
# 4. 이미지가 localhost:3000/images/... 에서 로드되는지 확인
```

**체크리스트:**
- [ ] 홈페이지 시나리오 카드 이미지 로드
- [ ] 홈페이지 배경 이미지 로드
- [ ] 채팅 인터페이스 프로필 이미지 로드
- [ ] 친밀도 패널 캐릭터 이미지 로드
- [ ] 캐릭터 선택 모달 이미지 로드

### 2. 프로덕션 빌드 테스트

```bash
# 1. 프로덕션 빌드
cd front
npm run build

# 2. 빌드 결과 확인
ls -la dist/

# 3. 로컬 서버로 프로덕션 빌드 테스트
npx serve -s dist

# 4. 브라우저에서 확인
# http://localhost:3000
```

### 3. AWS 배포 후 테스트

**이미지 업로드:**
```bash
# S3에 이미지 업로드
aws s3 sync front/public/images/ s3://kime-images-bucket/ --region ap-northeast-2

# CloudFront 캐시 무효화
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/*"
```

**배포 후 확인:**
1. `.env.production`에 실제 CloudFront URL 설정
2. 프론트엔드 재빌드 및 S3 배포
3. 브라우저 Network 탭에서 이미지가 CloudFront에서 로드되는지 확인

---

## 알아야 할 개념

### 1. 환경 변수란?
실행 환경에 따라 다른 값을 사용할 수 있는 변수
- 개발: 로컬 API 사용
- 프로덕션: AWS API 사용

### 2. CDN (Content Delivery Network)이란?
전 세계에 분산된 서버를 통해 콘텐츠를 빠르게 제공하는 네트워크
- **장점:** 빠른 로딩 속도, 서버 부하 감소
- **AWS CloudFront:** AWS의 CDN 서비스

### 3. Vite 환경 변수 규칙
- `VITE_` 접두사 필수
- `.env` vs `.env.production` 자동 전환
- 빌드 타임에 코드에 주입됨

### 4. TypeScript d.ts 파일
타입 정의만 포함하는 파일
- 실제 코드 없음
- 컴파일러에게 타입 정보만 제공

---

## 트러블슈팅

### 문제 1: import.meta.env 타입 에러

**에러 메시지:**
```
'ImportMeta' 형식에 'env' 속성이 없습니다. (TS2339)
```

**해결:**
`front/src/vite-env.d.ts` 파일 생성으로 해결

### 문제 2: 이미지가 로드되지 않음

**원인:** 환경 변수가 제대로 로드되지 않음

**해결:**
1. 개발 서버 재시작: `npm run dev`
2. `.env` 파일 위치 확인: `front/.env`
3. 파일명 확인: `.env` (숨김 파일)

### 문제 3: CSS 배경 이미지 적용 안 됨

**원인:** CSS는 환경 변수 사용 불가

**해결:**
인라인 스타일로 변경:
```typescript
style={{ backgroundImage: `url('${CDN_URL}/이미지.png')` }}
```

---

## 다음 단계

1. ✅ 로컬 이미지 경로 CDN 대응 완료
2. ⏳ AWS S3 버킷 생성
3. ⏳ CloudFront 배포 생성
4. ⏳ 이미지 S3 업로드
5. ⏳ `.env.production` 실제 URL 업데이트

**관련 문서:** [03_aws_deployment_guide.md](03_aws_deployment_guide.md)

---
작성일: 2025-10-30
수정 파일: 9개
이미지 경로: 43개
