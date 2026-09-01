import React, { useState } from 'react'
import { Server, CheckCircle2, AlertTriangle, X, RefreshCw } from 'lucide-react'
import { workflowClient } from '../services/workflowClient'

export default function ServerConfigModal({ isOpen, onClose, onServerUpdated }) {
  const [url, setUrl] = useState(workflowClient.getServerUrl())
  const [testResult, setTestResult] = useState(null)
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleTest = async () => {
    setLoading(true)
    setTestResult(null)
    const res = await workflowClient.testConnection(url)
    setTestResult(res)
    setLoading(false)
  }

  const handleSave = () => {
    workflowClient.setServerUrl(url)
    if (onServerUpdated) onServerUpdated(url)
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="flex items-center gap-2">
            <Server size={18} color="#818cf8" />
            <span className="modal-title">Workflow Server Connection</span>
          </div>
          <button className="icon-btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <p className="text-sm text-muted mb-4">
            Connect your local application to the deployed central Workflow Engine running on your server or another machine (e.g. <code>http://192.168.1.183:8000</code>).
          </p>

          <div className="field-group mb-4">
            <label className="field-label">Central Workflow Server URL</label>
            <input
              type="text"
              className="text-input font-mono"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="e.g. http://192.168.1.183:8000"
            />
          </div>

          <div className="flex gap-2 mb-4">
            <button
              type="button"
              className="preset-btn"
              onClick={() => setUrl('http://localhost:8000')}
            >
              Localhost (8000)
            </button>
            <button
              type="button"
              className="preset-btn"
              onClick={() => setUrl('http://192.168.1.183:8000')}
            >
              Server (192.168.1.183)
            </button>
          </div>

          {testResult && (
            <div className={`status-banner ${testResult.success ? 'success' : 'error'} mb-4`}>
              {testResult.success ? (
                <CheckCircle2 size={16} color="#4ade80" />
              ) : (
                <AlertTriangle size={16} color="#f87171" />
              )}
              <span className="text-xs">{testResult.message}</span>
            </div>
          )}
        </div>

        <div className="modal-footer flex justify-between items-center">
          <button
            className="btn btn-outline"
            onClick={handleTest}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>{loading ? 'Testing...' : 'Test Connection'}</span>
          </button>

          <div className="flex gap-2">
            <button className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSave}>
              Save Connection
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
