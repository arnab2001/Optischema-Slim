'use client'

import type * as React from "react";
import { useState, useEffect } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Area, AreaChart } from 'recharts'
import { AlertTriangle, TrendingUp, TrendingDown, Clock } from 'lucide-react'

interface LatencyData {
  timestamp: string
  avg_latency: number
  p95_latency: number
  p99_latency: number
  total_queries: number
  slow_queries: number
}

interface LatencyTrendChartProps {
  data: LatencyData[]
  timeRange?: '1h' | '6h' | '24h' | '7d'
  onTimeRangeChange?: (range: string) => void
}

const LatencyTrendChart: React.FC<LatencyTrendChartProps> = ({ 
  data, 
  timeRange = '1h',
  onTimeRangeChange 
}) => {
  const [chartData, setChartData] = useState<any[]>([])
  const [selectedMetric, setSelectedMetric] = useState<'avg' | 'p95' | 'p99'>('avg')

  useEffect(() => {
    if (!data || data.length === 0) return

    // Transform data for chart
    const transformedData = data.map((item, index) => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      timestamp: item.timestamp,
      avg: item.avg_latency,
      p95: item.p95_latency,
      p99: item.p99_latency,
      total: item.total_queries,
      slow: item.slow_queries,
      slowPercentage: item.total_queries > 0 ? (item.slow_queries / item.total_queries) * 100 : 0
    }))

    setChartData(transformedData)
  }, [data])

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
          <p className="font-medium text-gray-900">{data.time}</p>
          <p className="text-sm text-gray-600">Avg Latency: {data.avg.toFixed(2)}ms</p>
          <p className="text-sm text-gray-600">P95 Latency: {data.p95.toFixed(2)}ms</p>
          <p className="text-sm text-gray-600">P99 Latency: {data.p99.toFixed(2)}ms</p>
          <p className="text-sm text-gray-600">Total Queries: {data.total.toLocaleString()}</p>
          <p className="text-sm text-gray-600">Slow Queries: {data.slow.toLocaleString()} ({data.slowPercentage.toFixed(1)}%)</p>
        </div>
      )
    }
    return null
  }

  const getMetricColor = (metric: string): string => {
    switch (metric) {
      case 'avg': return '#3b82f6' // Blue
      case 'p95': return '#f59e0b' // Yellow
      case 'p99': return '#ef4444' // Red
      default: return '#3b82f6'
    }
  }

  const getMetricName = (metric: string): string => {
    switch (metric) {
      case 'avg': return 'Average'
      case 'p95': return '95th Percentile'
      case 'p99': return '99th Percentile'
      default: return 'Average'
    }
  }

  const calculateTrend = (): { direction: 'up' | 'down' | 'stable', percentage: number } => {
    if (chartData.length < 2) return { direction: 'stable', percentage: 0 }
    
    const first = chartData[0][selectedMetric]
    const last = chartData[chartData.length - 1][selectedMetric]
    const percentage = ((last - first) / first) * 100
    
    if (percentage > 5) return { direction: 'up', percentage: Math.abs(percentage) }
    if (percentage < -5) return { direction: 'down', percentage: Math.abs(percentage) }
    return { direction: 'stable', percentage: Math.abs(percentage) }
  }

  const trend = calculateTrend()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">No latency data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-gray-900">Latency Trends</h3>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-gray-500" />
            <span className="text-gray-600">Last {timeRange}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 text-sm">
            {trend.direction === 'up' && <TrendingUp className="w-4 h-4 text-red-500" />}
            {trend.direction === 'down' && <TrendingDown className="w-4 h-4 text-green-500" />}
            <span className={`text-sm ${
              trend.direction === 'up' ? 'text-red-600' : 
              trend.direction === 'down' ? 'text-green-600' : 'text-gray-600'
            }`}>
              {trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : '±'}
              {trend.percentage.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Metric:</span>
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as 'avg' | 'p95' | 'p99')}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="avg">Average</option>
            <option value="p95">95th Percentile</option>
            <option value="p99">99th Percentile</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Time Range:</span>
          <select
            value={timeRange}
            onChange={(e) => onTimeRangeChange?.(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="1h">1 Hour</option>
            <option value="6h">6 Hours</option>
            <option value="24h">24 Hours</option>
            <option value="7d">7 Days</option>
          </select>
        </div>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time" 
              label={{ value: 'Time', position: 'insideBottom', offset: -10 }}
            />
            <YAxis 
              label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey={selectedMetric}
              stroke={getMetricColor(selectedMetric)}
              fill={getMetricColor(selectedMetric)}
              fillOpacity={0.3}
              name={getMetricName(selectedMetric)}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div className="text-center">
          <p className="text-gray-600">Current {getMetricName(selectedMetric)}</p>
          <p className="text-lg font-semibold text-gray-900">
            {chartData.length > 0 ? chartData[chartData.length - 1][selectedMetric].toFixed(2) : '0'}ms
          </p>
        </div>
        <div className="text-center">
          <p className="text-gray-600">Total Queries</p>
          <p className="text-lg font-semibold text-gray-900">
            {chartData.length > 0 ? chartData[chartData.length - 1].total.toLocaleString() : '0'}
          </p>
        </div>
        <div className="text-center">
          <p className="text-gray-600">Slow Query %</p>
          <p className="text-lg font-semibold text-gray-900">
            {chartData.length > 0 ? chartData[chartData.length - 1].slowPercentage.toFixed(1) : '0'}%
          </p>
        </div>
      </div>
    </div>
  )
}

export default LatencyTrendChart 