import React, { useState, useEffect } from 'react'
import {
  ArrowLeft,
  Save,
  CheckSquare,
  Play,
  Sparkles,
  Download,
  Upload,
  MoreVertical,
  RotateCcw,
  GitBranch,
  Database,
  Link2,
  FolderOpen
} from 'lucide-react'
import { workflowStorage } from '../../services/workflowStorage'

export default function DesignerHeader({
  workflowName,
  setWorkflowName,
  versionNumber,
  workflowStatus,
  workflowConnectionId,
  onUpdateWorkflowConnection,
  saveStatus,
  saveWorkflow,
  handleAutoLayout,
  handleResetCanvas,
  handleValidateGraph,
  handleOpenTestModal,
  handleOpenBindingModal,
  handleOpenWorkflowSelector,
  handleExportJSON,
  fileInputRef,
  handleImportFile,
  showMoreMenu,
  setShowMoreMenu,
  onClose
}) {
  const [dbConnections, setDbConnections] = useState([])
  const [dbName, setDbName] = useState('')

  const isEditable = !workflowStatus || workflowStatus.toLowerCase() === 'draft' || workflowStatus.toLowerCase() === 'inactive'

  useEffect(() => {
    const fetcher = workflowStorage.getDatabaseConnections || workflowStorage.getConnections
    if (typeof fetcher === 'function') {
      fetcher.call(workflowStorage, true).then(conns => {
        setDbConnections(conns || [])
      }).catch(() => {})
    }
  }, [])

  useEffect(() => {
    if (!workflowConnectionId) {
      setDbName('')
      return
    }
    const found = (dbConnections || []).find(c => Number(c.connection_id) === Number(workflowConnectionId))
    if (found) {
      setDbName(found.connection_name)
    } else if (Number(workflowConnectionId) === 4) {
      setDbName('test_emp_leave')
    } else {
      setDbName(`DB #${workflowConnectionId}`)
    }
  }, [workflowConnectionId, dbConnections])

  return (
    <header className="wf-designer-header">
      {/* 1. LEFT SECTION: BACK BUTTON & WORKFLOW IDENTITY */}
      <div className="wf-header-left">
        {onClose && (
          <button className="wf-back-btn" onClick={onClose} title="Return to Dashboard">
            <ArrowLeft size={15} />
            <span>Back</span>
          </button>
        )}

        <div className="wf-header-divider" />

        {/* Workflow Title Input */}
        <div className="wf-header-title-wrapper">
          <GitBranch size={16} className="wf-title-icon" />
          <input
            type="text"
            className="wf-header-title-input"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
            placeholder="Specification ID (e.g. leave_request_wf)"
            title="Click to edit Specification ID"
            id="workflow-spec-name"
            name="workflow_spec_name"
            aria-label="Workflow Specification ID"
            autoComplete="off"
          />
        </div>

        {/* Metadata Badges */}
        <div className="wf-header-badges">
          <span className="wf-badge-version">v{versionNumber}</span>
          <span className={`wf-badge-status ${workflowStatus.toLowerCase()}`}>
            {workflowStatus}
          </span>
          {isEditable && onUpdateWorkflowConnection ? (
            <div 
              className="wf-header-db-select-wrapper" 
              title="Select Client Database Connection" 
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', maxWidth: '175px', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.28)', borderRadius: '6px', padding: '2px 6px', boxSizing: 'border-box' }}
            >
              <Database size={11} color="#38bdf8" style={{ flexShrink: 0 }} />
              <select
                id="designer-header-db-select"
                aria-label="Select Client Database"
                value={workflowConnectionId || ''}
                onChange={(e) => {
                  const val = e.target.value ? Number(e.target.value) : null
                  onUpdateWorkflowConnection(val)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#38bdf8',
                  fontSize: '11px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  outline: 'none',
                  maxWidth: '140px',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  paddingRight: '2px'
                }}
              >
                <option value="" style={{ background: '#0f172a', color: '#e2e8f0' }}>★ Default DB</option>
                {dbConnections.map(conn => (
                  <option key={conn.connection_id} value={conn.connection_id} style={{ background: '#0f172a', color: '#e2e8f0' }}>
                    {conn.connection_name}
                  </option>
                ))}
                {workflowConnectionId && !dbConnections.some(c => Number(c.connection_id) === Number(workflowConnectionId)) && (
                  <option key={workflowConnectionId} value={workflowConnectionId} style={{ background: '#0f172a', color: '#e2e8f0' }}>
                    {Number(workflowConnectionId) === 4 ? 'test_emp_leave' : `DB #${workflowConnectionId}`}
                  </option>
                )}
              </select>
            </div>
          ) : workflowConnectionId ? (
            <span className="wf-badge-db bound" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(56, 189, 248, 0.12)', borderColor: 'rgba(56, 189, 248, 0.3)', color: '#38bdf8' }}>
              <Database size={11} />
              {dbName || (Number(workflowConnectionId) === 4 ? 'test_emp_leave' : `DB #${workflowConnectionId}`)}
            </span>
          ) : (
            <span className="wf-badge-db default">
              ★ Default DB
            </span>
          )}

          {/* Auto-Save Indicator */}
          <span className={`wf-save-indicator wf-save-${saveStatus}`}>
            <span className="wf-save-dot" />
            {saveStatus === 'dirty' && 'Unsaved'}
            {saveStatus === 'saving' && 'Saving...'}
            {saveStatus === 'saved' && 'Saved'}
            {saveStatus === 'error' && 'Error'}
          </span>
        </div>
      </div>

      {/* 2. RIGHT SECTION: ACTION TOOLBAR */}
      <div className="wf-header-actions">
        {/* Open / Switch Workflow */}
        {handleOpenWorkflowSelector && (
          <button
            className="wf-btn wf-btn-outline"
            onClick={handleOpenWorkflowSelector}
            title="Open or switch workflow"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <FolderOpen size={14} color="#0284c7" />
            <span>Open Workflow</span>
          </button>
        )}

        {/* Auto Layout */}
        <button
          className="wf-btn wf-btn-outline"
          onClick={handleAutoLayout}
          title="Auto-align canvas nodes into a clean flow"
        >
          <Sparkles size={14} color="#818cf8" />
          <span>Auto Layout</span>
        </button>

        {/* Validate Graph */}
        <button
          className="wf-btn wf-btn-outline wf-btn-validate"
          onClick={handleValidateGraph}
          title="Validate node integrity and connection contracts"
        >
          <CheckSquare size={14} />
          <span>Validate</span>
        </button>

        {/* Test Simulator */}
        <button
          className="wf-btn wf-btn-outline wf-btn-test"
          onClick={handleOpenTestModal}
          title="Interactive workflow execution test runner"
        >
          <Play size={14} />
          <span>Test Flow</span>
        </button>



        {/* Save Button */}
        <button
          className="wf-btn wf-btn-primary"
          onClick={saveWorkflow}
          disabled={saveStatus === 'saving'}
          title="Save workflow definition"
        >
          <Save size={14} />
          <span>{saveStatus === 'saving' ? 'Saving...' : 'Save'}</span>
        </button>

        {/* More Actions Menu */}
        <div className="wf-more-menu-wrapper" style={{ position: 'relative' }}>
          <button
            className="wf-btn wf-btn-icon"
            onClick={() => setShowMoreMenu(!showMoreMenu)}
            title="More Options"
          >
            <MoreVertical size={15} />
          </button>

          {showMoreMenu && (
            <div
              className="wf-dropdown-menu"
              style={{
                position: 'absolute',
                right: 0,
                top: '40px',
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '6px',
                minWidth: '180px',
                boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                zIndex: 100
              }}
              onClick={() => setShowMoreMenu(false)}
            >
              <button
                className="wf-dropdown-item"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  background: 'transparent',
                  border: 'none',
                  color: '#334155',
                  fontSize: '12px',
                  cursor: 'pointer',
                  borderRadius: '4px'
                }}
                onClick={handleExportJSON}
              >
                <Download size={13} />
                <span>Export JSON</span>
              </button>
              <button
                className="wf-dropdown-item"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  background: 'transparent',
                  border: 'none',
                  color: '#334155',
                  fontSize: '12px',
                  cursor: 'pointer',
                  borderRadius: '4px'
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={13} />
                <span>Import JSON</span>
              </button>
              <div style={{ height: '1px', background: '#e2e8f0', margin: '4px 0' }} />
              <button
                className="wf-dropdown-item"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  background: 'transparent',
                  border: 'none',
                  color: '#dc2626',
                  fontSize: '12px',
                  cursor: 'pointer',
                  borderRadius: '4px'
                }}
                onClick={handleResetCanvas}
              >
                <RotateCcw size={13} />
                <span>Clear Canvas</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
