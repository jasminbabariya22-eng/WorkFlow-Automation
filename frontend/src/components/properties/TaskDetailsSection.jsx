import React, { useEffect } from 'react'

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
  // Automatically ensure taskCode is populated in the background without cluttering the UI
  useEffect(() => {
    if (!data.taskCode && !data.task_code) {
      const source = name || data.label || selectedNode?.id || 'TASK'
      const generated = source.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')
      handleFieldChange('taskCode', generated || 'NODE')
    }
  }, [selectedNode?.id])

  return (
    <>
      <div className="wf-field-group">
        <label htmlFor="node-title-field" className="wf-field-label">Node Title</label>
        <input
          id="node-title-field"
          name="node_title"
          aria-label="Node Title"
          type="text"
          className="wf-input"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder="Display Label"
        />
      </div>

      <div className="wf-field-group">
        <label htmlFor="node-desc-field" className="wf-field-label">Description</label>
        <textarea
          id="node-desc-field"
          name="node_description"
          aria-label="Node Description"
          className="wf-textarea"
          rows={2}
          value={description}
          onChange={(e) => handleDescriptionChange(e.target.value)}
          placeholder="Optional explanation or notes..."
        />
      </div>
    </>
  )
}
