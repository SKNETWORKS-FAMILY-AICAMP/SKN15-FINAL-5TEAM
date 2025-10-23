import { useState, useEffect, useCallback } from 'react';
import {
  BackgroundImage,
  getScenarioBackgrounds,
  getBackgroundById,
  getBackgroundImagePath,
  getBackgroundsByTag,
  getDefaultBackground
} from '../config/backgroundImages';

interface UseBackgroundImageReturn {
  currentBackground: BackgroundImage | undefined;
  backgroundImageUrl: string;
  setBackgroundById: (backgroundId: string) => void;
  setBackgroundByIndex: (index: number) => void;
  setBackgroundByTag: (tag: string, index?: number) => void;
  resetToDefault: () => void;
  preloadImages: () => void;
}

/**
 * 배경 이미지를 관리하는 React Hook
 *
 * @param scenarioId - 시나리오 ID (예: 'mugen_train')
 * @param initialBackgroundId - 초기 배경 이미지 ID (선택적, 미지정시 기본 배경 사용)
 */
export function useBackgroundImage(
  scenarioId: string,
  initialBackgroundId?: string
): UseBackgroundImageReturn {
  const [currentBackground, setCurrentBackground] = useState<BackgroundImage | undefined>();

  // 초기 배경 이미지 설정
  useEffect(() => {
    const scenario = getScenarioBackgrounds(scenarioId);
    if (!scenario) {
      console.warn(`Scenario not found: ${scenarioId}`);
      return;
    }

    // initialBackgroundId가 명시적으로 제공된 경우에만 설정
    // 제공되지 않으면 undefined로 두어 CSS fallback이 작동하도록 함
    if (initialBackgroundId) {
      const initialBg = getBackgroundById(scenarioId, initialBackgroundId);
      setCurrentBackground(initialBg);
    }
  }, [scenarioId, initialBackgroundId]);

  // 현재 배경 이미지 URL
  const backgroundImageUrl = currentBackground
    ? getBackgroundImagePath(scenarioId, currentBackground.fileName)
    : '';

  // ID로 배경 이미지 설정
  const setBackgroundById = useCallback(
    (backgroundId: string) => {
      const bg = getBackgroundById(scenarioId, backgroundId);
      if (bg) {
        setCurrentBackground(bg);
      } else {
        console.warn(`Background not found: ${backgroundId}`);
      }
    },
    [scenarioId]
  );

  // 인덱스로 배경 이미지 설정
  const setBackgroundByIndex = useCallback(
    (index: number) => {
      const scenario = getScenarioBackgrounds(scenarioId);
      if (!scenario) {
        console.warn(`Scenario not found: ${scenarioId}`);
        return;
      }

      const bg = scenario.backgrounds.find(b => b.index === index);
      if (bg) {
        setCurrentBackground(bg);
      } else {
        console.warn(`Background with index ${index} not found`);
      }
    },
    [scenarioId]
  );

  // 태그로 배경 이미지 설정
  const setBackgroundByTag = useCallback(
    (tag: string, index: number = 0) => {
      const backgrounds = getBackgroundsByTag(scenarioId, tag);
      if (backgrounds.length === 0) {
        console.warn(`No backgrounds found with tag: ${tag}`);
        return;
      }

      const bg = backgrounds[index] || backgrounds[0];
      setCurrentBackground(bg);
    },
    [scenarioId]
  );

  // 기본 배경으로 리셋
  const resetToDefault = useCallback(() => {
    const defaultBg = getDefaultBackground(scenarioId);
    if (defaultBg) {
      setCurrentBackground(defaultBg);
    }
  }, [scenarioId]);

  // 모든 배경 이미지 미리 로드 (성능 최적화)
  const preloadImages = useCallback(() => {
    const scenario = getScenarioBackgrounds(scenarioId);
    if (!scenario) return;

    scenario.backgrounds.forEach(bg => {
      const img = new Image();
      img.src = getBackgroundImagePath(scenarioId, bg.fileName);
    });
  }, [scenarioId]);

  return {
    currentBackground,
    backgroundImageUrl,
    setBackgroundById,
    setBackgroundByIndex,
    setBackgroundByTag,
    resetToDefault,
    preloadImages
  };
}
