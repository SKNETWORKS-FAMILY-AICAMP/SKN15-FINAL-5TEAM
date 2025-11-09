/**
 * useSoundManager Hook
 *
 * 사용자 설정에 기반한 사운드 관리 훅
 * - useSoundEffects와 설정을 결합
 * - 볼륨 제어
 */

import { useCallback } from 'react'
import { useSoundEffects } from './useSoundEffects'
import { UserSettings } from '@/services/api'

interface UseSoundManagerProps {
  settings: UserSettings
}

export function useSoundManager({ settings }: UseSoundManagerProps) {
  const soundEffects = useSoundEffects()

  /**
   * SFX 볼륨 가져오기 (0-100을 0-1로 변환)
   */
  const getSfxVolume = useCallback((): number => {
    if (!settings.sound_enabled) return 0
    return settings.sfx_volume / 100
  }, [settings.sound_enabled, settings.sfx_volume])

  /**
   * BGM 볼륨 가져오기 (0-100을 0-1로 변환)
   */
  const getBgmVolume = useCallback((): number => {
    if (!settings.sound_enabled) return 0
    return settings.bgm_volume / 100
  }, [settings.sound_enabled, settings.bgm_volume])

  /**
   * 일반 메시지 소리
   */
  const playMessageSound = useCallback(() => {
    if (getSfxVolume() > 0) {
      soundEffects.playMessageSound()
    }
  }, [getSfxVolume, soundEffects])

  /**
   * 시스템 메시지 소리
   */
  const playSystemSound = useCallback(() => {
    if (getSfxVolume() > 0) {
      soundEffects.playSystemSound()
    }
  }, [getSfxVolume, soundEffects])

  /**
   * 경고/알림 소리
   */
  const playAlertSound = useCallback(() => {
    if (getSfxVolume() > 0) {
      soundEffects.playAlertSound()
    }
  }, [getSfxVolume, soundEffects])

  /**
   * 타이핑 시작 소리
   */
  const playTypingStartSound = useCallback(() => {
    if (getSfxVolume() > 0) {
      soundEffects.playTypingStartSound()
    }
  }, [getSfxVolume, soundEffects])

  /**
   * 캐릭터 등장 소리
   */
  const playCharacterSound = useCallback(() => {
    if (getSfxVolume() > 0) {
      soundEffects.playCharacterSound()
    }
  }, [getSfxVolume, soundEffects])

  /**
   * 오디오 언락
   */
  const unlockAudio = useCallback(() => {
    if (settings.sound_enabled) {
      soundEffects.unlockAudio()
    }
  }, [settings.sound_enabled, soundEffects])

  return {
    playMessageSound,
    playSystemSound,
    playAlertSound,
    playTypingStartSound,
    playCharacterSound,
    unlockAudio,
    getSfxVolume,
    getBgmVolume,
    isSoundEnabled: settings.sound_enabled,
    sfxVolume: settings.sfx_volume,
    bgmVolume: settings.bgm_volume
  }
}
