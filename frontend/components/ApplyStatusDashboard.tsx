'use client';

import React, { useState, useEffect } from 'react';
import { Zap, CheckCircle, Play, RotateCcw, RefreshCw, BarChart3, AlertCircle, Loader2, Clock, XCircle } from 'lucide-react';

export function ApplyStatusDashboard() {
  const [status, setStatus] = useState<any>(null);
  const [changes, setChanges] = useState<any[]>([]);
  const [auditFallback, setAuditFallback] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [rollbackStates, setRollbackStates] = useState<Record<string, 'idle' | 'loading' | 'success' | 'error'>>({});
  const [rollbackMessages, setRollbackMessages] = useState<Record<string, string>>({});
  const [rollbackConfirm, setRollbackConfirm] = useState<{ show: boolean; change: any | null }>({ show: false, change: null });
  const [toast, setToast] = useState<{ show: boolean; message: string; type: 'success' | 'error' | 'info' }>({ show: false, message: '', type: 'info' });

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast({ show: false, message: '', type: 'info' }), 4000);
  };

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
      case 'completed':
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
      case 'completed':
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

  const handleRollback = async (change: any) => {
    if (!change?.recommendation_id) return;
    
    const id = change.recommendation_id;
    
    // Set loading state for this specific rollback
    setRollbackStates(prev => ({ ...prev, [id]: 'loading' }));
    setRollbackMessages(prev => ({ ...prev, [id]: 'Initiating rollback...' }));
    
    // Close confirmation dialog
    setRollbackConfirm({ show: false, change: null });
    
    try {
      // Try ApplyManager rollback first
      let res = await fetch(`/api/apply/${id}/rollback`, { method: 'POST' });
      let data: any = {};
      
      if (res.ok) {
        data = await res.json().catch(() => ({}));
      } else {
        // Fallback to apply-and-test rollback
        res = await fetch('/api/suggestions/rollback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recommendation_id: id })
        });
        data = await res.json().catch(() => ({}));
      }
      
      if (res.ok && (data.success !== false)) {
        // Success - update state and show confirmation
        const successMessage = data.message || 'Rollback completed successfully!';
        setRollbackStates(prev => ({ ...prev, [id]: 'success' }));
        setRollbackMessages(prev => ({ 
          ...prev, 
          [id]: successMessage
        }));
        
        // Show success toast
        showToast(successMessage, 'success');
        
        // Refresh status after a brief delay to show the success state
        setTimeout(() => {
          fetchStatus();
          // Reset rollback state after showing success
          setTimeout(() => {
            setRollbackStates(prev => ({ ...prev, [id]: 'idle' }));
            setRollbackMessages(prev => ({ ...prev, [id]: '' }));
          }, 3000);
        }, 1000);
        
      } else {
        // Rollback failed
        const errorMessage = data?.message || data?.detail || 'Rollback failed';
        console.error('Rollback failed:', data);
        
        setRollbackStates(prev => ({ ...prev, [id]: 'error' }));
        setRollbackMessages(prev => ({ ...prev, [id]: errorMessage }));
        
        // Show error toast
        showToast(errorMessage, 'error');
        
        // Reset error state after some time
        setTimeout(() => {
          setRollbackStates(prev => ({ ...prev, [id]: 'idle' }));
          setRollbackMessages(prev => ({ ...prev, [id]: '' }));
        }, 5000);
      }
    } catch (e) {
      console.error('Rollback error:', e);
      const errorMessage = 'Rollback failed due to a network or server error.';
      
      setRollbackStates(prev => ({ ...prev, [id]: 'error' }));
      setRollbackMessages(prev => ({ ...prev, [id]: errorMessage }));
      
      // Show error toast
      showToast(errorMessage, 'error');
      
      // Reset error state after some time
      setTimeout(() => {
        setRollbackStates(prev => ({ ...prev, [id]: 'idle' }));
        setRollbackMessages(prev => ({ ...prev, [id]: '' }));
      }, 5000);
    }
  };

  const getRollbackButton = (change: any) => {
    const id = change.recommendation_id;
    const rollbackState = rollbackStates[id] || 'idle';
    const rollbackMessage = rollbackMessages[id] || '';
    
    if (rollbackState === 'loading') {
      return (
        <button
          disabled
          className="px-3 py-1 text-xs bg-yellow-600 text-white rounded flex items-center gap-1"
        >
          <Loader2 className="w-3 h-3 animate-spin" />
          Rolling Back...
        </button>
      );
    }
    
    if (rollbackState === 'success') {
      return (
        <div className="flex items-center gap-2">
          <button
            disabled
            className="px-3 py-1 text-xs bg-green-600 text-white rounded flex items-center gap-1"
          >
            <CheckCircle className="w-3 h-3" />
            Rolled Back
          </button>
          <span className="text-xs text-green-600">{rollbackMessage}</span>
        </div>
      );
    }
    
    if (rollbackState === 'error') {
      return (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleRollback(change)}
            className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
          >
            <AlertCircle className="w-3 h-3" />
            Retry Rollback
          </button>
          <span className="text-xs text-red-600 max-w-32 truncate" title={rollbackMessage}>
            {rollbackMessage}
          </span>
        </div>
      );
    }
    
    // Default state - show rollback button
    return (
      <button
        onClick={() => setRollbackConfirm({ show: true, change })}
        className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
      >
        <RotateCcw className="w-3 h-3" />
        Rollback
      </button>
    );
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
            <p className="text-xs text-gray-500 mt-1">
              {Object.values(rollbackStates).filter(state => state === 'loading').length > 0 && 
                `${Object.values(rollbackStates).filter(state => state === 'loading').length} rolling back...`}
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

                <div className="mt-3 flex gap-2">
                  {(change.status === 'applied' || change.status === 'completed') && change.recommendation_id && (
                    getRollbackButton(change)
                  )}
                  {/* Compare modal trigger placeholder */}
                  {change.recommendation_id && (
                    <button
                      onClick={() => {
                        // Navigate to audit with filter to compare before vs after for this recommendation
                        window.location.hash = `#audit-${change.recommendation_id}`;
                      }}
                      className="px-3 py-1 text-xs bg-gray-100 text-gray-800 rounded hover:bg-gray-200"
                    >
                      Compare Before/After
                    </button>
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

      {/* Rollback Confirmation Dialog */}
      {rollbackConfirm.show && rollbackConfirm.change && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setRollbackConfirm({ show: false, change: null })}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <RotateCcw className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Confirm Rollback</h3>
                  <p className="text-sm text-gray-600">This action cannot be undone</p>
                </div>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-700 mb-2">
                  You are about to rollback the following optimization:
                </p>
                <div className="bg-gray-50 p-3 rounded border">
                  <p className="text-xs font-mono text-gray-800">
                    {rollbackConfirm.change.sql_executed || 'No SQL available'}
                  </p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setRollbackConfirm({ show: false, change: null })}
                  className="flex-1 px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleRollback(rollbackConfirm.change)}
                  className="flex-1 px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700"
                >
                  Confirm Rollback
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      {toast.show && (
        <div className="fixed top-4 right-4 z-50">
          <div className={`px-4 py-3 rounded-lg shadow-lg max-w-sm ${
            toast.type === 'success' ? 'bg-green-500 text-white' :
            toast.type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
          }`}>
            <div className="flex items-center gap-2">
              {toast.type === 'success' && <CheckCircle className="w-4 h-4" />}
              {toast.type === 'error' && <AlertCircle className="w-4 h-4" />}
              {toast.type === 'info' && <Zap className="w-4 h-4" />}
              <span className="text-sm font-medium">{toast.message}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 