import React, { useEffect, useState } from 'react'

export interface MemoryEvent {
  event_type: 'saved' | 'recalled'
  character_name: string
  memory_type: string
  memory_content: string
  importance: number
  count?: number
}

interface MemoryToastProps {
  event: MemoryEvent
  onClose: () => void
  duration?: number
}

const MemoryToast: React.FC<MemoryToastProps> = ({ event, onClose, duration = 5000 }) => {
  const [isVisible, setIsVisible] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)

  useEffect(() => {
    // Fade in animation
    setTimeout(() => setIsVisible(true), 10)

    // Auto close after duration
    const timer = setTimeout(() => {
      setIsLeaving(true)
      setTimeout(onClose, 300) // Wait for fade-out animation
    }, duration)

    return () => clearTimeout(timer)
  }, [duration, onClose])

  const getEventIcon = () => {
    if (event.event_type === 'saved') {
      return '💾'
    }
    return '🧠'
  }

  const getEventMessage = () => {
    if (event.event_type === 'saved') {
      return `${event.character_name}가 기억을 저장했습니다`
    }
    return `${event.character_name}가 기억을 떠올렸습니다`
  }

  const getMemoryTypeLabel = () => {
    const typeLabels: Record<string, string> = {
      fact: '사실',
      event: '사건',
      relationship: '관계',
      preference: '선호'
    }
    return typeLabels[event.memory_type] || event.memory_type
  }

  const getImportanceColor = () => {
    if (event.importance >= 0.8) return 'text-red-400'
    if (event.importance >= 0.6) return 'text-yellow-400'
    return 'text-gray-400'
  }

  return (
    <div
      className={`
        transform transition-all duration-300 ease-out
        ${isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        bg-gray-800 bg-opacity-95 backdrop-blur-sm
        rounded-lg shadow-2xl p-4 mb-3
        border border-gray-700
        min-w-[320px] max-w-[400px]
      `}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="text-2xl flex-shrink-0 mt-0.5">
          {getEventIcon()}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white font-medium text-sm">
              {getEventMessage()}
            </span>
            <button
              onClick={() => {
                setIsLeaving(true)
                setTimeout(onClose, 300)
              }}
              className="ml-auto text-gray-400 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Memory Type Badge */}
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-block px-2 py-0.5 rounded text-xs bg-blue-900 bg-opacity-50 text-blue-300 border border-blue-700">
              {getMemoryTypeLabel()}
            </span>
            <span className={`text-xs ${getImportanceColor()}`}>
              중요도: {(event.importance * 100).toFixed(0)}%
            </span>
          </div>

          {/* Memory Content */}
          <div className="text-gray-300 text-sm leading-relaxed">
            "{event.memory_content}"
          </div>
        </div>
      </div>
    </div>
  )
}

export default MemoryToast
