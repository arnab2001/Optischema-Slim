import { useState } from 'react'
import { Database, Eye, EyeOff, TestTube, CheckCircle, XCircle, Loader, Link2 } from 'lucide-react'

interface ConnectionConfig {
  host?: string
  port?: string
  database?: string
  username?: string
  password?: string
  ssl?: boolean
  connection_string?: string
}

interface ConnectionWizardProps {
  isOpen: boolean
  onClose: () => void
  onConnect: (config: ConnectionConfig) => void | Promise<void>
  currentConfig?: ConnectionConfig
}

export default function ConnectionWizard({ isOpen, onClose, onConnect, currentConfig }: ConnectionWizardProps) {
  const [config, setConfig] = useState<ConnectionConfig>({
    host: currentConfig?.host || 'postgres',
    port: currentConfig?.port || '5432',
    database: currentConfig?.database || 'optischema',
    username: currentConfig?.username || 'optischema',
    password: currentConfig?.password || 'optischema_pass',
    ssl: currentConfig?.ssl || false,
    connection_string: currentConfig?.connection_string || ''
  })

  const [showPassword, setShowPassword] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    details?: string
  } | null>(null)
  const [mode, setMode] = useState<'simple' | 'advanced'>(config.connection_string ? 'advanced' : 'simple')

  const handleInputChange = (field: keyof ConnectionConfig, value: string | boolean) => {
    setConfig(prev => ({ ...prev, [field]: value }))
    if (testResult) setTestResult(null)
  }

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const response = await fetch('/api/connection/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mode === 'advanced' ? { connection_string: config.connection_string } : config)
      })
      const result = await response.json()
      if (response.ok) {
        // Handle details object properly
        let detailsText = ''
        if (result.details) {
          if (typeof result.details === 'object') {
            // Convert object to readable text
            detailsText = Object.entries(result.details)
              .map(([key, value]) => `${key}: ${value}`)
              .join(', ')
          } else {
            detailsText = result.details
          }
        }
        
        setTestResult({
          success: true,
          message: 'Connection successful!',
          details: detailsText
        })
      } else {
        setTestResult({
          success: false,
          message: 'Connection failed',
          details: result.error || (typeof result.details === 'string' ? result.details : 'Unknown error occurred')
        })
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Connection failed',
        details: error instanceof Error ? error.message : 'Network error'
      })
    } finally {
      setTesting(false)
    }
  }

  const handleConnect = async () => {
    localStorage.setItem('optischema_connection', JSON.stringify(config))
    await onConnect(config)
    onClose()
  }

  const isValidConfig = mode === 'advanced'
    ? !!config.connection_string
    : config.host && config.port && config.database && config.username

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <Database className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-semibold">Connect to PostgreSQL</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Toggle */}
        <div className="flex justify-center space-x-2 mt-4">
          <button
            className={`px-3 py-1 rounded-md text-sm font-medium ${mode === 'simple' ? 'bg-primary text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setMode('simple')}
          >
            Simple
          </button>
          <button
            className={`px-3 py-1 rounded-md text-sm font-medium ${mode === 'advanced' ? 'bg-primary text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setMode('advanced')}
          >
            <Link2 className="inline w-4 h-4 mr-1" /> Advanced
          </button>
        </div>

        <div className="p-6 space-y-4">
          {mode === 'advanced' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Connection String
              </label>
              <input
                type="text"
                value={config.connection_string}
                onChange={e => handleInputChange('connection_string', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="postgresql://user:pass@host:port/db"
              />
              <p className="text-xs text-gray-500 mt-1">
                Example: <code>postgresql://optischema:optischema_pass@postgres:5432/optischema</code>
              </p>
            </div>
          ) : (
            <>
              {/* Host & Port */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Host
                  </label>
                  <input
                    type="text"
                    value={config.host}
                    onChange={(e) => handleInputChange('host', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="postgres (for Docker) or localhost"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Port
                  </label>
                  <input
                    type="text"
                    value={config.port}
                    onChange={(e) => handleInputChange('port', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="5432"
                  />
                </div>
              </div>

              {/* Database */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Database
                </label>
                <input
                  type="text"
                  value={config.database}
                  onChange={(e) => handleInputChange('database', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="optischema"
                />
              </div>

              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username
                </label>
                <input
                  type="text"
                  value={config.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="optischema"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={config.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="Enter password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* SSL Toggle */}
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="ssl"
                  checked={config.ssl}
                  onChange={(e) => handleInputChange('ssl', e.target.checked)}
                  className="w-4 h-4 text-primary focus:ring-primary border-gray-300 rounded"
                />
                <label htmlFor="ssl" className="text-sm font-medium text-gray-700">
                  Use SSL connection
                </label>
              </div>
            </>
          )}

          {/* Docker/Localhost Helper */}
          <div className="text-xs text-gray-500 space-y-1">
            <p>• If running in Docker, use <b>postgres</b> as the host. If running locally, use <b>localhost</b>.</p>
            <p>• You can also use a full connection string in Advanced mode.</p>
            <p>• Ensure <code>pg_stat_statements</code> extension is enabled.</p>
          </div>

          {/* Test Connection */}
          <div className="pt-4">
            <button
              onClick={testConnection}
              disabled={!isValidConfig || testing}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {testing ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <TestTube className="w-4 h-4" />
              )}
              <span>{testing ? 'Testing...' : 'Test Connection'}</span>
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`p-4 rounded-md ${
              testResult.success 
                ? 'bg-green-50 border border-green-200' 
                : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-center space-x-2">
                {testResult.success ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <span className={`font-medium ${
                  testResult.success ? 'text-green-800' : 'text-red-800'
                }`}>
                  {testResult.message}
                </span>
              </div>
              {testResult.details && (
                <div className={`text-sm mt-1 ${
                  testResult.success ? 'text-green-700' : 'text-red-700'
                }`}>
                  {testResult.details.split(', ').map((detail, index) => (
                    <p key={index} className="text-xs">
                      {detail}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Connect Button */}
          <div className="pt-4 border-t">
            <button
              onClick={handleConnect}
              disabled={!isValidConfig || !testResult?.success}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <Database className="w-4 h-4" />
              <span className='text-black'>Connect to Database</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
} 