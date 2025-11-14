import React from 'react'
import MemoryToast, { MemoryEvent } from './MemoryToast'

interface MemoryToastContainerProps {
  events: Array<MemoryEvent & { id: string }>
  onRemove: (id: string) => void
}

const MemoryToastContainer: React.FC<MemoryToastContainerProps> = ({ events, onRemove }) => {
  if (events.length === 0) return null

  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col items-end pointer-events-none">
      <div className="pointer-events-auto">
        {events.map((event) => (
          <MemoryToast
            key={event.id}
            event={event}
            onClose={() => onRemove(event.id)}
          />
        ))}
      </div>
    </div>
  )
}

export default MemoryToastContainer
