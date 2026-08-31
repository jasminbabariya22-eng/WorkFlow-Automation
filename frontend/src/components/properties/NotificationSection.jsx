import React from 'react'

export default function NotificationSection({
  data,
  name,
  handleFieldChange,
  handleFieldsChange
}) {
  const isNotif = data.subType === 'NOTIFICATION' || 
    data.type === 'notification' || 
    (!data.subType && String(data.label || name || '').toLowerCase().includes('notification'))

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
              placeholder="e.g. Assigned Role, Record Owner, {{owner.id}}"
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
          <div className="wf-section-divider">EMAIL RECIPIENTS</div>

          <div className="wf-field-group">
            <label className="wf-field-label">To (Context Variable or Email)</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.to || data.recipient || '{{risk_owner_email}}'}
              onChange={(e) => handleFieldChange('to', e.target.value)}
              placeholder="e.g. {{risk_owner_email}}, manager@company.com"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">CC (Optional)</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.cc || ''}
              onChange={(e) => handleFieldChange('cc', e.target.value)}
              placeholder="e.g. compliance@company.com"
            />
          </div>

          <div className="wf-section-divider">EMAIL CONTENT</div>

          <div className="wf-field-group">
            <label className="wf-field-label">Email Subject</label>
            <input
              type="text"
              className="wf-input"
              value={data.subject || data.title || 'Task Action Required: {{workflow.name}}'}
              onChange={(e) => handleFieldChange('subject', e.target.value)}
              placeholder="e.g. Risk #{{workflow.entity_id}} Approved"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Email Body (HTML / Text)</label>
            <textarea
              className="wf-textarea"
              rows={4}
              value={data.body || data.message || 'Dear {{recipient_name}}, Your record has been processed successfully.'}
              onChange={(e) => handleFieldChange('body', e.target.value)}
              placeholder="e.g. Dear User, Your record #{{workflow.entity_id}} has been approved."
            />
          </div>
        </>
      )}
    </>
  )
}
