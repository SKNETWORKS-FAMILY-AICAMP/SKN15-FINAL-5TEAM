
import { useState } from 'react';

interface LeftSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export default function LeftSidebar({ isOpen, onToggle }: LeftSidebarProps) {
  return (
    <>
      {/* 사이드바 토글 버튼 */}
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 bg-purple-600 text-white p-2 rounded-full shadow-lg hover:bg-purple-700 transition-colors"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* 사이드바 오버레이 */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={onToggle}
        />
      )}

      {/* 사이드바 */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-40 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* 헤더 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-purple-600 text-white">
            <h2 className="text-lg font-bold">⚔️ 귀살대 메뉴</h2>
            <button
              onClick={onToggle}
              className="text-white hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 메뉴 항목들 */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-2">
              <div className="border-b border-gray-200 pb-4 mb-4">
                <h3 className="font-semibold text-gray-800 mb-3">🏠 메인 메뉴</h3>
                <ul className="space-y-2">
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-purple-50 transition-colors">
                      💬 채팅방
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-purple-50 transition-colors">
                      👥 귀살대 목록
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-purple-50 transition-colors">
                      📚 호흡법 가이드
                    </button>
                  </li>
                </ul>
              </div>

              <div className="border-b border-gray-200 pb-4 mb-4">
                <h3 className="font-semibold text-gray-800 mb-3">🗡️ 호흡법</h3>
                <ul className="space-y-2">
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-blue-50 transition-colors text-blue-600">
                      🌊 물의 호흡
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-yellow-50 transition-colors text-yellow-600">
                      ⚡ 번개의 호흡
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-red-50 transition-colors text-red-600">
                      🔥 염의 호흡
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-green-50 transition-colors text-green-600">
                      🌪️ 바람의 호흡
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-purple-50 transition-colors text-purple-600">
                      🎵 음의 호흡
                    </button>
                  </li>
                </ul>
              </div>

              <div>
                <h3 className="font-semibold text-gray-800 mb-3">👹 도깨비 정보</h3>
                <ul className="space-y-2">
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-red-50 transition-colors">
                      🌙 십이귀월
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-red-50 transition-colors">
                      👑 무잔 정보
                    </button>
                  </li>
                  <li>
                    <button className="w-full text-left px-3 py-2 rounded hover:bg-red-50 transition-colors">
                      ⚔️ 도깨비 대처법
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* 푸터 */}
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <p className="text-xs text-gray-500 text-center">
              귀멸의 칼날 - Kimetsu Chat<br />
              ⚔️ 귀살대와 함께하는 대화
            </p>
          </div>
        </div>
      </div>
    </>
  );
}