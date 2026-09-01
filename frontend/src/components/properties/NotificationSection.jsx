import React, { useState } from 'react'

export default function NotificationSection({
  data,
  name,
  backendRoles = [],
  backendUsers = [],
  availableFields = [],
  handleFieldChange,
  handleFieldsChange
}) {
  const isNotif = data.subType === 'NOTIFICATION' || 
    data.type === 'notification' || 
    (!data.subType && String(data.label || name || '').toLowerCase().includes('notification'))

  const [recipientMode, setRecipientMode] = useState(() => {
    const toVal = String(data.to || data.recipient || '')
    if (toVal.startsWith('role:')) return 'ROLE'
    if (toVal.startsWith('user:')) return 'USER'
    if (toVal.includes('@') && !toVal.includes('{{')) return 'STATIC'
    return 'DYNAMIC'
  })

  // Quick insertion of variable tokens
  const handleInsertVariable = (field, varName) => {
    const currentVal = data[field] || ''
    const token = `{{${varName}}}`
    if (!currentVal) {
      handleFieldChange(field, token)
    } else {
      handleFieldChange(field, `${currentVal} ${token}`)
    }
  }

  // Common context variables available across workflows
  const commonVars = [
    { label: 'Employee Email', value: 'employee_email' },
    { label: 'Manager Email', value: 'manager_email' },
    { label: 'Initiator Email', value: 'initiator_email' },
    { label: 'Employee Name', value: 'employee_name' },
    { label: 'Entity ID', value: 'workflow.entity_id' },
    { label: 'Status', value: 'status' }
  ]

  // Add any introspected columns from the connected DB table
  const tableVars = (availableFields || [])
    .filter(f => !['created_at', 'updated_at'].includes(f.name))
    .map(f => ({ label: f.name, value: f.name }))

  const allSuggestedVars = [...commonVars]
  tableVars.forEach(tv => {
    if (!allSuggestedVars.some(v => v.value === tv.value)) {
      allSuggestedVars.push(tv)
    }
  })

  return (
    <>
      <div className="wf-field-group">
        <label className="wf-field-label">Communication Channel</label>
        <div className="wf-type-toggle-buttons">
          <button
            type="button"
            className={`wf-preset-btn ${isNotif ? 'active' : ''}`}
            onClick={() => {
              handleFieldsChange({
                subType: 'NOTIFICATION',
                label: (data.label || name || '').toLowerCase().includes('email') ? 'Notification' : (data.label || name)
              })
            }}
          >
            🔔 In-App Notification
          </button>
          <button
            type="button"
            className={`wf-preset-btn ${!isNotif ? 'active' : ''}`}
            onClick={() => {
              handleFieldsChange({
                subType: 'EMAIL',
                label: (data.label || name || '').toLowerCase().includes('notification') ? 'Send Email' : (data.label || name)
              })
            }}
          >
            ✉️ Send Email
          </button>
        </div>
      </div>

      {isNotif ? (
        <>
          <div className="wf-section-divider">NOTIFICATION TARGET</div>

          <div className="wf-field-group">
            <label className="wf-field-label">Recipient Target</label>
            <input
              type="text"
              className="wf-input"
              value={data.recipient || data.to || 'Assigned Role'}
              onChange={(e) => handleFieldChange('recipient', e.target.value)}
              placeholder="e.g. Assigned Role, Record Owner, {{employee_email}}"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Notification Type / Priority</label>
            <select
              className="wf-select"
              value={data.priority || 'Info'}
              onChange={(e) => handleFieldChange('priority', e.target.value)}
            >
              <option value="Info">Info (Standard In-App Alert)</option>
              <option value="Success">Success (Approval / Completed)</option>
              <option value="Warning">Warning (Action Required / Pending)</option>
              <option value="Critical">Critical (Rejection / Escalation)</option>
            </select>
          </div>

          <div className="wf-section-divider">ALERT CONTENT</div>

          <div className="wf-field-group">
            <label className="wf-field-label">Alert Title</label>
            <input
              type="text"
              className="wf-input"
              value={data.title || data.subject || 'Task Review Pending'}
              onChange={(e) => {
                handleFieldChange('title', e.target.value)
                handleFieldChange('subject', e.target.value)
              }}
              placeholder="e.g. Task Review Required"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Alert Message</label>
            <textarea
              className="wf-textarea"
              rows={4}
              value={data.message || data.body || 'A new workflow item requires your review.'}
              onChange={(e) => {
                handleFieldChange('message', e.target.value)
                handleFieldChange('body', e.target.value)
              }}
              placeholder="e.g. Record #{{workflow.entity_id}} is ready for your review."
            />
          </div>
        </>
      ) : (
        <>
          <div className="wf-section-divider">EMAIL RECIPIENT SETTINGS</div>

          {/* Recipient Source Mode Selector */}
          <div className="wf-field-group">
            <label className="wf-field-label">Recipient Mode</label>
            <div className="wf-type-toggle-buttons" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
              <button
                type="button"
                className={`wf-preset-btn ${recipientMode === 'DYNAMIC' ? 'active' : ''}`}
                style={{ fontSize: '11px', padding: '6px' }}
                onClick={() => {
                  setRecipientMode('DYNAMIC')
                  if (!data.to || data.to.startsWith('role:') || data.to.startsWith('user:')) {
                    handleFieldChange('to', '{{employee_email}}')
                  }
                }}
              >
                Dynamic Variable
              </button>
              <button
                type="button"
                className={`wf-preset-btn ${recipientMode === 'ROLE' ? 'active' : ''}`}
                style={{ fontSize: '11px', padding: '6px' }}
                onClick={() => {
                  setRecipientMode('ROLE')
                  const firstRole = backendRoles[0]?.name || 'MANAGER'
                  handleFieldChange('to', `role:${firstRole}`)
                }}
              >
                Client DB Role
              </button>
              <button
                type="button"
                className={`wf-preset-btn ${recipientMode === 'USER' ? 'active' : ''}`}
                style={{ fontSize: '11px', padding: '6px' }}
                onClick={() => {
                  setRecipientMode('USER')
                  const firstUser = backendUsers[0]?.name || 'User'
                  handleFieldChange('to', `user:${firstUser}`)
                }}
              >
                Specific User
              </button>
              <button
                type="button"
                className={`wf-preset-btn ${recipientMode === 'STATIC' ? 'active' : ''}`}
                style={{ fontSize: '11px', padding: '6px' }}
                onClick={() => {
                  setRecipientMode('STATIC')
                  if (data.to?.includes('{{') || data.to?.startsWith('role:')) {
                    handleFieldChange('to', '')
                  }
                }}
              >
                Custom Email
              </button>
            </div>
          </div>

          {/* Dynamic / Expression Input */}
          {recipientMode === 'DYNAMIC' && (
            <div className="wf-field-group">
              <label className="wf-field-label">To (Context Variable / Dynamic Field)</label>
              <input
                type="text"
                className="wf-input font-mono text-xs"
                value={data.to !== undefined ? data.to : (data.recipient || '{{employee_email}}')}
                onChange={(e) => handleFieldChange('to', e.target.value)}
                placeholder="e.g. {{employee_email}}, {{manager_email}}"
              />
              <div style={{ marginTop: '6px' }}>
                <span style={{ fontSize: '10px', color: 'var(--wf-text-muted)', display: 'block', marginBottom: '4px' }}>
                  Click to insert dynamic variables from Client DB:
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {allSuggestedVars.map(v => (
                    <button
                      key={v.value}
                      type="button"
                      className="wf-btn wf-btn-sm"
                      style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.25)' }}
                      onClick={() => handleFieldChange('to', `{{${v.value}}}`)}
                    >
                      +{v.value}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Role Dropdown */}
          {recipientMode === 'ROLE' && (
            <div className="wf-field-group">
              <label className="wf-field-label">Select Client DB Role (All members)</label>
              <select
                className="wf-select"
                value={data.to?.startsWith('role:') ? data.to.replace('role:', '') : (backendRoles[0]?.name || '')}
                onChange={(e) => handleFieldChange('to', `role:${e.target.value}`)}
              >
                {backendRoles.map(r => (
                  <option key={r.id || r.name} value={r.name}>
                    {r.name} (Role ID: {r.id})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* User Dropdown */}
          {recipientMode === 'USER' && (
            <div className="wf-field-group">
              <label className="wf-field-label">Select Specific User</label>
              <select
                className="wf-select"
                value={data.to?.startsWith('user:') ? data.to.replace('user:', '') : (backendUsers[0]?.name || '')}
                onChange={(e) => handleFieldChange('to', `user:${e.target.value}`)}
              >
                {backendUsers.map(u => (
                  <option key={u.id} value={u.name}>
                    {u.name} {u.email ? `(${u.email})` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Static Email Input */}
          {recipientMode === 'STATIC' && (
            <div className="wf-field-group">
              <label className="wf-field-label">Direct Email Address</label>
              <input
                type="email"
                className="wf-input font-mono text-xs"
                value={data.to || ''}
                onChange={(e) => handleFieldChange('to', e.target.value)}
                placeholder="e.g. hr@company.com, notifications@company.com"
              />
            </div>
          )}

          {/* CC Field */}
          <div className="wf-field-group">
            <label className="wf-field-label">CC (Optional)</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.cc || ''}
              onChange={(e) => handleFieldChange('cc', e.target.value)}
              placeholder="e.g. {{manager_email}}, hr@company.com"
            />
          </div>

          <div className="wf-section-divider">EMAIL CONTENT</div>

          <div className="wf-field-group">
            <label className="wf-field-label">Email Subject</label>
            <input
              type="text"
              className="wf-input"
              value={data.subject || data.title || ''}
              onChange={(e) => handleFieldChange('subject', e.target.value)}
              placeholder="e.g. Leave Request #{{workflow.entity_id}} Approved"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Email Body (HTML / Text)</label>
            <textarea
              className="wf-textarea"
              rows={5}
              value={data.body || data.message || ''}
              onChange={(e) => handleFieldChange('body', e.target.value)}
              placeholder="e.g. Hi {{employee_name}}, your leave request #{{workflow.entity_id}} has been approved."
            />
            {/* Quick Variable Insert Pills for Body */}
            <div style={{ marginTop: '6px' }}>
              <span style={{ fontSize: '10px', color: 'var(--wf-text-muted)', display: 'block', marginBottom: '4px' }}>
                Insert Variable into Body:
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {allSuggestedVars.map(v => (
                  <button
                    key={v.value}
                    type="button"
                    className="wf-btn wf-btn-sm"
                    style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(255, 255, 255, 0.05)', color: 'var(--wf-text-muted)', border: '1px solid var(--wf-border)' }}
                    onClick={() => handleInsertVariable('body', v.value)}
                  >
                    +{v.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}
