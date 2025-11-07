import { useState } from 'react';

interface TutorialOverlayProps {
  onComplete: () => void;
}

const steps = [
  {
    title: '대화 목록',
    description: '이 버튼을 눌러 이전 대화 기록을 보거나 새로운 대화를 시작할 수 있습니다.',
    position: 'top-4 left-4',
    arrow: 'top-full left-4'
  },
  {
    title: '설정 메뉴',
    description: '여기서 테마(다크/라이트)와 글씨 크기를 조절할 수 있습니다.',
    position: 'top-4 right-4',
    arrow: 'top-full right-4'
  },
  {
    title: '채팅 입력창',
    description: '이제 직접 참여해보세요!',
    position: 'bottom-20 left-1/2 -translate-x-1/2',
    arrow: 'bottom-full left-1/2 -translate-x-1/2'
  }
];

export default function TutorialOverlay({ onComplete }: TutorialOverlayProps) {
  const [step, setStep] = useState(0);

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      onComplete();
    }
  };

  const currentStep = steps[step];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[10000]">
      <div className={`absolute p-6 bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-xs w-full transition-all duration-300 ${currentStep.position}`}>
        <div className={`absolute w-4 h-4 bg-white dark:bg-gray-800 transform rotate-45 ${currentStep.arrow}`}></div>
        <h3 className="text-lg font-bold text-purple-600 dark:text-purple-400 mb-2">{currentStep.title}</h3>
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">{currentStep.description}</p>
        <div className="flex justify-between items-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {step + 1} / {steps.length}
          </div>
          <button 
            onClick={handleNext}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-semibold"
          >
            {step < steps.length - 1 ? '다음 →' : '시작하기'}
          </button>
        </div>
      </div>
    </div>
  );
}
