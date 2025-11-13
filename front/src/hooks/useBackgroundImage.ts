import { useState, useCallback } from 'react';
import { normalizeScenarioId } from '@/utils/scenario';

interface BackgroundImage {
  index: string;
  fileName: string;
  url: string;
}

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const SCENARIO_BACKGROUNDS: Record<string, BackgroundImage[]> = {
  'mugen-train': [
    { index: '0', fileName: 'mugen_train_bg1.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg1.jpg` },
    { index: '1', fileName: 'mugen_train_bg2.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg2.jpg` },
    { index: '2', fileName: 'mugen_train_bg3.jpg', url: `${CDN_URL}/scenarios/mugen_train/mugen_train_bg3.jpg` },
  ],
};

export function useBackgroundImage(scenarioId: string) {
  const normalizedScenarioId = normalizeScenarioId(scenarioId);
  const backgrounds = SCENARIO_BACKGROUNDS[normalizedScenarioId] || [];
  const [currentBackground, setCurrentBackground] = useState<BackgroundImage>(
    backgrounds[0] || { index: '0', fileName: '', url: '' }
  );

  const setBackgroundById = useCallback((id: string) => {
    const bg = backgrounds.find(b => b.index === id);
    if (bg) {
      setCurrentBackground(bg);
    }
  }, [backgrounds]);

  const setBackgroundByIndex = useCallback((index: number) => {
    if (backgrounds[index]) {
      setCurrentBackground(backgrounds[index]);
    }
  }, [backgrounds]);

  const preloadImages = useCallback(() => {
    backgrounds.forEach(bg => {
      const img = new Image();
      img.src = bg.url;
    });
  }, [backgrounds]);

  return {
    currentBackground,
    backgroundImageUrl: currentBackground.url,
    setBackgroundById,
    setBackgroundByIndex,
    preloadImages,
  };
}
