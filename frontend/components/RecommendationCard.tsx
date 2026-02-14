'use client';

import React, { useState, useEffect } from 'react';
import { Play, RotateCcw, CheckCircle, XCircle, Clock, AlertTriangle, Zap, ShoppingCart, Check } from 'lucide-react';
import { BenchmarkModal } from './BenchmarkModal';
import { useCartStore } from '@/store/cartStore';

interface RecommendationCardProps {
  recommendation: any;
  onApply?: (recommendationId: string) => void;
  onRollback?: (recommendationId: string) => void;
  onViewDetails?: (recommendation: any) => void;
}

export function RecommendationCard({
  recommendation,
  onApply,
  onRollback,
  onViewDetails
}: RecommendationCardProps) {
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [action, setAction] = useState<'apply' | 'rollback' | 'benchmark' | null>(null);
  const [showBenchmarkModal, setShowBenchmarkModal] = useState(false);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  // Map backend fields to frontend expectations
  const type = recommendation.recommendation_type || recommendation.type;
  const confidence = recommendation.confidence_score || recommendation.confidence || 0;
  const estimatedSavings = recommendation.estimated_improvement_percent || recommendation.estimated_savings || 0;
  const isApplied = recommendation.applied || recommendation.status === 'applied' || false;
  const status = recommendation.status || 'pending';

  // Clean up title
  let title = recommendation.title || 'Optimization Recommendation';
  if (title.startsWith('#') || title.startsWith('##')) {
    title = title.replace(/^#+\s*/, '').trim();
  }
  title = title.replace(/^\d+\.\s*\*\*?([^*]+)\*\*?/, '$1').trim();
  title = title.replace(/^\d+\.\s*/, '').trim();

  // Clean up description
  const description = recommendation.description
    ? recommendation.description
        .replace(/^\d+\.\s*\*\*?([^*]+)\*\*?:\s*/, '')
        .replace(/^\*\*([^*]+)\*\*:\s*/, '')
        .replace(/^\*\*([^*]+)\*\*\s*/, '')
        .trim()
    : '';

  // Check for existing benchmark job
  useEffect(() => {
    const checkJobStatus = async () => {
      try {
        const response = await fetch(`/api/suggestions/benchmark?recommendation_id=${recommendation.id}`);
        const result = await response.json();
        if (result.success && result.data && result.data.length > 0) {
          // Get the most recent job
          const latestJob = result.data[0];
          setJobStatus(latestJob);
        }
      } catch (error) {
        console.error('Failed to check job status:', error);
      }
    };

    checkJobStatus();
  }, [recommendation.id]);

  const handleBenchmark = async (options: any) => {
    if (isLoading) return;
    
    setIsLoading(true);
    setAction('benchmark');
    setShowBenchmarkModal(false);
    setBenchmarkError(null);
    
    try {
      const response = await fetch(`/api/suggestions/benchmark`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          recommendation_id: recommendation.id,
          benchmark_options: options
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Poll for job status
        const pollJobStatus = async () => {
          try {
            const statusResponse = await fetch(`/api/suggestions/benchmark?recommendation_id=${recommendation.id}`);
            const statusResult = await statusResponse.json();
            
            if (statusResult.success && statusResult.benchmark) {
              // New API response structure - benchmark data is directly in statusResult.benchmark
              setJobStatus({
                status: 'completed',
                result: statusResult.benchmark
              });
              setIsLoading(false);
              setAction(null);
            } else if (statusResult.data) {
              // Old API response structure - for backward compatibility
              setJobStatus(statusResult.data);
              
              if (statusResult.data.status === 'completed' || statusResult.data.status === 'failed') {
                setIsLoading(false);
                setAction(null);
              } else {
                // Continue polling
                setTimeout(pollJobStatus, 2000);
              }
            } else {
              // Error or unexpected response
              console.warn('Unexpected benchmark response:', statusResult);
              setIsLoading(false);
              setAction(null);
              setBenchmarkError(statusResult.message || 'Benchmark failed');
            }
          } catch (error) {
            console.error('Failed to poll job status:', error);
            setIsLoading(false);
            setAction(null);
            setBenchmarkError('Failed to get benchmark status');
          }
        };
        
        pollJobStatus();
      } else {
        console.error('Benchmark failed:', result.message);
        setBenchmarkError(result.benchmark?.error || result.message || 'Benchmark failed.');
        setIsLoading(false);
        setAction(null);
        setShowBenchmarkModal(true); // Reopen modal to show error
      }
    } catch (error) {
      console.error('Benchmark error:', error);
      setBenchmarkError('Benchmark failed due to a network or server error.');
      setIsLoading(false);
      setAction(null);
      setShowBenchmarkModal(true);
    }
  };

  const handleApply = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setAction('apply');
    
    try {
      const response = await fetch(`/api/suggestions/apply-and-test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ recommendation_id: recommendation.id })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Set job status with the apply and test results
        setJobStatus({
          status: 'completed',
          result: {
            type: 'apply_and_test',
            apply_result: result.apply_result,
            improvement: result.improvement,
            baseline_benchmark: result.baseline_benchmark,
            optimized_benchmark: result.optimized_benchmark,
            rollback_available: result.rollback_available,
            applied_at: result.applied_at
          }
        });
        
        onApply?.(recommendation.id);
      } else {
        console.error('Apply and test failed:', result.error || result.message);
        setBenchmarkError(result.error || result.message || 'Apply and test failed');
      }
    } catch (error) {
      console.error('Apply and test error:', error);
      setBenchmarkError('Apply and test failed due to a network or server error.');
    } finally {
      setIsLoading(false);
      setAction(null);
    }
  };

  const handleRollback = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setAction('rollback');
    
    try {
      // Check if this was applied via apply-and-test (has rollback_info)
      const rollbackInfo = recommendation.rollback_info;
      const isApplyAndTest = rollbackInfo && rollbackInfo.method === 'apply_and_test';
      
      let response;
      if (isApplyAndTest) {
        // Use apply-and-test specific rollback endpoint
        response = await fetch(`/api/suggestions/rollback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ recommendation_id: recommendation.id })
        });
      } else {
        // Use ApplyManager rollback endpoint
        response = await fetch(`/api/apply/${recommendation.id}/rollback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
      }
      
      const result = await response.json();
      
      if (result.success) {
        // Clear the job status to remove the "Applied & Tested" results
        setJobStatus(null);
        
        onRollback?.(recommendation.id);
      } else {
        console.error('Rollback failed:', result.message || result.detail);
        setBenchmarkError(result.message || result.detail || 'Rollback failed');
      }
    } catch (error) {
      console.error('Rollback error:', error);
      setBenchmarkError('Rollback failed due to a network or server error.');
    } finally {
      setIsLoading(false);
      setAction(null);
    }
  };

  const getStatusBadge = () => {
    if (isApplied) {
      return (
        <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          Applied
        </span>
      );
    }
    
    if (jobStatus?.status === 'completed') {
      return (
        <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 flex items-center gap-1">
          <Zap className="w-3 h-3" />
          Benchmarked
        </span>
      );
    }
    
    if (jobStatus?.status === 'running') {
      return (
        <span className="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          Running
        </span>
      );
    }
    
    if (jobStatus?.status === 'failed') {
      return (
        <span className="px-2 py-1 rounded-full text-xs bg-red-100 text-red-800 flex items-center gap-1">
          <XCircle className="w-3 h-3" />
          Failed
        </span>
      );
    }
    
    return (
      <span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800">
        {confidence}%
      </span>
    );
  };

  const getBenchmarkResults = () => {
    if (!jobStatus || jobStatus.status !== 'completed') {
      return null;
    }

    const { result } = jobStatus;
    if (!result) return null;

    // Handle Apply & Test results
    if (result.type === 'apply_and_test' && result.improvement) {
      const improvement = result.improvement;
      const isPositiveImprovement = improvement.improvement_percent > 0;
      
      return (
        <div className="mt-3 p-3 bg-green-50 rounded-md border border-green-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-green-800">✅ Applied & Tested</span>
            <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
              Optimization Active
            </span>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className={`text-lg font-semibold ${isPositiveImprovement ? 'text-green-600' : 'text-yellow-600'}`}>
                {isPositiveImprovement ? '+' : ''}{improvement.improvement_percent}% improvement
              </span>
              <span className="text-sm text-gray-600">
                {improvement.time_saved_ms}ms saved per query
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600">Before</div>
                <div className="font-medium">{improvement.baseline_time_ms.toFixed(2)}ms</div>
              </div>
              <div>
                <div className="text-gray-600">After</div>
                <div className="font-medium">{improvement.optimized_time_ms.toFixed(2)}ms</div>
              </div>
            </div>
            
            {improvement.recommendation && (
              <div className="mt-2 pt-2 border-t border-green-200">
                <div className="text-xs text-green-700">
                  💡 {improvement.recommendation === 'keep' 
                    ? 'Recommended: Keep this optimization' 
                    : 'Consider rolling back if improvement is not significant'}
                </div>
              </div>
            )}
            
            {result.rollback_available && (
              <div className="text-xs text-gray-500">
                🔄 Rollback available if needed
              </div>
            )}
            
            {/* Sandbox Verification Details */}
            {result.apply_result?.sandbox_verification && (
              <div className="mt-3 pt-3 border-t border-green-200">
                <div className="text-xs text-gray-700 space-y-1">
                  <div className="font-medium text-green-700">🔒 Sandbox Verification:</div>
                  <div>
                    <span className="font-medium">Environment:</span> {result.apply_result.environment || 'Isolated Sandbox'}
                  </div>
                  <div>
                    <span className="font-medium">Database:</span> {result.apply_result.sandbox_verification.database}@{result.apply_result.sandbox_verification.host}
                  </div>
                  {result.apply_result.ddl_executed && (
                    <div>
                      <span className="font-medium">DDL Applied:</span> 
                      <code className="ml-1 px-1 bg-gray-100 text-xs rounded">{result.apply_result.ddl_executed}</code>
                    </div>
                  )}
                  {result.apply_result.sandbox_verification.index_created && (
                    <div className="text-green-600">
                      ✅ Index verified: {result.apply_result.sandbox_verification.index_created.name} on {result.apply_result.sandbox_verification.index_created.table}
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Show what changed in detail */}
            {result.apply_result?.sandbox_verification?.current_indexes && (
              <details className="mt-2">
                <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                  📋 View Sandbox State ({result.apply_result.sandbox_verification.current_indexes.length} indexes)
                </summary>
                <div className="mt-1 text-xs text-gray-600 max-h-32 overflow-y-auto">
                  {result.apply_result.sandbox_verification.current_indexes.map((idx: any, i: number) => (
                    <div key={i} className="py-1">
                      <code className="bg-gray-100 px-1 rounded">{idx.index}</code> on <span className="font-medium">{idx.table}</span>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    // Handle regular benchmark results (for advisory recommendations)
    if (result.improvement) {
      const improvement = result.improvement;
      const hasExecutableSQL = recommendation.sql_fix;
      const isAdvisoryOnly = !hasExecutableSQL;

      return (
        <div className="mt-3 p-3 bg-gray-50 rounded-md border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Performance Test</span>
            {isAdvisoryOnly && (
              <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                Advisory Only
              </span>
            )}
          </div>
          
          {isAdvisoryOnly ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <AlertTriangle className="w-4 h-4 text-blue-500" />
                <span>This recommendation provides guidance but cannot be automatically tested.</span>
              </div>
              <div className="text-xs text-gray-500">
                Advisory recommendations require manual implementation and monitoring.
                Use the &quot;Manual Query&quot; option in benchmark to test your own implementation.
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-2">
                <span className="text-lg font-semibold text-green-600">
                  {(improvement.improvement_percent || improvement.time_improvement_percent || 0) > 0 ? '+' : ''}{(improvement.improvement_percent || improvement.time_improvement_percent || 0).toFixed(1)}%
                </span>
                <span className="text-sm text-gray-600">
                  {improvement.time_saved_ms}ms saved
                </span>
              </div>
              
              {improvement.io_improvement_percent && (
                <div className="text-xs text-gray-600 mb-2">
                  📊 I/O Efficiency: {improvement.io_improvement_percent > 0 ? '+' : ''}{improvement.io_improvement_percent}% ({improvement.baseline_blocks} → {improvement.optimized_blocks} blocks)
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-gray-600">Before</div>
                  <div className="font-medium">{improvement.baseline_time_ms.toFixed(2)}ms</div>
                  <div className="text-xs text-gray-500">
                    Execution: {result.baseline?.execution_time?.toFixed(2) || 0}ms
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">After</div>
                  <div className="font-medium">{improvement.optimized_time_ms.toFixed(2)}ms</div>
                  <div className="text-xs text-gray-500">
                    Execution: {result.optimized?.execution_time?.toFixed(2) || 0}ms
                  </div>
                </div>
              </div>
              
              {result.rollback_sql && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <div className="text-xs text-gray-600 mb-1">Rollback SQL</div>
                  <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                    {result.rollback_sql}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div className="border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-sm">{title}</h3>
        {getStatusBadge()}
      </div>
      
      <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
        {description}
      </p>

      {/* Confidence Meter */}
      {confidence > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  confidence >= 80 ? 'bg-green-500' : confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className={`text-[10px] font-bold ${
              confidence >= 80 ? 'text-green-600' : confidence >= 50 ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {confidence >= 80 ? 'High' : confidence >= 50 ? 'Medium' : 'Low'} ({confidence}%)
            </span>
          </div>
        </div>
      )}

      {/* Why this? Expandable section */}
      {(recommendation.reasoning || recommendation.confidence_factors) && (
        <details className="mb-3 group">
          <summary className="text-xs text-blue-600 hover:text-blue-500 cursor-pointer font-medium">
            Why this recommendation?
          </summary>
          <div className="mt-2 p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs space-y-2">
            {recommendation.reasoning && (
              <p className="text-muted-foreground leading-relaxed">{recommendation.reasoning}</p>
            )}
            {recommendation.confidence_factors && recommendation.confidence_factors.length > 0 && (
              <ul className="space-y-1">
                {recommendation.confidence_factors.map((factor: string, i: number) => (
                  <li key={i} className="flex items-start gap-1.5 text-muted-foreground">
                    <span className="text-green-500 mt-0.5 flex-shrink-0">&#x2713;</span>
                    {factor}
                  </li>
                ))}
              </ul>
            )}
            {recommendation.verification_status && (
              <div className="pt-1.5 border-t border-slate-200 dark:border-slate-700">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  recommendation.verification_status === 'verified' ? 'bg-green-100 text-green-700' :
                  recommendation.verification_status === 'estimated' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {recommendation.verification_status?.toUpperCase()}
                </span>
              </div>
            )}
          </div>
        </details>
      )}

      {/* Workload Impact */}
      {recommendation.workload_impact && recommendation.workload_impact.tested_queries > 0 && (
        <details className="mb-3 group">
          <summary className="text-xs text-purple-600 hover:text-purple-500 cursor-pointer font-medium flex items-center gap-1">
            <Zap className="w-3 h-3" />
            Workload Impact ({recommendation.workload_impact.tested_queries} queries tested)
          </summary>
          <div className="mt-2 p-2.5 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-xs space-y-2">
            {/* Summary */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="text-green-600 font-bold">↑ {recommendation.workload_impact.improved}</span>
                <span className="text-muted-foreground">improved</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-600 font-bold">− {recommendation.workload_impact.neutral}</span>
                <span className="text-muted-foreground">neutral</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-red-600 font-bold">↓ {recommendation.workload_impact.regressed}</span>
                <span className="text-muted-foreground">regressed</span>
              </div>
            </div>

            {/* Warning if regressions */}
            {recommendation.workload_impact.regressed > 0 && (
              <div className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-700 dark:text-red-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>
                  This index may hurt {recommendation.workload_impact.regressed} other {recommendation.workload_impact.regressed === 1 ? 'query' : 'queries'}.
                  Review workload details before applying.
                </span>
              </div>
            )}

            {/* Details table */}
            {recommendation.workload_impact.details && recommendation.workload_impact.details.length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-purple-600 hover:text-purple-500 cursor-pointer">
                  View query-by-query breakdown
                </summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead className="border-b border-purple-200 dark:border-purple-800">
                      <tr className="text-muted-foreground">
                        <th className="text-left py-1">Query</th>
                        <th className="text-right py-1">Calls</th>
                        <th className="text-right py-1">Before</th>
                        <th className="text-right py-1">After</th>
                        <th className="text-right py-1">Change</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-purple-100 dark:divide-purple-900/50">
                      {recommendation.workload_impact.details.slice(0, 10).map((detail: any, i: number) => (
                        <tr key={i}>
                          <td className="py-1 font-mono truncate max-w-[200px]" title={detail.query}>
                            {detail.query}
                          </td>
                          <td className="py-1 text-right">{detail.calls}</td>
                          <td className="py-1 text-right">{detail.cost_before.toFixed(0)}</td>
                          <td className="py-1 text-right">{detail.cost_after.toFixed(0)}</td>
                          <td className={`py-1 text-right font-bold ${
                            detail.status === 'improved' ? 'text-green-600' :
                            detail.status === 'regressed' ? 'text-red-600' :
                            'text-gray-600'
                          }`}>
                            {detail.improvement_percent > 0 ? '+' : ''}{detail.improvement_percent.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {recommendation.workload_impact.details.length > 10 && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Showing top 10 of {recommendation.workload_impact.details.length} tested queries
                    </p>
                  )}
                </div>
              </details>
            )}
          </div>
        </details>
      )}

      {getBenchmarkResults()}
      
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Potential improvement: {estimatedSavings}%
        </span>
        
        <div className="flex items-center gap-2">
          {/* Add to Cart button for executable recommendations */}
          {recommendation.sql_fix && !isApplied && (() => {
            const { addItem, isInCart } = useCartStore.getState();
            const inCart = useCartStore((s) => s.isInCart(recommendation.sql_fix));
            return (
              <button
                onClick={() => {
                  if (!inCart) {
                    const wi = recommendation.workload_impact;
                    const impactNote = wi && wi.tested_queries > 0
                      ? ` | Workload: ${wi.improved} improved, ${wi.regressed} regressed, ${wi.neutral} neutral`
                      : '';
                    addItem({
                      id: recommendation.id || crypto.randomUUID(),
                      type: type === 'INDEX' || type === 'index' ? 'index' : type === 'REWRITE' || type === 'rewrite' ? 'rewrite' : 'drop',
                      sql: recommendation.sql_fix,
                      description: `${title}${impactNote}`,
                      table: recommendation.table_name || '',
                      estimatedImprovement: estimatedSavings,
                      source: 'analysis',
                    });
                  }
                }}
                className={`px-3 py-1 text-xs rounded flex items-center gap-1 ${
                  inCart
                    ? 'bg-blue-100 text-blue-700 cursor-default'
                    : 'bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200'
                }`}
              >
                {inCart ? <Check className="w-3 h-3" /> : <ShoppingCart className="w-3 h-3" />}
                {inCart ? 'In Cart' : 'Add to Cart'}
              </button>
            );
          })()}

          {/* Show Apply button for executable recommendations */}
          {recommendation.sql_fix && !isApplied && (
            <button
              onClick={handleApply}
              disabled={isLoading}
              className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-1"
            >
              {isLoading && action === 'apply' ? (
                <Clock className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
              Apply & Test
            </button>
          )}
          
          {/* Show Benchmark button only for advisory recommendations */}
          {!recommendation.sql_fix && !jobStatus && (
            <button
              onClick={() => setShowBenchmarkModal(true)}
              disabled={isLoading}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              {isLoading && action === 'benchmark' ? (
                <Clock className="w-3 h-3 animate-spin" />
              ) : (
                <Zap className="w-3 h-3" />
              )}
              Test Manually
            </button>
          )}
          
          {/* Show Rollback if applied */}
          {isApplied && (
            <button
              onClick={handleRollback}
              disabled={isLoading}
              className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center gap-1"
            >
              {isLoading && action === 'rollback' ? (
                <Clock className="w-3 h-3 animate-spin" />
              ) : (
                <RotateCcw className="w-3 h-3" />
              )}
              Rollback
            </button>
          )}
          
          <button
            onClick={() => onViewDetails?.(recommendation)}
            className="text-xs text-primary hover:underline"
          >
            Details →
          </button>
        </div>
      </div>

      {/* Benchmark Modal - Only for advisory recommendations */}
      {!recommendation.sql_fix && (
        <BenchmarkModal
          isOpen={showBenchmarkModal}
          onClose={() => { setShowBenchmarkModal(false); setBenchmarkError(null); }}
          onBenchmark={handleBenchmark}
          recommendation={{ ...recommendation, benchmarkError }}
          isLoading={isLoading && action === 'benchmark'}
        />
      )}
    </div>
  );
} 