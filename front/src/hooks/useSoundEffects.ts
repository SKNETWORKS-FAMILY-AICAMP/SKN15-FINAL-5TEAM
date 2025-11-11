import { useCallback, useRef, useEffect } from 'react';

const SOUND_URLS = {
  message: '/sounds/message.mp3',
  system: '/sounds/system.mp3',
  typingStart: '/sounds/typing.mp3',
};

export function useSoundEffects() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const isUnlockedRef = useRef(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && 'AudioContext' in window) {
      audioContextRef.current = new AudioContext();
    }
  }, []);

  const unlockAudio = useCallback(() => {
    if (!isUnlockedRef.current && audioContextRef.current) {
      audioContextRef.current.resume();
      isUnlockedRef.current = true;
    }
  }, []);

  const playSound = useCallback((soundUrl: string) => {
    try {
      const audio = new Audio(soundUrl);
      audio.volume = 0.3;
      audio.play().catch(err => {
        console.warn('Failed to play sound:', err);
      });
    } catch (err) {
      console.warn('Sound playback error:', err);
    }
  }, []);

  const playMessageSound = useCallback(() => {
    playSound(SOUND_URLS.message);
  }, [playSound]);

  const playSystemSound = useCallback(() => {
    playSound(SOUND_URLS.system);
  }, [playSound]);

  const playTypingStartSound = useCallback(() => {
    playSound(SOUND_URLS.typingStart);
  }, [playSound]);

  return {
    playMessageSound,
    playSystemSound,
    playTypingStartSound,
    unlockAudio,
  };
}
