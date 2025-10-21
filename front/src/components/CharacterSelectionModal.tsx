
import { useState } from 'react';

interface Character {
  id: string;
  name: string;
  description: string;
  profileImage: string;
}

interface Friend {
  id: string;
  name: string;
  description: string;
  profileImage: string;
}

interface CharacterSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectCharacter: (characterId: string) => void;
  onSelectFriend: (friendId: string) => void;
  invitedCharacters?: string[]; // 이미 초대된 캐릭터들
}

export default function CharacterSelectionModal({
  isOpen,
  onClose,
  onSelectCharacter,
  onSelectFriend,
  invitedCharacters = []
}: CharacterSelectionModalProps) {
  const [selectedTab, setSelectedTab] = useState<'character' | 'friend'>('character');

  const characters: Character[] = [
    {
      id: 'tanjiro',
      name: '탄지로',
      description: '물의 호흡을 사용하는 귀살대원',
      profileImage: '/images/프로필_탄지로.png'
    },
    {
      id: 'zenitsu',
      name: '젠이츠',
      description: '번개의 호흡을 사용하는 동료',
      profileImage: '/images/프로필_젠이츠.png'
    },
    {
      id: 'nezuko',
      name: '네즈코',
      description: '탄지로의 여동생',
      profileImage: '/images/프로필_네즈코.png'
    },
    {
      id: 'inosuke',
      name: '이노스케',
      description: '야생의 호흡을 사용하는 멧돼지',
      profileImage: '/images/프로필_이노스케.png'
    },
    {
      id: 'giyu',
      name: '기유',
      description: '물의 기둥, 조용하지만 강한 검사',
      profileImage: '/images/프로필_기유.png'
    },
    {
      id: 'akaza',
      name: '아카자',
      description: '상현 삼, 강력한 상급 귀신',
      profileImage: '/images/프로필_아카자.png'
    }
  ];

  const friends: Friend[] = [
    {
      id: 'friend1',
      name: '캐릭터1',
      description: 'Supporting line text lorem ipsum dolor sit amet, consectetur.',
      profileImage: '/images/프로필_탄지로.png'
    },
    {
      id: 'friend2',
      name: '친구2',
      description: 'Supporting line text lorem ipsum dolor sit amet, consectetur.',
      profileImage: '/images/프로필_네즈코.png'
    }
  ];

  if (!isOpen) return null;

  const handleItemClick = (item: Character | Friend) => {
    // 이미 초대된 캐릭터인지 확인
    if (selectedTab === 'character' && invitedCharacters.includes(item.id)) {
      return; // 클릭 무시
    }

    if (selectedTab === 'character') {
      onSelectCharacter(item.id);
    } else {
      onSelectFriend(item.id);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-3xl w-80 max-h-96 overflow-hidden">
        {/* 헤더 탭 */}
        <div className="flex bg-gray-900 text-white">
          <button
            onClick={() => setSelectedTab('character')}
            className={`flex-1 py-4 px-4 text-sm font-medium ${
              selectedTab === 'character'
                ? 'text-red-400 border-b-2 border-red-400'
                : 'text-white'
            }`}
          >
            Character
          </button>
          <button
            onClick={() => setSelectedTab('friend')}
            className={`flex-1 py-4 px-4 text-sm font-medium ${
              selectedTab === 'friend'
                ? 'text-white border-b-2 border-white'
                : 'text-white'
            }`}
          >
            Friend
          </button>
        </div>

        {/* 콘텐츠 영역 */}
        <div className="max-h-80 overflow-y-auto bg-gray-900">
          {selectedTab === 'character' ? (
            <div>
              {characters.map((character) => {
                const isInvited = invitedCharacters.includes(character.id);
                return (
                  <div
                    key={character.id}
                    onClick={() => handleItemClick(character)}
                    className={`flex items-center p-4 border-b border-gray-700 last:border-b-0 ${
                      isInvited
                        ? 'bg-gray-700 cursor-not-allowed opacity-50'
                        : 'hover:bg-gray-800 cursor-pointer'
                    }`}
                  >
                  {/* 프로필 이미지 */}
                  <div className="w-10 h-10 rounded-full bg-purple-200 flex-shrink-0 mr-4 overflow-hidden">
                    <img
                      src={character.profileImage}
                      alt={character.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/images/프로필_탄지로.png';
                      }}
                    />
                  </div>

                  {/* 텍스트 콘텐츠 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="text-white text-base font-normal leading-6 mb-1">
                        {character.name}
                      </h3>
                      {isInvited && (
                        <span className="text-xs text-gray-400 bg-gray-600 px-2 py-1 rounded-full">
                          참여중
                        </span>
                      )}
                    </div>
                    <p className="text-white text-sm leading-5 opacity-90 truncate">
                      {character.description}
                    </p>
                  </div>
                </div>
                );
              })}
            </div>
          ) : (
            <div>
              {friends.map((friend) => (
                <div
                  key={friend.id}
                  onClick={() => handleItemClick(friend)}
                  className="flex items-center p-4 hover:bg-gray-800 cursor-pointer border-b border-gray-700 last:border-b-0"
                >
                  {/* 프로필 이미지 */}
                  <div className="w-10 h-10 rounded-full bg-purple-200 flex-shrink-0 mr-4 overflow-hidden">
                    <img
                      src={friend.profileImage}
                      alt={friend.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/images/프로필_탄지로.png';
                      }}
                    />
                  </div>

                  {/* 텍스트 콘텐츠 */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-white text-base font-normal leading-6 mb-1">
                      {friend.name}
                    </h3>
                    <p className="text-white text-sm leading-5 opacity-90 truncate">
                      {friend.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 닫기 버튼 (선택적) */}
        <div className="bg-gray-900 p-4">
          <button
            onClick={onClose}
            className="w-full py-2 text-white text-sm hover:bg-gray-800 rounded-lg transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}