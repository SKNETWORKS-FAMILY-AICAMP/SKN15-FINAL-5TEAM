import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { useApp } from '@/contexts/AppContext'

export default function PasswordResetConfirmPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { openLoginModal } = useApp()

  const [token, setToken] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // Extract token from URL on mount
  useEffect(() => {
    const tokenParam = searchParams.get('token')
    if (!tokenParam) {
      setError('유효하지 않은 재설정 링크입니다.')
    } else {
      setToken(tokenParam)
    }
  }, [searchParams])

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return '비밀번호는 최소 8자 이상이어야 합니다.'
    }
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
      return '비밀번호는 영문과 숫자를 포함해야 합니다.'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate passwords
    const passwordError = validatePassword(newPassword)
    if (passwordError) {
      setError(passwordError)
      return
    }

    if (newPassword !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }

    if (!token) {
      setError('유효하지 않은 재설정 링크입니다.')
      return
    }

    setLoading(true)

    try {
      const result = await apiClient.confirmPasswordReset(token, newPassword)

      if (result.success) {
        setSuccess(true)
        // Redirect to home page after 3 seconds
        setTimeout(() => {
          navigate('/')
          openLoginModal()
        }, 3000)
      } else {
        setError(result.message || '비밀번호 재설정에 실패했습니다.')
      }
    } catch (err: unknown) {
      console.error('Password reset confirm error:', err)
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('비밀번호 재설정 처리 중 오류가 발생했습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  // Show error if no token
  if (!token && error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-6">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">링크 오류</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link
            to="/"
            className="inline-block px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
          >
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  // Success screen
  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="text-6xl mb-6">✅</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">
            비밀번호 변경 완료!
          </h2>
          <p className="text-gray-600 mb-6">
            비밀번호가 성공적으로 변경되었습니다.<br />
            잠시 후 로그인 화면으로 이동합니다.
          </p>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    )
  }

  // Password reset form
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🔑</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            새 비밀번호 설정
          </h2>
          <p className="text-gray-600 text-sm">
            안전한 비밀번호를 입력해주세요
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* New Password Input */}
          <div>
            <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-2">
              새 비밀번호
            </label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="영문, 숫자 포함 8자 이상"
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
          </div>

          {/* Confirm Password Input */}
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
              비밀번호 확인
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="비밀번호를 다시 입력하세요"
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
          </div>

          {/* Password Requirements */}
          <div className="bg-purple-50 rounded-xl p-4 text-sm text-gray-600">
            <p className="font-semibold text-purple-800 mb-2">비밀번호 요구사항:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>최소 8자 이상</li>
              <li>영문자 포함</li>
              <li>숫자 포함</li>
            </ul>
          </div>

          {/* Error Message */}
          {error && (
            <div className="text-red-500 text-sm text-center bg-red-50 p-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
          >
            {loading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-5 h-5 border-t-2 border-white rounded-full animate-spin"></div>
                <span>처리 중...</span>
              </div>
            ) : (
              '비밀번호 변경'
            )}
          </button>

          {/* Back to Home Link */}
          <div className="text-center pt-4">
            <Link
              to="/"
              className="text-sm text-purple-600 hover:text-purple-700 hover:underline"
            >
              홈으로 돌아가기
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
