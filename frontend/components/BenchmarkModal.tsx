'use client';

import React, { useState, useEffect } from 'react';
import { X, Zap, Database, FileText, Play } from 'lucide-react';

interface BenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBenchmark: (options: BenchmarkOptions) => void;
  recommendation: any;
  isLoading?: boolean;
}

interface BenchmarkOptions {
  type: 'stock' | 'manual' | 'recommendation';
  query?: string;
  iterations?: number;
}

export function BenchmarkModal({
  isOpen,
  onClose,
  onBenchmark,
  recommendation,
  isLoading = false
}: BenchmarkModalProps) {
  // Auto-detect if recommendation has executable SQL
  const hasExecutableSQL = recommendation.sql_fix || recommendation.original_sql || recommendation.query_text;
  
  // Default to manual if no executable SQL available
  const defaultType = hasExecutableSQL ? 'stock' : 'manual';
  
  const [benchmarkType, setBenchmarkType] = useState<'stock' | 'manual' | 'recommendation'>(defaultType);
  const [manualQuery, setManualQuery] = useState('');
  const [iterations, setIterations] = useState(10);

  // Update default type when modal opens or recommendation changes
  useEffect(() => {
    if (isOpen) {
      const newDefaultType = hasExecutableSQL ? 'stock' : 'manual';
      console.log('BenchmarkModal: Setting default type to', newDefaultType, 'hasExecutableSQL:', hasExecutableSQL);
      setBenchmarkType(newDefaultType);
      setManualQuery(''); // Reset query when modal opens
    }
  }, [isOpen, hasExecutableSQL]);

  if (!isOpen) return null;

  // Debug logging
  console.log('BenchmarkModal render:', {
    isOpen,
    hasExecutableSQL,
    benchmarkType,
    recommendation: {
      id: recommendation.id,
      title: recommendation.title,
      sql_fix: recommendation.sql_fix,
      original_sql: recommendation.original_sql,
      recommendation_type: recommendation.recommendation_type
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const options: BenchmarkOptions = {
      type: benchmarkType,
      iterations
    };

    if (benchmarkType === 'manual' && manualQuery.trim()) {
      options.query = manualQuery.trim();
    }

    onBenchmark(options);
  };

  const getDefaultQuery = () => {
    if (recommendation.sql_fix) {
      return recommendation.sql_fix;
    }
    if (recommendation.original_sql) {
      return recommendation.original_sql;
    }
    return 'SELECT 1; -- Default test query';
  };

  const getSuggestedQueries = () => {
    // Clean title from markdown formatting
    const cleanTitle = recommendation.title?.replace(/\*\*/g, '').toLowerCase() || '';
    const description = recommendation.description?.toLowerCase() || '';
    
    const suggestions = [
      'SELECT COUNT(*) FROM sandbox.users;',
      'SELECT * FROM sandbox.users WHERE email = \'john@example.com\';',
      'SELECT u.username, o.amount FROM sandbox.users u JOIN sandbox.orders o ON u.id = o.user_id;',
      'SELECT COUNT(*) FROM sandbox.orders WHERE status = \'completed\';',
      'SELECT p.name, p.price FROM sandbox.products p WHERE p.category = \'Electronics\';'
    ];
    
    // Add specific suggestions based on recommendation type
    if (cleanTitle.includes('index') || description.includes('index')) {
      suggestions.unshift('SELECT * FROM sandbox.users WHERE email = \'john@example.com\';');
    }
    if (cleanTitle.includes('join') || description.includes('join')) {
      suggestions.unshift('SELECT u.username, o.amount, p.name FROM sandbox.users u JOIN sandbox.orders o ON u.id = o.user_id JOIN sandbox.order_items oi ON o.id = oi.order_id JOIN sandbox.products p ON oi.product_id = p.id;');
    }
    if (cleanTitle.includes('performance') || description.includes('performance')) {
      suggestions.unshift('SELECT COUNT(*) FROM sandbox.orders WHERE status = \'completed\';');
    }
    
    return suggestions;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-600" />
            Benchmark Options
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Error Message for Failed Benchmark */}
          {recommendation.benchmarkError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg mb-2">
              <div className="flex items-start gap-2">
                <div className="w-4 h-4 text-red-600 mt-0.5">❌</div>
                <div>
                  <p className="text-sm font-medium text-red-800">Benchmark Failed</p>
                  <p className="text-xs text-red-700 mt-1">
                    {recommendation.benchmarkError.includes('Failed to apply optimization in sandbox')
                      ? 'No executable SQL was provided, or the query could not be run in the sandbox. Please enter a custom query to benchmark. The default stock benchmark may not reflect your schema.'
                      : recommendation.benchmarkError}
                  </p>
                </div>
              </div>
            </div>
          )}
          {/* Warning for recommendations without executable SQL */}
          {!hasExecutableSQL && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start gap-2">
                <div className="w-4 h-4 text-yellow-600 mt-0.5">⚠️</div>
                <div>
                  <p className="text-sm font-medium text-yellow-800">Advisory Recommendation</p>
                  <p className="text-xs text-yellow-700 mt-1">
                    This recommendation provides guidance but doesn&apos;t include executable SQL. Please enter a custom query to test performance.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Benchmark Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Benchmark Type
            </label>
            <div className="grid grid-cols-1 gap-3">
              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="benchmarkType"
                  value="stock"
                  checked={benchmarkType === 'stock'}
                  onChange={(e) => setBenchmarkType(e.target.value as any)}
                  className="mr-3"
                />
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-blue-600" />
                  <div>
                    <div className="font-medium">Stock Benchmark</div>
                    <div className="text-sm text-gray-500">
                      Run a standard performance test with synthetic data
                    </div>
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="benchmarkType"
                  value="recommendation"
                  checked={benchmarkType === 'recommendation'}
                  onChange={(e) => setBenchmarkType(e.target.value as any)}
                  className="mr-3"
                />
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-green-600" />
                  <div>
                    <div className="font-medium">Use Recommendation SQL</div>
                    <div className="text-sm text-gray-500">
                      Test with the SQL fix provided in the recommendation
                    </div>
                  </div>
                </div>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="radio"
                  name="benchmarkType"
                  value="manual"
                  checked={benchmarkType === 'manual'}
                  onChange={(e) => setBenchmarkType(e.target.value as any)}
                  className="mr-3"
                />
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-purple-600" />
                  <div>
                    <div className="font-medium">Custom Query</div>
                    <div className="text-sm text-gray-500">
                      Test with your own SQL query
                    </div>
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Manual Query Input - Always show when manual is selected */}
          {benchmarkType === 'manual' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custom SQL Query *
              </label>
              <textarea
                value={manualQuery}
                onChange={(e) => setManualQuery(e.target.value)}
                placeholder="Enter your SQL query here... (Will be executed in sandbox database)"
                className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                This field is required for manual benchmarking
              </p>
              
              {/* Query Suggestions */}
              <div className="mt-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Suggested Queries (Click to use):
                </label>
                <div className="space-y-1">
                  {getSuggestedQueries().map((query, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => setManualQuery(query)}
                      className="block w-full text-left p-2 text-xs bg-gray-50 hover:bg-gray-100 rounded border text-gray-700 font-mono"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Recommendation SQL Preview */}
          {benchmarkType === 'recommendation' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                SQL to Test
              </label>
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {getDefaultQuery()}
                </pre>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                ⚠️ This SQL will be executed in the sandbox database, not your production database.
              </p>
            </div>
          )}

          {/* Iterations */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Iterations
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={iterations}
              onChange={(e) => setIterations(parseInt(e.target.value) || 10)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Higher iterations provide more accurate results but take longer
            </p>
          </div>

          {/* Safety Notice */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start gap-2">
              <div className="w-4 h-4 text-blue-600 mt-0.5">🔒</div>
              <div>
                <p className="text-sm font-medium text-blue-800">Safe Testing Environment</p>
                <p className="text-xs text-blue-700 mt-1">
                  All benchmarks are executed in an isolated sandbox database. Your production database will never be modified during testing.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || (benchmarkType === 'manual' && !manualQuery.trim())}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Start Benchmark
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 