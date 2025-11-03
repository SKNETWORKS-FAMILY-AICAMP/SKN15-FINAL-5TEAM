import { useState } from 'react'
import { apiClient } from '@/services/api'

interface PasswordResetModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function PasswordResetModal({ isOpen, onClose }: PasswordResetModalProps) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await apiClient.requestPasswordReset(email)

      if (result.success) {
        setSuccess(true)
        setEmail('')
      } else {
        setError(result.message || '비밀번호 재설정 요청에 실패했습니다.')
      }
    } catch (err) {
      console.error('Password reset error:', err)
      setError('서버 연결에 실패했습니다. 나중에 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setEmail('')
    setError('')
    setSuccess(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-2xl w-[480px] shadow-2xl relative overflow-hidden">
        {/* 브라우저 스타일 헤더 */}
        <div className="h-12 bg-gray-100 border-b border-gray-200 flex items-center px-4">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="bg-white rounded px-3 py-1 text-sm text-gray-600 border">
              https://kimechat.com/reset-password
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-8">
          {success ? (
            // 성공 화면
            <div className="text-center">
              <div className="text-6xl mb-6">📧</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-3">이메일을 확인하세요!</h2>
              <p className="text-gray-600 mb-6">
                비밀번호 재설정 링크가 이메일로 전송되었습니다.<br />
                이메일을 확인하고 링크를 클릭하여 비밀번호를 재설정하세요.
              </p>
              <p className="text-sm text-gray-500 mb-6">
                이메일이 도착하지 않았다면 스팸 폴더를 확인해주세요.
              </p>
              <button
                onClick={handleClose}
                className="w-full px-4 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors"
              >
                확인
              </button>
            </div>
          ) : (
            // 입력 화면
            <>
              <div className="text-center mb-6">
                <div className="text-5xl mb-4">🔑</div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">비밀번호 찾기</h2>
                <p className="text-gray-600 text-sm">
                  가입 시 사용한 이메일 주소를 입력하세요.<br />
                  비밀번호 재설정 링크를 보내드립니다.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    이메일 주소
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="example@email.com"
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    disabled={loading}
                  />
                </div>

                {error && (
                  <div className="text-red-500 text-sm text-center bg-red-50 p-3 rounded-lg">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full px-4 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center justify-center">
                      <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                      전송 중...
                    </span>
                  ) : (
                    '재설정 링크 보내기'
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleClose}
                  className="w-full px-4 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition-colors"
                >
                  취소
                </button>
              </form>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <p className="text-xs text-gray-500 text-center">
                  계정이 없으신가요?{' '}
                  <button
                    onClick={handleClose}
                    className="text-purple-600 hover:text-purple-700 font-semibold"
                  >
                    회원가입하기
                  </button>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
