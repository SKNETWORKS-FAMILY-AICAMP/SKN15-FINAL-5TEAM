/**
 * Background Image Configuration
 *
 * 채팅창 배경 이미지를 관리하는 설정 파일입니다.
 * 각 시나리오별로 배경 이미지를 매핑하여 상황에 맞는 배경을 표시합니다.
 */

export interface BackgroundImage {
  id: string;
  index: number;
  fileName: string;
  name: string;
  description: string;
  tags?: string[];
}

export interface ScenarioBackgrounds {
  scenarioId: string;
  scenarioName: string;
  defaultBackground: string;
  backgrounds: BackgroundImage[];
}

/**
 * 무한열차 시나리오 배경 이미지 설정
 */
export const mugenTrainBackgrounds: ScenarioBackgrounds = {
  scenarioId: 'mugen_train',
  scenarioName: '무한열차',
  defaultBackground: 'derailed_train',
  backgrounds: [
    {
      id: 'derailed_train',
      index: 1,
      fileName: '1.png',
      name: '무너진 열차, 필사의 질주',
      description: '탄지로가 열차 탈선 현장에서 필사적으로 달리는 장면',
      tags: ['train', 'disaster', 'desperate', 'tanjiro']
    },
    {
      id: 'rengoku_standing',
      index: 2,
      fileName: '2.png',
      name: '염주, 렌고쿠 쿄쥬로',
      description: '열차가 탈선 됐지만 당황하지 않고 굳건히 서 있는 렌고쿠의 모습',
      tags: ['rengoku', 'hashira', 'strong', 'flame']
    },
    {
      id: 'akaza_arrival',
      index: 3,
      fileName: '3.png',
      name: '상현의 등장',
      description: '상현 3 아카자가 압도적인 기운과 함께 처음 등장하는 장면',
      tags: ['akaza', 'upper_rank', 'demon', 'arrival', 'threatening']
    },
    {
      id: 'compass_battle',
      index: 4,
      fileName: '4.png',
      name: '나침반 위의 사투',
      description: '아카자의 술식 "파괴살: 나침" 위에서 렌고쿠와 격돌하는 장면',
      tags: ['battle', 'rengoku', 'akaza', 'technique', 'intense']
    },
    {
      id: 'compass_technique',
      index: 5,
      fileName: '5.png',
      name: '술식 전개: 파괴살 나침',
      description: '아카자가 본격적인 전투를 위해 자세를 잡고 기술을 전개하는 장면',
      tags: ['akaza', 'technique', 'blood_demon_art', 'battle_start']
    },
    {
      id: 'flame_vs_fighting_spirit',
      index: 6,
      fileName: '6.png',
      name: '붉은 화염, 푸른 투기',
      description: '렌고쿠의 화염과 아카자의 푸른 투기가 정면으로 충돌하는 모습',
      tags: ['battle', 'rengoku', 'akaza', 'clash', 'intense', 'fire']
    },
    {
      id: 'hashira_vs_upper_rank',
      index: 7,
      fileName: '7.png',
      name: '염주와 상현의 격돌',
      description: '렌고쿠가 아카자의 공격을 정면으로 받아치며 싸우는 격전',
      tags: ['battle', 'rengoku', 'akaza', 'intense', 'clash']
    },
    {
      id: 'inosuke_sharpening',
      index: 8,
      fileName: '8.png',
      name: '어둠 속의 칼날갈이',
      description: '이노스케를 만났을 때, 이노스케가 다음 전투를 준비하며 칼을 가는 장면',
      tags: ['inosuke', 'preparation', 'dark', 'beast']
    },
    {
      id: 'inosuke_charge',
      index: 9,
      fileName: '9.png',
      name: '짐승의 호흡, 돌격!',
      description: '이노스케를 설득했을 때 이노스케가 투지가 생긴 모습',
      tags: ['inosuke', 'beast_breathing', 'charge', 'motivated']
    },
    {
      id: 'duel_flame_and_fist',
      index: 10,
      fileName: '10.jpg',
      name: '일기토: 불꽃과 권무',
      description: '렌고쿠와 아카자가 서로의 모든 것을 걸고 싸우는 치열한 근접전',
      tags: ['battle', 'rengoku', 'akaza', 'intense', 'duel', 'climax']
    },
    {
      id: 'zenitsu_sleeping',
      index: 11,
      fileName: '11.png',
      name: '고요한 열차, 잠든 번개',
      description: '젠이츠가 파괴된 열차 안에서 잠들어 있는 모습',
      tags: ['zenitsu', 'sleeping', 'train', 'calm']
    },
    {
      id: 'thunderclap_and_flash',
      index: 12,
      fileName: '12.png',
      name: '벽력일섬',
      description: '젠이츠를 설득하는데 성공했을 때 투지가 생긴 젠이츠',
      tags: ['zenitsu', 'thunder_breathing', 'motivated', 'lightning']
    },
    {
      id: 'pierced_abdomen',
      index: 13,
      fileName: '13.png',
      name: '최후의 일격, 꿰뚫린 복부',
      description: '아카자의 팔이 렌고쿠의 복부를 꿰뚫은 결정적인 장면',
      tags: ['rengoku', 'akaza', 'critical', 'injury', 'dramatic', 'tragic']
    },
    {
      id: 'remaining_flame',
      index: 14,
      fileName: '14.png',
      name: '남겨진 불꽃',
      description: '싸움이 끝난 후, 렌고쿠의 일륜도와 하오리만 남아있는 장면',
      tags: ['rengoku', 'aftermath', 'tragic', 'emotional', 'sword', 'haori']
    },
    {
      id: 'cooperation_towards_dawn',
      index: 15,
      fileName: '15.png',
      name: '새벽을 향한 공조',
      description: '이노스케와 젠이츠가 함께 전장을 달리는 모습',
      tags: ['inosuke', 'zenitsu', 'cooperation', 'running', 'dawn']
    },
    {
      id: 'three_united',
      index: 16,
      fileName: '16.png',
      name: '삼인삼색, 합동 전선',
      description: '탄지로, 젠이츠, 이노스케가 각자의 기술을 상징하는 형상과 함께 싸우는 모습',
      tags: ['tanjiro', 'zenitsu', 'inosuke', 'trio', 'united', 'breathing', 'hidden_ending_route']
    },
    {
      id: 'rengoku_ninth_form',
      index: 17,
      fileName: '17.png',
      name: '불꽃의 호흡, 오의: 연옥',
      description: '렌고쿠가 화룡의 형상과 함께 최후의 오의를 사용하는 장면',
      tags: ['rengoku', 'flame_breathing', 'ninth_form', 'ultimate', 'dragon', 'climax']
    },
    {
      id: 'dawn_and_tears',
      index: 18,
      fileName: '18.png',
      name: '여명, 그리고 패배의 눈물',
      description: '해가 뜨고, 렌고쿠의 곁에서 오열하는 탄지로와 젠이츠, 그리고 분노하는 이노스케',
      tags: ['dawn', 'tanjiro', 'zenitsu', 'inosuke', 'rengoku', 'tears', 'grief', 'anger', 'tragic']
    },
    {
      id: 'fulfill_duty',
      index: 19,
      fileName: '19.jpg',
      name: '책무를 다하다',
      description: '모든 싸움을 마치고 어머니를 떠올리며 미소 짓는 렌고쿠의 마지막 모습',
      tags: ['rengoku', 'final_moment', 'smile', 'duty', 'mother', 'tragic', 'emotional']
    },
    {
      id: 'set_heart_ablaze',
      index: 20,
      fileName: '20.png',
      name: '마음을 불태워라',
      description: '렌고쿠가 죽기 직전, 탄지로에게 마지막 유언을 남기며 격려하는 장면',
      tags: ['rengoku', 'tanjiro', 'last_words', 'encouragement', 'emotional', 'legacy']
    },
    {
      id: 'hidden_ending',
      index: 21,
      fileName: '21.png',
      name: '[히든 엔딩] 불꽃과 함께 맞이한 여명',
      description: '염주 렌고쿠 쿄쥬로가 살아남아, 탄지로 일행과 함께 폐허 속에서 떠오르는 태양을 바라보는, 또 다른 이야기의 결말',
      tags: ['hidden_ending', 'rengoku', 'tanjiro', 'zenitsu', 'inosuke', 'sunrise', 'victory', 'happy', 'alternative']
    }
  ]
};

/**
 * 모든 시나리오의 배경 이미지 설정을 관리
 */
export const allScenarioBackgrounds: ScenarioBackgrounds[] = [
  mugenTrainBackgrounds,
  // 향후 다른 시나리오 추가 가능
  // trainStationBackgrounds,
  // demonSlayerHQBackgrounds,
  // etc...
];

/**
 * 시나리오 ID 매핑 (여러 시나리오 ID가 같은 배경 이미지를 사용할 수 있도록)
 */
const SCENARIO_ID_MAPPING: Record<string, string> = {
  'mugen_train_full': 'mugen_train',  // 무한열차 - 츠구코의 시련 → 무한열차 이미지 사용
  'train': 'mugen_train',              // train → mugen_train 이미지 사용
};

/**
 * 시나리오 ID로 배경 이미지 설정을 가져옵니다
 */
export function getScenarioBackgrounds(scenarioId: string): ScenarioBackgrounds | undefined {
  // ID 매핑이 있으면 매핑된 ID 사용
  const mappedId = SCENARIO_ID_MAPPING[scenarioId] || scenarioId;
  return allScenarioBackgrounds.find(scenario => scenario.scenarioId === mappedId);
}

/**
 * 배경 이미지 ID로 이미지 정보를 가져옵니다
 */
export function getBackgroundById(scenarioId: string, backgroundId: string): BackgroundImage | undefined {
  const scenario = getScenarioBackgrounds(scenarioId);
  return scenario?.backgrounds.find(bg => bg.id === backgroundId);
}

/**
 * 배경 이미지의 전체 경로를 반환합니다
 * 환경변수 VITE_CDN_URL을 사용하여 로컬/AWS 환경을 자동 전환합니다
 */
export function getBackgroundImagePath(scenarioId: string, fileName: string): string {
  const cdnUrl = import.meta.env.VITE_CDN_URL || '/images';
  // ID 매핑이 있으면 매핑된 ID로 경로 생성
  const mappedId = SCENARIO_ID_MAPPING[scenarioId] || scenarioId;
  return `${cdnUrl}/backgrounds/${mappedId}/${fileName}`;
}

/**
 * 태그로 배경 이미지를 검색합니다
 */
export function getBackgroundsByTag(scenarioId: string, tag: string): BackgroundImage[] {
  const scenario = getScenarioBackgrounds(scenarioId);
  if (!scenario) return [];

  return scenario.backgrounds.filter(bg => bg.tags?.includes(tag)) || [];
}

/**
 * 기본 배경 이미지를 가져옵니다
 */
export function getDefaultBackground(scenarioId: string): BackgroundImage | undefined {
  const scenario = getScenarioBackgrounds(scenarioId);
  if (!scenario) return undefined;

  return scenario.backgrounds.find(bg => bg.id === scenario.defaultBackground);
}
