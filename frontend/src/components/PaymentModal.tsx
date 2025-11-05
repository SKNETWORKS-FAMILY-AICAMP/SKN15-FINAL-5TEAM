
import { useState, useEffect } from 'react';
import { useApp } from '@/contexts/AppContext';
import { getBubbleColor, getBubbleStatus } from '@/utils/bubbleUtils';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface BubblePack {
  id: string;
  name: string;
  bubbles: number;
  price: string;
  originalPrice?: string;
  features: string[];
  isPopular?: boolean;
  savings?: string;
  bonus?: number;
}

const bubblePacks: BubblePack[] = [
  {
    id: 'small',
    name: '물의 호흡',
    bubbles: 1000,
    price: '₩2,900',
    features: [
      '🫧 호흡 버블 1,000개',
      '⏰ 즉시 충전',
      '💬 약 20회 대화 가능'
    ]
  },
  {
    id: 'medium',
    name: '뇌의 호흡',
    bubbles: 5000,
    price: '₩9,900',
    originalPrice: '₩14,500',
    features: [
      '🫧 호흡 버블 5,000개',
      '🎁 보너스 버블 +500개',
      '⏰ 즉시 충전',
      '💬 약 110회 대화 가능',
      '🌟 언어 학습 콘텐츠 영구 해금',
      '🗾 일본어 · 🇺🇸 영어 학습 가능'
    ],
    isPopular: true,
    savings: '32% 할인',
    bonus: 500
  },
  {
    id: 'large',
    name: '일의 호흡',
    bubbles: 12000,
    price: '₩19,900',
    originalPrice: '₩34,800',
    features: [
      '🫧 호흡 버블 12,000개',
      '🎁 보너스 버블 +3,000개',
      '⏰ 즉시 충전',
      '💬 약 300회 대화 가능',
      '🌟 언어 학습 콘텐츠 영구 해금',
      '🗾 일본어 · 🇺🇸 영어 학습 가능',
      '📚 VIP 호흡법 가이드'
    ],
    savings: '43% 할인',
    bonus: 3000
  }
];

const paymentMethods = [
  { id: 'card', name: '신용카드', icon: '💳' },
  { id: 'kakao', name: '카카오페이', icon: '🟡' },
  { id: 'toss', name: '토스페이', icon: '🔵' },
  { id: 'paypal', name: 'PayPal', icon: '🅿️' }
];

export default function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  const { currentBubbles, updateBubbles } = useApp();
  const [selectedPack, setSelectedPack] = useState('medium');
  const [selectedPayment, setSelectedPayment] = useState('card');
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasLanguageLearning, setHasLanguageLearning] = useState(false);

  // ESC 키로 닫기
  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => document.removeEventListener('keydown', handleEscKey);
  }, [isOpen, onClose]);

  // 모달이 열려있을 때 body 스크롤 방지
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const handlePayment = async () => {
    setIsProcessing(true);

    // 결제 시뮬레이션
    await new Promise(resolve => setTimeout(resolve, 2000));

    const selectedPackData = bubblePacks.find(pack => pack.id === selectedPack);
    if (selectedPackData) {
      const totalBubbles = selectedPackData.bubbles + (selectedPackData.bonus || 0);
      updateBubbles(currentBubbles + totalBubbles);

      // 뇌의 호흡 이상 구매 시 언어 학습 해금
      if ((selectedPackData.id === 'medium' || selectedPackData.id === 'large') && !hasLanguageLearning) {
        setHasLanguageLearning(true);
        alert(`🫧 호흡 버블 ${totalBubbles.toLocaleString()}개가 충전되었습니다!\n🌟 언어 학습 콘텐츠가 영구 해금되었습니다!\n캐릭터와 영어, 일본어를 배워보세요! 🗾🇺🇸`);
      } else {
        alert(`🫧 호흡 버블 ${totalBubbles.toLocaleString()}개가 충전되었습니다!\n전집중 호흡으로 더 강해졌습니다! ⚔️`);
      }
    }

    setIsProcessing(false);
    onClose();
  };


  if (!isOpen) return null;

  const selectedPackData = bubblePacks.find(pack => pack.id === selectedPack);

  return (
    <>
      {/* 오버레이 */}
      <div
        className="fixed inset-0 bg-black bg-opacity-60 z-[80]"
        onClick={onClose}
      />

      {/* 모달 */}
      <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl z-[90] w-[600px] max-w-[90vw] max-h-[90vh] overflow-y-auto">

        {/* 헤더 */}
        <div className="bg-gradient-to-r from-blue-400 via-cyan-400 to-teal-400 text-white p-6 rounded-t-2xl relative overflow-hidden">
          {/* 플로팅 버블 애니메이션 */}
          <div className="absolute inset-0">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="absolute animate-bounce text-white opacity-30"
                style={{
                  left: `${10 + i * 12}%`,
                  top: `${20 + (i % 3) * 20}%`,
                  animationDelay: `${i * 0.3}s`,
                  animationDuration: `${2 + i * 0.2}s`
                }}
              >
                🫧
              </div>
            ))}
          </div>
          <div className="relative z-10">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold flex items-center space-x-2">
                <span>🫧</span>
                <span>호흡 버블 충전소</span>
              </h2>
              <button
                onClick={onClose}
                className="text-white hover:text-gray-200 transition-colors p-2 rounded-lg hover:bg-white hover:bg-opacity-20"
                aria-label="버블 충전 창 닫기"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm opacity-90 mt-2">
              대화를 위한 호흡 버블을 충전하세요!
            </p>
          </div>
        </div>

        {/* 컨텐츠 */}
        <div className="p-6 space-y-6">

          {/* 현재 버블 상태 */}
          <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-4 border border-blue-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="text-3xl animate-pulse">🫧</div>
                <div>
                  <div className="text-sm font-medium text-gray-600">현재 보유 버블</div>
                  <div className={`text-2xl font-bold ${getBubbleColor(currentBubbles)}`}>
                    {currentBubbles.toLocaleString()}개
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">상태</div>
                <div className={`text-sm font-medium ${getBubbleColor(currentBubbles)}`}>
                  {getBubbleStatus(currentBubbles)}
                </div>
              </div>
            </div>

            {/* 진행 바 */}
            <div className="w-full h-3 bg-gray-200 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full ${getBubbleColor(currentBubbles).replace('text-', 'bg-')} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, (currentBubbles / 1000) * 100)}%` }}
              ></div>
            </div>
          </div>

          {/* 버블 팩 선택 */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-gray-800 flex items-center space-x-2">
              <span>🫧</span>
              <span>호흡 버블 팩 선택</span>
            </h3>
            <div className="grid gap-4">
              {bubblePacks.map((pack) => (
                <div
                  key={pack.id}
                  className={`relative border-2 rounded-xl p-4 cursor-pointer transition-all duration-300 ${
                    selectedPack === pack.id
                      ? 'border-cyan-500 bg-cyan-50 shadow-lg'
                      : 'border-gray-200 hover:border-cyan-300 hover:shadow-md'
                  }`}
                  onClick={() => setSelectedPack(pack.id)}
                >
                  {pack.isPopular && (
                    <div className="absolute -top-2 left-4 bg-cyan-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                      인기
                    </div>
                  )}
                  {pack.savings && (
                    <div className="absolute -top-2 right-4 bg-red-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                      {pack.savings}
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <input
                          type="radio"
                          checked={selectedPack === pack.id}
                          onChange={() => setSelectedPack(pack.id)}
                          className="text-cyan-500 focus:ring-cyan-500"
                        />
                        <h4 className="font-semibold text-gray-800 flex items-center space-x-2">
                          <span>{pack.name}</span>
                          {pack.bonus && (
                            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
                              +{pack.bonus.toLocaleString()} 보너스
                            </span>
                          )}
                        </h4>
                      </div>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {pack.features.map((feature, index) => (
                          <li key={index} className="flex items-center space-x-2">
                            <span className="text-cyan-500">✓</span>
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="text-right ml-4">
                      {pack.originalPrice && (
                        <div className="text-sm text-gray-400 line-through">
                          {pack.originalPrice}
                        </div>
                      )}
                      <div className="text-2xl font-bold text-gray-800">
                        {pack.price}
                      </div>
                      <div className="text-sm text-cyan-600 font-medium">
                        총 {(pack.bubbles + (pack.bonus || 0)).toLocaleString()}개
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 결제 수단 선택 */}
          <div>
            <h3 className="text-lg font-semibold mb-4 text-gray-800">결제 수단</h3>
            <div className="grid grid-cols-2 gap-3">
              {paymentMethods.map((method) => (
                <button
                  key={method.id}
                  onClick={() => setSelectedPayment(method.id)}
                  className={`flex items-center space-x-3 p-3 rounded-lg border-2 transition-all duration-300 ${
                    selectedPayment === method.id
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-orange-300'
                  }`}
                >
                  <span className="text-2xl">{method.icon}</span>
                  <span className="font-medium text-gray-800">{method.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 주문 요약 */}
          {selectedPackData && (
            <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-xl p-4 border border-cyan-200">
              <h3 className="text-lg font-semibold mb-3 text-gray-800 flex items-center space-x-2">
                <span>📋</span>
                <span>주문 요약</span>
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{selectedPackData.name}</span>
                  <span className="font-semibold">{selectedPackData.price}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">기본 버블</span>
                  <span className="text-cyan-600">🫧 {selectedPackData.bubbles.toLocaleString()}개</span>
                </div>
                {selectedPackData.bonus && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">보너스 버블</span>
                    <span className="text-yellow-600">🎁 +{selectedPackData.bonus.toLocaleString()}개</span>
                  </div>
                )}
                {(selectedPackData.id === 'medium' || selectedPackData.id === 'large') && !hasLanguageLearning && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">언어 학습 해금</span>
                    <span className="text-purple-600">🌟 영구 콘텐츠</span>
                  </div>
                )}
                <hr className="my-2" />
                <div className="flex justify-between items-center text-lg font-bold">
                  <span>총 획득 버블</span>
                  <span className="text-cyan-600">🫧 {(selectedPackData.bubbles + (selectedPackData.bonus || 0)).toLocaleString()}개</span>
                </div>
                <div className="flex justify-between items-center text-lg font-bold">
                  <span>결제 금액</span>
                  <span className="text-gray-800">{selectedPackData.price}</span>
                </div>

                {/* 충전 후 예상 버블 */}
                <div className="mt-3 p-3 bg-white rounded-lg border">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">충전 후 총 버블</span>
                    <span className={`font-bold ${getBubbleColor(currentBubbles + selectedPackData.bubbles + (selectedPackData.bonus || 0))}`}>
                      🫧 {(currentBubbles + selectedPackData.bubbles + (selectedPackData.bonus || 0)).toLocaleString()}개
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 결제 버튼 */}
        <div className="p-6 bg-gradient-to-r from-cyan-50 to-blue-50 rounded-b-2xl">
          <button
            onClick={handlePayment}
            disabled={isProcessing}
            className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-300 ${
              isProcessing
                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-500 via-cyan-500 to-teal-500 hover:from-blue-600 hover:via-cyan-600 hover:to-teal-600 text-white shadow-lg hover:shadow-xl transform hover:scale-105'
            }`}
          >
            {isProcessing ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>버블 충전 중...</span>
              </div>
            ) : (
              <div className="flex items-center justify-center space-x-2">
                <span>🫧</span>
                <span>호흡 버블 충전하기</span>
              </div>
            )}
          </button>

          <p className="text-xs text-gray-500 text-center mt-3">
            💡 충전된 버블은 즉시 사용 가능합니다.<br />
            💬 한 번의 대화당 약 50개의 버블이 소모됩니다.
          </p>
        </div>
      </div>
    </>
  );
}