import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ChatHeader from '@/components/ChatHeader';
import LoginModal from '@/components/LoginModal';
import AllImagesModal from '@/components/AllImagesModal';
import { useApp } from '@/contexts/AppContext';
import { apiClient } from '@/services/api';

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

interface ImageAsset {
  image_id: string;
  image_path: string;
  image_name: string;
  image_type: string;
  index_number: number;
  description: string;
  tags: string[];
  scenario_id: string;
  is_unlocked?: boolean;
  unlocked_at?: string;
}

interface GalleryStats {
  total_images: number;
  unlocked_images: number;
  unlock_percentage: number;
}

export default function MyGalleryPage() {
  const { toggleSidebar, openSettings, isLoggedIn, openLoginModal } = useApp();

  const [unlockedImages, setUnlockedImages] = useState<ImageAsset[]>([]);
  const [stats, setStats] = useState<GalleryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAllImagesModal, setShowAllImagesModal] = useState(false);

  // Load unlocked images and stats
  useEffect(() => {
    if (isLoggedIn) {
      loadGalleryData();
    } else {
      setLoading(false);
    }
  }, [isLoggedIn]);

  const loadGalleryData = async () => {
    setLoading(true);
    try {
      // Load unlocked images (limited to first 6 for preview)
      const imagesData = await apiClient.getUnlockedImages();
      setUnlockedImages(imagesData.images.slice(0, 6));

      // Load stats
      const statsData = await apiClient.getGalleryStats();
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load gallery data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Authentication guard
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="나의 갤러리"
          showBackButton={true}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center bg-white bg-opacity-90 p-8 rounded-xl shadow-xl max-w-md">
              <div className="text-6xl mb-6">🔐</div>
              <h1 className="text-3xl font-bold mb-4 text-gray-800">로그인이 필요합니다</h1>
              <p className="text-gray-600 mb-6">
                갤러리를 보려면 로그인해주세요.
              </p>
              <button
                onClick={openLoginModal}
                className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                로그인하기
              </button>
            </div>
          </div>
        </main>
        <LoginModal />
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <ChatHeader
          onToggleSidebar={toggleSidebar}
          onOpenSettings={openSettings}
          title="나의 갤러리"
          showBackButton={true}
        />
        <main className="relative" style={{ height: 'calc(100vh - 64px)' }}>
          <div className="relative z-10 flex items-center justify-center h-full">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
              <p className="mt-4 text-gray-600">갤러리를 불러오는 중...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50">
      <ChatHeader
        onToggleSidebar={toggleSidebar}
        onOpenSettings={openSettings}
        title="나의 갤러리"
        showBackButton={true}
      />

      <main className="container mx-auto px-4 py-8" style={{ minHeight: 'calc(100vh - 64px)' }}>
        {/* Gallery Stats */}
        {stats && (
          <div className="bg-white rounded-xl shadow-md p-6 mb-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">수집 현황</h2>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-purple-600">{stats.unlocked_images}</div>
                <div className="text-sm text-gray-600 mt-1">획득한 이미지</div>
              </div>
              <div className="bg-pink-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-pink-600">{stats.total_images}</div>
                <div className="text-sm text-gray-600 mt-1">전체 이미지</div>
              </div>
              <div className="bg-indigo-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-indigo-600">{stats.unlock_percentage.toFixed(1)}%</div>
                <div className="text-sm text-gray-600 mt-1">수집률</div>
              </div>
            </div>
          </div>
        )}

        {/* Unlocked Images Preview */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-800">획득한 이미지</h2>
            <button
              onClick={() => setShowAllImagesModal(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
            >
              모든 전리품 확인하기
            </button>
          </div>

          {unlockedImages.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🎴</div>
              <p className="text-gray-600">아직 획득한 이미지가 없습니다.</p>
              <p className="text-sm text-gray-500 mt-2">
                스토리를 진행하면서 이미지를 수집해보세요!
              </p>
              <Link
                to="/"
                className="inline-block mt-4 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                스토리 시작하기
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {unlockedImages.map((image) => (
                <div
                  key={image.image_id}
                  className="group relative bg-gray-100 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer aspect-video"
                >
                  <img
                    src={`${CDN_URL}/${image.image_path}`}
                    alt={image.image_name || `Image ${image.index_number}`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `${CDN_URL}/placeholder.png`;
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="absolute bottom-0 left-0 right-0 p-3">
                      <p className="text-white text-sm font-medium truncate">
                        {image.image_name || `이미지 #${image.index_number}`}
                      </p>
                      {image.unlocked_at && (
                        <p className="text-white/80 text-xs mt-1">
                          획득: {new Date(image.unlocked_at).toLocaleDateString('ko-KR')}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-4">
          <Link
            to="/"
            className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow text-center"
          >
            <div className="text-4xl mb-2">🏠</div>
            <h3 className="text-lg font-semibold text-gray-800">홈으로</h3>
            <p className="text-sm text-gray-600 mt-1">스토리 선택하기</p>
          </Link>
          <button
            onClick={() => setShowAllImagesModal(true)}
            className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow text-center"
          >
            <div className="text-4xl mb-2">🎨</div>
            <h3 className="text-lg font-semibold text-gray-800">전체 보기</h3>
            <p className="text-sm text-gray-600 mt-1">모든 이미지 확인</p>
          </button>
        </div>
      </main>

      <LoginModal />

      {/* All Images Modal */}
      {showAllImagesModal && (
        <AllImagesModal onClose={() => setShowAllImagesModal(false)} />
      )}
    </div>
  );
}
