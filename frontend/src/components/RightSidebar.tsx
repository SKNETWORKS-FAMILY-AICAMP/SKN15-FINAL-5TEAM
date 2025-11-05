
import { useState, useEffect } from 'react'
import { apiClient, UserProgression } from '@/services/api'

interface RightSidebarProps {
  isOpen: boolean
  onToggle: () => void
  currentUser?: string
}

// Helper function to map equipment status to Korean text
const getEquipmentStatusKo = (status: string): string => {
  const statusMap: Record<string, string> = {
    excellent: '완벽',
    good: '양호',
    fair: '보통',
    poor: '나쁨',
    broken: '파손',
    pristine: '새것',
    worn: '착용중',
    equipped: '장착',
    damaged: '손상',
    torn: '찢김',
    waiting: '대기중',
    active: '활동중',
    resting: '휴식',
    absent: '부재중'
  }
  return statusMap[status] || status
}

// Helper function to get equipment status color
const getEquipmentStatusColor = (status: string): string => {
  const colorMap: Record<string, string> = {
    excellent: 'text-blue-600',
    good: 'text-green-600',
    fair: 'text-yellow-600',
    poor: 'text-orange-600',
    broken: 'text-red-600',
    pristine: 'text-blue-600',
    worn: 'text-green-600',
    equipped: 'text-green-600',
    damaged: 'text-orange-600',
    torn: 'text-red-600',
    waiting: 'text-blue-600',
    active: 'text-green-600',
    resting: 'text-yellow-600',
    absent: 'text-gray-600'
  }
  return colorMap[status] || 'text-gray-600'
}

export default function RightSidebar({ isOpen, onToggle, currentUser }: RightSidebarProps) {
  const [selectedTab, setSelectedTab] = useState('info')
  const [progression, setProgression] = useState<UserProgression | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load progression data when sidebar opens and user is logged in
  useEffect(() => {
    if (isOpen && currentUser) {
      const loadProgression = async () => {
        setLoading(true)
        setError(null)
        try {
          const data = await apiClient.getUserProgression()
          setProgression(data)
        } catch (err) {
          console.error('Failed to load progression:', err)
          setError('진행도 데이터를 불러올 수 없습니다')
        } finally {
          setLoading(false)
        }
      }
      loadProgression()
    }
  }, [isOpen, currentUser])

  // Calculate XP progress percentage
  const xpProgressPercent = progression
    ? Math.min(100, (progression.experience_points / (progression.next_rank_xp || 1)) * 100)
    : 0

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
            {loading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-3"></div>
                  <p className="text-gray-600">데이터 로딩 중...</p>
                </div>
              </div>
            )}

            {error && !loading && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <p className="text-red-600">{error}</p>
                <button
                  onClick={() => window.location.reload()}
                  className="mt-2 text-sm text-red-700 underline"
                >
                  다시 시도
                </button>
              </div>
            )}

            {!loading && !error && selectedTab === 'info' && (
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">👤 현재 사용자</h3>
                  <p className="text-gray-600">
                    {currentUser || '로그인하지 않음'}
                  </p>
                </div>

                {progression && (
                  <>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-800 mb-2 flex items-center space-x-2">
                        <span>🎖️ 계급 정보</span>
                        <span className="text-lg">{progression.rank_icon}</span>
                      </h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>계급:</span>
                          <span className="font-medium">{progression.rank_name_ko}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>레벨:</span>
                          <span className="font-medium">Lv. {progression.level}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>경험치:</span>
                          <span className="font-medium">
                            {progression.experience_points.toLocaleString()}/{progression.next_rank_xp?.toLocaleString() || '∞'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${xpProgressPercent}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 text-center mt-1">
                          {xpProgressPercent.toFixed(1)}% 달성
                        </p>
                      </div>
                    </div>

                    <div className="bg-green-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-800 mb-2">⚔️ 장비 상태</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>일륜도:</span>
                          <span className={`${getEquipmentStatusColor(progression.sword_status)} font-medium`}>
                            {getEquipmentStatusKo(progression.sword_status)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>귀살대 복장:</span>
                          <span className={`${getEquipmentStatusColor(progression.uniform_status)} font-medium`}>
                            {getEquipmentStatusKo(progression.uniform_status)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>까마귀:</span>
                          <span className={`${getEquipmentStatusColor(progression.crow_status)} font-medium`}>
                            {getEquipmentStatusKo(progression.crow_status)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {!progression && !loading && currentUser && (
                  <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-600">
                    진행도 데이터를 사용할 수 없습니다
                  </div>
                )}
              </div>
            )}

            {!loading && !error && selectedTab === 'stats' && (
              <div className="space-y-4">
                {progression ? (
                  <>
                    <div className="bg-yellow-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-800 mb-2">📊 채팅 통계</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>총 메시지:</span>
                          <span className="font-medium">{progression.total_messages.toLocaleString()}개</span>
                        </div>
                        <div className="flex justify-between">
                          <span>총 세션:</span>
                          <span className="font-medium">{progression.total_sessions.toLocaleString()}회</span>
                        </div>
                        <div className="flex justify-between">
                          <span>플레이 시간:</span>
                          <span className="font-medium">
                            {Math.floor(progression.total_play_minutes / 60)}시간 {progression.total_play_minutes % 60}분
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-purple-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-800 mb-2">🏆 완료 현황</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>시나리오 완료:</span>
                          <span className="font-medium">{progression.scenarios_completed}개</span>
                        </div>
                        <div className="flex justify-between">
                          <span>획득 업적:</span>
                          <span className="font-medium">{progression.achievements_count}개</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-800 mb-2">📈 진행도 요약</h3>
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>레벨 진행도</span>
                            <span className="font-medium">Lv. {progression.level}</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ width: `${Math.min(100, (progression.level / 99) * 100)}%` }}
                            ></div>
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>다음 계급까지</span>
                            <span className="font-medium">{xpProgressPercent.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-green-500 h-2 rounded-full"
                              style={{ width: `${xpProgressPercent}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-600">
                    통계 데이터를 사용할 수 없습니다
                  </div>
                )}
              </div>
            )}

            {selectedTab === 'help' && (
              <div className="space-y-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🎮 게임 방법</h3>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li>• 시나리오를 선택하여 캐릭터와 대화하세요</li>
                    <li>• 메시지를 보내면 경험치를 획득합니다</li>
                    <li>• 경험치가 쌓이면 레벨이 올라갑니다</li>
                    <li>• 일정 경험치에 도달하면 계급이 상승합니다</li>
                  </ul>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🎖️ 계급 시스템</h3>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li>🌱 견습생 (Lv. 1-5)</li>
                    <li>⚔️ 귀살대 대원 (Lv. 6-15)</li>
                    <li>🏅 정예 대원 (Lv. 16-30)</li>
                    <li>🌟 주 후보 (Lv. 31-50)</li>
                    <li>💎 주 (柱) (Lv. 51-99)</li>
                  </ul>
                </div>

                <div className="bg-purple-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">💡 팁</h3>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li>• 매일 대화하여 꾸준히 경험치를 쌓으세요</li>
                    <li>• 다양한 시나리오를 완료하면 업적을 획득합니다</li>
                    <li>• 리더보드에서 다른 사용자와 순위를 비교하세요</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
