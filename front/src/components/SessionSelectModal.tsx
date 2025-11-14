import { useState, useEffect } from 'react'
import { RecentSession, apiClient } from '@/services/api'
import { normalizeScenarioId } from '@/utils/scenario'

interface SessionSelectModalProps {
  isOpen: boolean
  onClose: () => void
  scenarioId: string
  onSelectSession: (sessionId: string | null) => void // null = 새 세션 시작
}

export default function SessionSelectModal({
  isOpen,
  onClose,
  scenarioId,
  onSelectSession
}: SessionSelectModalProps) {
  const [sessions, setSessions] = useState<RecentSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen) {
      loadSessions()
    }
  }, [isOpen, scenarioId])

  const loadSessions = async () => {
    setLoading(true)
    try {
      const normalizedId = normalizeScenarioId(scenarioId)
      const data = await apiClient.getUserSessions(normalizedId, 10)
      setSessions(data)
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSession = (sessionId: string | null) => {
    onSelectSession(sessionId)
    onClose()
  }

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return '알 수 없음'
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(hours / 24)

    if (hours < 1) return '방금 전'
    if (hours < 24) return `${hours}시간 전`
    if (days < 7) return `${days}일 전`
    return date.toLocaleDateString('ko-KR')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-800">세션 선택</h2>
          <p className="text-sm text-gray-600 mt-1">
            이전 대화를 이어서 하시겠습니까?
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
              <span className="ml-3 text-gray-500">세션 불러오는 중...</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">이전 세션이 없습니다.</p>
              <button
                onClick={() => handleSelectSession(null)}
                className="px-6 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600 transition-colors"
              >
                새 대화 시작하기
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {/* New Session Option */}
              <button
                onClick={() => handleSelectSession(null)}
                className="w-full p-4 border-2 border-dashed border-purple-300 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <p className="font-semibold text-gray-800 group-hover:text-purple-600 transition-colors">
                      새로운 대화 시작
                    </p>
                    <p className="text-sm text-gray-500">처음부터 다시 시작합니다</p>
                  </div>
                </div>
              </button>

              {/* Existing Sessions */}
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => handleSelectSession(session.session_id)}
                  className="w-full p-4 border border-gray-200 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-all text-left"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-semibold text-gray-800 truncate">
                          {session.conversation_summary || `${session.turn_count || 0}개의 대화`}
                        </p>
                        <span className="text-xs text-gray-500 flex-shrink-0">
                          {formatDate(session.updated_at)}
                        </span>
                      </div>
                      {session.last_message_content && (
                        <p className="text-sm text-gray-600 truncate mb-2">
                          {session.last_message_speaker}: {session.last_message_content}
                        </p>
                      )}
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="px-2 py-1 bg-gray-100 rounded">
                          대화 {session.turn_count || 0}회
                        </span>
                        {session.current_stage && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                            {session.current_stage}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="w-full py-3 px-4 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  )
}
