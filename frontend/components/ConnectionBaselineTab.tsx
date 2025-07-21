'use client';

import React, { useState, useEffect } from 'react';
import { WifiIcon, RefreshCwIcon, PlusIcon, TrashIcon } from 'lucide-react';

interface ConnectionBaseline {
  id: string;
  connection_id: string;
  connection_name: string;
  baseline_latency_ms: number;
  measured_at: string;
  is_active: boolean;
  connection_config?: ConnectionConfig;
}

interface BaselineSummary {
  total_active_baselines: number;
  average_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  recent_measurements_24h: number;
}

interface ConnectionConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
  ssl?: string;
}

export default function ConnectionBaselineTab() {
  const [baselines, setBaselines] = useState<ConnectionBaseline[]>([]);
  const [summary, setSummary] = useState<BaselineSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [measuring, setMeasuring] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newConnection, setNewConnection] = useState<ConnectionConfig>({
    host: '',
    port: 5432,
    database: '',
    user: '',
    password: '',
    ssl: 'require'
  });
  const [connectionName, setConnectionName] = useState('');

  const fetchBaselines = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/connection-baseline/baselines');
      const data = await response.json();
      
      if (data.success) {
        setBaselines(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch baselines:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch('/api/connection-baseline/summary');
      const data = await response.json();
      
      if (data.success) {
        setSummary(data.data || null);
      }
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  const measureBaseline = async () => {
    if (!connectionName.trim() || !newConnection.host.trim() || !newConnection.database.trim()) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      setMeasuring(true);
      
      // Parse host to extract hostname and port if needed
      let host = newConnection.host;
      let port = newConnection.port;
      
      // If host contains port (e.g., "hostname:port"), extract it
      if (host.includes(':')) {
        const [hostname, hostPort] = host.split(':');
        host = hostname;
        port = parseInt(hostPort) || newConnection.port;
      }
      
      const connectionConfig = {
        ...newConnection,
        host: host,
        port: port
      };
      
      const response = await fetch('/api/connection-baseline/measure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          connection_config: connectionConfig,
          connection_name: connectionName
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        alert(`Baseline measured successfully: ${data.data.baseline_latency_ms.toFixed(2)}ms`);
        setShowAddForm(false);
        setConnectionName('');
        setNewConnection({
          host: '',
          port: 5432,
          database: '',
          user: '',
          password: ''
        });
        fetchBaselines();
        fetchSummary();
      } else {
        alert(`Failed to measure baseline: ${data.message}`);
      }
    } catch (error) {
      console.error('Failed to measure baseline:', error);
      alert('Failed to measure baseline');
    } finally {
      setMeasuring(false);
    }
  };

  const updateBaseline = async (connectionConfig: ConnectionConfig) => {
    try {
      const response = await fetch('/api/connection-baseline/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          connection_config: connectionConfig
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        alert(`Baseline updated successfully: ${data.new_latency_ms.toFixed(2)}ms`);
        fetchBaselines();
        fetchSummary();
      } else {
        alert(`Failed to update baseline: ${data.detail}`);
      }
    } catch (error) {
      console.error('Failed to update baseline:', error);
      alert('Failed to update baseline');
    }
  };

  const deactivateBaseline = async (connectionId: string) => {
    if (!confirm('Are you sure you want to deactivate this baseline?')) {
      return;
    }

    try {
      const response = await fetch(`/api/connection-baseline/baseline/${connectionId}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      
      if (data.success) {
        alert('Baseline deactivated successfully');
        fetchBaselines();
        fetchSummary();
      } else {
        alert(`Failed to deactivate baseline: ${data.detail}`);
      }
    } catch (error) {
      console.error('Failed to deactivate baseline:', error);
      alert('Failed to deactivate baseline');
    }
  };

  useEffect(() => {
    fetchBaselines();
    fetchSummary();
  }, []);

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

  const getLatencyColor = (latency: number) => {
    if (latency < 10) return 'text-green-600';
    if (latency < 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getLatencyBadge = (latency: number) => {
    if (latency < 10) return 'bg-green-100 text-green-800';
    if (latency < 50) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Connection Baselines</h2>
        <div className="flex gap-2">
          <button 
            onClick={() => { fetchBaselines(); fetchSummary(); }} 
            className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCwIcon className="h-4 w-4" />
            Refresh
          </button>
          <button 
            onClick={() => setShowAddForm(true)} 
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
          >
            <PlusIcon className="h-4 w-4" />
            Add Baseline
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Total Baselines</div>
            <div className="text-2xl font-bold">{summary.total_active_baselines}</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Avg Latency</div>
            <div className={`text-2xl font-bold ${getLatencyColor(summary.average_latency_ms)}`}>
              {summary.average_latency_ms?.toFixed(1) || '0.0'}ms
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Min Latency</div>
            <div className="text-2xl font-bold text-green-600">{summary.min_latency_ms?.toFixed(1) || '0.0'}ms</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="text-sm font-medium text-gray-600 mb-2">Max Latency</div>
            <div className="text-2xl font-bold text-red-600">{summary.max_latency_ms?.toFixed(1) || '0.0'}ms</div>
          </div>
        </div>
      )}

      {/* Add Baseline Form */}
      {showAddForm && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Add New Connection Baseline</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Connection Name</label>
              <input
                type="text"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                placeholder="e.g., Production DB, Read Replica"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
              <input
                type="text"
                value={newConnection.host}
                onChange={(e) => setNewConnection(prev => ({ ...prev, host: e.target.value }))}
                placeholder="localhost"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
              <input
                type="number"
                value={newConnection.port}
                onChange={(e) => setNewConnection(prev => ({ ...prev, port: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Database</label>
              <input
                type="text"
                value={newConnection.database}
                onChange={(e) => setNewConnection(prev => ({ ...prev, database: e.target.value }))}
                placeholder="mydb"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text"
                value={newConnection.user}
                onChange={(e) => setNewConnection(prev => ({ ...prev, user: e.target.value }))}
                placeholder="postgres"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                value={newConnection.password}
                onChange={(e) => setNewConnection(prev => ({ ...prev, password: e.target.value }))}
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">SSL Mode</label>
              <select
                value={newConnection.ssl}
                onChange={(e) => setNewConnection(prev => ({ ...prev, ssl: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="require">Require SSL (Recommended for RDS)</option>
                <option value="prefer">Prefer SSL</option>
                <option value="disable">Disable SSL</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={measureBaseline}
              disabled={measuring}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {measuring ? (
                <>
                  <RefreshCwIcon className="h-4 w-4 animate-spin" />
                  Measuring...
                </>
              ) : (
                <>
                  <WifiIcon className="h-4 w-4" />
                  Measure Baseline
                </>
              )}
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Baselines Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Connection Baselines</h3>
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
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Connection Name</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Baseline Latency</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Measured At</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(baselines || []).map((baseline) => (
                    <tr key={baseline.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="font-medium">{baseline.connection_name}</div>
                        <div className="text-sm text-gray-500">ID: {baseline.connection_id}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getLatencyBadge(baseline.baseline_latency_ms)}`}>
                          {baseline.baseline_latency_ms.toFixed(2)}ms
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {formatDate(baseline.measured_at)}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          baseline.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {baseline.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => baseline.connection_config && updateBaseline(baseline.connection_config)}
                            disabled={!baseline.connection_config}
                            className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200 disabled:opacity-50"
                          >
                            Update
                          </button>
                          <button
                            onClick={() => deactivateBaseline(baseline.connection_id)}
                            className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 flex items-center gap-1"
                          >
                            <TrashIcon className="h-3 w-3" />
                            Deactivate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {baselines.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No connection baselines found. Add your first baseline to get started.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 