import { useCallback, useRef } from 'react';

/**
 * 소리 효과를 관리하는 React Hook
 * Web Audio API를 사용하여 부드럽고 몰입감 있는 소리 효과를 제공
 */
export function useSoundEffects() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const isAudioUnlockedRef = useRef(false);
  const unlockPromiseRef = useRef<Promise<void> | null>(null);

  // AudioContext 초기화 및 unlock (사용자 인터랙션 필요)
  const unlockAudio = useCallback(async () => {
    // 이미 unlock되었으면 즉시 반환
    if (isAudioUnlockedRef.current) return;

    // unlock 진행 중이면 해당 Promise 반환 (중복 실행 방지)
    if (unlockPromiseRef.current) {
      return unlockPromiseRef.current;
    }

    // 새로운 unlock Promise 생성
    unlockPromiseRef.current = (async () => {
      try {
        if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        }

        const context = audioContextRef.current;

        // AudioContext가 suspended 상태면 resume
        if (context.state === 'suspended') {
          await context.resume();
        }

        // 무음 재생으로 브라우저 정책 우회
        const buffer = context.createBuffer(1, 1, 22050);
        const source = context.createBufferSource();
        source.buffer = buffer;
        source.connect(context.destination);
        source.start(0);

        // 약간의 지연을 줘서 AudioContext가 완전히 활성화되도록 함
        await new Promise(resolve => setTimeout(resolve, 50));

        isAudioUnlockedRef.current = true;
        console.log('🔊 Audio unlocked successfully');
      } catch (error) {
        console.warn('Failed to unlock audio:', error);
      } finally {
        unlockPromiseRef.current = null;
      }
    })();

    return unlockPromiseRef.current;
  }, []);

  // 기본 톤 생성 함수
  const playTone = useCallback(async (frequency: number, duration: number, volume: number = 0.1) => {
    try {
      // 오디오가 unlock되지 않았으면 먼저 unlock
      if (!isAudioUnlockedRef.current) {
        await unlockAudio();
      }

      if (!audioContextRef.current || !isAudioUnlockedRef.current) {
        console.warn('Audio context not available');
        return;
      }

      const audioContext = audioContextRef.current;

      // AudioContext가 suspended 상태면 resume
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      // Oscillator (톤 생성기)
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      // 사인파로 부드러운 소리 생성
      oscillator.type = 'sine';
      oscillator.frequency.value = frequency;

      // 볼륨 설정 (페이드 인/아웃 효과)
      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(volume, audioContext.currentTime + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

      // 재생
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + duration);
    } catch (error) {
      console.warn('Sound effect failed:', error);
    }
  }, [unlockAudio]);

  // 부드러운 "핑" 소리 - 일반 메시지용
  const playMessageSound = useCallback(() => {
    playTone(800, 0.15, 0.08); // 800Hz, 150ms, 낮은 볼륨
  }, [playTone]);

  // 시스템 메시지 소리 - 조금 더 낮은 톤
  const playSystemSound = useCallback(() => {
    playTone(600, 0.2, 0.1); // 600Hz, 200ms
  }, [playTone]);

  // 경고/알림 소리 - 2개의 톤 조합
  const playAlertSound = useCallback(() => {
    playTone(900, 0.1, 0.09);
    setTimeout(() => playTone(700, 0.15, 0.09), 100);
  }, [playTone]);

  // 타이핑 시작 소리 - 매우 부드러운 클릭
  const playTypingStartSound = useCallback(() => {
    playTone(1200, 0.05, 0.05); // 짧고 높은 톤, 매우 낮은 볼륨
  }, [playTone]);

  // 캐릭터 등장 소리 - 좀 더 극적인 효과
  const playCharacterSound = useCallback(() => {
    playTone(400, 0.1, 0.12);
    setTimeout(() => playTone(600, 0.15, 0.1), 80);
    setTimeout(() => playTone(800, 0.2, 0.08), 150);
  }, [playTone]);

  return {
    playMessageSound,
    playSystemSound,
    playAlertSound,
    playTypingStartSound,
    playCharacterSound,
    unlockAudio  // 외부에서 수동으로 unlock 가능
  };
}
