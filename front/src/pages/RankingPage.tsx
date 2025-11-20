import { useState } from 'react';
import { Link } from 'react-router-dom';
import ChatHeader from '@/components/ChatHeader';
import { useApp } from '@/contexts/AppContext';

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

interface RankingUser {
  rank: number;
  userId: string;
  username: string;
  avatar: string;
  level: number;
  exp: number;
  totalMessages: number;
  scenariosCompleted: number;
  rankCode: string;
  badge?: string;
}

// Mock data for ranking (백엔드 연결 전 디자인 확인용)
const mockRankingData: RankingUser[] = [
  {
    rank: 1,
    userId: '1',
    username: '귀멸의검사',
    avatar: `${CDN_URL}/프로필_탄지로.png`,
    level: 42,
    exp: 15800,
    totalMessages: 2450,
    scenariosCompleted: 8,
    rankCode: 'HASHIRA',
    badge: '🏆'
  },
  {
    rank: 2,
    userId: '2',
    username: '물의호흡',
    avatar: `${CDN_URL}/프로필_시노부.png`,
    level: 38,
    exp: 13200,
    totalMessages: 2180,
    scenariosCompleted: 7,
    rankCode: 'HASHIRA',
    badge: '🥈'
  },
  {
    rank: 3,
    userId: '3',
    username: '불꽃의심장',
    avatar: `${CDN_URL}/프로필_렌고쿠.png`,
    level: 35,
    exp: 11500,
    totalMessages: 1920,
    scenariosCompleted: 6,
    rankCode: 'KINOE',
    badge: '🥉'
  },
  {
    rank: 4,
    userId: '4',
    username: '뇌의호흡마스터',
    avatar: `${CDN_URL}/프로필_젠이츠.png`,
    level: 33,
    exp: 10200,
    totalMessages: 1750,
    scenariosCompleted: 6,
    rankCode: 'KINOE'
  },
  {
    rank: 5,
    userId: '5',
    username: '야수의왕',
    avatar: `${CDN_URL}/프로필_이노스케.png`,
    level: 31,
    exp: 9800,
    totalMessages: 1650,
    scenariosCompleted: 5,
    rankCode: 'KINOE'
  },
  {
    rank: 6,
    userId: '6',
    username: '달빛아래',
    avatar: `${CDN_URL}/프로필_네즈코.png`,
    level: 29,
    exp: 8900,
    totalMessages: 1480,
    scenariosCompleted: 5,
    rankCode: 'KINOTO'
  },
  {
    rank: 7,
    userId: '7',
    username: '검의달인',
    avatar: `${CDN_URL}/프로필_탄지로.png`,
    level: 27,
    exp: 8200,
    totalMessages: 1320,
    scenariosCompleted: 4,
    rankCode: 'KINOTO'
  },
  {
    rank: 8,
    userId: '8',
    username: '호흡의수련자',
    avatar: `${CDN_URL}/프로필_시노부.png`,
    level: 25,
    exp: 7500,
    totalMessages: 1180,
    scenariosCompleted: 4,
    rankCode: 'HINOE'
  },
  {
    rank: 9,
    userId: '9',
    username: '귀살대지망생',
    avatar: `${CDN_URL}/프로필_렌고쿠.png`,
    level: 23,
    exp: 6800,
    totalMessages: 1020,
    scenariosCompleted: 3,
    rankCode: 'HINOE'
  },
  {
    rank: 10,
    userId: '10',
    username: '초보검사',
    avatar: `${CDN_URL}/프로필_젠이츠.png`,
    level: 21,
    exp: 6100,
    totalMessages: 890,
    scenariosCompleted: 3,
    rankCode: 'HINOTO'
  },
  {
    rank: 11,
    userId: '11',
    username: '수련중',
    avatar: `${CDN_URL}/프로필_이노스케.png`,
    level: 19,
    exp: 5400,
    totalMessages: 750,
    scenariosCompleted: 2,
    rankCode: 'HINOTO'
  },
  {
    rank: 12,
    userId: '12',
    username: '도전자',
    avatar: `${CDN_URL}/프로필_네즈코.png`,
    level: 17,
    exp: 4800,
    totalMessages: 620,
    scenariosCompleted: 2,
    rankCode: 'MIZUNOE'
  }
];

const rankCodeNames: Record<string, string> = {
  HASHIRA: '주',
  KINOE: '갑',
  KINOTO: '을',
  HINOE: '병',
  HINOTO: '정',
  MIZUNOE: '무',
  MIZUNOTO: '기',
  KANOE: '경',
  KANOTO: '신',
  TSUCHINOE: '임',
  TSUCHINOTO: '계'
};

export default function RankingPage() {
  const [selectedTab, setSelectedTab] = useState<'level' | 'messages' | 'scenarios'>('level');
  const { toggleSidebar, currentUser } = useApp();

  // Sort data based on selected tab
  const getSortedRanking = () => {
    const sorted = [...mockRankingData];
    switch (selectedTab) {
      case 'level':
        return sorted.sort((a, b) => b.level - a.level);
      case 'messages':
        return sorted.sort((a, b) => b.totalMessages - a.totalMessages);
      case 'scenarios':
        return sorted.sort((a, b) => b.scenariosCompleted - a.scenariosCompleted);
      default:
        return sorted;
    }
  };

  const sortedData = getSortedRanking();

  const getRankBadgeColor = (rank: number) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white';
    if (rank === 2) return 'bg-gradient-to-r from-gray-300 to-gray-400 text-white';
    if (rank === 3) return 'bg-gradient-to-r from-orange-400 to-orange-600 text-white';
    if (rank <= 10) return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white';
    return 'bg-gray-200 text-gray-700';
  };

  const getRankCodeColor = (rankCode: string) => {
    if (rankCode === 'HASHIRA') return 'bg-purple-600 text-white';
    if (rankCode === 'KINOE') return 'bg-red-600 text-white';
    if (rankCode === 'KINOTO') return 'bg-orange-500 text-white';
    if (rankCode === 'HINOE') return 'bg-blue-500 text-white';
    if (rankCode === 'HINOTO') return 'bg-green-500 text-white';
    return 'bg-gray-500 text-white';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        title="랭킹"
        showBackButton={true}
      />

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Title Section */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            귀살대 랭킹
          </h1>
          <p className="text-gray-600">
            최고의 귀살대원들을 만나보세요
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-2xl shadow-lg p-2 mb-6 flex gap-2">
          <button
            onClick={() => setSelectedTab('level')}
            className={`flex-1 py-3 px-4 rounded-xl font-semibold transition-all duration-200 ${
              selectedTab === 'level'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            레벨 랭킹
          </button>
          <button
            onClick={() => setSelectedTab('messages')}
            className={`flex-1 py-3 px-4 rounded-xl font-semibold transition-all duration-200 ${
              selectedTab === 'messages'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            대화 랭킹
          </button>
          <button
            onClick={() => setSelectedTab('scenarios')}
            className={`flex-1 py-3 px-4 rounded-xl font-semibold transition-all duration-200 ${
              selectedTab === 'scenarios'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            시나리오 클리어
          </button>
        </div>

        {/* Ranking List */}
        <div className="space-y-3">
          {sortedData.map((user, index) => {
            const actualRank = index + 1;
            const isCurrentUser = currentUser?.user_id === user.userId;

            return (
              <div
                key={user.userId}
                className={`bg-white rounded-2xl shadow-md hover:shadow-xl transition-all duration-300 p-6 ${
                  isCurrentUser ? 'ring-2 ring-purple-500 ring-offset-2' : ''
                }`}
              >
                <div className="flex items-center gap-6">
                  {/* Rank Badge */}
                  <div className={`flex-shrink-0 w-16 h-16 rounded-2xl ${getRankBadgeColor(actualRank)} flex items-center justify-center shadow-md`}>
                    <div className="text-center">
                      {user.badge && <div className="text-2xl">{user.badge}</div>}
                      <div className="text-lg font-bold">{actualRank}</div>
                    </div>
                  </div>

                  {/* Avatar */}
                  <div className="flex-shrink-0">
                    <img
                      src={user.avatar}
                      alt={user.username}
                      className="w-16 h-16 rounded-full border-4 border-white shadow-lg object-cover"
                      onError={(e) => {
                        e.currentTarget.src = `${CDN_URL}/프로필_탄지로.png`;
                      }}
                    />
                  </div>

                  {/* User Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-bold text-gray-800 truncate">
                        {user.username}
                      </h3>
                      {isCurrentUser && (
                        <span className="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">
                          나
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 flex-wrap">
                      <span className={`px-3 py-1 rounded-lg text-sm font-semibold ${getRankCodeColor(user.rankCode)}`}>
                        {rankCodeNames[user.rankCode] || user.rankCode}
                      </span>
                      <span className="text-gray-600 text-sm">
                        Lv. {user.level}
                      </span>
                      <span className="text-gray-500 text-sm">
                        EXP {user.exp.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="hidden md:flex flex-col items-end gap-1">
                    <div className="flex items-center gap-2 text-gray-700">
                      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                        <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
                      </svg>
                      <span className="font-semibold">{user.totalMessages.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-700">
                      <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="font-semibold">{user.scenariosCompleted}</span>
                    </div>
                  </div>

                  {/* Mobile Stats */}
                  <div className="flex md:hidden flex-col items-end gap-1">
                    <span className="text-sm text-gray-600">💬 {user.totalMessages}</span>
                    <span className="text-sm text-gray-600">✅ {user.scenariosCompleted}</span>
                  </div>
                </div>

                {/* Progress Bar (Level Progress) */}
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center justify-between text-xs text-gray-600 mb-2">
                    <span>다음 레벨까지</span>
                    <span>{((user.exp % 500) / 500 * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-indigo-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(user.exp % 500) / 500 * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Back to Home Button */}
        <div className="mt-8 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-700 rounded-xl shadow-md hover:shadow-lg transition-all duration-200 font-semibold"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  );
}
