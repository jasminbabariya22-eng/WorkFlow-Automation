import React from 'react'

export default function TaskDetailsSection({
  selectedNode,
  data,
  name,
  description,
  handleFieldChange,
  handleNameChange,
  handleDescriptionChange,
  onUpdateNodeData
}) {
  return (
    <>
      <div className="wf-field-group">
        <label className="wf-field-label">Node Title</label>
        <input
          type="text"
          className="wf-input"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder="Display Label"
        />
      </div>

      <div className="wf-field-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <label className="wf-field-label" style={{ margin: 0 }}>Task Code / Key</label>
          <button
            type="button"
            className="wf-preset-btn"
            style={{ padding: '2px 8px', fontSize: '11px', height: '22px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            title="Generate Task Code from Node Name"
            onClick={() => {
              const source = name || data.label || selectedNode.id || 'TASK'
              const generated = source.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')
              handleFieldChange('taskCode', generated)
            }}
          >
            ⚡ Auto
          </button>
        </div>
        <input
          type="text"
          className="wf-input font-mono uppercase"
          value={data.taskCode || data.task_code || ''}
          onChange={(e) => handleFieldChange('taskCode', e.target.value.toUpperCase().replace(/\s+/g, '_'))}
          placeholder="e.g. USER_REVIEW, APPROVAL_STAGE_1"
        />
      </div>

      <div className="wf-field-group">
        <label className="wf-field-label">Description</label>
        <textarea
          className="wf-textarea"
          rows={2}
          value={description}
          onChange={(e) => handleDescriptionChange(e.target.value)}
          placeholder="Optional explanation or instructions..."
        />
      </div>
    </>
  )
}
