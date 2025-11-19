
import { useState } from 'react';
import { useApp } from '@/contexts/AppContext';
import { setTokens, setUserData, TokenData, UserData } from '@/utils/authUtils';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type AuthMode = 'login' | 'register';

export default function LoginModal() {
  const { isLoginModalOpen, closeLoginModal, login, openPasswordResetModal } = useApp();
  const [mode, setMode] = useState<AuthMode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isLoginModalOpen) return null;

  const handleSocialLogin = async (provider: string) => {
    console.log(`${provider} 로그인 시도`);

    try {
      let authUrl: string;

      if (provider === 'Google') {
        const response = await fetch(`${API_BASE_URL}/api/auth/google`);
        const data = await response.json();
        authUrl = data.auth_url;
      } else if (provider === 'Kakao') {
        const response = await fetch(`${API_BASE_URL}/api/auth/kakao`);
        const data = await response.json();
        authUrl = data.auth_url;
      } else {
        console.error('지원하지 않는 소셜 로그인 제공자:', provider);
        return;
      }

      window.location.href = authUrl;
    } catch (err) {
      console.error(`${provider} 로그인 오류:`, err);
      setError(`${provider} 로그인에 실패했습니다. 나중에 다시 시도해주세요.`);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        // 토큰 저장
        const tokens: TokenData = {
          access_token: data.access_token,
          refresh_token: data.access_token, // refresh_token이 없으면 access_token 사용
          token_type: data.token_type || 'bearer',
        };
        setTokens(tokens);

        // 사용자 데이터 저장
        const userData: UserData = {
          user_id: data.user_id,
          username: data.username,
          display_name: data.display_name || data.username, // display_name이 없으면 username 사용
          email: `${data.username}@kimechat.com`,
        };
        setUserData(userData);

        login(`${username}@kimechat.com`);
        closeLoginModal();
        setError('');
        setUsername('');
        setPassword('');
      } else {
        setError(data.detail || data.message || '사용자명 또는 비밀번호가 올바르지 않습니다.');
      }
    } catch (err) {
      console.error('로그인 오류:', err);
      setError('서버 연결에 실패했습니다. 나중에 다시 시도해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // 유효성 검사
    if (password !== passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    // Password validation - must match PasswordResetConfirmPage requirements
    if (password.length < 8) {
      setError('비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
      setError('비밀번호는 영문과 숫자를 포함해야 합니다.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
          email: email || undefined,
          display_name: displayName || username,
        }),
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        // 회원가입 성공 시 자동 로그인
        const tokens: TokenData = {
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          token_type: data.token_type || 'bearer',
        };
        setTokens(tokens);

        const userData: UserData = {
          user_id: data.user_id,
          username: data.username,
          display_name: data.display_name,
          email: data.email || `${username}@kimechat.com`,
        };
        setUserData(userData);

        login(email || `${username}@kimechat.com`);
        closeLoginModal();

        // 폼 초기화
        setUsername('');
        setPassword('');
        setPasswordConfirm('');
        setEmail('');
        setDisplayName('');
        setError('');
      } else {
        setError(data.detail || data.message || '회원가입 중 오류가 발생했습니다.');
      }
    } catch (err) {
      console.error('회원가입 오류:', err);
      setError('서버 연결에 실패했습니다. 나중에 다시 시도해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode);
    setError('');
    setUsername('');
    setPassword('');
    setPasswordConfirm('');
    setEmail('');
    setDisplayName('');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      {/* Browser-style window */}
      <div className="w-[520px] max-w-[90vw] bg-white rounded-lg shadow-2xl overflow-hidden" style={{ backgroundColor: 'rgb(254,247,255)' }}>

        {/* Chrome browser header */}
        <div className="flex items-center px-4 py-2 bg-gray-100 border-b border-gray-200">
          {/* Traffic lights */}
          <div className="flex space-x-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          </div>

          {/* Navigation buttons */}
          <div className="flex items-center ml-4 space-x-2">
            <button className="p-1 text-gray-400">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M11 2L5 8l6 6"/>
              </svg>
            </button>
            <button className="p-1 text-gray-400">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M5 2l6 6-6 6"/>
              </svg>
            </button>
            <button className="p-1 text-gray-400">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 2v12M2 8h12"/>
              </svg>
            </button>
          </div>

          {/* Address bar */}
          <div className="flex-1 mx-4">
            <div className="bg-white rounded px-3 py-1 text-sm text-gray-600 border">
              🔒 www.kimechat.com/{mode}
            </div>
          </div>

          {/* Browser menu */}
          <button className="p-1 text-gray-400">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <circle cx="8" cy="3" r="1"/>
              <circle cx="8" cy="8" r="1"/>
              <circle cx="8" cy="13" r="1"/>
            </svg>
          </button>
        </div>

        {/* Main content area */}
        <div className="p-8" style={{ backgroundColor: 'rgb(254,247,255)' }}>
          {/* Close button */}
          <div className="flex justify-end mb-4">
            <button
              onClick={closeLoginModal}
              className="text-gray-400 hover:text-gray-600 text-xl"
            >
              ×
            </button>
          </div>

          {/* Mode Toggle */}
          <div className="flex mb-6 bg-gray-200 rounded-lg p-1">
            <button
              onClick={() => switchMode('login')}
              className={`flex-1 py-2 rounded-md transition-all ${
                mode === 'login'
                  ? 'bg-white shadow text-purple-600 font-semibold'
                  : 'text-gray-600'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => switchMode('register')}
              className={`flex-1 py-2 rounded-md transition-all ${
                mode === 'register'
                  ? 'bg-white shadow text-purple-600 font-semibold'
                  : 'text-gray-600'
              }`}
            >
              회원가입
            </button>
          </div>

          {mode === 'login' ? (
            <>
              {/* Login Section */}
              <div className="space-y-4">
                <h2 className="text-xl font-semibold text-center mb-6" style={{ color: 'rgb(121,116,126)' }}>
                  로그인 방법을 선택하세요
                </h2>

                {/* Social login buttons */}
                <div className="space-y-3">
                  {/* Kakao */}
                  <button
                    onClick={() => handleSocialLogin('Kakao')}
                    className="w-full flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-6 h-6 bg-yellow-400 rounded"></div>
                      <span>카카오</span>
                    </div>
                    <span className="text-gray-400 text-sm">0</span>
                  </button>

                  {/* Google */}
                  <button
                    onClick={() => handleSocialLogin('Google')}
                    className="w-full flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-6 h-6 bg-gradient-to-r from-red-500 to-yellow-500 rounded"></div>
                      <span>구글</span>
                    </div>
                    <span className="text-gray-400 text-sm">0</span>
                  </button>
                </div>

                {/* Email login form */}
                <form onSubmit={handleLogin} className="mt-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      귀살대 이름
                    </label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="tanjiro, zenitsu, inosuke..."
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      비밀번호
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="123"
                      required
                    />
                  </div>

                  {error && (
                    <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <div className="flex items-center justify-center space-x-2">
                        <div className="w-5 h-5 border-t-2 border-white rounded-full animate-spin"></div>
                        <span>로그인 중...</span>
                      </div>
                    ) : (
                      '로그인'
                    )}
                  </button>
                </form>

                {/* Forgot Password Link */}
                <div className="mt-4 text-center">
                  <button
                    onClick={() => {
                      closeLoginModal()
                      openPasswordResetModal()
                    }}
                    className="text-sm text-purple-600 hover:text-purple-700 hover:underline"
                  >
                    비밀번호를 잊으셨나요?
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Register Section */}
              <div className="space-y-4">
                <h2 className="text-xl font-semibold text-center mb-6" style={{ color: 'rgb(121,116,126)' }}>
                  새 계정 만들기
                </h2>

                <form onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      사용자명 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="예: muichiro, shinobu..."
                      required
                      minLength={3}
                    />
                    <p className="text-xs text-gray-500 mt-1">3자 이상, 영문/숫자 가능</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      비밀번호 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="비밀번호 입력"
                      required
                      minLength={3}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      비밀번호 확인 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="비밀번호 재입력"
                      required
                      minLength={3}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      이메일 (선택)
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="example@email.com"
                    />
                    <p className="text-xs text-gray-500 mt-1">비밀번호 찾기에 사용됩니다</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1" style={{ color: 'rgb(121,116,126)' }}>
                      표시 이름 (선택)
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="화면에 표시될 이름"
                    />
                    <p className="text-xs text-gray-500 mt-1">미입력 시 사용자명이 표시됩니다</p>
                  </div>

                  {error && (
                    <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-semibold"
                  >
                    {isLoading ? (
                      <div className="flex items-center justify-center space-x-2">
                        <div className="w-5 h-5 border-t-2 border-white rounded-full animate-spin"></div>
                        <span>가입 중...</span>
                      </div>
                    ) : (
                      '회원가입'
                    )}
                  </button>
                </form>

                <div className="mt-4 text-center text-sm text-gray-600">
                  <p>회원가입 시 자동으로 로그인됩니다</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
