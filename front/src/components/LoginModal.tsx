
import { useState } from 'react';
import { useApp } from '@/contexts/AppContext';

export default function LoginModal() {
  const { isLoginModalOpen, closeLoginModal, login } = useApp();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  if (!isLoginModalOpen) return null;

  const handleSocialLogin = (provider: string) => {
    console.log(`${provider} 로그인 시도`);
    login('user@example.com');
    closeLoginModal();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // 간단한 로그인 검증
    const validAccounts = [
      { username: 'tanjiro', password: '123' },
      { username: 'zenitsu', password: '123' },
      { username: 'inosuke', password: '123' },
      { username: 'giyu', password: '123' },
      { username: 'rengoku', password: '123' },
      { username: 'tengen', password: '123' }
    ];

    const account = validAccounts.find(acc => acc.username === username && acc.password === password);

    if (account) {
      login(`${username}@kimechat.com`);
      closeLoginModal();
      setError('');
      setUsername('');
      setPassword('');
    } else {
      setError('사용자명 또는 비밀번호가 올바르지 않습니다.');
    }
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
              🔒 www.kimechat.com/login
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

          {/* Login options */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-center mb-6" style={{ color: 'rgb(121,116,126)' }}>
              로그인 방법을 선택하세요
            </h2>

            {/* Social login buttons */}
            <div className="space-y-3">
              {/* Kakao - disabled */}
              <div className="flex items-center justify-between p-3 bg-gray-100 rounded-lg opacity-50">
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-yellow-400 rounded"></div>
                  <span className="text-gray-500">카카오</span>
                </div>
                <span className="text-red-500 text-sm">삭제</span>
              </div>

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

              {/* Email */}
              <button
                onClick={() => {/* Show email form */}}
                className="w-full flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-blue-500 rounded"></div>
                  <span>이메일(자체 db)</span>
                </div>
                <span className="text-gray-400 text-sm">0</span>
              </button>
            </div>

            {/* Email login form */}
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
                className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                로그인
              </button>
            </form>

            {/* Account info */}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="text-xs text-gray-500 space-y-1">
                <p className="font-semibold text-center mb-2">📋 사용 가능한 계정:</p>
                <div className="grid grid-cols-2 gap-1 text-center">
                  <div>tanjiro / 123</div>
                  <div>zenitsu / 123</div>
                  <div>inosuke / 123</div>
                  <div>giyu / 123</div>
                  <div>rengoku / 123</div>
                  <div>tengen / 123</div>
                </div>
                <p className="text-center text-xs mt-2">모든 계정의 비밀번호는 123입니다! 🗡️</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}