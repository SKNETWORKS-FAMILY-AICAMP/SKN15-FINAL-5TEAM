import { useState, useCallback, useMemo, useEffect } from 'react';
import { normalizeScenarioId } from '@/utils/scenario';
import {
  BackgroundImage,
  getBackgroundById,
  getBackgroundImagePath,
  getScenarioBackgrounds,
  getDefaultBackground
} from '@/config/backgroundImages';

interface BackgroundState {
  id: string;
  index: number;
  name: string;
  description: string;
  url: string;
}

const buildBackgroundState = (scenarioId: string, image?: BackgroundImage | null): BackgroundState | null => {
  if (!image) return null;

  return {
    id: image.id,
    index: Number(image.index),
    name: image.name,
    description: image.description,
    url: getBackgroundImagePath(scenarioId, image.fileName)
  };
};

export function useBackgroundImage(scenarioId: string) {
  const normalizedScenarioId = normalizeScenarioId(scenarioId);
  // backgroundImages.ts 에서는 snake_case ID를 사용하므로 변환
  const configScenarioId = useMemo(() => normalizedScenarioId.replace(/-/g, '_'), [normalizedScenarioId]);

  const scenarioConfig = useMemo(
    () => getScenarioBackgrounds(configScenarioId),
    [configScenarioId]
  );
  const scenarioBackgrounds = scenarioConfig?.backgrounds ?? [];

  const defaultBackgroundState = useMemo(() => {
    const defaultImage = getDefaultBackground(configScenarioId) ?? scenarioBackgrounds[0];
    return buildBackgroundState(configScenarioId, defaultImage) ?? {
      id: 'default',
      index: 0,
      name: 'Default Background',
      description: '',
      url: ''
    };
  }, [configScenarioId, scenarioBackgrounds]);

  const [currentBackground, setCurrentBackground] = useState<BackgroundState>(defaultBackgroundState);

  useEffect(() => {
    setCurrentBackground(defaultBackgroundState);
  }, [defaultBackgroundState]);

  const setBackgroundById = useCallback(
    (id: string): boolean => {
      const image = getBackgroundById(configScenarioId, id);
      if (!image) {
        console.warn(`[useBackgroundImage] Unknown background id: ${id}`);
        return false;
      }
      const state = buildBackgroundState(configScenarioId, image);
      if (state) {
        setCurrentBackground(state);
        return true;
      }
      return false;
    },
    [configScenarioId]
  );

  const setBackgroundByIndex = useCallback(
    (index: number | string): boolean => {
      const idx = String(index);
      const image = scenarioBackgrounds.find(bg => String(bg.index) === idx);
      if (!image) {
        console.warn(`[useBackgroundImage] Unknown background index: ${index}`);
        return false;
      }
      const state = buildBackgroundState(configScenarioId, image);
      if (state) {
        setCurrentBackground(state);
        return true;
      }
      return false;
    },
    [configScenarioId, scenarioBackgrounds]
  );

  const setBackgroundByFileName = useCallback(
    (fileName: string): boolean => {
      const image = scenarioBackgrounds.find(bg => bg.fileName === fileName);
      if (!image) {
        console.warn(`[useBackgroundImage] Unknown background file name: ${fileName}`);
        return false;
      }
      const state = buildBackgroundState(configScenarioId, image);
      if (state) {
        setCurrentBackground(state);
        return true;
      }
      return false;
    },
    [configScenarioId, scenarioBackgrounds]
  );

  const preloadImages = useCallback(() => {
    scenarioBackgrounds.forEach(bg => {
      const img = new Image();
      img.src = getBackgroundImagePath(configScenarioId, bg.fileName);
    });
  }, [configScenarioId, scenarioBackgrounds]);

  return {
    currentBackground,
    backgroundImageUrl: currentBackground?.url || '',
    setBackgroundById,
    setBackgroundByIndex,
    setBackgroundByFileName,
    preloadImages,
    availableBackgrounds: scenarioBackgrounds
  };
}
