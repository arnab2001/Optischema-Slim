import { useState, useEffect } from 'react'
import { Database, Settings, History, LogOut, CheckCircle, XCircle, Loader, ChevronDown, ChevronUp, AlertTriangle, Activity, RefreshCw, Star, Trash2 } from 'lucide-react'
import { SaveConnectionDialog } from './SaveConnectionDialog'
import { useConnectionStore } from '@/store/connectionStore'

interface ConnectionConfig {
  host: string
  port: string
  database: string
  username?: string
  user?: string
  password: string
  ssl?: boolean
  connection_string?: string
}

interface ConnectionHistory {
  config: ConnectionConfig
  connected_at: string
  status: string
}

interface ConnectionStatus {
  connected: boolean
  current_config: ConnectionConfig | null
  saved_connection_id?: number | null
  connection_history: ConnectionHistory[]
}

export default function DatabaseSwitcher() {
  const { syncStatus } = useConnectionStore()
  const [isOpen, setIsOpen] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [newConnection, setNewConnection] = useState<ConnectionConfig>({
    host: 'localhost',
    port: '5432',
    database: 'postgres',
    username: 'postgres',
    password: '',
    ssl: false
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    details?: any
  } | null>(null)
  const [pgStatInfo, setPgStatInfo] = useState<any>(null)
  const [showPgStatManager, setShowPgStatManager] = useState(false)
  const [savedConnections, setSavedConnections] = useState<any[]>([])
  const [showSavedConnections, setShowSavedConnections] = useState(true) // Expanded by default
  const [showSaveDialog, setShowSaveDialog] = useState(false)

  // Fetch pg_stat_statements info
  const fetchPgStatInfo = async () => {
    try {
      const response = await fetch('/api/connection/pg-stat-info')
      if (response.ok) {
        const data = await response.json()
        setPgStatInfo(data)
      }
    } catch (error) {
      console.error('Failed to fetch pg_stat_statements info:', error)
    }
  }

  // Fetch current connection status
  const fetchConnectionStatus = async () => {
    try {
      // Sync with global store
      await syncStatus()

      const response = await fetch('/api/connection/status')
      if (response.ok) {
        const status = await response.json()
        setConnectionStatus(status)
      }
    } catch (error) {
      console.error('Failed to fetch connection status:', error)
    }
  }

  // Fetch saved connections
  const fetchSavedConnections = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
      const response = await fetch(`${apiUrl}/api/connection/saved`)
      if (response.ok) {
        const data = await response.json()
        const connections = data.connections || []
        console.log('Fetched saved connections:', connections.length, connections)
        setSavedConnections(connections)
        // Auto-expand if there are saved connections
        if (connections.length > 0) {
          setShowSavedConnections(true)
        }
      } else {
        const errorText = await response.text()
        console.error('Failed to fetch saved connections:', response.status, response.statusText, errorText)
      }
    } catch (error) {
      console.error('Failed to fetch saved connections:', error)
    }
  }

  useEffect(() => {
    fetchConnectionStatus()
    fetchPgStatInfo()
    fetchSavedConnections()

    // Refresh saved connections when dialog opens
    if (isOpen) {
      fetchSavedConnections()
    }
  }, [isOpen])

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)

    try {
      const response = await fetch('/api/connection/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConnection),
      })

      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test connection'
      })
    } finally {
      setTesting(false)
    }
  }

  const switchConnection = async () => {
    setLoading(true)

    try {
      console.log('Switching to connection:', newConnection)

      const response = await fetch('/api/connection/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConnection),
      })

      console.log('Switch response status:', response.status)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      console.log('Switch response:', result)

      if (result.success) {
        console.log('Switch successful, refreshing connection status...')

        // Refresh connection status
        await fetchConnectionStatus()
        setIsOpen(false)
        setTestResult(null)

        // Show success message and reload the page
        console.log('Successfully connected to new database! Reloading dashboard...')

        // Reload the page to refresh all data
        try {
          window.location.reload()
        } catch (reloadError) {
          console.error('Failed to reload page:', reloadError)
          // Fallback: redirect to dashboard
          window.location.href = '/dashboard'
        }
      } else {
        console.log('Switch failed:', result)
        setTestResult(result)
      }
    } catch (error) {
      console.error('Switch connection error:', error)
      setTestResult({
        success: false,
        message: `Failed to switch connection: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    } finally {
      setLoading(false)
    }
  }

  const disconnect = async () => {
    setLoading(true)

    try {
      const response = await fetch('/api/connection/disconnect', {
        method: 'POST',
      })

      if (response.ok) {
        await fetchConnectionStatus()
        // Reload the page
        window.location.reload()
      }
    } catch (error) {
      console.error('Failed to disconnect:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadFromHistory = (historyItem: ConnectionHistory) => {
    setNewConnection(historyItem.config)
    setTestResult(null)
  }

  const handleSaveCurrentConnection = async (name: string) => {
    if (!connectionStatus || !connectionStatus.current_config) {
      throw new Error("No active connection to save")
    }

    const config = connectionStatus.current_config

    // Extract connection details from connection_string (most reliable)
    let extractedHost = config.host
    let extractedPort = config.port || '5432'
    let extractedUser = config.username || config.user
    let extractedDb = config.database
    let extractedPassword = ''
    let extractedSsl = config.ssl || false

    if (config.connection_string) {
      try {
        // Normalize postgres:// to postgresql:// for URL parsing
        const normalizedStr = config.connection_string.replace(/^postgres:\/\//, 'postgresql://')
        const url = new URL(normalizedStr)

        extractedHost = url.hostname || extractedHost
        extractedPort = url.port || extractedPort
        extractedUser = url.username ? decodeURIComponent(url.username) : extractedUser
        extractedPassword = url.password ? decodeURIComponent(url.password) : ''
        extractedDb = url.pathname ? url.pathname.replace(/^\//, '') : extractedDb
        extractedSsl = normalizedStr.includes('sslmode=require') || extractedSsl

        console.log('Extracted from connection string:', {
          host: extractedHost,
          port: extractedPort,
          user: extractedUser,
          password: extractedPassword ? '***' : '(empty)',
          database: extractedDb,
          ssl: extractedSsl
        })
      } catch (e) {
        console.warn('Could not parse connection string:', e)
      }
    }

    if (!extractedPassword) {
      throw new Error("Could not extract password from connection. Please reconnect with your credentials.")
    }

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
    const savePayload = {
      name,
      host: extractedHost,
      port: extractedPort,
      database: extractedDb,
      username: extractedUser,
      password: extractedPassword,
      ssl: extractedSsl
    }

    console.log('Saving connection:', { ...savePayload, password: '***' })

    const response = await fetch(`${apiUrl}/api/connection/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(savePayload)
    })

    if (!response.ok) {
      let errorMessage = 'Failed to save connection'
      try {
        const error = await response.json()
        errorMessage = (error.detail && typeof error.detail === 'string') ? error.detail :
          (error.message && typeof error.message === 'string') ? error.message :
            (error.error && typeof error.error === 'string') ? error.error : errorMessage
      } catch (e) {
        errorMessage = response.statusText || errorMessage
      }
      throw new Error(errorMessage)
    }

    const result = await response.json()
    console.log('Connection saved successfully:', result)

    // Refresh saved connections and connection status
    await Promise.all([
      fetchSavedConnections(),
      fetchConnectionStatus()
    ])

    // Show success message
    alert(`Connection "${name}" saved successfully!`)
  }

  const handleSwitchToSaved = async (connectionId: number) => {
    if (loading) return // Prevent double-clicks

    setLoading(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
      console.log('Switching to connection ID:', connectionId)

      const response = await fetch(`${apiUrl}/api/connection/switch/${connectionId}`, {
        method: 'POST'
      })

      if (!response.ok) {
        let errorMessage = 'Failed to switch connection'
        try {
          const error = await response.json()
          errorMessage = (error.detail && typeof error.detail === 'string') ? error.detail :
            (error.message && typeof error.message === 'string') ? error.message :
              (error.error && typeof error.error === 'string') ? error.error : errorMessage
        } catch (e) {
          errorMessage = response.statusText || errorMessage
        }
        throw new Error(errorMessage)
      }

      const result = await response.json()
      console.log('Switch successful:', result)

      // Refresh connection status and saved connections
      await Promise.all([
        fetchConnectionStatus(),
        fetchSavedConnections()
      ])

      setIsOpen(false)

      // Reload page to refresh all data
      setTimeout(() => {
        window.location.reload()
      }, 500) // Small delay to show success
    } catch (error) {
      console.error('Failed to switch connection:', error)
      alert(error instanceof Error ? error.message : 'Failed to switch connection')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSaved = async (connectionId: number) => {
    if (!confirm('Are you sure you want to delete this saved connection?')) {
      return
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
      const response = await fetch(`${apiUrl}/api/connection/saved/${connectionId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        let errorMessage = 'Failed to delete connection'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || error.error || errorMessage
        } catch (e) {
          errorMessage = response.statusText || errorMessage
        }
        throw new Error(errorMessage)
      }

      await fetchSavedConnections()
      // If deleted connection was the active one, refresh status
      if (connectionStatus && connectionStatus.saved_connection_id === connectionId) {
        await fetchConnectionStatus()
      }
    } catch (error) {
      console.error('Failed to delete connection:', error)
      alert(error instanceof Error ? error.message : 'Failed to delete connection')
    }
  }

  const handleEnablePgStat = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/connection/enable-pg-stat', {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        alert(result.message)
        await fetchPgStatInfo() // Refresh info
      } else {
        const error = await response.json()
        alert(`Failed to enable pg_stat_statements: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error enabling pg_stat_statements:', error)
      alert('Error enabling pg_stat_statements')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPgStat = async () => {
    if (!confirm('Are you sure you want to reset pg_stat_statements? This will clear all collected query statistics.')) {
      return
    }

    try {
      setLoading(true)
      const response = await fetch('/api/connection/reset-pg-stat', {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        alert(result.message)
        await fetchPgStatInfo() // Refresh info
      } else {
        const error = await response.json()
        alert(`Failed to reset pg_stat_statements: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error resetting pg_stat_statements:', error)
      alert('Error resetting pg_stat_statements')
    } finally {
      setLoading(false)
    }
  }

  if (!connectionStatus) {
    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <Loader className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading connection status...</span>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Connection Status Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2.5 text-sm bg-white/80 backdrop-blur border border-gray-200 rounded-lg hover:bg-white hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all duration-200 shadow-sm"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-gray-600" />
          {connectionStatus.connected && connectionStatus.current_config ? (
            <div className="text-left">
              <div className="font-medium text-gray-900 truncate max-w-48">
                {connectionStatus.current_config.host}
              </div>
              <div className="text-xs text-gray-500">
                {connectionStatus.current_config.database}
              </div>
            </div>
          ) : (
            <span className="font-medium text-gray-600">Not Connected</span>
          )}
        </div>

        {connectionStatus.connected && (
          <div className="flex items-center gap-1.5 ml-2 pl-2 border-l border-gray-200">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-xs font-medium text-green-600">Connected</span>
          </div>
        )}

        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-400 ml-1" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400 ml-1" />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white/95 backdrop-blur border border-gray-200 rounded-lg shadow-xl z-50">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Database Connection</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Current Connection Status */}
            {connectionStatus.connected && connectionStatus.current_config && (
              <div className="mb-4 p-3 bg-green-50/80 border border-green-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium text-green-800">Currently Connected</span>
                    {connectionStatus.saved_connection_id && (
                      <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" title="Saved connection" />
                    )}
                  </div>
                  {!connectionStatus.saved_connection_id && (
                    <button
                      onClick={() => setShowSaveDialog(true)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Save
                    </button>
                  )}
                </div>
                <div className="text-sm text-green-700 space-y-1">
                  <div><strong>Host:</strong> {connectionStatus.current_config.host}:{connectionStatus.current_config.port}</div>
                  <div><strong>Database:</strong> {connectionStatus.current_config.database}</div>
                  <div><strong>User:</strong> {connectionStatus.current_config.user || connectionStatus.current_config.username}</div>
                </div>
                <button
                  onClick={disconnect}
                  disabled={loading}
                  className="mt-3 flex items-center space-x-1 text-sm text-red-600 hover:text-red-800 disabled:opacity-50 transition-colors"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Disconnect</span>
                </button>
              </div>
            )}

            {/* Saved Connections - Always show if there are any */}
            <div className="mb-4 border-t border-gray-200 pt-3">
              <div className="flex items-center justify-between mb-2">
                <button
                  onClick={() => setShowSavedConnections(!showSavedConnections)}
                  className="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900 w-full text-left"
                >
                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  <span>Saved Connections ({savedConnections.length})</span>
                  {showSavedConnections ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />}
                </button>
              </div>

              {showSavedConnections && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {savedConnections.length === 0 ? (
                    <div className="text-xs text-gray-500 text-center py-4">
                      No saved connections. Connect to a database and click "Save" to add one.
                    </div>
                  ) : (
                    savedConnections.map((conn) => (
                      <div
                        key={conn.id}
                        className={`p-3 rounded-lg border transition-colors ${connectionStatus.saved_connection_id === conn.id
                          ? 'bg-blue-50 border-blue-300 shadow-sm'
                          : 'bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
                          }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <div className="font-semibold text-sm text-gray-900 truncate">{conn.name}</div>
                              {connectionStatus.saved_connection_id === conn.id && (
                                <span className="px-1.5 py-0.5 text-xs font-medium bg-blue-200 text-blue-800 rounded">
                                  Active
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-gray-600 space-y-0.5">
                              <div className="font-mono truncate">{conn.host}:{conn.port}</div>
                              <div>Database: <span className="font-medium">{conn.database}</span></div>
                              <div>User: <span className="font-medium">{conn.username}</span></div>
                              {conn.last_used_at && (
                                <div className="text-gray-500 mt-1">
                                  Last used: {new Date(conn.last_used_at).toLocaleString()}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            <button
                              onClick={() => handleSwitchToSaved(conn.id)}
                              disabled={loading || connectionStatus.saved_connection_id === conn.id}
                              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${connectionStatus.saved_connection_id === conn.id
                                ? 'bg-gray-200 text-gray-600 cursor-not-allowed'
                                : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
                                }`}
                              title={connectionStatus.saved_connection_id === conn.id ? "Currently connected" : "Connect to this database"}
                            >
                              {connectionStatus.saved_connection_id === conn.id ? 'Active' : 'Connect'}
                            </button>
                            <button
                              onClick={() => handleDeleteSaved(conn.id)}
                              disabled={loading}
                              className="p-1.5 text-red-600 hover:text-red-800 hover:bg-red-50 rounded disabled:opacity-50 transition-colors"
                              title="Delete saved connection"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* pg_stat_statements Manager */}
            {connectionStatus.connected && (
              <div className="border-t border-gray-200 pt-3 mb-4">
                <button
                  onClick={() => setShowPgStatManager(!showPgStatManager)}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800 w-full"
                >
                  <Activity className="w-4 h-4" />
                  <span>pg_stat_statements Manager</span>
                  {showPgStatManager ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />}
                </button>

                {showPgStatManager && (
                  <div className="mt-3 bg-gray-50 rounded-lg p-3">
                    {pgStatInfo ? (
                      <div className="space-y-3">
                        {/* Status */}
                        <div className="flex items-center space-x-2">
                          {pgStatInfo.enabled ? (
                            <>
                              <CheckCircle className="w-4 h-4 text-green-600" />
                              <span className="text-sm font-medium text-green-800">Enabled</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-4 h-4 text-red-600" />
                              <span className="text-sm font-medium text-red-800">Disabled</span>
                            </>
                          )}
                        </div>

                        {/* Statistics */}
                        {pgStatInfo.enabled && (
                          <div className="text-xs text-gray-600 space-y-1">
                            <div><strong>Total Queries:</strong> {pgStatInfo.total_queries?.toLocaleString() || 'Unknown'}</div>
                            <div><strong>Max Statements:</strong> {pgStatInfo.max_statements?.toLocaleString() || 'Unknown'}</div>
                            {pgStatInfo.large_dataset && (
                              <div className="flex items-center space-x-1 text-amber-600">
                                <AlertTriangle className="w-3 h-3" />
                                <span>Large dataset detected</span>
                              </div>
                            )}
                            {pgStatInfo.memory_warning && (
                              <div className="flex items-center space-x-1 text-red-600">
                                <AlertTriangle className="w-3 h-3" />
                                <span>High memory usage</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex space-x-2 pt-2">
                          {!pgStatInfo.enabled && (
                            <button
                              onClick={handleEnablePgStat}
                              disabled={loading}
                              className="flex items-center space-x-1 px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50"
                            >
                              <CheckCircle className="w-3 h-3" />
                              <span>Enable</span>
                            </button>
                          )}

                          <button
                            onClick={() => fetchPgStatInfo()}
                            disabled={loading}
                            className="flex items-center space-x-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                          >
                            <RefreshCw className="w-3 h-3" />
                            <span>Refresh</span>
                          </button>

                          {pgStatInfo.enabled && (
                            <button
                              onClick={handleResetPgStat}
                              disabled={loading}
                              className="flex items-center space-x-1 px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
                            >
                              <RefreshCw className="w-3 h-3" />
                              <span>Reset Stats</span>
                            </button>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <Loader className="w-4 h-4 animate-spin" />
                        <span className="text-sm text-gray-600">Loading pg_stat_statements info...</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Connection History */}
            {connectionStatus.connection_history.length > 0 && (
              <div className="mb-4">
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  <History className="w-4 h-4" />
                  <span>Connection History</span>
                  {showHistory ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {showHistory && (
                  <div className="mt-2 space-y-2 max-h-32 overflow-y-auto">
                    {connectionStatus.connection_history.map((item, index) => (
                      <button
                        key={index}
                        onClick={() => loadFromHistory(item)}
                        className="w-full text-left p-2 text-xs bg-gray-50 hover:bg-gray-100 rounded border"
                      >
                        <div className="font-medium">
                          {item.config.host}:{item.config.port}/{item.config.database}
                        </div>
                        <div className="text-gray-500">
                          {new Date(item.connected_at).toLocaleString()}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* New Connection Form */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-900">Connect to New Database</h4>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Host</label>
                  <input
                    type="text"
                    value={newConnection.host}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, host: e.target.value }))}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="localhost"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="text"
                    value={newConnection.port}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, port: e.target.value }))}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="5432"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Database</label>
                <input
                  type="text"
                  value={newConnection.database}
                  onChange={(e) => setNewConnection(prev => ({ ...prev, database: e.target.value }))}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="postgres"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={newConnection.username}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="postgres"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
                  <input
                    type="password"
                    value={newConnection.password}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="password"
                  />
                </div>
              </div>

              {/* SSL Option */}
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="ssl-toggle"
                  checked={newConnection.ssl || false}
                  onChange={(e) => setNewConnection(prev => ({ ...prev, ssl: e.target.checked }))}
                  className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
                <label htmlFor="ssl-toggle" className="text-xs font-medium text-gray-700">
                  Enable SSL connection
                </label>
              </div>

              {/* Test Result */}
              {testResult && (
                <div className={`p-4 rounded-lg border-2 ${testResult.success
                  ? 'bg-green-50 border-green-300 text-green-800'
                  : 'bg-red-50 border-red-300 text-red-800'
                  }`}>
                  <div className="flex items-center space-x-2 mb-3">
                    {testResult.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className="font-semibold text-lg">{testResult.success ? 'Connection Test Successful!' : 'Connection Test Failed'}</span>
                  </div>
                  <div className="text-sm mb-3 bg-white/50 p-3 rounded border">{testResult.message}</div>
                  {testResult.details && (
                    <div className="text-xs opacity-75 space-y-1 bg-white/30 p-2 rounded">
                      {testResult.details.version && <div><strong>Version:</strong> {testResult.details.version}</div>}
                      {testResult.details.pg_stat_statements_enabled !== undefined && (
                        <div><strong>pg_stat_statements:</strong> {testResult.details.pg_stat_statements_enabled ? 'Enabled' : 'Disabled'}</div>
                      )}
                    </div>
                  )}
                  {testResult.success && (
                    <div className="mt-3 p-3 bg-green-100 rounded border border-green-200">
                      <div className="flex items-center space-x-2 text-green-700">
                        <Database className="w-4 h-4" />
                        <span className="text-sm font-medium">Ready to Connect!</span>
                      </div>
                      <div className="text-xs text-green-600 mt-1">
                        Click the &quot;Connect&quot; button below to switch to this database.
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-2 pt-2">
                <button
                  onClick={testConnection}
                  disabled={testing}
                  className={`flex-1 flex items-center justify-center space-x-1 px-3 py-2 text-sm rounded transition-all duration-200 ${testing
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
                    }`}
                >
                  {testing ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Settings className="w-4 h-4" />
                  )}
                  <span>{testing ? 'Testing...' : 'Test Connection'}</span>
                </button>

                <button
                  onClick={switchConnection}
                  disabled={loading || !testResult?.success}
                  className={`flex-1 flex items-center justify-center space-x-1 px-3 py-2 text-sm rounded transition-all duration-200 ${testResult?.success
                    ? 'bg-green-600 text-white hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2'
                    : 'bg-gray-200 text-gray-500 cursor-not-allowed border border-gray-300'
                    }`}
                  title={!testResult?.success ? 'Test connection first' : 'Connect to this database'}
                >
                  {loading ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Database className="w-4 h-4" />
                  )}
                  <span>{loading ? 'Connecting...' : 'Connect'}</span>
                </button>
              </div>

              {/* Connection Status */}
              {testResult && (
                <div className="text-xs text-gray-600 mt-3 p-3 bg-gray-50 rounded border">
                  {testResult.success ? (
                    <div className="flex items-center space-x-1 text-green-600">
                      <CheckCircle className="w-3 h-3" />
                      <span>Connection test successful! Click &quot;Connect&quot; to switch to this database.</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1 text-red-600">
                      <XCircle className="w-3 h-3" />
                      <span>Connection test failed. Please check your settings and try again.</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Save Connection Dialog */}
      <SaveConnectionDialog
        isOpen={showSaveDialog}
        onClose={() => setShowSaveDialog(false)}
        onSave={handleSaveCurrentConnection}
        connectionDetails={connectionStatus.current_config ? {
          host: connectionStatus.current_config.host,
          port: connectionStatus.current_config.port,
          database: connectionStatus.current_config.database,
          username: connectionStatus.current_config.username || connectionStatus.current_config.user || ''
        } : null}
      />
    </div>
  )
} 