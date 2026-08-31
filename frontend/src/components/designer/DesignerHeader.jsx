import React from 'react'
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
  GitBranch
} from 'lucide-react'

export default function DesignerHeader({
  workflowName,
  setWorkflowName,
  versionNumber,
  workflowStatus,
  workflowConnectionId,
  saveStatus,
  saveWorkflow,
  handleAutoLayout,
  handleResetCanvas,
  handleValidateGraph,
  handleOpenTestModal,
  handleExportJSON,
  fileInputRef,
  handleImportFile,
  showMoreMenu,
  setShowMoreMenu,
  onClose
}) {
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
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="Workflow Name"
            title="Click to rename workflow"
          />
        </div>

        {/* Metadata Badges */}
        <div className="wf-header-badges">
          <span className="wf-badge-version">v{versionNumber}</span>
          <span className={`wf-badge-status ${workflowStatus.toLowerCase()}`}>
            {workflowStatus}
          </span>
          {workflowConnectionId ? (
            <span className="wf-badge-db bound">
              🗄️ DB #{workflowConnectionId}
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
                background: '#1a1f2c',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '8px',
                padding: '6px',
                minWidth: '180px',
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
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
                  color: '#e2e8f0',
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
                  color: '#e2e8f0',
                  fontSize: '12px',
                  cursor: 'pointer',
                  borderRadius: '4px'
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={13} />
                <span>Import JSON</span>
              </button>
              <div style={{ height: '1px', background: 'rgba(255,255,255,0.08)', margin: '4px 0' }} />
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
                  color: '#f87171',
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
