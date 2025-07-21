'use client';

import React, { useState, useEffect } from 'react';
import { DownloadIcon, FilterIcon, RefreshCwIcon } from 'lucide-react';

interface AuditLog {
  id: string;
  action_type: string;
  user_id: string;
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
    user_id: '',
    limit: 100,
    offset: 0
  });
  const [actionTypes, setActionTypes] = useState<string[]>([]);
  const [users, setUsers] = useState<string[]>([]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.user_id) params.append('user_id', filters.user_id);
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

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/audit/users');
      const data = await response.json();
      if (data.success) {
        setUsers(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const exportAuditLogs = async (format: 'csv' | 'json' = 'csv') => {
    try {
      const params = new URLSearchParams();
      
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.user_id) params.append('user_id', filters.user_id);
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
    fetchUsers();
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">User</label>
            <select 
              value={filters.user_id} 
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilters(prev => ({ ...prev, user_id: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All users</option>
              {users.map(user => (
                <option key={user} value={user}>{user}</option>
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
                    <th className="text-left py-3 px-4 font-medium text-gray-700">User</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Risk Level</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Improvement</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Before Metrics</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">After Metrics</th>
                  </tr>
                </thead>
                <tbody>
                  {(auditLogs || []).map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{log.action_type}</div>
                        {log.recommendation_id && (
                          <div className="text-sm text-gray-500">ID: {log.recommendation_id}</div>
                        )}
                      </td>
                      <td className="py-3 px-4">{log.user_id || 'System'}</td>
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
                      <td className="py-3 px-4 max-w-xs truncate" title={formatMetrics(log.before_metrics)}>
                        {formatMetrics(log.before_metrics)}
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate" title={formatMetrics(log.after_metrics)}>
                        {formatMetrics(log.after_metrics)}
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
    </div>
  );
} 