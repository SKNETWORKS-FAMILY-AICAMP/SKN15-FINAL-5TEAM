
interface AdvancedSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AdvancedSettingsModal({ isOpen, onClose }: AdvancedSettingsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">고급 설정</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">AI 응답 설정</h3>
            <label className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">긴 응답 허용</span>
            </label>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">응답 속도</h3>
            <select className="w-full p-2 border rounded">
              <option>빠름</option>
              <option>보통</option>
              <option>느림</option>
            </select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">캐릭터 설정</h3>
            <label className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">캐릭터 일관성 유지</span>
            </label>
          </div>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            취소
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            적용
          </button>
        </div>
      </div>
    </div>
  );
}