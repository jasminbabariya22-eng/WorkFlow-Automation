import React from 'react'
import { Plus } from 'lucide-react'

export default function ConditionSection({
  nodeType,
  data,
  handleFieldChange,
  fieldMappings = [],
  availableFields = [],
  cases = [],
  newCaseLabel = '',
  setNewCaseLabel,
  handleAddCase,
  handleRemoveCase
}) {
  if (nodeType === 'condition') {
    return (
      <>
        <div className="wf-section-divider">EVALUATION LOGIC</div>

        <div className="wf-field-group">
          <label className="wf-field-label">Field / Context Variable</label>
          <input
            type="text"
            className="wf-input font-mono"
            value={data.field || 'action'}
            onChange={(e) => handleFieldChange('field', e.target.value)}
            placeholder="e.g. action, amount, score"
          />
        </div>

        <div className="wf-field-group">
          <label className="wf-field-label">Operator</label>
          <select
            className="wf-select"
            value={data.operator || 'EQUALS'}
            onChange={(e) => handleFieldChange('operator', e.target.value)}
          >
            <option value="EQUALS">EQUALS (==)</option>
            <option value="NOT_EQUALS">NOT EQUALS (!=)</option>
            <option value="GREATER_THAN">GREATER THAN (&gt;)</option>
            <option value="LESS_THAN">LESS THAN (&lt;)</option>
            <option value="IN">IN (Comma-separated list)</option>
            <option value="CONTAINS">CONTAINS</option>
          </select>
        </div>

        <div className="wf-field-group">
          <label className="wf-field-label">Expected Match Value</label>
          <input
            type="text"
            className="wf-input"
            value={data.value || 'APPROVE'}
            onChange={(e) => handleFieldChange('value', e.target.value)}
            placeholder="e.g. APPROVE, 5000, HIGH"
          />
        </div>

        <div className="wf-section-divider">DECISION PORTS (OUTGOING HANDLES)</div>
        <p className="wf-hint-text">
          Connect the <strong style={{ color: '#4ade80' }}>TRUE</strong> port to the next step when condition matches, and <strong style={{ color: '#f87171' }}>FALSE</strong> port otherwise.
        </p>
      </>
    )
  }

  if (nodeType === 'switch') {
    return (
      <>
        <div className="wf-section-divider">SWITCH EXPRESSION</div>

        <div className="wf-field-group">
          <label className="wf-field-label">Field / Variable to Inspect</label>
          <input
            type="text"
            className="wf-input font-mono"
            value={data.field || 'category'}
            onChange={(e) => handleFieldChange('field', e.target.value)}
            placeholder="e.g. priority, status, department"
          />
        </div>

        <div className="wf-section-divider">SWITCH BRANCHES / CASES</div>
        <p className="wf-hint-text">Each case creates an active branch port on this node:</p>

        <div className="wf-tag-list">
          {cases.map((c) => (
            <span key={c} className="wf-tag-item">
              <span>{c}</span>
              <button type="button" onClick={() => handleRemoveCase(c)}>×</button>
            </span>
          ))}
        </div>

        <div className="wf-custom-add-row mt-2">
          <input
            type="text"
            className="wf-input wf-input-sm uppercase font-mono"
            placeholder="New Case Value (e.g. HIGH)"
            value={newCaseLabel}
            onChange={(e) => setNewCaseLabel(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddCase()}
          />
          <button type="button" className="wf-btn wf-btn-sm wf-btn-primary" onClick={handleAddCase}>
            <Plus size={13} />
          </button>
        </div>
      </>
    )
  }

  return null
}
