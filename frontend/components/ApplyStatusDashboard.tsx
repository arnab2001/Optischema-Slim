'use client';

import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Clock, RotateCcw, Play, Zap, RefreshCw } from 'lucide-react';

export function ApplyStatusDashboard() {
  const [status, setStatus] = useState<any>(null);
  const [changes, setChanges] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [auditFallback, setAuditFallback] = useState<any[]>([]);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const [statusResponse, changesResponse] = await Promise.all([
        fetch('/api/apply/status'),
        fetch('/api/apply/changes')
      ]);
      
      const statusResult = await statusResponse.json();
      const changesResult = await changesResponse.json();
      
      if (statusResult.success) {
        setStatus(statusResult.data);
      }
      
      if (changesResult.success) {
        setChanges(changesResult.data.changes || []);
      }
      
      // Fallback to audit logs if no in-memory changes present
      if ((!changesResult.success || (changesResult.data?.changes || []).length === 0)) {
        try {
          const auditRes = await fetch('/api/audit/logs?action_type=recommendation_applied&limit=50');
          const auditData = await auditRes.json();
          if (auditData.success) {
            const mapped = (auditData.data || []).map((log: any) => ({
              status: log.status || 'applied',
              applied_at: log.created_at,
              recommendation_id: log.recommendation_id,
              sql_executed: (log.details && (log.details.sql_executed || log.details.ddl_executed)) || '',
              schema_name: (log.details && log.details.schema_name) || 'sandbox',
              rollback_sql: (log.details && log.details.rollback_sql) || null,
              rolled_back_at: null,
            }));
            setAuditFallback(mapped);
          } else {
            setAuditFallback([]);
          }
        } catch (e) {
          setAuditFallback([]);
        }
      } else {
        setAuditFallback([]);
      }
    } catch (error) {
      console.error('Failed to fetch apply status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'applied':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'rolled_back':
        return <RotateCcw className="w-4 h-4 text-orange-600" />;
      case 'running':
        return <Clock className="w-4 h-4 text-blue-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return 'bg-green-100 text-green-800';
      case 'rolled_back':
        return 'bg-orange-100 text-orange-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold">Apply Manager Status</h2>
        </div>
        <button
          onClick={fetchStatus}
          disabled={isLoading}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      {/* Status Overview */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium">Total Changes</span>
            </div>
            <p className="text-2xl font-bold">{status.total_changes}</p>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Play className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium">Applied</span>
            </div>
            <p className="text-2xl font-bold text-green-600">
              {status.status_counts?.applied || 0}
            </p>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <RotateCcw className="w-5 h-5 text-orange-600" />
              <span className="text-sm font-medium">Rolled Back</span>
            </div>
            <p className="text-2xl font-bold text-orange-600">
              {status.status_counts?.rolled_back || 0}
            </p>
          </div>
        </div>
      )}

      {/* Applied Changes List (with audit fallback) */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Applied Changes</h3>
        
        {(changes.length === 0 && auditFallback.length === 0) ? (
          <div className="text-center py-8 text-muted-foreground">
            <Zap className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>No changes have been applied yet.</p>
            <p className="text-sm">Run benchmarks and apply recommendations to see changes here.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {(changes.length > 0 ? changes : auditFallback).map((change, index) => (
              <div
                key={index}
                className="border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(change.status)}
                    <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(change.status)}`}>
                      {change.status.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(change.applied_at).toLocaleString()}
                  </span>
                </div>
                
                <div className="mb-3">
                  <h4 className="font-medium text-sm mb-1">Recommendation ID</h4>
                  <p className="text-sm text-muted-foreground font-mono">
                    {change.recommendation_id}
                  </p>
                </div>
                
                <div className="mb-3">
                  <h4 className="font-medium text-sm mb-1">SQL Executed</h4>
                  <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                    {change.sql_executed || '—'}
                  </pre>
                </div>
                
                {change.rolled_back_at && (
                  <div className="mb-3">
                    <h4 className="font-medium text-sm mb-1">Rolled Back At</h4>
                    <p className="text-sm text-muted-foreground">
                      {new Date(change.rolled_back_at).toLocaleString()}
                    </p>
                  </div>
                )}
                
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Schema: {change.schema_name || 'sandbox'}</span>
                  {change.rollback_sql && (
                    <span className="text-green-600">• Rollback available</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available Operations */}
      {status && (
        <div className="bg-card border border-border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Available Operations</h3>
          <div className="flex flex-wrap gap-2">
            {status.available_operations?.map((op: string) => (
              <span
                key={op}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {op}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 