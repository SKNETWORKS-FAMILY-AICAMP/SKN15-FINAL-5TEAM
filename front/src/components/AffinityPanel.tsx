import React from 'react';

interface AffinityPanelProps {
  affinityScores: Record<string, number>;
}

interface CharacterInfo {
  id: string;
  name: string;
  profileImage: string;
  color: string;
}

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

const CHARACTERS: CharacterInfo[] = [
  {
    id: 'tanjiro',
    name: '탄지로',
    profileImage: `${CDN_URL}/프로필_탄지로.png`,
    color: 'from-green-500 to-green-600'
  },
  {
    id: 'inosuke',
    name: '이노스케',
    profileImage: `${CDN_URL}/프로필_이노스케.png`,
    color: 'from-blue-500 to-blue-600'
  },
  {
    id: 'zenitsu',
    name: '젠이츠',
    profileImage: `${CDN_URL}/프로필_젠이츠.png`,
    color: 'from-yellow-500 to-yellow-600'
  },
  {
    id: 'rengoku',
    name: '렌고쿠',
    profileImage: `${CDN_URL}/프로필_렌고쿠.png`,
    color: 'from-red-500 to-red-600'
  }
];

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

export default function AffinityPanel({ affinityScores }: AffinityPanelProps) {
  // 모든 캐릭터 표시 (친밀도가 없으면 0으로 표시)
  if (Object.keys(affinityScores).length === 0) {
    return null; // 친밀도 데이터가 전혀 없으면 패널을 표시하지 않음
  }

  return (
    <div className="w-full bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg p-2.5 border border-purple-200/50">
      {/* 헤더 */}
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-purple-600">💜</span>
        <span className="text-xs font-bold text-gray-700">친밀도</span>
      </div>

      {/* 캐릭터별 프로그레스 바 - 가로 배치 */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        {CHARACTERS.map((character) => {
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
