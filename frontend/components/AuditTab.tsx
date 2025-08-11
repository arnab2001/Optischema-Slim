'use client';

import React, { useState, useEffect } from 'react';
import { DownloadIcon, FilterIcon, RefreshCwIcon, EyeIcon, XIcon } from 'lucide-react';

interface AuditLog {
  id: string;
  action_type: string;
  recommendation_id: string;
  query_hash: string;
  before_metrics: any;
  after_metrics: any;
  improvement_percent: number;
  details: any;
  risk_level: string;
  status: string;
  created_at: string;
}

interface AuditSummary {
  total_logs: number;
  action_type_counts: Record<string, number>;
  status_counts: Record<string, number>;
  recent_activity_24h: number;
  average_improvement_percent: number;
}

interface AuditResponse {
  logs: AuditLog[];
  summary: AuditSummary;
  pagination: {
    limit: number;
    offset: number;
    total: number;
    has_more: boolean;
  };
}

export default function AuditTab() {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    action_type: '',
    limit: 100,
    offset: 0
  });
  const [actionTypes, setActionTypes] = useState<string[]>([]);
  const [compareLog, setCompareLog] = useState<AuditLog | null>(null);
  const [showRawData, setShowRawData] = useState(false);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.action_type) params.append('action_type', filters.action_type);
      params.append('limit', filters.limit.toString());
      params.append('offset', filters.offset.toString());

      const response = await fetch(`/api/audit/logs?${params}`);
      const data = await response.json();

      if (data.success) {
        setAuditLogs(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditSummary = async () => {
    try {
      const response = await fetch('/api/audit/summary');
      const data = await response.json();
      if (data.success) {
        setSummary(data.data || null);
      }
    } catch (error) {
      console.error('Failed to fetch audit summary:', error);
    }
  };

  const fetchActionTypes = async () => {
    try {
      const response = await fetch('/api/audit/action-types');
      const data = await response.json();
      if (data.success) {
        setActionTypes(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch action types:', error);
    }
  };



  const exportAuditLogs = async (format: 'csv' | 'json' = 'csv') => {
    try {
      const params = new URLSearchParams();
      
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.action_type) params.append('action_type', filters.action_type);
      params.append('format', format);

      const response = await fetch(`/api/audit/logs/export?${params}`);
      const blob = await response.blob();
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export audit logs:', error);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
    fetchAuditSummary();
    fetchActionTypes();
  }, [filters]);

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'rolled_back': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatMetrics = (metrics: any) => {
    if (!metrics) return 'N/A';
    return Object.entries(metrics)
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
  };

  const formatMetricsForDisplay = (metrics: any) => {
    if (!metrics) return null;
    
    // Extract key performance metrics
    const keyMetrics = {
      execution_time: metrics.execution_time,
      planning_time: metrics.planning_time,
      total_time: metrics.total_time,
      rows: metrics.rows,
      shared_hit_blocks: metrics.shared_hit_blocks,
      shared_read_blocks: metrics.shared_read_blocks,
      query_used: metrics.query_used
    };

    // Extract execution plan summary
    let planSummary = 'No plan available';
    if (metrics.explain_plan && Array.isArray(metrics.explain_plan) && metrics.explain_plan.length > 0) {
      const plan = metrics.explain_plan[0];
      if (plan.Plan) {
        const nodeType = plan.Plan['Node Type'] || 'Unknown';
        const strategy = plan.Plan.Strategy || '';
        const actualRows = plan.Plan['Actual Rows'] || 'N/A';
        const actualTime = plan.Plan['Actual Total Time'] || 'N/A';
        
        planSummary = `${nodeType}${strategy ? ` (${strategy})` : ''} - ${actualRows} rows in ${actualTime}ms`;
        
        // Add sub-plan info if available
        if (plan.Plan.Plans && Array.isArray(plan.Plan.Plans) && plan.Plan.Plans.length > 0) {
          const subPlan = plan.Plan.Plans[0];
          if (subPlan['Node Type']) {
            const subNodeType = subPlan['Node Type'];
            const subActualRows = subPlan['Actual Rows'] || 'N/A';
            const subActualTime = subPlan['Actual Total Time'] || 'N/A';
            const filter = subPlan.Filter ? ` with filter: ${subPlan.Filter}` : '';
            
            planSummary += `\n└─ ${subNodeType} - ${subActualRows} rows in ${subActualTime}ms${filter}`;
          }
        }
      }
    }

    return { keyMetrics, planSummary };
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Audit Log</h2>
        <div className="flex gap-2">
          <button 
            onClick={() => fetchAuditLogs()} 
            className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCwIcon className="h-4 w-4" />
            Refresh
          </button>
          <button 
            onClick={() => exportAuditLogs('csv')} 
            className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
          >
            <DownloadIcon className="h-4 w-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Total Logs</div>
            <div className="text-2xl font-bold">{summary.total_logs}</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Recent Activity (24h)</div>
            <div className="text-2xl font-bold">{summary.recent_activity_24h}</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Avg Improvement</div>
            <div className="text-2xl font-bold">{summary.average_improvement_percent.toFixed(1)}%</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Action Types</div>
            <div className="text-2xl font-bold">{Object.keys(summary.action_type_counts).length}</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <FilterIcon className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters(prev => ({ ...prev, start_date: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters(prev => ({ ...prev, end_date: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
            <select 
              value={filters.action_type} 
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilters(prev => ({ ...prev, action_type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All actions</option>
              {actionTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Audit Logs</h3>
        </div>
        <div className="p-6">
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCwIcon className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Timestamp</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Action</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Compare</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Risk Level</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Improvement</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Query</th>
                  </tr>
                </thead>
                <tbody>
                  {(auditLogs || []).map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="text-xs text-gray-600">{formatDate(log.created_at)}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{log.action_type}</div>
                        {log.recommendation_id && (
                          <div className="text-sm text-gray-500">ID: {log.recommendation_id}</div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
                          onClick={() => {
                            setCompareLog(log);
                            setShowRawData(false);
                          }}
                        >
                          <EyeIcon className="w-3 h-3" />
                          View
                        </button>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskLevelColor(log.risk_level)}`}>
                          {log.risk_level || 'N/A'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(log.status)}`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {log.improvement_percent ? (
                          <span className={log.improvement_percent > 0 ? 'text-green-600' : 'text-red-600'}>
                            {log.improvement_percent > 0 ? '+' : ''}{log.improvement_percent.toFixed(1)}%
                          </span>
                        ) : 'N/A'}
                      </td>
                      <td className="py-3 px-4 max-w-md truncate" title={(log.details && (log.details.sql_executed || log.details.original_sql)) || ''}>
                        <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
                          {(log.details && (log.details.sql_executed || log.details.original_sql)) || '—'}
                        </code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {auditLogs.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No audit logs found
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Compare Modal */}
      {compareLog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setCompareLog(null)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h4 className="text-lg font-semibold">Before vs After</h4>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={showRawData}
                    onChange={(e) => setShowRawData(e.target.checked)}
                    className="w-4 h-4"
                  />
                  Show Raw Data
                </label>
                <button className="text-gray-600 hover:text-gray-900" onClick={() => setCompareLog(null)}>
                  <XIcon className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-4 space-y-4">
              {/* Summary Section */}
              {(() => {
                const beforeData = formatMetricsForDisplay(compareLog.before_metrics);
                const afterData = formatMetricsForDisplay(compareLog.after_metrics);
                
                if (!beforeData || !afterData) return null;
                
                const beforeTotal = beforeData.keyMetrics.total_time * 1000;
                const afterTotal = afterData.keyMetrics.total_time * 1000;
                const improvement = ((beforeTotal - afterTotal) / beforeTotal) * 100;
                const timeSaved = beforeTotal - afterTotal;
                
                return (
                  <div className="bg-gradient-to-r from-blue-50 to-green-50 p-4 rounded-lg border border-blue-200">
                    <h5 className="text-sm font-semibold text-gray-800 mb-3">Performance Summary</h5>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center">
                        <div className="text-xs text-gray-600">Before</div>
                        <div className="text-lg font-bold text-red-600">{beforeTotal.toFixed(2)}ms</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-600">After</div>
                        <div className="text-lg font-bold text-green-600">{afterTotal.toFixed(2)}ms</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-600">Time Saved</div>
                        <div className="text-lg font-bold text-blue-600">{timeSaved.toFixed(2)}ms</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-600">Improvement</div>
                        <div className="text-lg font-bold text-green-600">+{improvement.toFixed(1)}%</div>
                      </div>
                    </div>
                  </div>
                );
              })()}
              
              <div>
                <div className="text-sm text-gray-600 mb-1">Recommendation ID</div>
                <div className="font-mono text-sm">{compareLog.recommendation_id || 'N/A'}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">SQL Applied</div>
                <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
{((compareLog.details && (compareLog.details.sql_executed || compareLog.details.original_sql)) || '—')}
                </pre>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded p-3">
                  <div className="text-sm font-medium mb-2 text-red-600">Before</div>
                  {(() => {
                    const beforeData = formatMetricsForDisplay(compareLog.before_metrics);
                    if (!beforeData) return <div className="text-xs text-gray-500">No metrics available</div>;
                    
                    return (
                      <div className="space-y-3">
                        {/* Key Performance Metrics */}
                        <div>
                          <h5 className="text-xs font-semibold text-gray-700 mb-2">Performance Metrics</h5>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-red-50 p-2 rounded">
                              <span className="font-medium">Total Time:</span>
                              <div className="text-red-600 font-bold">{(beforeData.keyMetrics.total_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-red-50 p-2 rounded">
                              <span className="font-medium">Execution:</span>
                              <div className="text-red-600">{(beforeData.keyMetrics.execution_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-red-50 p-2 rounded">
                              <span className="font-medium">Planning:</span>
                              <div className="text-red-600">{(beforeData.keyMetrics.planning_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-red-50 p-2 rounded">
                              <span className="font-medium">Rows:</span>
                              <div className="text-red-600">{beforeData.keyMetrics.rows}</div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Execution Plan Summary */}
                        <div>
                          <h5 className="text-xs font-semibold text-gray-700 mb-2">Execution Plan</h5>
                          <div className="bg-gray-50 p-2 rounded text-xs font-mono whitespace-pre-line">
                            {beforeData.planSummary}
                          </div>
                        </div>
                        
                        {/* Query Used */}
                        {beforeData.keyMetrics.query_used && (
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-2">Query</h5>
                            <div className="bg-gray-100 p-2 rounded text-xs font-mono">
                              {beforeData.keyMetrics.query_used}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
                
                <div className="border rounded p-3">
                  <div className="text-sm font-medium mb-2 text-green-600">After</div>
                  {(() => {
                    const afterData = formatMetricsForDisplay(compareLog.after_metrics);
                    if (!afterData) return <div className="text-xs text-gray-500">No metrics available</div>;
                    
                    return (
                      <div className="space-y-3">
                        {/* Key Performance Metrics */}
                        <div>
                          <h5 className="text-xs font-semibold text-gray-700 mb-2">Performance Metrics</h5>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-green-50 p-2 rounded">
                              <span className="font-medium">Total Time:</span>
                              <div className="text-green-600 font-bold">{(afterData.keyMetrics.total_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-green-50 p-2 rounded">
                              <span className="font-medium">Execution:</span>
                              <div className="text-green-600">{(afterData.keyMetrics.execution_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-green-50 p-2 rounded">
                              <span className="font-medium">Planning:</span>
                              <div className="text-green-600">{(afterData.keyMetrics.planning_time * 1000).toFixed(2)}ms</div>
                            </div>
                            <div className="bg-green-50 p-2 rounded">
                              <span className="font-medium">Rows:</span>
                              <div className="text-green-600">{afterData.keyMetrics.rows}</div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Execution Plan Summary */}
                        <div>
                          <h5 className="text-xs font-semibold text-gray-700 mb-2">Execution Plan</h5>
                          <div className="bg-gray-50 p-2 rounded text-xs font-mono whitespace-pre-line">
                            {afterData.planSummary}
                          </div>
                        </div>
                        
                        {/* Query Used */}
                        {afterData.keyMetrics.query_used && (
                          <div>
                            <h5 className="text-xs font-semibold text-gray-700 mb-2">Query</h5>
                            <div className="bg-gray-100 p-2 rounded text-xs font-mono">
                              {afterData.keyMetrics.query_used}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
              {typeof compareLog.improvement_percent === 'number' && (
                <div className="text-sm">
                  Improvement: <span className={compareLog.improvement_percent > 0 ? 'text-green-600' : 'text-red-600'}>
                    {compareLog.improvement_percent > 0 ? '+' : ''}{compareLog.improvement_percent.toFixed(1)}%
                  </span>
                </div>
              )}

              {/* Raw Data Section (Toggle) */}
              {showRawData && (
                <div className="border-t pt-4">
                  <h5 className="text-sm font-semibold text-gray-700 mb-3">Raw Data (Advanced)</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h6 className="text-xs font-medium text-gray-600 mb-2">Before Metrics (Raw)</h6>
                      <pre className="text-xs bg-gray-100 p-3 rounded overflow-auto max-h-64">
                        {JSON.stringify(compareLog.before_metrics, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <h6 className="text-xs font-medium text-gray-600 mb-2">After Metrics (Raw)</h6>
                      <pre className="text-xs bg-gray-100 p-3 rounded overflow-auto max-h-64">
                        {JSON.stringify(compareLog.after_metrics, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 