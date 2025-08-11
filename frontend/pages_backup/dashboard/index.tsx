import { useState, useEffect } from 'react'
import MetricsCard from '../../components/MetricsCard'
import PerformanceChart from '../../components/PerformanceChart'
import SystemStatus from '../../components/SystemStatus'
import RecommendationModal from '../../components/RecommendationModal'
import QueryDetails from '@/components/QueryDetails'
import WelcomeBanner from '../../components/WelcomeBanner'
import DatabaseStatus from '../../components/DatabaseStatus'
import LiveIndicator from '../../components/LiveIndicator'
import SkeletonLoader from '../../components/SkeletonLoader'
import ConnectionWizard from '../../components/ConnectionWizard'

// Helper function to filter business queries
function isBusinessQuery(query: string) {
  if (!query) return false;
  const q = query.trim().toUpperCase();
  return (
    q.startsWith('SELECT') ||
    q.startsWith('INSERT') ||
    q.startsWith('UPDATE') ||
    q.startsWith('DELETE')
  );
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null)
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSuggestion, setSelectedSuggestion] = useState<any>(null)
  const [selectedQuery, setSelectedQuery] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'queries' | 'suggestions'>('overview')
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [showConnectionWizard, setShowConnectionWizard] = useState(false)
  const [connectionConfig, setConnectionConfig] = useState<any>(null)
  const [connected, setConnected] = useState<boolean>(false)
  const [checkingStatus, setCheckingStatus] = useState(true)

  // Load saved connection config on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('optischema_connection')
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig)
        setConnectionConfig(config)
      } catch (error) {
        console.error('Failed to load saved connection config:', error)
      }
    }
  }, [])

  // Check backend connection status on mount
  useEffect(() => {
    const checkStatus = async () => {
      setCheckingStatus(true)
      try {
        const res = await fetch('/api/connection/status')
        const data = await res.json()
        setConnected(!!data.connected)
      } catch (e) {
        setConnected(false)
      } finally {
        setCheckingStatus(false)
      }
    }
    checkStatus()
  }, [])

  const handleConnect = (config: any) => {
    setConnectionConfig(config)
    // In a real implementation, you would send this to the backend
    // to establish the connection
    console.log('Connecting to database:', config)
  }

  // Only fetch metrics/suggestions if connected
  useEffect(() => {
    if (!connected) return
    setLoading(true)
    const fetchData = async () => {
      try {
        const [metricsRes, suggestionsRes] = await Promise.all([
          fetch('/api/metrics/raw'),
          fetch('/api/suggestions/latest')
        ])
        if (metricsRes.ok) {
          const metricsData = await metricsRes.json()
          setMetrics(metricsData)
          setLastUpdate(new Date())
        }
        if (suggestionsRes.ok) {
          const suggestionsData = await suggestionsRes.json()
          setSuggestions(suggestionsData)
        }
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [connected])

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics/raw')
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSuggestions = async () => {
    try {
      const response = await fetch('/api/suggestions/latest')
      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
    }
  }

  const getTopQueries = () => {
    if (!metrics) return []
    return metrics
      .sort((a: any, b: any) => b.total_time - a.total_time)
      .slice(0, 10)
  }

  const getSlowestQueries = () => {
    if (!metrics) return []
    return metrics
      .filter((q: any) => q.calls > 1) // Only queries called multiple times
      .sort((a: any, b: any) => b.mean_time - a.mean_time)
      .slice(0, 5)
  }

  const getMostFrequentQueries = () => {
    if (!metrics) return []
    return metrics
      .sort((a: any, b: any) => b.calls - a.calls)
      .slice(0, 5)
  }

  // Filter metrics to only show business queries
  const businessMetrics = metrics?.filter((m: any) => isBusinessQuery(m.query));

  if (checkingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Checking database connection...</p>
        </div>
      </div>
    )
  }

  if (!connected) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">Not connected to a database</h2>
          <p className="text-muted-foreground mb-4">Connect to your PostgreSQL instance to begin monitoring and optimization.</p>
          <button
            className="px-6 py-2 bg-primary text-black rounded-md hover:bg-primary/90 transition-colors"
            onClick={() => setShowConnectionWizard(true)}
          >
            Connect to Database
          </button>
        </div>
        <ConnectionWizard
          isOpen={showConnectionWizard}
          onClose={() => setShowConnectionWizard(false)}
          onConnect={handleConnect}
          currentConfig={connectionConfig}
        />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading OptiSchema...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">OptiSchema</h1>
              <p className="text-muted-foreground">AI-Powered PostgreSQL Optimization</p>
            </div>
            <div className="flex items-center space-x-6">
              <DatabaseStatus 
                dbName={connectionConfig?.database || "optischema"} 
                status={connectionConfig ? "connected" : "disconnected"}
                onConnect={() => setShowConnectionWizard(true)}
              />
              <LiveIndicator isLive={true} lastUpdate={lastUpdate} />
              <SystemStatus />
            </div>
          </div>
        </div>
      </header>

      {/* Welcome Banner */}
      <div className="container mx-auto px-4 py-4">
        <WelcomeBanner />
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-border bg-card">
        <div className="container mx-auto px-4">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: '📊' },
              { id: 'queries', label: 'Query Analysis', icon: '🔍' },
              { id: 'suggestions', label: 'Optimizations', icon: '⚡' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Performance Metrics */}
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-foreground">Performance Metrics</h2>
                <LiveIndicator isLive={true} lastUpdate={lastUpdate} />
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                Real-time performance metrics from your PostgreSQL database. Data refreshes automatically every 30 seconds.
              </p>
              {loading ? (
                <SkeletonLoader type="table" lines={5} />
              ) : businessMetrics.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  <p>No business queries detected yet.</p>
                  <p className="text-xs mt-2">Once your application runs SELECT, INSERT, UPDATE, or DELETE queries, they will appear here.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {businessMetrics.slice(0, 5).map((metric: any, index: number) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-4 bg-muted/50 rounded-lg hover:bg-muted/70 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedQuery(metric)
                        setActiveTab('queries')
                      }}
                    >
                      <div className="flex-1">
                        <div className="font-medium text-foreground truncate">
                          {metric.query?.substring(0, 100)}...
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Calls: {metric.calls} | Avg Time: {metric.mean_time?.toFixed(2)}ms
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-foreground">
                          {metric.total_time?.toFixed(2)}ms
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {((metric.total_time / businessMetrics.reduce((sum: number, m: any) => sum + (m.total_time || 0), 0)) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Optimization Suggestions */}
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-foreground">Optimization Suggestions</h2>
                <LiveIndicator isLive={true} lastUpdate={lastUpdate} />
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                AI-powered recommendations to improve your database performance. Click any suggestion to see detailed analysis.
              </p>
              {loading ? (
                <SkeletonLoader type="table" lines={3} />
              ) : (
                <div className="space-y-4">
                  {suggestions.slice(0, 3).map((suggestion, index) => (
                    <div
                      key={index}
                      className="p-4 bg-muted/50 rounded-lg hover:bg-muted/70 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedSuggestion(suggestion)
                        setActiveTab('suggestions')
                      }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-medium text-foreground mb-2">
                            {suggestion.title}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {suggestion.description}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            suggestion.impact === 'high' ? 'bg-red-100 text-red-800' :
                            suggestion.impact === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {suggestion.impact} impact
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'queries' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">Query Analysis</h2>
              <button
                onClick={fetchMetrics}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Refresh Data
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Most Frequent Queries */}
              <div className="lg:col-span-2 bg-card border border-border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Most Frequent Queries</h3>
                <div className="space-y-3">
                  {getMostFrequentQueries().map((query: any, index: number) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-muted/30 rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setSelectedQuery(query)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          Query {index + 1}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {query.query?.substring(0, 100)}...
                        </p>
                      </div>
                      <div className="text-right ml-4">
                        <span className="text-sm font-medium text-blue-600">
                          {query.calls} calls
                        </span>
                        <p className="text-xs text-muted-foreground">
                          {query.mean_time.toFixed(2)}ms avg
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Query Details Panel */}
              <div className="bg-card border border-border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Query Details</h3>
                {selectedQuery ? (
                  <QueryDetails query={selectedQuery} />
                ) : (
                  <p className="text-muted-foreground text-center py-8">
                    Select a query to view details
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'suggestions' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">Optimization Suggestions</h2>
              <button
                onClick={fetchSuggestions}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Refresh Suggestions
              </button>
            </div>
            
            {suggestions.length === 0 ? (
              <div className="bg-card border border-border rounded-lg p-8 text-center">
                <div className="text-4xl mb-4">🔍</div>
                <h3 className="text-lg font-semibold mb-2">No Suggestions Available</h3>
                <p className="text-muted-foreground mb-4">
                  The system is analyzing your queries for optimization opportunities...
                </p>
                <button
                  onClick={() => setActiveTab('queries')}
                  className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors"
                >
                  View Query Analysis
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => setSelectedSuggestion(suggestion)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-sm">{suggestion.type}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        suggestion.confidence > 0.8 ? 'bg-green-100 text-green-800' :
                        suggestion.confidence > 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {Math.round(suggestion.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {suggestion.description}
                    </p>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        Potential savings: {suggestion.estimated_savings}
                      </span>
                      <button className="text-xs text-primary hover:underline">
                        View Details →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Recommendation Modal */}
      {selectedSuggestion && (
        <RecommendationModal
          suggestion={selectedSuggestion}
          onClose={() => setSelectedSuggestion(null)}
          onApply={async () => {
            // Handle apply logic
            console.log('Applying suggestion:', selectedSuggestion)
            setSelectedSuggestion(null)
          }}
        />
      )}

      {/* Connection Wizard */}
      <ConnectionWizard
        isOpen={showConnectionWizard}
        onClose={() => setShowConnectionWizard(false)}
        onConnect={handleConnect}
        currentConfig={connectionConfig}
      />
    </div>
  )
} 