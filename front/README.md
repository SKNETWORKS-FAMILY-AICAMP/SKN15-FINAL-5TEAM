# 탄지로 편의점 채팅 앱

Zeplin 디자인을 기반으로 한 React + Tailwind CSS 메시징 앱입니다.

## 기능

- 🏪 탄지로 편의점 배경 (귀멸의 칼날 테마)
- 💬 실시간 채팅 인터페이스
- 📱 완전 반응형 디자인 (모바일/데스크톱)
- ⚡ 빠른 응답 버튼
- 🎨 Zeplin 디자인 시스템 기반 UI

## 기술 스택

- **프레임워크**: Next.js 14 (App Router)
- **스타일링**: Tailwind CSS
- **언어**: TypeScript
- **폰트**: Roboto

## 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 프로덕션 실행
npm start
```

## 프로젝트 구조

```
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── ConvenienceStoreBackground.tsx
│   └── ChatInterface.tsx
├── public/
│   └── images/
├── tailwind.config.js
├── postcss.config.js
└── next.config.js
```

## 주요 컴포넌트

### ConvenienceStoreBackground
- 탄지로 캐릭터와 편의점 배경
- CSS 애니메이션 효과
- 완전 반응형 디자인

### ChatInterface
- 실시간 메시지 전송/수신
- 빠른 응답 버튼
- 자동 봇 응답
- 모바일 최적화

## 디자인 시스템

Zeplin 프로젝트에서 추출한 색상과 타이포그래피를 사용:

- **Primary**: #625b71
- **Secondary**: #ece6f0
- **Accent**: #e8def8
- **Background**: #fef7ff
- **Font**: Roboto

## 반응형 브레이크포인트

- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

## 라이선스

MIT License