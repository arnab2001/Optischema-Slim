import { useState, useEffect } from 'react'

export default function SystemStatus() {
  const [status, setStatus] = useState<'healthy' | 'warning' | 'error'>('healthy')
  const [lastCheck, setLastCheck] = useState<Date>(new Date())

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('/api/health', { headers });
      if (response.ok) {
        setStatus('healthy')
      } else {
        setStatus('warning')
      }
    } catch (error) {
      setStatus('error')
    }
    setLastCheck(new Date())
  }

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500'
      case 'warning':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'healthy':
        return 'System Healthy'
      case 'warning':
        return 'System Warning'
      case 'error':
        return 'System Error'
    }
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-white/80 backdrop-blur border border-gray-200 rounded-lg">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span className="text-xs font-medium text-gray-900">{getStatusText()}</span>
        </div>
        <span className="text-xs text-gray-500 border-l border-gray-200 pl-2">
          {lastCheck.toLocaleTimeString()}
        </span>
      </div>
    </div>
  )
} 