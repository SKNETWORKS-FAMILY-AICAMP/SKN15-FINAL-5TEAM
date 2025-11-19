/**
 * Background Image Configuration (auto-generated from mugen_train_images.json)
 */

export interface BackgroundImage {
  id: string;
  index: number;
  fileName: string;
  name: string;
  description: string;
}

export interface ScenarioBackgrounds {
  scenarioId: string;
  scenarioName: string;
  defaultBackground: string;
  backgrounds: BackgroundImage[];
}

const normalizeScenarioId = (id: string) => id.replace(/_/g, '-').toLowerCase();

export const mugenTrainBackgrounds: ScenarioBackgrounds = {
  scenarioId: 'mugen-train',
  scenarioName: '무한열차',
  defaultBackground: '무한열차.png',
  backgrounds: [
  {
    id: "무한열차.png",
    index: 0,
    fileName: "무한열차.png",
    name: "무한열차 기본 배경",
    description: "무한열차 외관 기본 컷"
  },
  {
    id: "탄지로_기본.png",
    index: 1,
    fileName: "탄지로_기본.png",
    name: "탄지로 기본",
    description: "탄지로가 기본 자세로 서 있는 모습"
  },
  {
    id: "탄지로_속삭임.png",
    index: 2,
    fileName: "탄지로_속삭임.png",
    name: "탄지로의 속삭임",
    description: "탄지로가 가까이서 조용히 속삭이는 장면"
  },
  {
    id: "아카자_기본.png",
    index: 3,
    fileName: "아카자_기본.png",
    name: "아카자 기본",
    description: "아카자가 모습을 드러내며 서 있는 장면"
  },
  {
    id: "렌고쿠_전투1.png",
    index: 4,
    fileName: "렌고쿠_전투1.png",
    name: "렌고쿠 전투 1",
    description: "렌고쿠가 전투 자세로 맞서는 순간"
  },
  {
    id: "아카자_술식.mp4",
    index: 5,
    fileName: "아카자_술식.mp4",
    name: "아카자 술식 전개",
    description: "아카자가 혈귀술을 펼치는 영상"
  },
  {
    id: "렌고쿠_전투2.png",
    index: 6,
    fileName: "렌고쿠_전투2.png",
    name: "렌고쿠 전투 2",
    description: "렌고쿠가 불꽃으로 격돌하는 장면"
  },
  {
    id: "렌고쿠_발악.jpg",
    index: 7,
    fileName: "렌고쿠_발악.jpg",
    name: "렌고쿠 분투",
    description: "렌고쿠가 절규하며 싸우는 순간"
  },
  {
    id: "이노스케_기본.png",
    index: 8,
    fileName: "이노스케_기본.png",
    name: "이노스케 기본",
    description: "이노스케가 기본 자세로 서 있는 모습"
  },
  {
    id: "이노스케_흥분.png",
    index: 9,
    fileName: "이노스케_흥분.png",
    name: "이노스케 흥분",
    description: "흥분한 이노스케가 포효하는 모습"
  },
  {
    id: "엔무_등장.png",
    index: 10,
    fileName: "엔무_등장.png",
    name: "엔무 등장",
    description: "엔무가 모습을 드러내는 장면"
  },
  {
    id: "엔무_패배.png",
    index: 38,
    fileName: "엔무_패배.png",
    name: "엔무 패배",
    description: "엔무를 쓰러뜨리고 열차가 요동치는 순간"
  },
  {
    id: "유저_좌절.png",
    index: 11,
    fileName: "유저_좌절.png",
    name: "절망의 꿈",
    description: "사용자가 꿈속에서 좌절하는 모습"
  },
  {
    id: "유저_렌고쿠.png",
    index: 12,
    fileName: "유저_렌고쿠.png",
    name: "렌고쿠와의 다짐",
    description: "사용자가 꿈속에서 렌고쿠와 각오를 다지는 장면"
  },
  {
    id: "렌고쿠_패배.png",
    index: 13,
    fileName: "렌고쿠_패배.png",
    name: "렌고쿠 패배",
    description: "렌고쿠가 치명상을 입은 장면"
  },
  {
    id: "배드_엔딩.png",
    index: 14,
    fileName: "배드_엔딩.png",
    name: "배드 엔딩",
    description: "패배 후 남겨진 불꽃"
  },
  {
    id: "유저_렌고쿠.png",
    index: 15,
    fileName: "유저_렌고쿠.png",
    name: "렌고쿠와의 다짐(반복)",
    description: "사용자가 꿈속에서 렌고쿠와 각오를 다지는 장면"
  },
  {
    id: "동료_지원.png",
    index: 16,
    fileName: "동료_지원.png",
    name: "동료 지원",
    description: "탄지로와 동료들이 함께 싸우는 모습"
  },
  {
    id: "렌고쿠_각성.mp4",
    index: 17,
    fileName: "렌고쿠_각성.mp4",
    name: "렌고쿠 각성",
    description: "렌고쿠가 각성하는 영상"
  },
  {
    id: "배드_엔딩_2.png",
    index: 18,
    fileName: "배드_엔딩_2.png",
    name: "배드 엔딩 2",
    description: "눈물의 여명이 비치는 배드엔딩"
  },
  {
    id: "렌고쿠_유언.jpg",
    index: 19,
    fileName: "렌고쿠_유언.jpg",
    name: "렌고쿠 유언",
    description: "렌고쿠가 마지막 말을 전하는 장면"
  },
  {
    id: "히든엔딩1.png",
    index: 20,
    fileName: "히든엔딩1.png",
    name: "히든 엔딩 1",
    description: "숨겨진 결말 1"
  },
  {
    id: "히든엔딩2.png",
    index: 21,
    fileName: "히든엔딩2.png",
    name: "히든 엔딩 2",
    description: "숨겨진 결말 2"
  },
  {
    id: "탄지로_등장.png",
    index: 22,
    fileName: "탄지로_등장.png",
    name: "탄지로 등장",
    description: "탄지로가 객차 문을 열고 등장하는 장면"
  },
  {
    id: "렌고쿠_식사.png",
    index: 23,
    fileName: "렌고쿠_식사.png",
    name: "렌고쿠 식사",
    description: "렌고쿠가 도시락을 먹으며 웃는 장면"
  },
  {
    id: "잠든_모두.jpg",
    index: 24,
    fileName: "잠든_모두.jpg",
    name: "잠든 모두",
    description: "최면에 걸려 모두 잠든 모습"
  },
  {
    id: "렌고쿠_섬멸.mp4",
    index: 25,
    fileName: "렌고쿠_섬멸.mp4",
    name: "렌고쿠 섬멸",
    description: "렌고쿠가 적을 섬멸하는 영상"
  },
  {
    id: "동료_합류.png",
    index: 26,
    fileName: "동료_합류.png",
    name: "동료 합류",
    description: "동료들이 함께 전장에 합류하는 모습"
  },
  {
    id: "렌고쿠_기본.png",
    index: 27,
    fileName: "렌고쿠_기본.png",
    name: "렌고쿠 기본",
    description: "렌고쿠가 당당히 서 있는 기본 자세"
  },
  {
    id: "렌고쿠_기본.jpg",
    index: 28,
    fileName: "렌고쿠_기본.jpg",
    name: "렌고쿠 기본(일러스트)",
    description: "렌고쿠가 서 있는 일러스트 컷"
  },
  {
    id: "렌고쿠_결의.png",
    index: 29,
    fileName: "렌고쿠_결의.png",
    name: "렌고쿠 결의",
    description: "렌고쿠가 결의를 다지는 모습"
  },
  {
    id: "탄지로_속삭임.jpg",
    index: 30,
    fileName: "탄지로_속삭임.jpg",
    name: "탄지로 속삭임(일러스트)",
    description: "탄지로가 속삭이는 일러스트 컷"
  },
  {
    id: "탄지로_탈출.png",
    index: 31,
    fileName: "탄지로_탈출.png",
    name: "탄지로 탈출",
    description: "탄지로가 열차에서 탈출하며 돌진하는 장면"
  },
  {
    id: "젠이츠_각성.png",
    index: 32,
    fileName: "젠이츠_각성.png",
    name: "젠이츠 각성",
    description: "젠이츠가 번개와 함께 각성하는 장면"
  },
  {
    id: "젠이츠_기본.png",
    index: 33,
    fileName: "젠이츠_기본.png",
    name: "젠이츠 기본",
    description: "젠이츠가 기본 자세로 서 있는 모습"
  },
  {
    id: "젠이츠_숙면.png",
    index: 34,
    fileName: "젠이츠_숙면.png",
    name: "젠이츠 숙면",
    description: "젠이츠가 곤히 잠든 모습"
  },
  {
    id: "네즈코_기본.png",
    index: 35,
    fileName: "네즈코_기본.png",
    name: "네즈코 기본",
    description: "네즈코가 상자에서 나온 기본 모습"
  },
  {
    id: "기유_기본.png",
    index: 36,
    fileName: "기유_기본.png",
    name: "기유 기본",
    description: "기유가 차분히 서 있는 모습"
  },
  {
    id: "시노부_기본.png",
    index: 37,
    fileName: "시노부_기본.png",
    name: "시노부 기본",
    description: "시노부가 미소를 머금은 기본 모습"
  },
  {
    id: "remaining_flame.png",
    index: 38,
    fileName: "remaining_flame.png",
    name: "Remaining Flame",
    description: "(추가 설명 필요)"
  },
  {
    id: "three_united.png",
    index: 39,
    fileName: "three_united.png",
    name: "Three United",
    description: "(추가 설명 필요)"
  },
  {
    id: "akaza_arrival.png",
    index: 40,
    fileName: "akaza_arrival.png",
    name: "Akaza Arrival",
    description: "(추가 설명 필요)"
  },
  {
    id: "dawn_and_tears.png",
    index: 41,
    fileName: "dawn_and_tears.png",
    name: "Dawn And Tears",
    description: "(추가 설명 필요)"
  },
  {
    id: "pierced_abdomen.png",
    index: 42,
    fileName: "pierced_abdomen.png",
    name: "Pierced Abdomen",
    description: "(추가 설명 필요)"
  },
  {
    id: "set_heart_ablaze.png",
    index: 43,
    fileName: "set_heart_ablaze.png",
    name: "Set Heart Ablaze",
    description: "(추가 설명 필요)"
  },
  {
    id: "derailed_train.png",
    index: 44,
    fileName: "derailed_train.png",
    name: "Derailed Train",
    description: "(추가 설명 필요)"
  },
  {
    id: "compass_battle.png",
    index: 45,
    fileName: "compass_battle.png",
    name: "Compass Battle",
    description: "(추가 설명 필요)"
  },
  {
    id: "hidden_ending.png",
    index: 46,
    fileName: "hidden_ending.png",
    name: "Hidden Ending",
    description: "(추가 설명 필요)"
  },
  {
    id: "compass_technique.png",
    index: 47,
    fileName: "compass_technique.png",
    name: "Compass Technique",
    description: "(추가 설명 필요)"
  },
  {
    id: "rengoku_bento.png",
    index: 48,
    fileName: "rengoku_bento.png",
    name: "Rengoku Bento",
    description: "(추가 설명 필요)"
  },
  {
    id: "inosuke_sharpening.png",
    index: 49,
    fileName: "inosuke_sharpening.png",
    name: "Inosuke Sharpening",
    description: "(추가 설명 필요)"
  },
  {
    id: "fulfill_duty.png",
    index: 50,
    fileName: "fulfill_duty.png",
    name: "Fulfill Duty",
    description: "(추가 설명 필요)"
  },
  {
    id: "akaza_arrival",
    index: 51,
    fileName: "akaza_arrival",
    name: "Akaza Arrival",
    description: "(매칭용 placeholder)"
  },
  {
    id: "compass_battle",
    index: 52,
    fileName: "compass_battle",
    name: "Compass Battle",
    description: "(매칭용 placeholder)"
  },
  {
    id: "compass_technique",
    index: 53,
    fileName: "compass_technique",
    name: "Compass Technique",
    description: "(매칭용 placeholder)"
  },
  {
    id: "dawn_and_tears",
    index: 54,
    fileName: "dawn_and_tears",
    name: "Dawn And Tears",
    description: "(매칭용 placeholder)"
  },
  {
    id: "derailed_train",
    index: 55,
    fileName: "derailed_train",
    name: "Derailed Train",
    description: "(매칭용 placeholder)"
  },
  {
    id: "fulfill_duty",
    index: 56,
    fileName: "fulfill_duty",
    name: "Fulfill Duty",
    description: "(매칭용 placeholder)"
  },
  {
    id: "hidden_ending",
    index: 57,
    fileName: "hidden_ending",
    name: "Hidden Ending",
    description: "(매칭용 placeholder)"
  },
  {
    id: "inosuke_sharpening",
    index: 58,
    fileName: "inosuke_sharpening",
    name: "Inosuke Sharpening",
    description: "(매칭용 placeholder)"
  },
  {
    id: "pierced_abdomen",
    index: 59,
    fileName: "pierced_abdomen",
    name: "Pierced Abdomen",
    description: "(매칭용 placeholder)"
  },
  {
    id: "remaining_flame",
    index: 60,
    fileName: "remaining_flame",
    name: "Remaining Flame",
    description: "(매칭용 placeholder)"
  },
  {
    id: "rengoku_bento",
    index: 61,
    fileName: "rengoku_bento",
    name: "Rengoku Bento",
    description: "(매칭용 placeholder)"
  },
  {
    id: "set_heart_ablaze",
    index: 62,
    fileName: "set_heart_ablaze",
    name: "Set Heart Ablaze",
    description: "(매칭용 placeholder)"
  },
  {
    id: "three_united",
    index: 63,
    fileName: "three_united",
    name: "Three United",
    description: "(매칭용 placeholder)"
  }
  ]
};

export const idolBandBackgrounds: ScenarioBackgrounds = {
  scenarioId: 'idol-band',
  scenarioName: '아이돌/밴드 AU',
  defaultBackground: '아이돌밴드.png',
  backgrounds: [
    {
      id: "아이돌밴드.png",
      index: 0,
      fileName: "아이돌밴드.png",
      name: "아이돌 밴드 기본 배경",
      description: "카게부신 밴드 연습실"
    }
  ]
};

export const allScenarioBackgrounds: ScenarioBackgrounds[] = [mugenTrainBackgrounds, idolBandBackgrounds];

export function getScenarioBackgrounds(scenarioId: string): ScenarioBackgrounds | undefined {
  const normalized = normalizeScenarioId(scenarioId);
  return allScenarioBackgrounds.find(s => normalizeScenarioId(s.scenarioId) === normalized);
}

export function getBackgroundById(scenarioId: string, backgroundId: string): BackgroundImage | undefined {
  const scenario = getScenarioBackgrounds(scenarioId);
  return scenario?.backgrounds.find(bg => bg.id === backgroundId);
}

export function getBackgroundImagePath(_scenarioId: string, fileName: string): string {
  const cdnUrl = import.meta.env.VITE_CDN_URL || '/images';
  return `${cdnUrl}/backgrounds/${fileName}`;
}

export function getDefaultBackground(scenarioId: string): BackgroundImage | undefined {
  const scenario = getScenarioBackgrounds(scenarioId);
  return scenario?.backgrounds.find(bg => bg.id === scenario.defaultBackground);
}
