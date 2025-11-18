import { useEffect, useMemo, useRef, useState } from 'react';
import tmiData from '@/data/tmi.json';

type TmiDataMap = Record<string, string[]>;

interface TmiLoadingOverlayProps {
  isVisible: boolean;
  assetBaseUrl?: string;
}

const IMAGE_MAP: Record<string, string> = {
  tanjiro: '탄지로_기본.png',
  nezuko: '네즈코_기본.png',
  zenitsu: '젠이츠_기본.png',
  inosuke: '이노스케_기본.png',
  rengoku: '렌고쿠_기본.png',
  giyu: '기유_기본.png',
  shinobu: '시노부_기본.png',
  muichiro: '무이치로_기본.png',
  mitsuri: '미츠리_기본.png',
  tengen: '텐겐_기본.png',
  obanai: '오바나이_기본.png',
  sanemi: '사네미_기본.png',
  gyomei: '교메이_기본.png'
};

const LONG_WAIT_MS = 10_000;
const FAST_PROGRESS_MS = 2_800;
const FAST_TARGET = 90;
const PROGRESS_CAP = 97;

const characterKeys = Object.keys(IMAGE_MAP);

const getTmiList = (key: string): string[] => {
  const map = tmiData as TmiDataMap;
  if (map[key]?.length) return map[key];
  return map[characterKeys[0]] || [];
};

export default function TmiLoadingOverlay({
  isVisible,
  assetBaseUrl = '/images'
}: TmiLoadingOverlayProps) {
  const [progress, setProgress] = useState(0);
  const [tmi, setTmi] = useState('');
  const [characterKey, setCharacterKey] = useState<string>(characterKeys[0]);
  const [isLongWait, setIsLongWait] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const lastIndexRef = useRef<Record<string, number>>({});
  const lastCharacterRef = useRef<string | null>(null);
  const progressRef = useRef(0);

  useEffect(() => {
    if (isVisible) {
      const filtered = characterKeys.filter((key) => key !== lastCharacterRef.current);
      const pool = filtered.length ? filtered : characterKeys;
      const next = pool[Math.floor(Math.random() * pool.length)];
      lastCharacterRef.current = next;
      setCharacterKey(next);
    }
  }, [isVisible]);

  useEffect(() => {
    if (!isVisible) {
      setProgress(0);
      setIsLongWait(false);
      return;
    }

    const list = getTmiList(characterKey);
    if (list.length) {
      const lastIndex = lastIndexRef.current[characterKey];
      const candidates = list.map((item, idx) => ({ item, idx }));
      const filtered = candidates.filter(({ idx }) => idx !== lastIndex);
      const { item, idx } =
        filtered[Math.floor(Math.random() * filtered.length)] ||
        candidates[Math.floor(Math.random() * candidates.length)];
      setTmi(item);
      lastIndexRef.current[characterKey] = idx;
    } else {
      setTmi('AI가 정보를 정리하는 중입니다...');
    }
  }, [characterKey, isVisible]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      setPrefersReducedMotion(event.matches);
    };

    handleChange(media);

    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handleChange);
      return () => media.removeEventListener('change', handleChange);
    }

    media.addListener(handleChange);
    return () => media.removeListener(handleChange);
  }, []);

  useEffect(() => {
    if (!isVisible) {
      return;
    }

    progressRef.current = 0;
    setProgress(0);
    setIsLongWait(false);

    const start = performance.now();
    let rafId: number | null = null;
    let holdTimer: number | null = null;
    const fastDuration = prefersReducedMotion ? 1_800 : FAST_PROGRESS_MS;

    const tick = (now: number) => {
      const elapsed = now - start;
      const ratio = Math.min(1, elapsed / fastDuration);
      const next = Math.min(FAST_TARGET, Math.round(ratio * FAST_TARGET));
      progressRef.current = next;
      setProgress(next);

      if (next < FAST_TARGET) {
        rafId = requestAnimationFrame(tick);
      } else if (!holdTimer) {
        holdTimer = window.setInterval(() => {
          progressRef.current = Math.min(PROGRESS_CAP, progressRef.current + 0.35);
          setProgress(progressRef.current);
        }, 220);
      }
    };

    rafId = requestAnimationFrame(tick);

    const longWaitTimer = window.setTimeout(() => {
      setIsLongWait(true);
    }, LONG_WAIT_MS);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      if (holdTimer) clearInterval(holdTimer);
      clearTimeout(longWaitTimer);
    };
  }, [isVisible, prefersReducedMotion]);

  if (!isVisible) return null;

  const imageFile = IMAGE_MAP[characterKey] || IMAGE_MAP[characterKeys[0]];
  const imageSrc = `${assetBaseUrl}/overray/${imageFile}`;

  return (
    <div className="fixed inset-0 z-[12000] flex items-center justify-center bg-black/70 backdrop-blur-md px-4 py-6">
      <div className="relative w-full max-w-sm sm:max-w-md md:max-w-lg aspect-[3/4] rounded-3xl overflow-hidden bg-slate-950/80 border border-white/10 shadow-2xl">
        <img
          src={imageSrc}
          alt={`${characterKey} overlay`}
          className={`absolute inset-0 w-full h-full object-cover ${
            prefersReducedMotion ? '' : 'ken-burns-soft'
          }`}
          onError={(e) => {
            (e.target as HTMLImageElement).src = `${assetBaseUrl}/overray/${IMAGE_MAP[characterKeys[0]]}`;
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/35 to-black/85" />

        {isLongWait ? (
          <div className="relative z-10 flex h-full flex-col items-center justify-center gap-3 text-center px-4 text-white">
            <div className="w-12 h-12 border-2 border-purple-200 border-t-transparent rounded-full animate-spin" />
            <p className="text-lg font-semibold">답변을 신중하게 고르는 중입니다...</p>
            <p className="text-sm text-white/70">곧 이어서 대사를 계속할게요.</p>
          </div>
        ) : (
          <>
            <div className="absolute top-4 left-4 z-10 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-[10px] tracking-[0.24em] uppercase text-purple-50">
              Character TMI
            </div>

            <div className="absolute inset-x-0 bottom-0 z-10 p-4 sm:p-6">
              <div className="bg-black/45 backdrop-blur-md rounded-2xl border border-white/10 p-4 sm:p-5 space-y-3">
                <p
                  className={`text-lg sm:text-xl font-semibold leading-snug text-white drop-shadow ${
                    prefersReducedMotion ? '' : 'tmi-text-reveal'
                  }`}
                >
                  {tmi}
                </p>
                <p className="text-xs text-white/75">AI가 대사를 준비하고 있습니다</p>

                <div className="space-y-2">
                  <div className="h-3 rounded-full bg-white/15 overflow-hidden">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r from-purple-300 via-indigo-300 to-pink-300 ${
                        prefersReducedMotion ? '' : 'progress-shimmer'
                      }`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-gray-200/80">
                    <span>응답 준비 중</span>
                    <span>{Math.round(progress)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
