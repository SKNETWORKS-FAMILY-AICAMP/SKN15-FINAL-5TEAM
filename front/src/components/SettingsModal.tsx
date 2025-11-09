import { useSettings } from '@/hooks/useSettings'
import { useState, useEffect } from 'react'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const {
    settings,
    isLoading,
    error,
    setSoundEnabled,
    setBgmVolume,
    setSfxVolume,
    setAutoSave,
    setLanguage,
    setFontSize,
    setAnimationSpeed
  } = useSettings()

  // 로컬 상태 (슬라이더 실시간 반영용)
  const [localBgmVolume, setLocalBgmVolume] = useState(settings.bgm_volume)
  const [localSfxVolume, setLocalSfxVolume] = useState(settings.sfx_volume)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')

  // settings 변경 시 로컬 상태 동기화
  useEffect(() => {
    setLocalBgmVolume(settings.bgm_volume)
    setLocalSfxVolume(settings.sfx_volume)
  }, [settings.bgm_volume, settings.sfx_volume])

  if (!isOpen) return null

  const handleBgmVolumeChange = async (value: number) => {
    setLocalBgmVolume(value)
  }

  const handleBgmVolumeCommit = async () => {
    try {
      setSaveStatus('saving')
      await setBgmVolume(localBgmVolume)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleSfxVolumeChange = async (value: number) => {
    setLocalSfxVolume(value)
  }

  const handleSfxVolumeCommit = async () => {
    try {
      setSaveStatus('saving')
      await setSfxVolume(localSfxVolume)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleToggleSoundEnabled = async () => {
    try {
      setSaveStatus('saving')
      await setSoundEnabled(!settings.sound_enabled)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleToggleAutoSave = async () => {
    try {
      setSaveStatus('saving')
      await setAutoSave(!settings.auto_save)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleLanguageChange = async (lang: string) => {
    try {
      setSaveStatus('saving')
      await setLanguage(lang)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleFontSizeChange = async (size: 'small' | 'medium' | 'large') => {
    try {
      setSaveStatus('saving')
      await setFontSize(size)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleAnimationSpeedChange = async (speed: 'slow' | 'normal' | 'fast') => {
    try {
      setSaveStatus('saving')
      await setAnimationSpeed(speed)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (err) {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800">설정</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-8 text-gray-500">
            설정을 불러오는 중...
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Save Status */}
        {saveStatus === 'saving' && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
            저장 중...
          </div>
        )}
        {saveStatus === 'saved' && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
            저장되었습니다
          </div>
        )}
        {saveStatus === 'error' && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            저장 실패
          </div>
        )}

        {!isLoading && (
          <div className="space-y-6">
            {/* Sound Settings */}
            <div className="border-b border-gray-200 pb-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-4">사운드 설정</h3>

              {/* Sound ON/OFF */}
              <label className="flex items-center justify-between mb-4 cursor-pointer">
                <span className="text-sm text-gray-700">사운드 활성화</span>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.sound_enabled}
                    onChange={handleToggleSoundEnabled}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                </div>
              </label>

              {/* BGM Volume */}
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm text-gray-700">BGM 볼륨</label>
                  <span className="text-sm font-medium text-purple-600">{localBgmVolume}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={localBgmVolume}
                  onChange={(e) => handleBgmVolumeChange(parseInt(e.target.value))}
                  onMouseUp={handleBgmVolumeCommit}
                  onTouchEnd={handleBgmVolumeCommit}
                  disabled={!settings.sound_enabled}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              {/* SFX Volume */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm text-gray-700">효과음 볼륨</label>
                  <span className="text-sm font-medium text-purple-600">{localSfxVolume}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={localSfxVolume}
                  onChange={(e) => handleSfxVolumeChange(parseInt(e.target.value))}
                  onMouseUp={handleSfxVolumeCommit}
                  onTouchEnd={handleSfxVolumeCommit}
                  disabled={!settings.sound_enabled}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Game Settings */}
            <div className="border-b border-gray-200 pb-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-4">게임 설정</h3>

              {/* Auto Save */}
              <label className="flex items-center justify-between mb-4 cursor-pointer">
                <span className="text-sm text-gray-700">자동 저장</span>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.auto_save}
                    onChange={handleToggleAutoSave}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                </div>
              </label>

              {/* Language */}
              <div className="mb-4">
                <label className="block text-sm text-gray-700 mb-2">언어</label>
                <select
                  value={settings.language}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="ko">한국어</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                </select>
              </div>

              {/* Font Size */}
              <div className="mb-4">
                <label className="block text-sm text-gray-700 mb-2">폰트 크기</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['small', 'medium', 'large'] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => handleFontSizeChange(size)}
                      className={`p-2 text-sm border rounded transition-colors ${
                        settings.font_size === size
                          ? 'bg-purple-600 text-white border-purple-600'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-purple-400'
                      }`}
                    >
                      {size === 'small' ? '작게' : size === 'medium' ? '보통' : '크게'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Animation Speed */}
              <div>
                <label className="block text-sm text-gray-700 mb-2">애니메이션 속도</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['slow', 'normal', 'fast'] as const).map((speed) => (
                    <button
                      key={speed}
                      onClick={() => handleAnimationSpeedChange(speed)}
                      className={`p-2 text-sm border rounded transition-colors ${
                        settings.animation_speed === speed
                          ? 'bg-purple-600 text-white border-purple-600'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-purple-400'
                      }`}
                    >
                      {speed === 'slow' ? '느리게' : speed === 'normal' ? '보통' : '빠르게'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}