import { useState, useEffect } from 'react'
import { Wifi } from 'lucide-react'

export default function LiveIndicator({ isLive = true, lastUpdate }: { isLive?: boolean, lastUpdate?: Date }) {
  const [pulse, setPulse] = useState(false)

  useEffect(() => {
    if (isLive) {
      const interval = setInterval(() => {
        setPulse(prev => !prev)
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [isLive])

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-white/80 backdrop-blur border border-gray-200 rounded-lg">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5">
          <Wifi className={`w-3.5 h-3.5 ${isLive ? 'text-green-500' : 'text-gray-400'}`} />
          <span className={`text-xs font-medium ${isLive ? 'text-green-600' : 'text-gray-500'}`}>
            LIVE
          </span>
          {isLive && (
            <div className={`w-1.5 h-1.5 bg-green-500 rounded-full ${pulse ? 'animate-pulse' : ''}`} />
          )}
        </div>
        {lastUpdate && (
          <span className="text-xs text-gray-500 border-l border-gray-200 pl-2">
            {lastUpdate.toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
} 