
import { useApp } from '@/contexts/AppContext';

export default function MyAccountModal() {
  const { isMyAccountModalOpen, closeMyAccount, userEmail, logout } = useApp();

  if (!isMyAccountModalOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-2xl w-[480px] h-[600px] shadow-2xl relative overflow-hidden">
        {/* 브라우저 스타일 헤더 */}
        <div className="h-12 bg-gray-100 border-b border-gray-200 flex items-center px-4">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="bg-white rounded px-3 py-1 text-sm text-gray-600 border">
              https://example.com/account
            </div>
          </div>
          <button
            onClick={closeMyAccount}
            className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="h-[calc(100%-48px)] overflow-y-auto p-6">
          {/* 프로필 섹션 */}
          <div className="flex items-center space-x-4 mb-8">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-purple-600 text-xl font-bold">
                {userEmail.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">내 계정</h2>
              <p className="text-gray-600">{userEmail}</p>
            </div>
          </div>

          {/* 계정 정보 */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">계정 정보</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-600">이메일</span>
                <span className="text-gray-800 font-medium">{userEmail}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-600">회원 등급</span>
                <span className="text-purple-600 font-medium">프리미엄</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-600">가입일</span>
                <span className="text-gray-800 font-medium">2024.01.15</span>
              </div>
            </div>
          </div>

          {/* 대화 기록 */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">최근 대화</h3>
            <div className="space-y-3">
              <div className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-gray-800">네즈코와의 대화</span>
                  <span className="text-sm text-gray-500">2시간 전</span>
                </div>
                <p className="text-sm text-gray-600">안녕하세요! 오늘 날씨가 좋네요.</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-gray-800">탄지로와의 대화</span>
                  <span className="text-sm text-gray-500">1일 전</span>
                </div>
                <p className="text-sm text-gray-600">호흡법에 대해 알려주세요.</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-gray-800">이노스케와의 대화</span>
                  <span className="text-sm text-gray-500">3일 전</span>
                </div>
                <p className="text-sm text-gray-600">멧돼지 머리를 쓰는 이유가 뭔가요?</p>
              </div>
            </div>
          </div>

          {/* 설정 및 액션 */}
          <div className="space-y-3">
            <button className="w-full p-3 bg-gray-50 rounded-lg text-left hover:bg-gray-100 transition-colors">
              <span className="text-gray-800">개인정보 설정</span>
            </button>
            <button className="w-full p-3 bg-gray-50 rounded-lg text-left hover:bg-gray-100 transition-colors">
              <span className="text-gray-800">알림 설정</span>
            </button>
            <button className="w-full p-3 bg-gray-50 rounded-lg text-left hover:bg-gray-100 transition-colors">
              <span className="text-gray-800">도움말</span>
            </button>
            <button
              onClick={() => {
                logout();
                closeMyAccount();
              }}
              className="w-full p-3 bg-red-50 rounded-lg text-left hover:bg-red-100 transition-colors"
            >
              <span className="text-red-600">로그아웃</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}