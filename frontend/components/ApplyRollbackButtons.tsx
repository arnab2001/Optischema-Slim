'use client';

import React, { useState } from 'react';

interface ApplyRollbackButtonsProps {
  recommendationId: string;
  isApplied: boolean;
  onApply?: () => void;
  onRollback?: () => void;
  disabled?: boolean;
}

export function ApplyRollbackButtons({
  recommendationId,
  isApplied,
  onApply,
  onRollback,
  disabled = false
}: ApplyRollbackButtonsProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [action, setAction] = useState<'apply' | 'rollback' | null>(null);

  const handleApply = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setAction('apply');
    
    try {
      const response = await fetch(`/api/apply/${recommendationId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const result = await response.json();
      
      if (result.success) {
        onApply?.();
      } else {
        console.error('Apply failed:', result.message);
      }
    } catch (error) {
      console.error('Apply error:', error);
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
      const response = await fetch(`/api/apply/${recommendationId}/rollback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const result = await response.json();
      
      if (result.success) {
        onRollback?.();
      } else {
        console.error('Rollback failed:', result.message);
      }
    } catch (error) {
      console.error('Rollback error:', error);
    } finally {
      setIsLoading(false);
      setAction(null);
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-lg font-semibold">Apply / Rollback</h3>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          isApplied ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
        }`}>
          {isApplied ? "Applied" : "Pending"}
        </span>
      </div>
      
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            onClick={handleApply}
            disabled={disabled || isLoading || isApplied}
            className={`flex-1 px-4 py-2 rounded font-medium ${
              disabled || isLoading || isApplied
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isLoading && action === 'apply' ? 'Applying...' : 'Apply'}
          </button>
          
          <button
            onClick={handleRollback}
            disabled={disabled || isLoading || !isApplied}
            className={`flex-1 px-4 py-2 rounded font-medium border ${
              disabled || isLoading || !isApplied
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {isLoading && action === 'rollback' ? 'Rolling back...' : 'Rollback'}
          </button>
        </div>
        
        <div className="text-sm text-gray-600">
          <p>• Apply: Executes DDL changes on sandbox database</p>
          <p>• Rollback: Reverts applied changes safely</p>
          <p>• All operations are logged and tracked</p>
        </div>
      </div>
    </div>
  );
}

export function ApplyStatusCard() {
  const [status, setStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/apply/status');
      const result = await response.json();
      if (result.success) {
        setStatus(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  React.useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-lg font-semibold">Apply Manager Status</h3>
        <button
          onClick={fetchStatus}
          disabled={isLoading}
          className="px-2 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      
      <div className="space-y-2">
        {status ? (
          <>
            <div className="flex justify-between">
              <span>Total Changes:</span>
              <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-sm">
                {status.total_changes}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Status Counts:</span>
              <div className="flex gap-1">
                {Object.entries(status.status_counts).map(([status, count]) => (
                  <span key={status} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                    {status}: {String(count)}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex justify-between">
              <span>Operations:</span>
              <div className="flex gap-1">
                {status.available_operations.map((op: string) => (
                  <span key={op} className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                    {op}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="text-center text-gray-500">
            {isLoading ? 'Loading...' : 'No status available'}
          </div>
        )}
      </div>
    </div>
  );
} 