/**
 * useSettings Hook
 *
 * 사용자 설정을 관리하는 훅입니다.
 * - localStorage에 캐싱
 * - 백엔드와 동기화
 * - 설정 변경 시 즉시 저장
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient, UserSettings, UserSettingsUpdate } from '@/services/api'
import { isAuthenticated } from '@/utils/authUtils'

const SETTINGS_STORAGE_KEY = 'kime_user_settings'
const SETTINGS_CACHE_DURATION = 1000 * 60 * 60 // 1 hour

interface SettingsCache {
  settings: UserSettings
  timestamp: number
}

// 기본 설정값
const DEFAULT_SETTINGS: UserSettings = {
  sound_enabled: true,
  bgm_volume: 70,
  sfx_volume: 80,
  auto_save: true,
  language: 'ko',
  font_size: 'medium',
  animation_speed: 'normal'
}

export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const isInitializedRef = useRef(false)

  /**
   * 로컬 스토리지에서 설정 로드
   */
  const loadFromLocalStorage = useCallback((): UserSettings | null => {
    try {
      const cached = localStorage.getItem(SETTINGS_STORAGE_KEY)
      if (!cached) return null

      const parsed: SettingsCache = JSON.parse(cached)
      const now = Date.now()

      // 캐시가 유효한지 확인
      if (now - parsed.timestamp < SETTINGS_CACHE_DURATION) {
        return parsed.settings
      }

      // 캐시 만료됨
      return null
    } catch (err) {
      console.error('Error loading settings from localStorage:', err)
      return null
    }
  }, [])

  /**
   * 로컬 스토리지에 설정 저장
   */
  const saveToLocalStorage = useCallback((settings: UserSettings) => {
    try {
      const cache: SettingsCache = {
        settings,
        timestamp: Date.now()
      }
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(cache))
    } catch (err) {
      console.error('Error saving settings to localStorage:', err)
    }
  }, [])

  /**
   * 백엔드에서 설정 로드
   */
  const loadFromBackend = useCallback(async () => {
    // 로그인하지 않은 경우 백엔드 호출 건너뛰기
    if (!isAuthenticated()) {
      return null
    }

    try {
      const backendSettings = await apiClient.getUserSettings()
      setSettings(backendSettings)
      saveToLocalStorage(backendSettings)
      setError(null)
      return backendSettings
    } catch (err: any) {
      console.error('Error loading settings from backend:', err)
      setError(err.message || '설정을 불러오는데 실패했습니다')
      throw err
    }
  }, [saveToLocalStorage])

  /**
   * 초기 로드
   */
  useEffect(() => {
    if (isInitializedRef.current) return
    isInitializedRef.current = true

    const initSettings = async () => {
      setIsLoading(true)

      // 1. 로컬 스토리지에서 먼저 로드 (빠른 초기 렌더링)
      const cachedSettings = loadFromLocalStorage()
      if (cachedSettings) {
        setSettings(cachedSettings)
      }

      // 2. 백엔드에서 최신 설정 가져오기
      try {
        await loadFromBackend()
      } catch (err) {
        // 백엔드 로드 실패 시 캐시된 값 사용
        if (!cachedSettings) {
          // 캐시도 없으면 기본값 사용
          setSettings(DEFAULT_SETTINGS)
        }
      } finally {
        setIsLoading(false)
      }
    }

    initSettings()
  }, [loadFromLocalStorage, loadFromBackend])

  /**
   * 설정 업데이트 (로컬 + 백엔드)
   */
  const updateSettings = useCallback(async (updates: UserSettingsUpdate) => {
    try {
      // Optimistic update
      const newSettings = { ...settings, ...updates }
      setSettings(newSettings)
      saveToLocalStorage(newSettings)

      // 로그인한 경우에만 백엔드 동기화
      if (isAuthenticated()) {
        await apiClient.updateUserSettings(updates)
      }
      setError(null)
    } catch (err: any) {
      console.error('Error updating settings:', err)
      setError(err.message || '설정을 저장하는데 실패했습니다')

      // Rollback on error
      const cachedSettings = loadFromLocalStorage()
      if (cachedSettings) {
        setSettings(cachedSettings)
      }

      throw err
    }
  }, [settings, saveToLocalStorage, loadFromLocalStorage])

  /**
   * 특정 설정 값 업데이트 (편의 함수)
   */
  const setSoundEnabled = useCallback((enabled: boolean) => {
    return updateSettings({ sound_enabled: enabled })
  }, [updateSettings])

  const setBgmVolume = useCallback((volume: number) => {
    const clampedVolume = Math.max(0, Math.min(100, volume))
    return updateSettings({ bgm_volume: clampedVolume })
  }, [updateSettings])

  const setSfxVolume = useCallback((volume: number) => {
    const clampedVolume = Math.max(0, Math.min(100, volume))
    return updateSettings({ sfx_volume: clampedVolume })
  }, [updateSettings])

  const setAutoSave = useCallback((enabled: boolean) => {
    return updateSettings({ auto_save: enabled })
  }, [updateSettings])

  const setLanguage = useCallback((language: string) => {
    return updateSettings({ language })
  }, [updateSettings])

  const setFontSize = useCallback((size: 'small' | 'medium' | 'large') => {
    return updateSettings({ font_size: size })
  }, [updateSettings])

  const setAnimationSpeed = useCallback((speed: 'slow' | 'normal' | 'fast') => {
    return updateSettings({ animation_speed: speed })
  }, [updateSettings])

  /**
   * 설정 새로고침 (백엔드에서 다시 로드)
   */
  const refreshSettings = useCallback(async () => {
    // 로그인하지 않은 경우 새로고침 건너뛰기
    if (!isAuthenticated()) {
      return
    }

    setIsLoading(true)
    try {
      await loadFromBackend()
    } finally {
      setIsLoading(false)
    }
  }, [loadFromBackend])

  return {
    // 상태
    settings,
    isLoading,
    error,

    // 일반 업데이트
    updateSettings,
    refreshSettings,

    // 개별 설정 업데이트 (편의 함수)
    setSoundEnabled,
    setBgmVolume,
    setSfxVolume,
    setAutoSave,
    setLanguage,
    setFontSize,
    setAnimationSpeed
  }
}
