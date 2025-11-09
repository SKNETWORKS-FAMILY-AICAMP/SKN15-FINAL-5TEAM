import { useEffect, useState } from 'react';
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
  is_unlocked: boolean;
  unlocked_at?: string;
}

interface AllImagesModalProps {
  onClose: () => void;
}

export default function AllImagesModal({ onClose }: AllImagesModalProps) {
  const [unlockedImages, setUnlockedImages] = useState<ImageAsset[]>([]);
  const [lockedImages, setLockedImages] = useState<ImageAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'unlocked' | 'locked'>('unlocked');

  useEffect(() => {
    loadAllImages();
  }, []);

  const loadAllImages = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getAllImagesWithStatus();
      setUnlockedImages(data.unlocked_images);
      setLockedImages(data.locked_images);
    } catch (error) {
      console.error('Failed to load all images:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-800">모든 전리품</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="닫기"
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('unlocked')}
            className={`flex-1 px-6 py-4 font-semibold transition-colors ${
              activeTab === 'unlocked'
                ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            }`}
          >
            획득 ({unlockedImages.length})
          </button>
          <button
            onClick={() => setActiveTab('locked')}
            className={`flex-1 px-6 py-4 font-semibold transition-colors ${
              activeTab === 'locked'
                ? 'text-gray-600 border-b-2 border-gray-600 bg-gray-50'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            }`}
          >
            미획득 ({lockedImages.length})
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
                <p className="mt-4 text-gray-600">이미지를 불러오는 중...</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {activeTab === 'unlocked' ? (
                unlockedImages.length === 0 ? (
                  <div className="col-span-full text-center py-12">
                    <div className="text-6xl mb-4">🎴</div>
                    <p className="text-gray-600">아직 획득한 이미지가 없습니다.</p>
                  </div>
                ) : (
                  unlockedImages.map((image) => (
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
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="absolute bottom-0 left-0 right-0 p-2">
                          <p className="text-white text-xs font-medium truncate">
                            {image.image_name || `#${image.index_number}`}
                          </p>
                          {image.description && (
                            <p className="text-white/80 text-xs truncate mt-1">
                              {image.description}
                            </p>
                          )}
                          {image.unlocked_at && (
                            <p className="text-white/70 text-xs mt-1">
                              {new Date(image.unlocked_at).toLocaleDateString('ko-KR')}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )
              ) : (
                lockedImages.length === 0 ? (
                  <div className="col-span-full text-center py-12">
                    <div className="text-6xl mb-4">🎉</div>
                    <p className="text-gray-600">모든 이미지를 획득했습니다!</p>
                  </div>
                ) : (
                  lockedImages.map((image) => (
                    <div
                      key={image.image_id}
                      className="group relative bg-gray-900 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer aspect-video"
                    >
                      {/* Locked overlay */}
                      <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                        <div className="text-center">
                          <svg
                            className="w-12 h-12 text-gray-600 mx-auto mb-2"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                            />
                          </svg>
                          <p className="text-gray-500 text-xs">잠김</p>
                        </div>
                      </div>
                      {/* Hover info */}
                      <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-end">
                        <div className="w-full p-2">
                          <p className="text-white text-xs font-medium truncate">
                            {image.image_name || `미지의 이미지 #${image.index_number}`}
                          </p>
                          {image.description && (
                            <p className="text-white/80 text-xs truncate mt-1">
                              {image.description}
                            </p>
                          )}
                          <p className="text-white/70 text-xs mt-1">
                            스토리를 진행하여 획득하세요
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            총 <span className="font-semibold text-purple-600">{unlockedImages.length + lockedImages.length}</span>개의 이미지 중{' '}
            <span className="font-semibold text-purple-600">{unlockedImages.length}</span>개 획득
          </div>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
