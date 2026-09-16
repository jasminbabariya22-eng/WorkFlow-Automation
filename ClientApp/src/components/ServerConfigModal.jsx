import React, { useState, useEffect } from 'react'
import { Server, CheckCircle2, AlertTriangle, X, RefreshCw, Unlink, WifiOff, Check } from 'lucide-react'
import { workflowClient } from '../services/workflowClient'

export default function ServerConfigModal({ isOpen, onClose, onServerUpdated }) {
  const [url, setUrl] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setUrl(workflowClient.getServerUrl() || '')
      setTestResult(null)
      setLoading(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleTest = async () => {
    if (!url.trim()) {
      setTestResult({
        success: false,
        isDisconnected: true,
        message: 'No server URL entered. Application is in Disconnected / Offline mode.'
      })
      return
    }
    setLoading(true)
    setTestResult(null)
    const res = await workflowClient.testConnection(url)
    setTestResult(res)
    setLoading(false)
  }

  const handleSave = () => {
    const trimmed = (url || '').trim()
    workflowClient.setServerUrl(trimmed)
    if (onServerUpdated) onServerUpdated(trimmed)
    onClose()
  }

  const handleDisconnect = () => {
    setUrl('')
    workflowClient.disconnect()
    if (onServerUpdated) onServerUpdated('')
    onClose()
  }

  const isDisconnected = !url.trim()

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
          <p className="text-sm text-muted mb-2">
            Connect your local application to the deployed central Workflow Engine running on your server or another machine (e.g. <code>http://192.168.1.183:8000</code>).
          </p>

          <div className="info-banner mb-4">
            <span className="text-xs text-slate-300">
              💡 <strong>Optional Connection:</strong> Connecting to a central workflow server is optional. You can disconnect anytime to run in standalone / local clientDB mode.
            </span>
          </div>

          <div className="field-group mb-3">
            <div className="flex items-center justify-between mb-1">
              <label className="field-label mb-0">Central Workflow Server URL</label>
              {isDisconnected ? (
                <span className="badge badge-neutral text-xs" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>
                  Disconnected (Offline)
                </span>
              ) : (
                <span className="badge text-xs" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                  Server Configured
                </span>
              )}
            </div>
            <div className="relative">
              <input
                type="text"
                className="text-input font-mono"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value)
                  setTestResult(null)
                }}
                placeholder="e.g. http://192.168.1.183:8000 (leave empty for No Connection)"
              />
              {url && (
                <button
                  type="button"
                  className="icon-btn-sm absolute right-2 top-2.5 text-muted hover:text-white"
                  onClick={() => {
                    setUrl('')
                    setTestResult(null)
                  }}
                  title="Clear URL"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Preset Buttons including No Connection */}
          <div className="flex flex-wrap gap-2 mb-4">
            <button
              type="button"
              className={`preset-btn ${url === 'http://localhost:8000' ? 'active font-bold border-indigo-500' : ''}`}
              onClick={() => {
                setUrl('http://localhost:8000')
                setTestResult(null)
              }}
            >
              Localhost (8000)
            </button>
            <button
              type="button"
              className={`preset-btn ${url === 'http://192.168.1.183:8000' ? 'active font-bold border-indigo-500' : ''}`}
              onClick={() => {
                setUrl('http://192.168.1.183:8000')
                setTestResult(null)
              }}
            >
              Server (192.168.1.183)
            </button>
            <button
              type="button"
              className={`preset-btn ${isDisconnected ? 'active font-bold' : ''}`}
              style={isDisconnected ? { borderColor: '#f87171', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.1)' } : {}}
              onClick={() => {
                setUrl('')
                setTestResult({
                  success: true,
                  isDisconnected: true,
                  message: 'Disconnected mode selected (Optional / Standalone)'
                })
              }}
              title="Work without workflow server"
            >
              <WifiOff size={11} style={{ display: 'inline', marginRight: 4 }} />
              No Connection (Disconnect)
            </button>
          </div>

          {testResult && (
            <div className={`status-banner ${testResult.isDisconnected ? 'neutral' : testResult.success ? 'success' : 'error'} mb-2`}>
              {testResult.isDisconnected ? (
                <WifiOff size={16} color="#94a3b8" />
              ) : testResult.success ? (
                <CheckCircle2 size={16} color="#4ade80" />
              ) : (
                <AlertTriangle size={16} color="#f87171" />
              )}
              <span className="text-xs">{testResult.message}</span>
            </div>
          )}

          {isDisconnected && !testResult && (
            <div className="status-banner neutral mb-2" style={{ background: 'rgba(148, 163, 184, 0.08)', border: '1px solid rgba(148, 163, 184, 0.2)' }}>
              <WifiOff size={15} color="#94a3b8" />
              <span className="text-xs text-slate-300">
                Workflow connection is currently disconnected. Application will run in local standalone mode.
              </span>
            </div>
          )}
        </div>

        <div className="modal-footer flex justify-between items-center">
          <div className="flex items-center gap-2">
            <button
              className="btn btn-outline"
              onClick={handleTest}
              disabled={loading || isDisconnected}
              title={isDisconnected ? 'Enter a URL to test connection' : 'Test server connection'}
            >
              <RefreshCw size={13} className={loading ? 'spin' : ''} />
              <span>{loading ? 'Testing...' : 'Test Connection'}</span>
            </button>

            {!isDisconnected && (
              <button
                className="btn btn-danger-outline text-xs"
                onClick={handleDisconnect}
                title="Disconnect from central server"
              >
                <Unlink size={13} />
                <span>Disconnect</span>
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <button className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSave}>
              {isDisconnected ? 'Save (No Connection)' : 'Save Connection'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
