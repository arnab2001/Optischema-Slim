'use client'

import type * as React from "react";
import { useState } from 'react'
import { Download, FileText, FileCode, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'

interface Recommendation {
  id: string
  title: string
  description: string
  sql_fix?: string
  estimated_improvement_percent?: number
  confidence_score?: number
  risk_level?: string
  recommendation_type: string
}

interface ExportManagerProps {
  recommendations: Recommendation[]
  metrics?: any[]
  onExport?: (type: 'sql' | 'pdf', data: any) => void
}

const ExportManager: React.FC<ExportManagerProps> = ({ 
  recommendations, 
  metrics = [],
  onExport 
}) => {
  const [isExporting, setIsExporting] = useState(false)
  const [exportType, setExportType] = useState<'sql' | 'pdf' | null>(null)
  const [selectedRecommendations, setSelectedRecommendations] = useState<string[]>([])

  const handleSelectAll = () => {
    if (selectedRecommendations.length === recommendations.length) {
      setSelectedRecommendations([])
    } else {
      setSelectedRecommendations(recommendations.map(r => r.id))
    }
  }

  const handleSelectRecommendation = (id: string) => {
    setSelectedRecommendations(prev => 
      prev.includes(id) 
        ? prev.filter(r => r !== id)
        : [...prev, id]
    )
  }

  const exportSQL = async () => {
    setIsExporting(true)
    setExportType('sql')

    try {
      const selectedRecs = recommendations.filter(r => selectedRecommendations.includes(r.id))
      const sqlContent = generateSQLContent(selectedRecs)
      
      // Create and download SQL file
      const blob = new Blob([sqlContent], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `optischema_optimizations_${new Date().toISOString().split('T')[0]}.sql`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      onExport?.('sql', selectedRecs)
    } catch (error) {
      console.error('SQL export failed:', error)
    } finally {
      setIsExporting(false)
      setExportType(null)
    }
  }

  const exportPDF = async () => {
    setIsExporting(true)
    setExportType('pdf')

    try {
      const selectedRecs = recommendations.filter(r => selectedRecommendations.includes(r.id))
      await generatePDFReport(selectedRecs, metrics)
      onExport?.('pdf', selectedRecs)
    } catch (error) {
      console.error('PDF export failed:', error)
    } finally {
      setIsExporting(false)
      setExportType(null)
    }
  }

  const generateSQLContent = (recs: Recommendation[]): string => {
    let content = `-- OptiSchema Optimization Recommendations\n`
    content += `-- Generated on: ${new Date().toLocaleString()}\n`
    content += `-- Total recommendations: ${recs.length}\n\n`

    recs.forEach((rec, index) => {
      content += `-- Recommendation ${index + 1}: ${rec.title}\n`
      content += `-- Confidence: ${rec.confidence_score}% | Risk: ${rec.risk_level || 'Unknown'}\n`
      content += `-- Estimated improvement: ${rec.estimated_improvement_percent || 'Unknown'}%\n`
      content += `-- Description: ${rec.description}\n\n`

      if (rec.sql_fix) {
        content += `${rec.sql_fix}\n\n`
      } else {
        content += `-- No SQL fix available for this recommendation\n\n`
      }
    })

    return content
  }

  const generatePDFReport = async (recs: Recommendation[], metrics: any[]) => {
    const pdf = new jsPDF()
    
    // Title
    pdf.setFontSize(20)
    pdf.text('OptiSchema Performance Report', 20, 20)
    
    pdf.setFontSize(12)
    pdf.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30)
    pdf.text(`Total recommendations: ${recs.length}`, 20, 40)
    
    let yPosition = 60

    // Summary
    pdf.setFontSize(16)
    pdf.text('Executive Summary', 20, yPosition)
    yPosition += 10

    pdf.setFontSize(10)
    const totalImprovement = recs.reduce((sum, r) => sum + (r.estimated_improvement_percent || 0), 0)
    const avgConfidence = recs.reduce((sum, r) => sum + (r.confidence_score || 0), 0) / recs.length

    pdf.text(`• Total estimated improvement: ${totalImprovement.toFixed(1)}%`, 20, yPosition)
    yPosition += 7
    pdf.text(`• Average confidence score: ${avgConfidence.toFixed(1)}%`, 20, yPosition)
    yPosition += 7
    pdf.text(`• High-risk recommendations: ${recs.filter(r => r.risk_level === 'high').length}`, 20, yPosition)
    yPosition += 15

    // Recommendations
    pdf.setFontSize(16)
    pdf.text('Detailed Recommendations', 20, yPosition)
    yPosition += 10

    recs.forEach((rec, index) => {
      if (yPosition > 250) {
        pdf.addPage()
        yPosition = 20
      }

      pdf.setFontSize(12)
      pdf.text(`${index + 1}. ${rec.title}`, 20, yPosition)
      yPosition += 7

      pdf.setFontSize(10)
      pdf.text(`Confidence: ${rec.confidence_score}% | Risk: ${rec.risk_level || 'Unknown'} | Improvement: ${rec.estimated_improvement_percent || 'Unknown'}%`, 20, yPosition)
      yPosition += 7

      // Wrap description text
      const description = rec.description
      const maxWidth = 170
      const words = description.split(' ')
      let line = ''
      let lines = []

      words.forEach(word => {
        const testLine = line + word + ' '
        if (pdf.getTextWidth(testLine) < maxWidth) {
          line = testLine
        } else {
          lines.push(line)
          line = word + ' '
        }
      })
      lines.push(line)

      lines.forEach(line => {
        if (yPosition > 250) {
          pdf.addPage()
          yPosition = 20
        }
        pdf.text(line, 20, yPosition)
        yPosition += 5
      })

      if (rec.sql_fix) {
        yPosition += 3
        pdf.setFontSize(9)
        pdf.text('SQL Fix:', 20, yPosition)
        yPosition += 5
        pdf.text(rec.sql_fix, 20, yPosition)
        yPosition += 10
      } else {
        yPosition += 5
      }
    })

    // Save PDF
    pdf.save(`optischema_report_${new Date().toISOString().split('T')[0]}.pdf`)
  }

  if (recommendations.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-center h-32">
          <div className="text-center">
            <AlertCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">No recommendations available for export</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Export Recommendations</h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">
            {selectedRecommendations.length} of {recommendations.length} selected
          </span>
        </div>
      </div>

      {/* Selection Controls */}
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={handleSelectAll}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          {selectedRecommendations.length === recommendations.length ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      {/* Recommendations List */}
      <div className="max-h-64 overflow-y-auto mb-4 border border-gray-200 rounded">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className={`flex items-center gap-3 p-3 border-b border-gray-100 last:border-b-0 cursor-pointer hover:bg-gray-50 ${
              selectedRecommendations.includes(rec.id) ? 'bg-blue-50' : ''
            }`}
            onClick={() => handleSelectRecommendation(rec.id)}
          >
            <input
              type="checkbox"
              checked={selectedRecommendations.includes(rec.id)}
              onChange={() => handleSelectRecommendation(rec.id)}
              className="rounded"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {rec.title.startsWith('#') ? rec.title.replace(/^#+\s*/, '').trim() : rec.title}
              </p>
              <p className="text-xs text-gray-600">
                {rec.confidence_score}% confidence • {rec.estimated_improvement_percent || 'Unknown'}% improvement
              </p>
            </div>
            <div className="flex items-center gap-2">
              {rec.sql_fix && <FileCode className="w-4 h-4 text-green-600" />}
              <span className={`px-2 py-1 rounded text-xs ${
                rec.risk_level === 'low' ? 'bg-green-100 text-green-800' :
                rec.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {rec.risk_level || 'Unknown'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Export Buttons */}
      <div className="flex items-center gap-3">
        <button
          onClick={exportSQL}
          disabled={selectedRecommendations.length === 0 || isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExporting && exportType === 'sql' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileCode className="w-4 h-4" />
          )}
          Export SQL
        </button>

        <button
          onClick={exportPDF}
          disabled={selectedRecommendations.length === 0 || isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExporting && exportType === 'pdf' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileText className="w-4 h-4" />
          )}
          Export PDF Report
        </button>
      </div>

      <div className="mt-3 text-xs text-gray-600">
        <p>• SQL export includes all selected recommendations with their SQL fixes</p>
        <p>• PDF report includes detailed analysis and recommendations summary</p>
      </div>
    </div>
  )
}

export default ExportManager 