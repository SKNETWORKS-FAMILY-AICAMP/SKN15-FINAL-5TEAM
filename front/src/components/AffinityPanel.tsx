import React from 'react';

interface AffinityPanelProps {
  affinityScores: Record<string, number>;
  characterIds?: string[]; // 동적 캐릭터 목록
}

interface CharacterInfo {
  id: string;
  name: string;
  profileImage: string;
  color: string;
}

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const CHARACTER_META: Record<string, CharacterInfo> = {
  tanjiro: {
    id: 'tanjiro',
    name: '탄지로',
    profileImage: `${CDN_URL}/프로필_탄지로.png`,
    color: 'from-green-500 to-green-600'
  },
  inosuke: {
    id: 'inosuke',
    name: '이노스케',
    profileImage: `${CDN_URL}/프로필_이노스케.png`,
    color: 'from-blue-500 to-blue-600'
  },
  zenitsu: {
    id: 'zenitsu',
    name: '젠이츠',
    profileImage: `${CDN_URL}/프로필_젠이츠.png`,
    color: 'from-yellow-500 to-yellow-600'
  },
  rengoku: {
    id: 'rengoku',
    name: '렌고쿠',
    profileImage: `${CDN_URL}/프로필_렌고쿠.png`,
    color: 'from-red-500 to-red-600'
  },
  nezuko: {
    id: 'nezuko',
    name: '네즈코',
    profileImage: `${CDN_URL}/프로필_네즈코.png`,
    color: 'from-pink-500 to-pink-600'
  },
  giyu: {
    id: 'giyu',
    name: '기유',
    profileImage: `${CDN_URL}/프로필_기유.png`,
    color: 'from-cyan-500 to-cyan-600'
  },
  shinobu: {
    id: 'shinobu',
    name: '시노부',
    profileImage: `${CDN_URL}/프로필_시노부.png`,
    color: 'from-violet-500 to-violet-600'
  }
};

const DEFAULT_ORDER = ['tanjiro', 'nezuko', 'zenitsu', 'inosuke', 'rengoku'];

function toCharacterList(ids?: string[]): CharacterInfo[] {
  const base = ids && ids.length > 0 ? ids : DEFAULT_ORDER;
  return base.map((rawId) => {
    const id = rawId?.toLowerCase?.() ?? rawId;
    if (CHARACTER_META[id]) return CHARACTER_META[id];
    // fallback: 기본 프로필/색상
    return {
      id,
      name: id,
      profileImage: `${CDN_URL}/프로필_탄지로.png`,
      color: 'from-purple-500 to-purple-600'
    };
  });
}

const MAX_AFFINITY = 1000;
const LEVEL_THRESHOLD = 200; // 200점마다 1레벨

function calculateLevel(score: number): number {
  if (score < 200) return 1;
  if (score < 400) return 2;
  if (score < 600) return 3;
  if (score < 800) return 4;
  return 5;
}

function getLevelProgress(score: number): number {
  const level = calculateLevel(score);
  const base = (level - 1) * LEVEL_THRESHOLD;
  const progress = ((score - base) / LEVEL_THRESHOLD) * 100;
  return Math.min(progress, 100);
}

export default function AffinityPanel({ affinityScores, characterIds }: AffinityPanelProps) {
  const charactersToShow = toCharacterList(characterIds);

  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg p-2.5 border border-purple-200/50">
      {/* 헤더 */}
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-purple-600">💜</span>
        <span className="text-xs font-bold text-gray-700">친밀도</span>
      </div>

      {/* 캐릭터별 프로그레스 바 - 가로 배치 */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        {charactersToShow.map((character) => {
          const score = affinityScores[character.id] || 0;
          const level = calculateLevel(score);
          const progress = (score / MAX_AFFINITY) * 100;

          return (
            <div key={character.id} className="flex items-center gap-1.5">
              <img
                src={character.profileImage}
                alt={character.name}
                className="w-5 h-5 rounded-full border border-gray-300 flex-shrink-0"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/images/프로필_탄지로.png';
                }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-1">
                    <span className="text-xs font-semibold text-gray-700">{character.name}</span>
                    <span className="text-xs text-gray-500 bg-gray-100/70 px-1 py-0.5 rounded text-[10px]">Lv.{level}</span>
                  </div>
                  <span className="text-[10px] text-purple-600 font-bold">{score}/{MAX_AFFINITY}</span>
                </div>
                {/* 프로그레스 바 with 눈금 */}
                <div className="relative w-full bg-gray-200/70 rounded-full h-1.5">
                  {/* 눈금선 (20%, 40%, 60%, 80%) */}
                  <div className="absolute inset-0 flex justify-between px-[20%]">
                    {[1, 2, 3].map((tick) => (
                      <div key={tick} className="w-px h-1.5 bg-white/50" />
                    ))}
                  </div>
                  {/* 진행 바 */}
                  <div
                    className={`h-1.5 rounded-full transition-all duration-300 bg-gradient-to-r ${character.color}`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
