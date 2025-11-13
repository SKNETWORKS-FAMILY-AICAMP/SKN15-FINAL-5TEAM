import { useState, useEffect } from 'react'
import { useApp } from '@/contexts/AppContext'
import { apiClient, UserInfo, UserProgression, UserCredits, CreditTransaction } from '@/services/api'

export default function MyAccountModal() {
  const { isMyAccountModalOpen, closeMyAccount, logout } = useApp()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [progression, setProgression] = useState<UserProgression | null>(null)
  const [credits, setCredits] = useState<UserCredits | null>(null)
  const [transactions, setTransactions] = useState<CreditTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Password change state
  const [showPasswordChange, setShowPasswordChange] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordChangeLoading, setPasswordChangeLoading] = useState(false)
  const [passwordChangeError, setPasswordChangeError] = useState('')
  const [passwordChangeSuccess, setPasswordChangeSuccess] = useState('')

  // Credit management state
  const [showCreditSection, setShowCreditSection] = useState(false)
  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [purchaseAmount, setPurchaseAmount] = useState('100')
  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [purchaseError, setPurchaseError] = useState('')
  const [purchaseSuccess, setPurchaseSuccess] = useState('')

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

      // Load user progression (rank, level, XP)
      try {
        const prog = await apiClient.getUserProgression()
        setProgression(prog)
      } catch (progError) {
        console.error('Failed to load progression:', progError)
        // Don't fail the whole modal if progression fails
      }

      // Load user credits
      try {
        const cred = await apiClient.getUserCredits()
        setCredits(cred)
      } catch (credError) {
        console.error('Failed to load credits:', credError)
      }
    } catch (err) {
      console.error('Failed to load user info:', err)
      setError('사용자 정보를 불러올 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  const loadCreditTransactions = async () => {
    try {
      const txs = await apiClient.getCreditTransactions(undefined, 10)
      setTransactions(txs)
    } catch (err) {
      console.error('Failed to load transactions:', err)
    }
  }

  const handlePurchaseCredits = async () => {
    setPurchaseError('')
    setPurchaseSuccess('')

    const amount = parseInt(purchaseAmount)
    if (isNaN(amount) || amount <= 0) {
      setPurchaseError('올바른 금액을 입력해주세요.')
      return
    }

    try {
      setPurchaseLoading(true)
      await apiClient.purchaseCredits(amount, `크레딧 구매 ${amount}개`)
      setPurchaseSuccess(`${amount}개의 크레딧이 성공적으로 충전되었습니다!`)

      // Reload credits
      const cred = await apiClient.getUserCredits()
      setCredits(cred)

      // Reload transactions if section is open
      if (showCreditSection) {
        await loadCreditTransactions()
      }

      // Close modal after 2 seconds
      setTimeout(() => {
        setShowPurchaseModal(false)
        setPurchaseSuccess('')
        setPurchaseAmount('100')
      }, 2000)
    } catch (err: any) {
      setPurchaseError(err.message || '크레딧 구매에 실패했습니다.')
    } finally {
      setPurchaseLoading(false)
    }
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordChangeError('')
    setPasswordChangeSuccess('')

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordChangeError('모든 필드를 입력해주세요.')
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordChangeError('새 비밀번호가 일치하지 않습니다.')
      return
    }

    if (newPassword.length < 6) {
      setPasswordChangeError('비밀번호는 최소 6자 이상이어야 합니다.')
      return
    }

    if (currentPassword === newPassword) {
      setPasswordChangeError('새 비밀번호는 현재 비밀번호와 달라야 합니다.')
      return
    }

    try {
      setPasswordChangeLoading(true)
      await apiClient.changePassword(currentPassword, newPassword)
      setPasswordChangeSuccess('비밀번호가 성공적으로 변경되었습니다.')

      // Reset form
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')

      // Hide form after 2 seconds
      setTimeout(() => {
        setShowPasswordChange(false)
        setPasswordChangeSuccess('')
      }, 2000)
    } catch (err: any) {
      setPasswordChangeError(err.message || '비밀번호 변경에 실패했습니다.')
    } finally {
      setPasswordChangeLoading(false)
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
                    {((userInfo.display_name || userInfo.username) || 'U').charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-gray-800">내 계정</h2>
                  <p className="text-gray-600">{userInfo.display_name || userInfo.username || '사용자'}</p>
                  {progression && (
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-lg">{progression.rank_icon}</span>
                      <span className="text-sm font-semibold text-purple-600">{progression.rank_name_ko}</span>
                      <span className="text-xs text-gray-500">Lv.{progression.level}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* 계급 및 진행도 정보 */}
              {progression && (
                <div className="mb-8">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">귀살대 계급</h3>
                  <div className="p-4 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg border border-purple-100">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-2xl">{progression.rank_icon}</span>
                        <div>
                          <p className="font-bold text-lg text-gray-800">{progression.rank_name_ko}</p>
                          <p className="text-xs text-gray-600">레벨 {progression.level}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">경험치</p>
                        <p className="font-semibold text-purple-600">{progression.experience_points.toLocaleString()} XP</p>
                      </div>
                    </div>

                    {/* 진행도 바 */}
                    {progression.next_rank_xp && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                          <span>다음 계급까지</span>
                          <span>{(progression.next_rank_xp - progression.experience_points).toLocaleString()} XP</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-purple-500 to-indigo-500 h-2 rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(100, (progression.experience_points / progression.next_rank_xp) * 100)}%`
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* 통계 */}
                    <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-purple-200">
                      <div className="text-center">
                        <p className="text-xs text-gray-600">시나리오</p>
                        <p className="text-sm font-semibold text-gray-800">{progression.scenarios_completed}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-600">대화 수</p>
                        <p className="text-sm font-semibold text-gray-800">{progression.total_messages.toLocaleString()}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-600">세션 수</p>
                        <p className="text-sm font-semibold text-gray-800">{progression.total_sessions}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 크레딧 정보 */}
              {credits && (
                <div className="mb-8">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">크레딧 (버블)</h3>
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="text-sm text-gray-600">보유 크레딧</p>
                        <p className="text-3xl font-bold text-purple-600">{credits.bubble_count.toLocaleString()}</p>
                      </div>
                      <button
                        onClick={() => setShowPurchaseModal(true)}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
                      >
                        💰 충전하기
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-3 border-t border-purple-200">
                      <div>
                        <p className="text-xs text-gray-600">총 구매</p>
                        <p className="text-sm font-semibold text-gray-800">{credits.total_purchased.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600">총 사용</p>
                        <p className="text-sm font-semibold text-gray-800">{credits.total_consumed.toLocaleString()}</p>
                      </div>
                    </div>

                    {!showCreditSection ? (
                      <button
                        onClick={async () => {
                          setShowCreditSection(true)
                          await loadCreditTransactions()
                        }}
                        className="w-full mt-3 p-2 text-sm text-purple-600 hover:bg-purple-100 rounded-lg transition-colors"
                      >
                        📊 거래 내역 보기
                      </button>
                    ) : (
                      <div className="mt-4 pt-3 border-t border-purple-200">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-semibold text-gray-800">최근 거래</h4>
                          <button
                            onClick={() => setShowCreditSection(false)}
                            className="text-xs text-gray-500 hover:text-gray-700"
                          >
                            접기
                          </button>
                        </div>
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                          {transactions.length === 0 ? (
                            <p className="text-sm text-gray-500 text-center py-4">거래 내역이 없습니다</p>
                          ) : (
                            transactions.map((tx) => (
                              <div key={tx.transaction_id} className="bg-white p-3 rounded-lg">
                                <div className="flex items-center justify-between">
                                  <div className="flex-1">
                                    <p className="text-xs text-gray-500">
                                      {new Date(tx.created_at).toLocaleDateString('ko-KR', {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                      })}
                                    </p>
                                    <p className="text-sm font-medium text-gray-800">{tx.description || tx.transaction_type}</p>
                                  </div>
                                  <div className="text-right">
                                    <p className={`text-sm font-bold ${tx.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {tx.amount > 0 ? '+' : ''}{tx.amount.toLocaleString()}
                                    </p>
                                    <p className="text-xs text-gray-500">잔액: {tx.balance_after.toLocaleString()}</p>
                                  </div>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 크레딧 구매 모달 */}
              {showPurchaseModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                  <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-bold text-gray-800">크레딧 충전</h3>
                      <button
                        onClick={() => {
                          setShowPurchaseModal(false)
                          setPurchaseError('')
                          setPurchaseSuccess('')
                        }}
                        className="text-gray-500 hover:text-gray-700"
                      >
                        ✕
                      </button>
                    </div>

                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        충전할 크레딧 수량
                      </label>
                      <input
                        type="number"
                        value={purchaseAmount}
                        onChange={(e) => setPurchaseAmount(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        placeholder="100"
                        min="1"
                      />
                      <div className="flex gap-2 mt-2">
                        {[100, 500, 1000, 5000].map((amount) => (
                          <button
                            key={amount}
                            onClick={() => setPurchaseAmount(amount.toString())}
                            className="flex-1 px-3 py-1 text-sm bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                          >
                            {amount}
                          </button>
                        ))}
                      </div>
                    </div>

                    {purchaseError && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-600">{purchaseError}</p>
                      </div>
                    )}

                    {purchaseSuccess && (
                      <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <p className="text-sm text-green-600">{purchaseSuccess}</p>
                      </div>
                    )}

                    <button
                      onClick={handlePurchaseCredits}
                      disabled={purchaseLoading}
                      className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                    >
                      {purchaseLoading ? '처리 중...' : `${purchaseAmount}개 충전하기`}
                    </button>

                    <p className="text-xs text-gray-500 text-center mt-3">
                      * 테스트 환경입니다. 실제 결제는 진행되지 않습니다.
                    </p>
                  </div>
                </div>
              )}

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
                    <span className="text-gray-800 font-medium">{userInfo.username || '사용자'}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">표시 이름</span>
                    <span className="text-gray-800 font-medium">{userInfo.display_name || userInfo.username || '사용자'}</span>
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

              {/* 비밀번호 변경 섹션 */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">보안 설정</h3>

                {!showPasswordChange ? (
                  <button
                    onClick={() => setShowPasswordChange(true)}
                    className="w-full p-3 bg-purple-50 rounded-lg text-left hover:bg-purple-100 transition-colors"
                  >
                    <span className="text-purple-600 font-medium">🔒 비밀번호 변경</span>
                  </button>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-semibold text-gray-800">비밀번호 변경</h4>
                      <button
                        onClick={() => {
                          setShowPasswordChange(false)
                          setPasswordChangeError('')
                          setPasswordChangeSuccess('')
                          setCurrentPassword('')
                          setNewPassword('')
                          setConfirmPassword('')
                        }}
                        className="text-gray-500 hover:text-gray-700"
                      >
                        ✕
                      </button>
                    </div>

                    <form onSubmit={handlePasswordChange} className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          현재 비밀번호
                        </label>
                        <input
                          type="password"
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                          placeholder="현재 비밀번호를 입력하세요"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          새 비밀번호
                        </label>
                        <input
                          type="password"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                          placeholder="새 비밀번호를 입력하세요 (최소 6자)"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          새 비밀번호 확인
                        </label>
                        <input
                          type="password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                          placeholder="새 비밀번호를 다시 입력하세요"
                        />
                      </div>

                      {passwordChangeError && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-600">{passwordChangeError}</p>
                        </div>
                      )}

                      {passwordChangeSuccess && (
                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                          <p className="text-sm text-green-600">{passwordChangeSuccess}</p>
                        </div>
                      )}

                      <button
                        type="submit"
                        disabled={passwordChangeLoading}
                        className="w-full py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        {passwordChangeLoading ? '변경 중...' : '비밀번호 변경'}
                      </button>
                    </form>
                  </div>
                )}
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
