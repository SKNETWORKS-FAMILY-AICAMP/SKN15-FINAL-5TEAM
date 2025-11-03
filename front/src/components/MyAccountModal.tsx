import { useState, useEffect } from 'react'
import { useApp } from '@/contexts/AppContext'
import { apiClient, UserInfo } from '@/services/api'

export default function MyAccountModal() {
  const { isMyAccountModalOpen, closeMyAccount, logout } = useApp()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isMyAccountModalOpen) {
      loadUserInfo()
    }
  }, [isMyAccountModalOpen])

  const loadUserInfo = async () => {
    try {
      setLoading(true)
      setError('')
      const info = await apiClient.getCurrentUser()
      setUserInfo(info)
    } catch (err) {
      console.error('Failed to load user info:', err)
      setError('사용자 정보를 불러올 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (!isMyAccountModalOpen) return null

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
              https://kimechat.com/account
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
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-4"></div>
                <p className="text-gray-500">로딩 중...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-red-500 mb-4">{error}</p>
                <button
                  onClick={loadUserInfo}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  다시 시도
                </button>
              </div>
            </div>
          ) : userInfo ? (
            <>
              {/* 프로필 섹션 */}
              <div className="flex items-center space-x-4 mb-8">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 text-xl font-bold">
                    {userInfo.display_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">내 계정</h2>
                  <p className="text-gray-600">{userInfo.display_name}</p>
                </div>
              </div>

              {/* 계정 정보 */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">계정 정보</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">사용자 ID</span>
                    <span className="text-gray-800 font-medium text-xs">{userInfo.user_id.slice(0, 8)}...</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">사용자명</span>
                    <span className="text-gray-800 font-medium">{userInfo.username}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">표시 이름</span>
                    <span className="text-gray-800 font-medium">{userInfo.display_name}</span>
                  </div>
                </div>
              </div>

              {/* 대화 기록 안내 */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">최근 대화</h3>
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <p className="text-gray-500 text-sm">
                    대화 기록은 채팅 페이지에서<br />
                    "이어서 하기" 기능으로 확인하실 수 있습니다
                  </p>
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
                    logout()
                    closeMyAccount()
                  }}
                  className="w-full p-3 bg-red-50 rounded-lg text-left hover:bg-red-100 transition-colors"
                >
                  <span className="text-red-600">로그아웃</span>
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
