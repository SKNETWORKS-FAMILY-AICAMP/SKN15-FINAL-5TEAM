
import BubbleCounter from './BubbleCounter';

export default function ConvenienceStoreBackground() {
  return (
    <div className="relative w-full h-full convenience-store-bg overflow-hidden">
      {/* 편의점 배경 요소들 */}
      <div className="absolute inset-0 bg-gradient-to-b from-yellow-200 via-orange-200 to-pink-200">
        {/* 편의점 진열대 */}
        <div className="absolute bottom-0 left-8 w-32 h-40 bg-gray-300 rounded-t-lg opacity-80">
          <div className="grid grid-cols-3 gap-1 p-2">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="h-4 bg-gradient-to-r from-red-400 to-blue-400 rounded-sm"></div>
            ))}
          </div>
        </div>

        {/* 편의점 냉장고 */}
        <div className="absolute bottom-0 right-8 w-20 h-48 bg-blue-100 rounded-t-lg opacity-80 border-2 border-blue-300">
          <div className="mt-4 space-y-2 px-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-4 bg-gradient-to-r from-green-400 to-blue-400 rounded"></div>
            ))}
          </div>
        </div>

        {/* 탄지로 캐릭터 이미지 - 화면 전체 채우기 */}
        <div className="absolute inset-0">
          <img
            src="/images/tanjiro.png"
            alt="탄지로"
            className="w-full h-full object-cover"
          />
        </div>

        {/* 어두운 오버레이 (텍스트 가독성을 위해) */}
        <div className="absolute inset-0 bg-black bg-opacity-30 z-10"></div>

        {/* 버블 카운터 - 우상단 */}
        <div className="absolute top-4 right-4 z-30">
          <BubbleCounter />
        </div>

      </div>
    </div>
  );
}