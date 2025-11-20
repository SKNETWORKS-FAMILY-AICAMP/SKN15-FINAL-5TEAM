import { CSSProperties, useCallback, useLayoutEffect, useRef, useState } from 'react';

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
    placement: 'left'
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
  const [step, setStep] = useState(0);
  const [cardPosition, setCardPosition] = useState<CSSProperties>({});
  const [arrowPosition, setArrowPosition] = useState<CSSProperties>({});
  const cardRef = useRef<HTMLDivElement | null>(null);

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  const updatePosition = useCallback(() => {
    const current = steps[step];
    const cardEl = cardRef.current;
    const targetEl = document.querySelector(current.targetSelector) as HTMLElement | null;

    if (!cardEl) return;

    const cardRect = cardEl.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const padding = 12;
    const offset = 10;

    // 기본값: 화면 중앙
    let top = (viewportHeight - cardRect.height) / 2;
    let left = (viewportWidth - cardRect.width) / 2;
    let arrow: CSSProperties = { top: '50%', left: '50%', transform: 'translate(-50%, -50%) rotate(45deg)' };

    if (targetEl) {
      const rect = targetEl.getBoundingClientRect();
      switch (current.placement) {
        case 'bottom':
          top = rect.bottom + offset;
          left = rect.left + rect.width / 2 - cardRect.width / 2;
          arrow = { top: -8, left: '50%', transform: 'translateX(-50%) rotate(45deg)' };
          break;
        case 'top':
          top = rect.top - cardRect.height - offset;
          left = rect.left + rect.width / 2 - cardRect.width / 2;
          arrow = { bottom: -8, left: '50%', transform: 'translateX(-50%) rotate(45deg)' };
          break;
        case 'left':
          top = rect.top + rect.height / 2 - cardRect.height / 2;
          left = rect.left - cardRect.width - offset;
          arrow = { right: -8, top: '50%', transform: 'translateY(-50%) rotate(45deg)' };
          break;
        case 'right':
          top = rect.top + rect.height / 2 - cardRect.height / 2;
          left = rect.right + offset;
          arrow = { left: -8, top: '50%', transform: 'translateY(-50%) rotate(45deg)' };
          break;
      }
    }

    const clampedTop = Math.min(Math.max(top, padding), viewportHeight - cardRect.height - padding);
    const clampedLeft = Math.min(Math.max(left, padding), viewportWidth - cardRect.width - padding);

    setCardPosition({ top: `${clampedTop}px`, left: `${clampedLeft}px` });
    setArrowPosition(arrow);
  }, [step]);

  useLayoutEffect(() => {
    updatePosition();
    window.addEventListener('resize', updatePosition);
    return () => window.removeEventListener('resize', updatePosition);
  }, [updatePosition]);

  const currentStep = steps[step];

  return (
    <div className="fixed inset-0 bg-black/40 z-[10000]">
      <div
        ref={cardRef}
        style={cardPosition}
        className="absolute p-6 bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-xs w-full transition-all duration-300"
      >
        <div
          className="absolute w-4 h-4 bg-white dark:bg-gray-800 transform rotate-45"
          style={arrowPosition}
        ></div>
        <h3 className="text-lg font-bold text-purple-600 dark:text-purple-400 mb-2">{currentStep.title}</h3>
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">{currentStep.description}</p>
        <div className="flex justify-between items-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {step + 1} / {steps.length}
          </div>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                onClick={handlePrevious}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors font-semibold"
              >
                ← 이전
              </button>
            )}
            <button
              onClick={handleNext}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-semibold"
            >
              {step < steps.length - 1 ? '다음 →' : '시작하기'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
