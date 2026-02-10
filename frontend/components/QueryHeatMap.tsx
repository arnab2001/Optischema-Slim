'use client'

import type * as React from "react";
import { useState, useEffect } from 'react'
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts'
import { AlertTriangle, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'

interface QueryData {
  mean_time: number
  calls: number
  queryid: string
  query_text: string
  performance_score?: number
  time_percentage?: number
}

interface QueryHeatMapProps {
  data: QueryData[]
  onQueryClick?: (query: QueryData) => void
}

const QueryHeatMap: React.FC<QueryHeatMapProps> = ({ data, onQueryClick }) => {
  const [chartData, setChartData] = useState<any[]>([])
  const [hoveredPoint, setHoveredPoint] = useState<any>(null)
  const [chartType, setChartType] = useState<'scatter' | 'heatmap'>('scatter')
  const [heatmapData, setHeatmapData] = useState<any[]>([])

  useEffect(() => {
    if (!data || data.length === 0) return

    // Calculate data ranges for better scaling
    const calls = data.map(item => item.calls).filter(c => c > 0)
    const times = data.map(item => item.mean_time).filter(t => t > 0)
    
    const minCalls = Math.min(...calls)
    const maxCalls = Math.max(...calls)
    const minTime = Math.min(...times)
    const maxTime = Math.max(...times)
    
    // Use logarithmic scaling for better distribution
    const logMinCalls = Math.log10(Math.max(1, minCalls))
    const logMaxCalls = Math.log10(Math.max(1, maxCalls))
    const logMinTime = Math.log10(Math.max(0.1, minTime))
    const logMaxTime = Math.log10(Math.max(0.1, maxTime))

    // Transform data for scatter plot with better scaling
    const transformedData = data.map((item, index) => {
      const logCalls = Math.log10(Math.max(1, item.calls))
      const logTime = Math.log10(Math.max(0.1, item.mean_time))
      
      // Normalize to 0-100 scale for better visualization
      const normalizedX = ((logCalls - logMinCalls) / (logMaxCalls - logMinCalls)) * 100
      const normalizedY = ((logTime - logMinTime) / (logMaxTime - logMinTime)) * 100
      
      return {
        x: normalizedX,
        y: normalizedY,
        originalCalls: item.calls,
        originalTime: item.mean_time,
        queryid: item.queryid,
        query_text: item.query_text,
        performance_score: item.performance_score || 50,
        time_percentage: item.time_percentage || 0,
        size: Math.max(8, Math.min(25, (item.time_percentage || 0) * 3)), // Larger size range
        color: getColorByPerformance(item.performance_score || 50),
        opacity: Math.min(1, Math.max(0.3, (item.time_percentage || 0) / 10)) // Opacity based on importance
      }
    })

    setChartData(transformedData)

    // Generate heatmap data
    const generateHeatmapData = () => {
      const gridSize = 20
      const heatmap = []
      
      for (let i = 0; i < gridSize; i++) {
        for (let j = 0; j < gridSize; j++) {
          const x = (i / gridSize) * 100
          const y = (j / gridSize) * 100
          
          // Find queries in this grid cell
          const queriesInCell = transformedData.filter(point => 
            Math.abs(point.x - x) < 5 && Math.abs(point.y - y) < 5
          )
          
          if (queriesInCell.length > 0) {
            const totalTimePercentage = queriesInCell.reduce((sum, q) => sum + q.time_percentage, 0)
            const avgPerformance = queriesInCell.reduce((sum, q) => sum + q.performance_score, 0) / queriesInCell.length
            
            heatmap.push({
              x: i,
              y: j,
              value: totalTimePercentage,
              performance: avgPerformance,
              queries: queriesInCell,
              color: getColorByPerformance(avgPerformance),
              opacity: Math.min(1, totalTimePercentage / 20)
            })
          }
        }
      }
      
      setHeatmapData(heatmap)
    }
    
    generateHeatmapData()
  }, [data])

  const getColorByPerformance = (score: number): string => {
    if (score >= 80) return '#10b981' // Green
    if (score >= 60) return '#f59e0b' // Yellow
    return '#ef4444' // Red
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
          <p className="font-medium text-gray-900">Query Performance</p>
          <p className="text-sm text-gray-600">Calls: {data.originalCalls.toLocaleString()}</p>
          <p className="text-sm text-gray-600">Avg Time: {data.originalTime.toFixed(2)}ms</p>
          <p className="text-sm text-gray-600">Performance Score: {data.performance_score}%</p>
          <p className="text-sm text-gray-600">Time %: {data.time_percentage.toFixed(1)}%</p>
          <div className="mt-2 max-w-xs">
            <p className="text-xs text-gray-500 truncate">{data.query_text}</p>
          </div>
        </div>
      )
    }
    return null
  }

  const handlePointClick = (data: any) => {
    if (onQueryClick) {
      const queryData: QueryData = {
        mean_time: data.originalTime,
        calls: data.originalCalls,
        queryid: data.queryid,
        query_text: data.query_text,
        performance_score: data.performance_score,
        time_percentage: data.time_percentage
      }
      onQueryClick(queryData)
    }
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">No query data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Query Performance Heat Map</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <button
              onClick={() => setChartType('scatter')}
              className={`px-2 py-1 rounded text-xs ${
                chartType === 'scatter' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Scatter View
            </button>
            <button
              onClick={() => setChartType('heatmap')}
              className={`px-2 py-1 rounded text-xs ${
                chartType === 'heatmap' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Heat Map
            </button>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Good (80%+)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span>Fair (60-79%)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Poor (&lt;60%)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="h-80">
        {chartType === 'scatter' ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart
              margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
              onClick={handlePointClick}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Calls (log scale)"
                label={{ value: 'Number of Calls (Log Scale)', position: 'insideBottom', offset: -10 }}
                domain={[0, 100]}
                tickFormatter={(value) => {
                  // Convert back to original scale for display
                  const calls = data.map(item => item.calls).filter(c => c > 0)
                  const minCalls = Math.min(...calls)
                  const maxCalls = Math.max(...calls)
                  const logMinCalls = Math.log10(Math.max(1, minCalls))
                  const logMaxCalls = Math.log10(Math.max(1, maxCalls))
                  const originalValue = Math.pow(10, logMinCalls + (value / 100) * (logMaxCalls - logMinCalls))
                  return originalValue.toLocaleString()
                }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Mean Time (log scale)"
                label={{ value: 'Mean Execution Time (ms, Log Scale)', angle: -90, position: 'insideLeft' }}
                domain={[0, 100]}
                tickFormatter={(value) => {
                  // Convert back to original scale for display
                  const times = data.map(item => item.mean_time).filter(t => t > 0)
                  const minTime = Math.min(...times)
                  const maxTime = Math.max(...times)
                  const logMinTime = Math.log10(Math.max(0.1, minTime))
                  const logMaxTime = Math.log10(Math.max(0.1, maxTime))
                  const originalValue = Math.pow(10, logMinTime + (value / 100) * (logMaxTime - logMinTime))
                  return originalValue.toFixed(1)
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Scatter data={chartData} fill="#8884d8">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    opacity={entry.opacity}
                    onMouseEnter={() => setHoveredPoint(entry)}
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <div className="relative w-full h-full">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <BarChart3 className="w-8 h-8 mx-auto mb-2" />
                <p>Heat Map View</p>
                <p className="text-sm">Coming soon...</p>
              </div>
            </div>
            {/* Heat map grid would go here */}
            <div className="absolute inset-0 grid grid-cols-20 grid-rows-20 gap-0">
              {heatmapData.map((cell, index) => (
                <div
                  key={index}
                  className="border border-gray-100"
                  style={{
                    backgroundColor: cell.color,
                    opacity: cell.opacity,
                    cursor: 'pointer'
                  }}
                  onClick={() => {
                    if (cell.queries && cell.queries.length > 0) {
                      handlePointClick(cell.queries[0])
                    }
                  }}
                  title={`${cell.queries?.length || 0} queries, ${cell.value.toFixed(1)}% time, ${cell.performance.toFixed(0)}% performance`}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <p>• <strong>Logarithmic scaling</strong> spreads data across the chart for better visualization</p>
        <p>• <strong>Point size</strong> indicates time percentage of total database time</p>
        <p>• <strong>Color</strong> indicates performance score (green = good, yellow = fair, red = poor)</p>
        <p>• <strong>Opacity</strong> indicates query importance (more opaque = higher time percentage)</p>
        <p>• Click on a point to view detailed query analysis</p>
      </div>
    </div>
  )
}

export default QueryHeatMap 