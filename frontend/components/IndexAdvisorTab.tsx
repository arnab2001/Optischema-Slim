'use client';

import React, { useState, useEffect } from 'react';
import { DatabaseIcon, RefreshCwIcon, AlertTriangleIcon, TrashIcon, PlayIcon, ShoppingCart, Check } from 'lucide-react';
import { useCartStore } from '@/store/cartStore';

interface IndexRecommendation {
  id: string;
  index_name: string;
  table_name: string;
  schema_name: string;
  size_bytes: number;
  size_pretty: string;
  idx_scan: number;
  idx_tup_read: number;
  idx_tup_fetch: number;
  last_used: string | null;
  days_unused: number;
  estimated_savings_mb: number;
  risk_level: string;
  recommendation_type: string;
  sql_fix: string;
  created_at: string;
}

interface IndexSummary {
  total_recommendations: number;
  recommendations_by_type: Record<string, number>;
  recommendations_by_risk: Record<string, number>;
  total_potential_savings_mb: number;
  recent_recommendations_24h: number;
}

function IndexAdvisorCartButton({ rec }: { rec: IndexRecommendation }) {
  const { addItem } = useCartStore();
  const inCart = useCartStore((s) => s.isInCart(rec.sql_fix));

  return (
    <button
      onClick={() => {
        if (!inCart) {
          addItem({
            id: rec.id,
            type: rec.recommendation_type === 'drop' ? 'drop' : 'index',
            sql: rec.sql_fix,
            description: `${rec.recommendation_type === 'drop' ? 'Drop' : 'Optimize'} ${rec.index_name} on ${rec.table_name}`,
            table: rec.table_name,
            estimatedImprovement: rec.estimated_savings_mb,
            source: 'index-advisor',
          });
        }
      }}
      className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
        inCart
          ? 'bg-blue-100 text-blue-700 cursor-default'
          : 'bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200'
      }`}
    >
      {inCart ? <Check className="h-3 w-3" /> : <ShoppingCart className="h-3 w-3" />}
      {inCart ? 'In Cart' : 'Add to Cart'}
    </button>
  );
}

export default function IndexAdvisorTab() {
  const [recommendations, setRecommendations] = useState<IndexRecommendation[]>([]);
  const [summary, setSummary] = useState<IndexSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [filters, setFilters] = useState({
    risk_level: '',
    recommendation_type: '',
    limit: 100
  });
  const [useSandbox, setUseSandbox] = useState(false);
  const [presentIndexes, setPresentIndexes] = useState<any[]>([]);
  const [loadingIndexes, setLoadingIndexes] = useState(false);
  const [collapseDuplicates, setCollapseDuplicates] = useState(true);
  const [showUnusedOnly, setShowUnusedOnly] = useState(false);
  const [showLowUsageOnly, setShowLowUsageOnly] = useState(false);
  const [topN, setTopN] = useState(100);
  const [schemaFilter, setSchemaFilter] = useState('');

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (filters.risk_level) params.append('risk_level', filters.risk_level);
      if (filters.recommendation_type) params.append('recommendation_type', filters.recommendation_type);
      params.append('limit', filters.limit.toString());

      const response = await fetch(`/api/index-advisor/recommendations?${params}`);
      const data = await response.json();
      
      if (data.success) {
        setRecommendations(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch('/api/index-advisor/summary');
      const data = await response.json();
      
      if (data.success) {
        setSummary(data.data || null);
      }
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  const runAnalysis = async () => {
    try {
      setAnalyzing(true);
      let response: Response;
      if (useSandbox) {
        response = await fetch('/api/index-advisor/analyze/sandbox', { method: 'POST' });
      } else {
        // Get the current connection config from the connection status
        const connectionResponse = await fetch('/api/connection/status');
        const connectionData = await connectionResponse.json();
        if (!connectionData.connected) {
          alert('No active database connection. Please connect to a database first.');
          return;
        }
        const connectionConfig = connectionData.current_config;
        response = await fetch('/api/index-advisor/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ connection_config: connectionConfig }),
        });
      }

      const data = await response.json();
      
      if (data.success) {
        alert(`Analysis completed successfully!\n\nFound:\n- ${data.data.unused_indexes} unused indexes\n- ${data.data.redundant_indexes} redundant indexes\n- Total potential savings: ${data.data.total_potential_savings_mb.toFixed(1)} MB`);
        fetchRecommendations();
        fetchSummary();
      } else {
        alert(`Failed to run analysis: ${data.detail}`);
      }
    } catch (error) {
      console.error('Failed to run analysis:', error);
      alert('Failed to run analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchPresentIndexes = async () => {
    try {
      setLoadingIndexes(true);
      const response = await fetch(`/api/index-advisor/present-indexes?use_sandbox=${useSandbox ? 'true' : 'false'}`);
      const data = await response.json();
      if (data.success) {
        setPresentIndexes(data.data || []);
      } else {
        setPresentIndexes([]);
      }
    } catch (e) {
      console.error('Failed to fetch present indexes:', e);
      setPresentIndexes([]);
    } finally {
      setLoadingIndexes(false);
    }
  };

  // Auto-load indexes on mount and when toggling sandbox
  useEffect(() => {
    fetchPresentIndexes();
  }, []);
  useEffect(() => {
    fetchPresentIndexes();
  }, [useSandbox]);

  const normalizeDefinition = (def: string) => {
    if (!def) return '';
    try {
      // Remove schema qualifications like "schema".table or schema.table
      return def
        .replace(/"[^"\s]+"\./g, '')
        .replace(/\b[a-zA-Z_][a-zA-Z0-9_]*\./g, '')
        .replace(/\s+/g, ' ')
        .trim();
    } catch {
      return def;
    }
  };

  const filteredIndexes = React.useMemo(() => {
    let list = [...presentIndexes];
    if (schemaFilter.trim()) {
      const f = schemaFilter.trim().toLowerCase();
      list = list.filter((idx) => `${idx.schema_name}`.toLowerCase().includes(f));
    }
    if (showUnusedOnly) {
      list = list.filter((idx) => (idx.idx_scan ?? 0) === 0);
    }
    if (showLowUsageOnly) {
      list = list.filter((idx) => (idx.idx_scan ?? 0) > 0 && (idx.idx_scan ?? 0) < 10);
    }
    // Sort by size descending by default to surface largest
    list.sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0));
    return list;
  }, [presentIndexes, schemaFilter, showUnusedOnly, showLowUsageOnly]);

  const groupedIndexes = React.useMemo(() => {
    if (!collapseDuplicates) return filteredIndexes.slice(0, topN);
    const groups: Record<string, any> = {};
    for (const idx of filteredIndexes) {
      const signature = `${idx.index_name}::${idx.table_name}::${normalizeDefinition(idx.index_definition)}`;
      if (!groups[signature]) {
        groups[signature] = {
          ...idx,
          schemas_count: 1,
          schemas: new Set<string>([idx.schema_name]),
          total_size_bytes: idx.size_bytes || 0,
          max_idx_scan: idx.idx_scan || 0,
        };
      } else {
        const g = groups[signature];
        g.schemas.add(idx.schema_name);
        g.schemas_count = g.schemas.size;
        g.total_size_bytes += idx.size_bytes || 0;
        g.max_idx_scan = Math.max(g.max_idx_scan, idx.idx_scan || 0);
        // Prefer the largest definition row as representative
        if ((idx.size_bytes || 0) > (g.size_bytes || 0)) {
          g.schema_name = idx.schema_name;
          g.table_name = idx.table_name;
          g.index_definition = idx.index_definition;
          g.size_bytes = idx.size_bytes;
          g.size_pretty = idx.size_pretty;
        }
      }
    }
    const aggregated = Object.values(groups)
      .sort((a: any, b: any) => (b.total_size_bytes || 0) - (a.total_size_bytes || 0));
    return aggregated.slice(0, topN);
  }, [filteredIndexes, collapseDuplicates, topN]);

  const applyRecommendation = async (recommendationId: string) => {
    if (!confirm('Are you sure you want to apply this recommendation? This will execute the SQL fix.')) {
      return;
    }

    try {
      const response = await fetch(`/api/index-advisor/recommendations/${recommendationId}/apply`, {
        method: 'POST',
      });

      const data = await response.json();
      
      if (data.success) {
        alert('Recommendation applied successfully');
        fetchRecommendations();
        fetchSummary();
      } else {
        alert(`Failed to apply recommendation: ${data.detail}`);
      }
    } catch (error) {
      console.error('Failed to apply recommendation:', error);
      alert('Failed to apply recommendation');
    }
  };

  const deleteRecommendation = async (recommendationId: string) => {
    if (!confirm('Are you sure you want to delete this recommendation?')) {
      return;
    }

    try {
      const response = await fetch(`/api/index-advisor/recommendations/${recommendationId}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      
      if (data.success) {
        alert('Recommendation deleted successfully');
        fetchRecommendations();
        fetchSummary();
      } else {
        alert(`Failed to delete recommendation: ${data.detail}`);
      }
    } catch (error) {
      console.error('Failed to delete recommendation:', error);
      alert('Failed to delete recommendation');
    }
  };

  useEffect(() => {
    fetchRecommendations();
    fetchSummary();
  }, [filters]);

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

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getRecommendationTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'drop': return 'bg-red-100 text-red-800';
      case 'analyze': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Index Advisor</h2>
        <div className="flex gap-3 items-center">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useSandbox}
              onChange={(e) => { setUseSandbox(e.target.checked); }}
            />
            Use Sandbox DB
          </label>
          <button 
            onClick={() => { fetchRecommendations(); fetchSummary(); }} 
            className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCwIcon className="h-4 w-4" />
            Refresh
          </button>
          <button 
            onClick={runAnalysis}
            disabled={analyzing}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {analyzing ? (
              <>
                <RefreshCwIcon className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <DatabaseIcon className="h-4 w-4" />
                Run Analysis
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary Cards (hidden if all zeros) */}
      {(() => {
        const hasData = !!summary && (
          (summary.total_recommendations || 0) > 0 ||
          (summary.total_potential_savings_mb || 0) > 0 ||
          (summary.recommendations_by_type?.drop || 0) > 0 ||
          (summary.recommendations_by_type?.analyze || 0) > 0
        );
        return hasData;
      })() && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Total Recommendations</div>
            <div className="text-2xl font-bold">{summary?.total_recommendations || 0}</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Total Savings</div>
            <div className="text-2xl font-bold text-green-600">{summary?.total_potential_savings_mb?.toFixed(1) || '0.0'} MB</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Drop Recommendations</div>
            <div className="text-2xl font-bold text-red-600">{summary?.recommendations_by_type?.drop || 0}</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Analyze Recommendations</div>
            <div className="text-2xl font-bold text-yellow-600">{summary?.recommendations_by_type?.analyze || 0}</div>
          </div>
        </div>
      )}

      {/* Risk Breakdown (hidden if all zeros) */}
      {(() => {
        const totalRisk = (summary?.recommendations_by_risk?.low || 0) + (summary?.recommendations_by_risk?.medium || 0) + (summary?.recommendations_by_risk?.high || 0);
        return totalRisk > 0;
      })() && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Risk Breakdown</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary?.recommendations_by_risk?.low || 0}</div>
              <div className="text-sm text-gray-600">Low Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">{summary?.recommendations_by_risk?.medium || 0}</div>
              <div className="text-sm text-gray-600">Medium Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{summary?.recommendations_by_risk?.high || 0}</div>
              <div className="text-sm text-gray-600">High Risk</div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity (hidden if zero) */}
      {(summary?.recent_recommendations_24h || 0) > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{summary?.recent_recommendations_24h || 0}</div>
            <div className="text-sm text-gray-600">Recommendations in last 24h</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Risk Level</label>
            <select 
              value={filters.risk_level} 
              onChange={(e) => setFilters(prev => ({ ...prev, risk_level: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All risk levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Recommendation Type</label>
            <select 
              value={filters.recommendation_type} 
              onChange={(e) => setFilters(prev => ({ ...prev, recommendation_type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All types</option>
              <option value="drop">Drop</option>
              <option value="analyze">Analyze</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Limit</label>
            <select 
              value={filters.limit} 
              onChange={(e) => setFilters(prev => ({ ...prev, limit: parseInt(e.target.value) }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
            </select>
          </div>
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Index Recommendations</h3>
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
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Index</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Table</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Size</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Usage</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Savings</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Risk</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(recommendations || []).map((rec) => (
                    <tr key={rec.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium">{rec.index_name}</div>
                        <div className="text-sm text-gray-500">{rec.schema_name}</div>
                      </td>
                      <td className="py-3 px-4">{rec.table_name}</td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{rec.size_pretty}</div>
                        <div className="text-sm text-gray-500">{formatSize(rec.size_bytes)}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{rec.idx_scan} scans</div>
                        <div className="text-sm text-gray-500">{rec.days_unused} days unused</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-green-600">
                          {rec.estimated_savings_mb.toFixed(1)} MB
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskLevelColor(rec.risk_level)}`}>
                          {rec.risk_level}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRecommendationTypeColor(rec.recommendation_type)}`}>
                          {rec.recommendation_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <IndexAdvisorCartButton rec={rec} />
                        <div className="flex gap-2 mt-1">
                          <button
                            onClick={() => applyRecommendation(rec.id)}
                            className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200 flex items-center gap-1"
                            title="Apply recommendation"
                          >
                            <PlayIcon className="h-3 w-3" />
                            Apply
                          </button>
                          <button
                            onClick={() => deleteRecommendation(rec.id)}
                            className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 flex items-center gap-1"
                            title="Delete recommendation"
                          >
                            <TrashIcon className="h-3 w-3" />
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {recommendations.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No index recommendations found. Run an analysis to discover optimization opportunities.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Present Indexes Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between gap-4 flex-wrap">
          <h3 className="text-lg font-semibold">Present Indexes {useSandbox ? '(Sandbox)' : '(Connected DB)'}</h3>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Filter schema..."
              value={schemaFilter}
              onChange={(e) => setSchemaFilter(e.target.value)}
              className="px-2 py-1 text-sm border rounded"
            />
            <label className="text-sm flex items-center gap-2">
              <input type="checkbox" checked={showUnusedOnly} onChange={(e) => setShowUnusedOnly(e.target.checked)} />
              Unused only
            </label>
            <label className="text-sm flex items-center gap-2">
              <input type="checkbox" checked={showLowUsageOnly} onChange={(e) => setShowLowUsageOnly(e.target.checked)} />
              Low usage (&lt;10 scans)
            </label>
            <label className="text-sm flex items-center gap-2">
              <input type="checkbox" checked={collapseDuplicates} onChange={(e) => setCollapseDuplicates(e.target.checked)} />
              Collapse per-tenant duplicates
            </label>
            <label className="text-sm flex items-center gap-2">
              Top
              <select className="px-2 py-1 text-sm border rounded" value={topN} onChange={(e) => setTopN(parseInt(e.target.value))}>
                {[50, 100, 200, 500, 1000].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
            <button 
              onClick={fetchPresentIndexes}
              className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
            >
              <RefreshCwIcon className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>
        <div className="p-6">
          {loadingIndexes ? (
            <div className="flex justify-center py-8">
              <RefreshCwIcon className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Index</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Table</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Size</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Usage</th>
                    {collapseDuplicates && <th className="text-left py-3 px-4 font-medium text-gray-700">Schemas</th>}
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Definition</th>
                  </tr>
                </thead>
                <tbody>
                  {(groupedIndexes || []).map((idx: any) => (
                    <tr key={`${idx.schema_name}.${idx.index_name}.${idx.index_definition}`} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium">{idx.index_name}</div>
                        <div className="text-sm text-gray-500">{idx.schema_name}</div>
                      </td>
                      <td className="py-3 px-4">{idx.table_name}</td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{collapseDuplicates ? formatSize(idx.total_size_bytes) : idx.size_pretty}</div>
                        {!collapseDuplicates && (
                          <div className="text-sm text-gray-500">{formatSize(idx.size_bytes)}</div>
                        )}
                      </td>
                      <td className="py-3 px-4">{collapseDuplicates ? (idx.max_idx_scan || 0) : (idx.idx_scan || 0)} scans</td>
                      {collapseDuplicates && (
                        <td className="py-3 px-4">{idx.schemas_count}</td>
                      )}
                      <td className="py-3 px-4">
                        <code className="text-xs bg-gray-100 px-1 py-0.5 rounded inline-block max-w-[500px] truncate" title={idx.index_definition}>
                          {idx.index_definition}
                        </code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {groupedIndexes.length === 0 && (
                <div className="text-center py-8 text-gray-500">No indexes found.</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 