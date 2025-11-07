import { useApp, Theme, FontSize, ChatWindowSize } from '@/contexts/AppContext';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { theme, setTheme, fontSize, setFontSize, chatWindowSize, setChatWindowSize } = useApp();

  if (!isOpen) return null;

  const getButtonClass = (isActive: boolean) => {
    return `px-3 py-1 text-sm rounded-md transition-colors ${
      isActive
        ? 'bg-purple-600 text-white'
        : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
    }`;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-80 dark:bg-gray-800">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold dark:text-white">설정</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-6">
          {/* 테마 설정 */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">테마</h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setTheme('light')}
                className={getButtonClass(theme === 'light')}
              >
                라이트
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={getButtonClass(theme === 'dark')}
              >
                다크
              </button>
            </div>
          </div>

          {/* 글씨 크기 설정 */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">글씨 크기</h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setFontSize('sm')}
                className={getButtonClass(fontSize === 'sm')}
              >
                작게
              </button>
              <button
                onClick={() => setFontSize('md')}
                className={getButtonClass(fontSize === 'md')}
              >
                보통
              </button>
              <button
                onClick={() => setFontSize('lg')}
                className={getButtonClass(fontSize === 'lg')}
              >
                크게
              </button>
            </div>
          </div>

          {/* 채팅창 크기 설정 */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">채팅창 크기</h3>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: '콤팩트', value: 'compact' },
                { label: '보통', value: 'cozy' },
                { label: '넓게', value: 'spacious' }
              ].map(option => (
                <button
                  key={option.value}
                  onClick={() => setChatWindowSize(option.value as ChatWindowSize)}
                  className={getButtonClass(chatWindowSize === option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              채팅 영역의 가로폭을 조절해 원하는 레이아웃으로 즐길 수 있어요.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}
