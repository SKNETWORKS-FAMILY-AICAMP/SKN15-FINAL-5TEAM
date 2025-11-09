import { useState, useEffect } from 'react'
import { useApp } from '@/contexts/AppContext'
import { Link, useNavigate } from 'react-router-dom'
import { apiClient, RecentSession, UserStatistics } from '@/services/api'

interface LeftSidebarProps {
  isOpen: boolean
  onToggle: () => void
}

export default function LeftSidebar({ isOpen, onToggle }: LeftSidebarProps) {
  const { logout, userEmail } = useApp()
  const navigate = useNavigate()
  const [activeSection, setActiveSection] = useState<'profile' | 'gallery' | 'chats' | null>(null)
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([])
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)

  // 햄버거 메뉴가 열릴 때 자동으로 최근 채팅 섹션 열기
  useEffect(() => {
    if (isOpen) {
      setActiveSection('chats')
      fetchRecentSessions()
    }
  }, [isOpen])

  // 최근 세션 데이터 가져오기
  const fetchRecentSessions = async () => {
    try {
      setLoadingSessions(true)
      const sessions = await apiClient.getRecentSessions(4)
      setRecentSessions(sessions)
    } catch (error) {
      console.error('Failed to fetch recent sessions:', error)
      setRecentSessions([])
    } finally {
      setLoadingSessions(false)
    }
  }

  // 사용자 통계 데이터 가져오기
  const fetchStatistics = async () => {
    try {
      setLoadingStats(true)
      const stats = await apiClient.getUserStatistics()
      setStatistics(stats)
    } catch (error) {
      console.error('Failed to fetch statistics:', error)
      setStatistics(null)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleLogout = () => {
    if (confirm('로그아웃 하시겠습니까?')) {
      logout()
      onToggle()
      navigate('/')
    }
  }

  const handleGoHome = () => {
    navigate('/')
    onToggle()
  }

  const handleSessionClick = (sessionId: string, scenarioId: string) => {
    navigate(`/chat?scenario=${scenarioId}&session=${sessionId}`)
    onToggle()
  }

  const toggleSection = (section: 'profile' | 'gallery' | 'chats') => {
    const newSection = activeSection === section ? null : section
    setActiveSection(newSection)

    // 프로필 섹션을 열 때마다 최신 통계 데이터 가져오기
    if (newSection === 'profile') {
      fetchStatistics()
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '방금 전'
    if (diffMins < 60) return `${diffMins}분 전`
    if (diffHours < 24) return `${diffHours}시간 전`
    if (diffDays < 7) return `${diffDays}일 전`
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }

  return (
    <>
      {/* 사이드바 오버레이 */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-[100]"
          onClick={onToggle}
        />
      )}

      {/* 사이드바 */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-[110] ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* 헤더 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-purple-600 text-white">
            <div>
              <h2 className="text-lg font-bold">메뉴</h2>
              {userEmail && <p className="text-xs text-purple-100 mt-1">{userEmail}</p>}
            </div>
            <button
              onClick={onToggle}
              className="text-white hover:text-gray-200"
              aria-label="메뉴 닫기"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 메뉴 항목들 */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-2">
              {/* 홈으로 */}
              <button
                onClick={handleGoHome}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-purple-50 transition-colors flex items-center space-x-3"
              >
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="font-medium text-gray-700">홈으로</span>
              </button>

              <div className="border-t border-gray-200 my-3"></div>

              {/* 프로필/통계 */}
              <div>
                <button
                  onClick={() => toggleSection('profile')}
                  className="w-full text-left px-4 py-3 rounded-lg hover:bg-purple-50 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="font-medium text-gray-700">프로필 & 통계</span>
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${activeSection === 'profile' ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {activeSection === 'profile' && (
                  <div className="ml-4 mt-2 space-y-3">
                    {/* 새로고침 버튼 */}
                    <div className="flex justify-end">
                      <button
                        onClick={fetchStatistics}
                        disabled={loadingStats}
                        className="text-xs text-purple-600 hover:text-purple-700 flex items-center space-x-1 disabled:opacity-50"
                      >
                        <svg className={`w-4 h-4 ${loadingStats ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>새로고침</span>
                      </button>
                    </div>

                    {loadingStats ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                      </div>
                    ) : statistics ? (
                      <>
                        {/* 계급 및 레벨 */}
                        {statistics.rank && (
                          <div className="bg-gradient-to-br from-amber-50 to-orange-50 p-3 rounded-lg border border-amber-200">
                            <p className="text-xs font-semibold text-amber-700 mb-2">{statistics.rank.rank_icon} 계급</p>
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-bold text-gray-800">{statistics.rank.rank_name_ko}</span>
                                <span className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded-full font-semibold">
                                  Lv. {statistics.rank.level}
                                </span>
                              </div>
                              <div>
                                <div className="flex justify-between text-xs text-gray-600 mb-1">
                                  <span>경험치</span>
                                  <span className="font-semibold">
                                    {statistics.rank.experience_points.toLocaleString()} XP
                                    {statistics.rank.next_rank_xp && ` / ${statistics.rank.next_rank_xp.toLocaleString()} XP`}
                                  </span>
                                </div>
                                {statistics.rank.next_rank_xp && (
                                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-amber-400 to-orange-500"
                                      style={{
                                        width: `${Math.min(100, (statistics.rank.experience_points / statistics.rank.next_rank_xp) * 100)}%`
                                      }}
                                    />
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 시나리오 진행도 */}
                        {statistics.scenario_progress && (
                          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-3 rounded-lg border border-blue-200">
                            <p className="text-xs font-semibold text-blue-700 mb-2">🎮 시나리오 진행도</p>
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-700">클리어한 시나리오</span>
                                <span className="text-sm font-bold text-blue-600">
                                  {statistics.scenario_progress.completed_count} / {statistics.scenario_progress.total_count}
                                </span>
                              </div>
                              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-blue-400 to-indigo-500"
                                  style={{
                                    width: `${statistics.scenario_progress.total_count > 0 ? (statistics.scenario_progress.completed_count / statistics.scenario_progress.total_count) * 100 : 0}%`
                                  }}
                                />
                              </div>
                              <div className="text-xs text-gray-600">
                                총 클리어 횟수: <span className="font-semibold text-blue-600">{statistics.scenario_progress.total_completions}회</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 친밀도 TOP 5 (글로벌, 최대 1000점) */}
                        {statistics.top_affinity_characters.length > 0 && (
                          <div className="bg-gradient-to-br from-pink-50 to-purple-50 p-3 rounded-lg border border-pink-200">
                            <p className="text-xs font-semibold text-pink-700 mb-2">💜 친밀도 TOP 5</p>
                            <div className="space-y-2.5">
                              {statistics.top_affinity_characters.slice(0, 5).map((char, index) => (
                                <div key={index} className="space-y-1">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-xs font-bold text-pink-600 w-5">#{index + 1}</span>
                                      <span className="text-xs font-semibold text-gray-800">{char.character_name}</span>
                                      <span className="text-xs px-1.5 py-0.5 bg-pink-100 text-pink-700 rounded font-bold">
                                        Lv.{char.affinity_level}
                                      </span>
                                    </div>
                                    <span className="text-xs font-bold text-pink-600">
                                      {char.affinity_score} / 1000
                                    </span>
                                  </div>
                                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden ml-7">
                                    <div
                                      className="h-full bg-gradient-to-r from-pink-400 to-purple-500"
                                      style={{ width: `${(char.affinity_score / 1000) * 100}%` }}
                                    />
                                  </div>
                                  <div className="text-xs text-gray-500 ml-7">
                                    상호작용 {char.total_interactions}회
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 기본 통계 */}
                        <div className="bg-gradient-to-br from-purple-50 to-indigo-50 p-3 rounded-lg">
                          <p className="text-xs font-semibold text-purple-700 mb-2">📊 활동 통계</p>
                          <div className="space-y-1 text-xs text-gray-700">
                            <div className="flex justify-between">
                              <span>총 대화 세션:</span>
                              <span className="font-semibold text-purple-600">{statistics.total_sessions}회</span>
                            </div>
                            <div className="flex justify-between">
                              <span>총 메시지:</span>
                              <span className="font-semibold text-purple-600">{statistics.total_messages}개</span>
                            </div>
                          </div>
                        </div>

                        {/* 자주 사용한 시나리오 */}
                        {statistics.frequent_scenarios.length > 0 && (
                          <div className="bg-white border border-purple-100 p-3 rounded-lg">
                            <p className="text-xs font-semibold text-purple-700 mb-2">🎭 자주 사용한 시나리오</p>
                            <div className="space-y-2">
                              {statistics.frequent_scenarios.slice(0, 5).map((scenario, index) => (
                                <div key={index} className="text-xs">
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <span className="text-gray-800 font-medium">{scenario.title}</span>
                                    </div>
                                    <span className="text-purple-600 font-semibold ml-2">{scenario.play_count}회</span>
                                  </div>
                                  <div className="text-gray-500 text-xs mt-0.5">
                                    메시지 {scenario.total_messages}개
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 데이터가 없는 경우 */}
                        {statistics.top_affinity_characters.length === 0 &&
                         statistics.frequent_scenarios.length === 0 && (
                          <div className="text-center py-6 px-4">
                            <p className="text-sm text-gray-500 mb-1">아직 데이터가 없습니다</p>
                            <p className="text-xs text-gray-400">시나리오를 시작하고 캐릭터와 대화해보세요!</p>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-center py-6 px-4">
                        <p className="text-sm text-gray-500 mb-1">통계를 불러올 수 없습니다</p>
                        <p className="text-xs text-gray-400">잠시 후 다시 시도해주세요</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 나의 갤러리 */}
              <div>
                <Link
                  to="/gallery"
                  onClick={() => onToggle()}
                  className="w-full text-left px-4 py-3 rounded-lg hover:bg-purple-50 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="font-medium text-gray-700">나의 갤러리</span>
                  </div>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>

              {/* 최근 채팅 목록 */}
              <div>
                <div className="w-full text-left px-4 py-3 flex items-center space-x-3">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <span className="font-medium text-gray-700">최근 채팅</span>
                </div>
                <div className="ml-4 mt-2">
                  {loadingSessions ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                    </div>
                  ) : recentSessions.length === 0 ? (
                    <div className="text-center py-8 px-4">
                      <p className="text-sm text-gray-500 mb-2">저장된 대화가 없습니다</p>
                      <p className="text-xs text-gray-400">새로운 시나리오를 시작해보세요!</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {recentSessions.map((session) => (
                        <button
                          key={session.session_id}
                          onClick={() => handleSessionClick(session.session_id, session.scenario_id)}
                          className="w-full text-left p-3 bg-white rounded-lg hover:bg-purple-50 transition-colors border border-gray-200 hover:border-purple-300"
                        >
                          <div className="flex items-start space-x-3">
                            {/* 썸네일 또는 아이콘 */}
                            <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-lg flex items-center justify-center">
                              {session.scenario_thumbnail ? (
                                <img
                                  src={session.scenario_thumbnail}
                                  alt=""
                                  className="w-full h-full object-cover rounded-lg"
                                />
                              ) : (
                                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                              )}
                            </div>

                            {/* 세션 정보 */}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-gray-800 truncate">
                                {session.scenario_title || '시나리오'}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                대화 {session.turn_count}회 • {formatDate(session.updated_at)}
                              </p>
                              {session.last_message_content && (
                                <p className="text-xs text-gray-600 mt-1 line-clamp-1">
                                  <span className="font-semibold text-purple-600">{session.last_message_speaker}</span>: {session.last_message_content}
                                </p>
                              )}
                            </div>

                            {/* 화살표 아이콘 */}
                            <div className="flex-shrink-0">
                              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 푸터 - 로그아웃 */}
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center space-x-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span className="font-medium">로그아웃</span>
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
