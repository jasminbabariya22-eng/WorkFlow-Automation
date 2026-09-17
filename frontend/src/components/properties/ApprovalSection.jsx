import React from 'react'
import { Shield, Plus, X } from 'lucide-react'

export default function ApprovalSection({
  data,
  backendRoles,
  actions,
  newActionLabel,
  setNewActionLabel,
  newActionId,
  setNewActionId,
  handleAddAction,
  handleRemoveAction,
  handleFieldChange
}) {
  return (
    <>
      <div className="wf-section-divider">ASSIGNMENT</div>

      <div className="wf-field-group">
        <label className="wf-field-label" htmlFor="approval-assignment-type">Assignment Type</label>
        <select
          id="approval-assignment-type"
          name="assignment_type"
          aria-label="Assignment Type"
          className="wf-select"
          value={data.assignmentType || 'Role'}
          onChange={(e) => handleFieldChange('assignmentType', e.target.value)}
        >
          <option value="Role">Role</option>
          <option value="User">User</option>
          <option value="Department">Department</option>
        </select>
      </div>

      <div className="wf-field-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <label className="wf-field-label" htmlFor={backendRoles.length > 0 ? "approval-role-select" : "approval-role-input"} style={{ margin: 0, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Shield size={12} color="#818cf8" />
            <span>Approver Role / Group</span>
          </label>
          {backendRoles.length === 0 && (
            <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: '500' }}>⚠️ No role table in DB</span>
          )}
        </div>
        {backendRoles.length > 0 ? (
          <select
            id="approval-role-select"
            name="role"
            aria-label="Approver Role or Group"
            className="wf-select"
            value={data.role || ''}
            onChange={(e) => handleFieldChange('role', e.target.value)}
          >
            <option value="">-- Select Client Role --</option>
            {backendRoles.map(r => (
              <option key={r.id} value={r.name}>{r.name}</option>
            ))}
          </select>
        ) : (
          <input
            id="approval-role-input"
            name="role"
            aria-label="Approver Role or Group"
            type="text"
            className="wf-input font-mono uppercase"
            value={data.role || ''}
            onChange={(e) => handleFieldChange('role', e.target.value.toUpperCase())}
            placeholder="e.g. MANAGER, RISK_OFFICER, APPROVER"
          />
        )}
      </div>

      <div className="wf-section-divider">ACTIONS / OUTCOMES (DECISION HANDLES)</div>
      <p className="wf-hint-text">Each action generates a decision outcome port on the node:</p>

      <div className="wf-action-tag-list">
        {actions.map((act) => {
          const actionId = typeof act === 'string' ? act : act.id
          const label = typeof act === 'string' ? act.replace(/_/g, ' ') : act.label
          return (
            <div key={actionId} className={`wf-action-port-chip ${actionId === 'APPROVE' ? 'approve' : actionId === 'REJECT' ? 'reject' : 'force'}`}>
              <span className="wf-action-chip-label">{label}</span>
              <span className="wf-action-chip-id">({actionId})</span>
              <button 
                type="button" 
                onClick={() => handleRemoveAction(actionId)}
                aria-label={`Remove ${label} action`}
                title={`Remove ${label} action`}
              >
                <X size={12} />
              </button>
            </div>
          )
        })}
      </div>

      <div className="wf-add-action-box">
        <input
          id="approval-new-action-label"
          name="new_action_label"
          aria-label="New Action Label"
          type="text"
          className="wf-input wf-input-sm"
          placeholder="e.g. Delegate / Resubmit"
          value={newActionLabel}
          onChange={(e) => setNewActionLabel(e.target.value)}
        />
        <input
          id="approval-new-action-id"
          name="new_action_id"
          aria-label="New Action Identifier"
          type="text"
          className="wf-input wf-input-sm font-mono uppercase"
          placeholder="ID (e.g. DELEGATE)"
          value={newActionId}
          onChange={(e) => setNewActionId(e.target.value)}
        />
        <button 
          type="button" 
          className="wf-btn wf-btn-sm wf-btn-primary" 
          onClick={handleAddAction}
          aria-label="Add Action Outcome"
        >
          <Plus size={13} />
          <span>Add Action</span>
        </button>
      </div>

      <div className="wf-section-divider">APPROVAL RULES</div>
      <div className="wf-toggle-list">
        <label className="wf-checkbox-label" htmlFor="approval-comment-reject">
          <input
            id="approval-comment-reject"
            name="comment_on_reject"
            aria-label="Require comment on Reject"
            type="checkbox"
            checked={data.commentOnReject !== false}
            onChange={(e) => handleFieldChange('commentOnReject', e.target.checked)}
          />
          <span>Require comment on Reject</span>
        </label>
        <label className="wf-checkbox-label" htmlFor="approval-comment-approve">
          <input
            id="approval-comment-approve"
            name="comment_on_approve"
            aria-label="Require comment on Approve"
            type="checkbox"
            checked={Boolean(data.commentOnApprove)}
            onChange={(e) => handleFieldChange('commentOnApprove', e.target.checked)}
          />
          <span>Require comment on Approve</span>
        </label>
      </div>

      <div className="wf-section-divider">NOTIFICATIONS</div>
      <div className="wf-toggle-list">
        <label className="wf-checkbox-label" htmlFor="approval-notify-assign">
          <input
            id="approval-notify-assign"
            name="notify_on_assign"
            aria-label="Notify on Assignment"
            type="checkbox"
            checked={data.notifyOnAssign !== false}
            onChange={(e) => handleFieldChange('notifyOnAssign', e.target.checked)}
          />
          <span>On Assignment</span>
        </label>
        <label className="wf-checkbox-label" htmlFor="approval-notify-approve">
          <input
            id="approval-notify-approve"
            name="notify_on_approve"
            aria-label="Notify on Approve"
            type="checkbox"
            checked={data.notifyOnApprove !== false}
            onChange={(e) => handleFieldChange('notifyOnApprove', e.target.checked)}
          />
          <span>On Approve</span>
        </label>
        <label className="wf-checkbox-label" htmlFor="approval-notify-reject">
          <input
            id="approval-notify-reject"
            name="notify_on_reject"
            aria-label="Notify on Reject"
            type="checkbox"
            checked={data.notifyOnReject !== false}
            onChange={(e) => handleFieldChange('notifyOnReject', e.target.checked)}
          />
          <span>On Reject</span>
        </label>
      </div>
    </>
  )
}
