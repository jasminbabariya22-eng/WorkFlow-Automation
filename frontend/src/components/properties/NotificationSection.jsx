import React from 'react'
import EmailNodeSection from './EmailNodeSection'

export default function NotificationSection({
  data,
  name,
  workflowConnectionId = null,
  backendRoles = [],
  backendUsers = [],
  backendReportsTo = [],
  availableFields = [],
  handleFieldChange,
  handleFieldsChange
}) {
  const isNotif = data.subType === 'NOTIFICATION' || 
    data.type === 'notification' || 
    (!data.subType && String(data.label || name || '').toLowerCase().includes('notification'))

  if (!isNotif) {
    return (
      <EmailNodeSection
        data={data}
        workflowConnectionId={workflowConnectionId}
        backendRoles={backendRoles}
        backendUsers={backendUsers}
        backendReportsTo={backendReportsTo}
        availableFields={availableFields}
        handleFieldChange={handleFieldChange}
        handleFieldsChange={handleFieldsChange}
      />
    )
  }

  return (
    <>
      <div className="wf-section-divider">NOTIFICATION TARGET</div>

      <div className="wf-field-group">
        <label className="wf-field-label" htmlFor="notification-recipient">Recipient Target</label>
        <input
          id="notification-recipient"
          name="notification_recipient"
          aria-label="Recipient Target"
          type="text"
          className="wf-input"
          value={data.recipient || data.to || 'Assigned Role'}
          onChange={(e) => handleFieldChange('recipient', e.target.value)}
          placeholder="e.g. Assigned Role, Record Owner, {{employee_email}}"
        />
      </div>

      <div className="wf-field-group">
        <label className="wf-field-label" htmlFor="notification-priority">Notification Type / Priority</label>
        <select
          id="notification-priority"
          name="notification_priority"
          aria-label="Notification Type and Priority"
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
        <label className="wf-field-label" htmlFor="notification-title">Alert Title</label>
        <input
          id="notification-title"
          name="notification_title"
          aria-label="Alert Title"
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
        <label className="wf-field-label" htmlFor="notification-message">Alert Message</label>
        <textarea
          id="notification-message"
          name="notification_message"
          aria-label="Alert Message Content"
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
  )
}
