import React from 'react'
import { Check, AlertCircle, XCircle, X } from 'lucide-react'

export default function DesignerValidationModal({
  isOpen,
  onClose,
  validationErrors,
  onSelectNode
}) {
  if (!isOpen) return null

  return (
    <div className="wf-validation-modal-overlay" onClick={onClose}>
      <div className="wf-validation-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="wf-modal-header">
          <div className="flex items-center gap-2">
            {validationErrors.length === 0 ? (
              <Check size={18} color="#4ade80" />
            ) : (
              <AlertCircle size={18} color="#f87171" />
            )}
            <span className="font-bold text-sm">
              {validationErrors.length === 0 ? 'Workflow Validation Passed' : 'Validation Issues Found'}
            </span>
          </div>
          <button className="wf-icon-btn-sm" onClick={onClose}>
            <X size={14} />
          </button>
        </div>

        <div className="wf-modal-body">
          {validationErrors.length === 0 ? (
            <div className="wf-validation-success">
              <p className="text-sm font-medium" style={{ color: '#4ade80' }}>
                🎉 Graph integrity check completed successfully!
              </p>
              <p className="text-xs text-muted mt-1">
                The diagram contains a valid START event, an active END terminal, and all decision ports & pathways are fully reachable without loose endpoints.
              </p>
            </div>
          ) : (
            <div className="wf-validation-error-list">
              {validationErrors.map((err, i) => (
                <div
                  key={i}
                  className={`wf-validation-error-item ${err.severity.toLowerCase()}`}
                  onClick={() => {
                    if (err.node_id) {
                      onSelectNode(err.node_id)
                      onClose()
                    }
                  }}
                >
                  <div className="wf-validation-error-icon">
                    {err.severity === 'Error' ? (
                      <XCircle size={15} color="#f87171" />
                    ) : (
                      <AlertCircle size={15} color="#facc15" />
                    )}
                  </div>
                  <div className="wf-validation-error-content">
                    <div className="wf-validation-error-title">
                      {err.node_name || 'Workflow Architecture'}
                      {err.node_id && <span className="font-mono text-xs opacity-60"> ({err.node_id})</span>}
                    </div>
                    <div className="wf-validation-error-msg">{err.message}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="wf-modal-footer">
          <button className="wf-btn wf-btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
