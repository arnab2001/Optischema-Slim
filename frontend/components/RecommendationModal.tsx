import { useState } from 'react'
import { Loader2, Play, CheckCircle, AlertTriangle, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BenchmarkModal } from './BenchmarkModal'

interface RecommendationModalProps {
  suggestion: any
  onClose: () => void
  onApply: () => Promise<void>
}

export default function RecommendationModal({ suggestion, onClose, onApply }: RecommendationModalProps) {
  const [isApplying, setIsApplying] = useState(false)
  const [showBenchmarkModal, setShowBenchmarkModal] = useState(false)
  const [benchmarkResults, setBenchmarkResults] = useState<any>(null)
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null)

  const handleApply = async () => {
    setIsApplying(true)
    try {
      await onApply()
    } catch (error) {
      console.error('Failed to apply suggestion:', error)
    } finally {
      setIsApplying(false)
    }
  }

  const handleBenchmark = async (options: any) => {
    try {
      const response = await fetch('/api/suggestions/benchmark', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          recommendation_id: suggestion.id,
          benchmark_options: options
        })
      })
      
      const data = await response.json()
      
      if (data.success && data.benchmark.success) {
        setBenchmarkResults(data.benchmark)
        setShowBenchmarkModal(false)
      } else {
        setBenchmarkError(data.benchmark?.error || data.message || 'Benchmark failed')
        setShowBenchmarkModal(true) // Keep modal open to show error
      }
    } catch (error) {
      setBenchmarkError('Failed to run benchmark')
      setShowBenchmarkModal(true)
      console.error('Benchmark error:', error)
    }
  }

  // Map backend fields to frontend expectations
  const type = suggestion.recommendation_type || suggestion.type
  const confidence = suggestion.confidence_score || suggestion.confidence || 0
  const estimatedSavings = suggestion.estimated_improvement_percent || suggestion.estimated_savings || 0
  const description = suggestion.description || ''
  const sqlFix = suggestion.sql_fix || suggestion.sql_changes || null
  
  // Clean up title - remove markdown formatting and numbered prefixes
  let title = suggestion.title || 'Optimization Recommendation'
  if (title.startsWith('#') || title.startsWith('##')) {
    title = title.replace(/^#+\s*/, '').trim()
  }
  // Remove numbered prefixes like "1. **Title**" or "1. Title"
  title = title.replace(/^\d+\.\s*\*\*?([^*]+)\*\*?/, '$1').trim()
  title = title.replace(/^\d+\.\s*/, '').trim()

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white border border-gray-200 rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Recommendation Details */}
          <div className="space-y-4">
            {/* Recommendation Type */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Type</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm">
                {type}
              </span>
            </div>

            {/* Confidence Score */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Confidence</span>
              <span className={`px-2 py-1 rounded-md text-sm ${
                confidence > 80 ? 'bg-green-100 text-green-800' :
                confidence > 60 ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {confidence}%
              </span>
            </div>

            {/* Estimated Improvement */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Estimated Improvement</span>
              <span className="text-sm font-medium text-green-600">
                {estimatedSavings}%
              </span>
            </div>

            {/* Risk Level */}
            {suggestion.risk_level && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">Risk Level</span>
                <span className={`px-2 py-1 rounded-md text-sm ${
                  suggestion.risk_level === 'low' ? 'bg-green-100 text-green-800' :
                  suggestion.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {suggestion.risk_level.charAt(0).toUpperCase() + suggestion.risk_level.slice(1)}
                </span>
              </div>
            )}

            {/* Description */}
            <div>
              <span className="text-sm font-medium text-gray-600 block mb-2">Description</span>
              <div className="text-sm text-gray-800 bg-gray-50 p-3 rounded-md border border-gray-200 prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {description}
                </ReactMarkdown>
              </div>
            </div>

            {/* SQL Fix */}
            {sqlFix && (
              <div>
                <span className="text-sm font-medium text-gray-600 block mb-2">SQL Fix</span>
                <pre className="text-sm text-gray-800 bg-gray-50 p-3 rounded-md overflow-x-auto border border-gray-200">
                  <code>{sqlFix}</code>
                </pre>
              </div>
            )}
          </div>

          {/* Right Column - Benchmark Results */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Performance Test</h3>
              <button
                onClick={() => setShowBenchmarkModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <Play className="w-4 h-4" />
                Run Benchmark
              </button>
            </div>

            {benchmarkError && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700">{benchmarkError}</span>
              </div>
            )}



            {benchmarkResults && benchmarkResults.success && (
              <div className="space-y-4">
                {/* Improvement Summary */}
                <div className="bg-green-50 border border-green-200 rounded-md p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <span className="font-semibold text-green-800">Performance Improvement</span>
                  </div>
                  <div className="text-2xl font-bold text-green-600">
                    {benchmarkResults.improvement?.time_improvement_percent || 0}%
                  </div>
                  <div className="text-sm text-green-700">
                    {benchmarkResults.improvement?.time_saved_ms || 0}ms saved
                  </div>
                </div>

                {/* Before/After Comparison */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                    <h4 className="font-medium text-sm mb-2 text-gray-900">Before</h4>
                    <div className="text-2xl font-bold text-red-600">
                      {benchmarkResults.baseline?.total_time?.toFixed(2) || 0}ms
                    </div>
                    <div className="text-xs text-gray-600">
                      Execution: {benchmarkResults.baseline?.execution_time?.toFixed(2) || 0}ms
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                    <h4 className="font-medium text-sm mb-2 text-gray-900">After</h4>
                    <div className="text-2xl font-bold text-green-600">
                      {benchmarkResults.optimized?.total_time?.toFixed(2) || 0}ms
                    </div>
                    <div className="text-xs text-gray-600">
                      Execution: {benchmarkResults.optimized?.execution_time?.toFixed(2) || 0}ms
                    </div>
                  </div>
                </div>

                {/* Rollback SQL */}
                {benchmarkResults.rollback_sql && (
                  <div>
                    <span className="text-sm font-medium text-gray-600 block mb-2">Rollback SQL</span>
                    <pre className="text-sm text-gray-800 bg-gray-50 p-3 rounded-md overflow-x-auto border border-gray-200">
                      <code>{benchmarkResults.rollback_sql}</code>
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            disabled={isApplying}
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={isApplying}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {isApplying ? 'Applying...' : 'Apply Recommendation'}
          </button>
        </div>
      </div>

      {/* Benchmark Modal */}
      <BenchmarkModal
        isOpen={showBenchmarkModal}
        onClose={() => { setShowBenchmarkModal(false); setBenchmarkError(null); }}
        onBenchmark={handleBenchmark}
        recommendation={{ ...suggestion, benchmarkError }}
        isLoading={false}
      />
    </div>
  )
} 