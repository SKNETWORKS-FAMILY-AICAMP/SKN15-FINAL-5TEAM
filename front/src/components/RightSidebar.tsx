
import { useState } from 'react';

interface RightSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  currentUser?: string;
}

export default function RightSidebar({ isOpen, onToggle, currentUser }: RightSidebarProps) {
  const [selectedTab, setSelectedTab] = useState('info');

  return (
    <>
      {/* 사이드바 토글 버튼 */}
      <button
        onClick={onToggle}
        className="fixed top-4 right-4 z-50 bg-indigo-600 text-white p-2 rounded-full shadow-lg hover:bg-indigo-700 transition-colors"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>

      {/* 사이드바 오버레이 */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={onToggle}
        />
      )}

      {/* 사이드바 */}
      <div
        className={`fixed top-0 right-0 h-full w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-40 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* 헤더 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-indigo-600 text-white">
            <h2 className="text-lg font-bold">📊 정보 패널</h2>
            <button
              onClick={onToggle}
              className="text-white hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 탭 메뉴 */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setSelectedTab('info')}
              className={`flex-1 px-4 py-2 text-sm font-medium ${
                selectedTab === 'info'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              💁‍♂️ 내 정보
            </button>
            <button
              onClick={() => setSelectedTab('stats')}
              className={`flex-1 px-4 py-2 text-sm font-medium ${
                selectedTab === 'stats'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📈 통계
            </button>
            <button
              onClick={() => setSelectedTab('help')}
              className={`flex-1 px-4 py-2 text-sm font-medium ${
                selectedTab === 'help'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              ❓ 도움말
            </button>
          </div>

          {/* 탭 컨텐츠 */}
          <div className="flex-1 overflow-y-auto p-4">
            {selectedTab === 'info' && (
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">👤 현재 사용자</h3>
                  <p className="text-gray-600">
                    {currentUser || '로그인하지 않음'}
                  </p>
                </div>

                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🎖️ 계급 정보</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>계급:</span>
                      <span className="font-medium">귀살대 대원</span>
                    </div>
                    <div className="flex justify-between">
                      <span>경험치:</span>
                      <span className="font-medium">150/500</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: '30%' }}></div>
                    </div>
                  </div>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">⚔️ 장비 상태</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>일륜도:</span>
                      <span className="text-green-600 font-medium">양호</span>
                    </div>
                    <div className="flex justify-between">
                      <span>귀살대 복장:</span>
                      <span className="text-green-600 font-medium">착용중</span>
                    </div>
                    <div className="flex justify-between">
                      <span>까마귀:</span>
                      <span className="text-blue-600 font-medium">대기중</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {selectedTab === 'stats' && (
              <div className="space-y-4">
                <div className="bg-yellow-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">📊 채팅 통계</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>총 메시지:</span>
                      <span className="font-medium">47개</span>
                    </div>
                    <div className="flex justify-between">
                      <span>오늘 메시지:</span>
                      <span className="font-medium">12개</span>
                    </div>
                    <div className="flex justify-between">
                      <span>연속 대화일:</span>
                      <span className="font-medium">3일</span>
                    </div>
                  </div>
                </div>

                <div className="bg-purple-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🏆 업적</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center space-x-2">
                      <span>🥉</span>
                      <span>첫 대화 달성</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span>💬</span>
                      <span>활발한 대화꾼</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-400">
                      <span>🔒</span>
                      <span>백전백승 (잠김)</span>
                    </div>
                  </div>
                </div>

                <div className="bg-red-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">👹 도깨비 토벌 기록</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>토벌 수:</span>
                      <span className="font-medium">23마리</span>
                    </div>
                    <div className="flex justify-between">
                      <span>최고 연승:</span>
                      <span className="font-medium">7연승</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {selectedTab === 'help' && (
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🔧 사용법</h3>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>• 왼쪽 상단 버튼으로 메뉴를 열 수 있습니다</p>
                    <p>• 로그인 후 채팅을 시작할 수 있습니다</p>
                    <p>• 빠른 응답 버튼을 활용해보세요</p>
                    <p>• 다양한 호흡법을 배워보세요</p>
                  </div>
                </div>

                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🎮 단축키</h3>
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex justify-between">
                      <span>Enter:</span>
                      <span>메시지 전송</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Esc:</span>
                      <span>모달 닫기</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Ctrl + L:</span>
                      <span>로그인</span>
                    </div>
                  </div>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">💡 팁</h3>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>• 탄지로와 친해지려면 자주 대화하세요</p>
                    <p>• 호흡법을 배우면 더 강해집니다</p>
                    <p>• 도깨비 정보를 숙지하세요</p>
                    <p>• 동료 귀살대와 협력하세요</p>
                  </div>
                </div>

                <div className="bg-red-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">⚠️ 주의사항</h3>
                  <div className="space-y-2 text-sm text-red-600">
                    <p>• 밤에는 도깨비를 조심하세요</p>
                    <p>• 햇빛이 없는 곳은 위험합니다</p>
                    <p>• 무잔을 만나면 즉시 도망치세요</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 푸터 */}
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <p className="text-xs text-gray-500 text-center">
              Kimetsu Chat v1.0<br />
              📞 문의: demon.slayer@kimetsu.jp
            </p>
          </div>
        </div>
      </div>
    </>
  );
}