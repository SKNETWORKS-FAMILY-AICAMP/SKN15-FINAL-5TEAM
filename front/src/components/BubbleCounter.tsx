
import { useState, useEffect } from 'react';
import { useApp } from '@/contexts/AppContext';
import { getBubbleColor, getBubbleStatus } from '@/utils/bubbleUtils';

interface BubbleCounterProps {
  showEmergencyRefill?: boolean;
}

export default function BubbleCounter({ showEmergencyRefill = true }: BubbleCounterProps) {
  const { currentBubbles, updateBubbles, openPaymentModal } = useApp();
  const [isAnimating, setIsAnimating] = useState(false);

  // 버블 감소 애니메이션
  useEffect(() => {
    if (currentBubbles < 1000) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 500);
      return () => clearTimeout(timer);
    }
  }, [currentBubbles]);

  // 움직이는 버블들 생성
  const renderFloatingBubbles = () => {
    const bubbles = [];
    for (let i = 0; i < 5; i++) {
      bubbles.push(
        <div
          key={i}
          className={`absolute animate-bounce text-blue-400 opacity-70`}
          style={{
            left: `${10 + i * 15}%`,
            animationDelay: `${i * 0.2}s`,
            animationDuration: `${2 + i * 0.3}s`
          }}
        >
          🫧
        </div>
      );
    }
    return bubbles;
  };

  return (
    <div className="relative bg-white bg-opacity-90 backdrop-blur-sm rounded-xl p-4 shadow-lg border border-purple-200">
      {/* 플로팅 버블들 */}
      <div className="absolute -top-2 left-0 w-full h-8">
        {renderFloatingBubbles()}
      </div>

      {/* 메인 카운터 */}
      <div className="flex items-center space-x-3">
        {/* 메인 버블 아이콘 */}
        <div className={`text-4xl ${isAnimating ? 'animate-pulse scale-110' : ''} transition-all duration-500`}>
          🫧
        </div>

        {/* 카운터 정보 */}
        <div className="flex flex-col">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold text-gray-600">버블</span>
            <span className={`text-2xl font-bold ${getBubbleColor(currentBubbles)} ${isAnimating ? 'animate-bounce' : ''} transition-all duration-300`}>
              {currentBubbles.toLocaleString()}
            </span>
          </div>

          {/* 진행 바 */}
          <div className="w-24 h-2 bg-gray-200 rounded-full mt-1 overflow-hidden">
            <div
              className={`h-full ${getBubbleColor(currentBubbles).replace('text-', 'bg-')} rounded-full transition-all duration-500 ease-out`}
              style={{ width: `${Math.min(100, (currentBubbles / 1000) * 100)}%` }}
            ></div>
          </div>

          {/* 상태 텍스트 */}
          <span className="text-xs text-gray-500 mt-1">
            {getBubbleStatus(currentBubbles)}
          </span>
        </div>
      </div>

      {/* 경고 메시지 */}
      {currentBubbles <= 100 && (
        <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded animate-pulse">
          ⚠️ 버블이 부족합니다! 대화를 줄여주세요.
        </div>
      )}

      {/* 보충 버튼 */}
      {showEmergencyRefill && currentBubbles <= 50 && (
        <div className="mt-2 space-y-1">
          <button
            onClick={() => updateBubbles(currentBubbles + 1000)}
            className="w-full px-3 py-1 bg-purple-500 text-white text-xs rounded hover:bg-purple-600 transition-colors animate-bounce"
          >
            🔄 응급 충전 (1000개)
          </button>
          <button
            onClick={openPaymentModal}
            className="w-full px-3 py-1 bg-cyan-500 text-white text-xs rounded hover:bg-cyan-600 transition-colors"
          >
            💰 정식 충전하기
          </button>
        </div>
      )}
    </div>
  );
}