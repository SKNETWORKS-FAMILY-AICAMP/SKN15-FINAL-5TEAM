import { CSSProperties, useCallback, useLayoutEffect, useRef, useState, useEffect } from 'react';

interface TutorialOverlayProps {
  onComplete: () => void;
}

type Placement = 'top' | 'bottom' | 'left' | 'right';

interface Step {
  title: string;
  description: string;
  targetSelector: string;
  placement: Placement;
}

const steps: Step[] = [
  {
    title: '대화 목록',
    description: '이 버튼을 눌러 이전 대화 기록을 보거나 새로운 대화를 시작할 수 있습니다.',
    targetSelector: '[data-tour-target="chat-menu-button"]',
    placement: 'right'
  },
  {
    title: '설정 메뉴',
    description: '여기서 테마(다크/라이트)와 글씨 크기를 조절, 다국어 설정을 할 수 있습니다.',
    targetSelector: '[data-tour-target="chat-settings-button"]',
    placement: 'left'
  },
  {
    title: '내 계정',
    description: 'My account 버튼을 눌러 계정 정보와 크레딧을 확인할 수 있습니다.',
    targetSelector: '[data-tour-target="my-account-button"]',
    placement: 'bottom'
  },
  {
    title: '친밀도',
    description: '각 캐릭터와의 친밀도를 확인할 수 있습니다. 대화를 통해 친밀도를 높여보세요!',
    targetSelector: '[data-tour-target="affinity-panel"]',
    placement: 'top'
  },
  {
    title: '버블 크레딧',
    description: '버블이 0이 되면 채팅을 할 수 없습니다. 버블을 충전하여 대화를 계속하세요!',
    targetSelector: '[data-tour-target="bubble-counter"]',
    placement: 'top'
  },
  {
    title: '채팅 입력창',
    description: '이제 직접 참여해보세요!',
    targetSelector: '[data-tour-target="chat-input"]',
    placement: 'top'
  }
];

export default function TutorialOverlay({ onComplete }: TutorialOverlayProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [cardPosition, setCardPosition] = useState<CSSProperties>({});
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [cardPositions, setCardPositions] = useState<Record<number, CSSProperties>>({});
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  const calculatePosition = useCallback(() => {
    if (!cardRef.current) return;

    const current = steps[currentStep];
    const targetEl = document.querySelector(current.targetSelector) as HTMLElement | null;
    const cardRect = cardRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const padding = 12;
    const offset = 10;

    // 기본값: 화면 중앙
    let top = (viewportHeight - cardRect.height) / 2;
    let left = (viewportWidth - cardRect.width) / 2;

    if (targetEl) {
      const rect = targetEl.getBoundingClientRect();
      switch (current.placement) {
        case 'bottom':
          top = rect.bottom + offset;
          left = rect.left + rect.width / 2 - cardRect.width / 2;
          break;
        case 'top':
          top = rect.top - cardRect.height - offset;
          left = rect.left + rect.width / 2 - cardRect.width / 2;
          break;
        case 'left':
          top = rect.top + rect.height / 2 - cardRect.height / 2;
          left = rect.left - cardRect.width - offset;
          break;
        case 'right':
          top = rect.top + rect.height / 2 - cardRect.height / 2;
          left = rect.right + offset;
          break;
      }
    }

    const clampedTop = Math.min(Math.max(top, padding), viewportHeight - cardRect.height - padding);
    const clampedLeft = Math.min(Math.max(left, padding), viewportWidth - cardRect.width - padding);

    setCardPosition({ top: `${clampedTop}px`, left: `${clampedLeft}px` });
  }, [currentStep]);

  useLayoutEffect(() => {
    calculatePosition();
    window.addEventListener('resize', calculatePosition);
    return () => window.removeEventListener('resize', calculatePosition);
  }, [calculatePosition]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const current = steps[currentStep];

  const getArrowStyle = (placement: Placement): CSSProperties => {
    switch (placement) {
      case 'bottom':
        return { top: -8, left: '50%', transform: 'translateX(-50%) rotate(45deg)' };
      case 'top':
        return { bottom: -8, left: '50%', transform: 'translateX(-50%) rotate(45deg)' };
      case 'left':
        return { right: -8, top: '50%', transform: 'translateY(-50%) rotate(45deg)' };
      case 'right':
        return { left: -8, top: '50%', transform: 'translateY(-50%) rotate(45deg)' };
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 z-[10000]">
      {/* 튜토리얼 카드 */}
      <div
        ref={cardRef}
        style={cardPosition}
        className="absolute p-6 bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-xs w-full"
      >
        {/* 화살표 */}
        <div
          className="absolute w-4 h-4 bg-white dark:bg-gray-800 transform rotate-45"
          style={getArrowStyle(current.placement)}
        ></div>

        {/* 진행 표시 */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {currentStep + 1} / {steps.length}
          </span>
          <button
            onClick={onComplete}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        {/* 제목 및 설명 */}
        <h3 className="text-lg font-bold text-purple-600 dark:text-purple-400 mb-2">
          {current.title}
        </h3>
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
          {current.description}
        </p>

        {/* 네비게이션 버튼 */}
        <div className="flex justify-between items-center">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 disabled:opacity-30 disabled:cursor-not-allowed hover:text-purple-600"
          >
            이전
          </button>
          <button
            onClick={handleNext}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 text-sm"
          >
            {currentStep === steps.length - 1 ? '완료' : '다음'}
          </button>
        </div>
      </div>
    </div>
  );
}
