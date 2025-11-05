
import BubbleCounter from './BubbleCounter';

export default function EndingBackground() {
  return (
    <div className="relative w-full h-full ending-bg overflow-hidden">
      {/* 엔딩 배경 요소들 */}
      <div className="absolute inset-0 bg-gradient-to-b from-blue-100 via-purple-100 to-pink-100">
        {/* 평화로운 마을 요소들 */}
        <div className="absolute bottom-0 left-8 w-24 h-32 bg-green-200 rounded-t-lg opacity-70">
          <div className="grid grid-cols-2 gap-1 p-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-3 bg-gradient-to-r from-green-400 to-yellow-400 rounded-sm"></div>
            ))}
          </div>
        </div>

        {/* 벚꽃나무 */}
        <div className="absolute bottom-0 right-8 w-16 h-40 bg-brown-400 rounded-t-lg opacity-80">
          <div className="mt-2 space-y-1 px-1">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-2 bg-pink-300 rounded-full"></div>
            ))}
          </div>
        </div>

        {/* 엔딩 캐릭터 이미지 - 화면 전체 채우기 */}
        <div className="absolute inset-0">
          <img
            src="/images/엔딩이후.png"
            alt="엔딩 이후"
            className="w-full h-full object-cover"
          />
        </div>

        {/* 부드러운 오버레이 (텍스트 가독성을 위해) */}
        <div className="absolute inset-0 bg-white bg-opacity-20 z-10"></div>

        {/* 버블 카운터 - 우상단 */}
        <div className="absolute top-4 right-4 z-30">
          <BubbleCounter />
        </div>
      </div>
    </div>
  );
}