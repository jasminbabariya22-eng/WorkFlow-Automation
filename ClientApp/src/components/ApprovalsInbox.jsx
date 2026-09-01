import React, { useState } from 'react'
import { Inbox, CheckCircle2, XCircle, AlertCircle, ArrowRight, User, Clock, Check } from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { workflowClient } from '../services/workflowClient'

export default function ApprovalsInbox({ currentUser, onDataChanged }) {
  const [tasks, setTasks] = useState(clientDb.getPendingApprovalsForUser(currentUser))
  const [remarksMap, setRemarksMap] = useState({})
  const [actionLoading, setActionLoading] = useState(null)
  const [feedback, setFeedback] = useState(null)

  const reloadTasks = () => {
    const list = clientDb.getPendingApprovalsForUser(currentUser)
    setTasks(list)
    if (onDataChanged) onDataChanged()
  }

  const handleAction = async (task, actionType) => {
    const actionKey = `${task.entityType}_${task.entityId}_${actionType}`
    setActionLoading(actionKey)
    setFeedback(null)
    const remarks = remarksMap[`${task.entityType}_${task.entityId}`] || ''

    // 1. Submit Action to Centralized Workflow Engine over the Network
    try {
      await workflowClient.executeAction(task.workflowId, {
        entityType: task.entityType,
        entityId: task.entityId,
        action: actionType,
        userId: currentUser.id,
        remarks: remarks || `Action ${actionType} submitted by ${currentUser.name}`
      })

      setFeedback({
        success: true,
        message: `Workflow #${task.workflowId} updated! Action '${actionType}' completed successfully.`
      })
    } catch (err) {
      setFeedback({
        success: false,
        message: `Workflow Server message: ${err.message}. (Updated locally in ClientDB)`
      })
    }

    // 2. Synchronize Status in Local clientDB
    try {
      if (task.entityType === 'LeaveRequest') {
        if (actionType === 'APPROVE') {
          clientDb.approveLeave(task.entityId, currentUser, remarks)
        } else {
          clientDb.rejectLeave(task.entityId, currentUser, remarks || 'Rejected by manager in inbox')
        }
      } else if (task.entityType === 'ExpenseClaim') {
        const newStatus = actionType === 'APPROVE' ? 'APPROVED' : 'REJECTED'
        clientDb.updateExpenseStatus(task.entityId, newStatus, remarks)
      } else if (task.entityType === 'PurchaseOrder') {
        const newStatus = actionType === 'APPROVE' ? 'APPROVED' : 'REJECTED'
        clientDb.updatePOStatus(task.entityId, newStatus, remarks)
      } else if (task.entityType === 'ItRequest') {
        const newStatus = actionType === 'APPROVE' ? 'APPROVED' : 'REJECTED'
        clientDb.updateItStatus(task.entityId, newStatus, remarks)
      } else if (task.entityType === 'CustomerKyc') {
        const newStatus = actionType === 'APPROVE' ? 'APPROVED' : 'REJECTED'
        clientDb.updateKycStatus(task.entityId, newStatus, remarks)
      }
    } catch (dbErr) {
      setFeedback({
        success: false,
        message: dbErr.message
      })
    }

    setActionLoading(null)
    reloadTasks()
  }

  return (
    <div className="module-container">
      {/* Header */}
      <div className="module-header-row">
        <div>
          <h2 className="module-title">📥 Unified Approvals Inbox</h2>
          <p className="module-subtitle">
            Items awaiting your review as <strong>{currentUser.name} ({currentUser.role})</strong> across all connected workflows.
          </p>
        </div>

        <span className="badge badge-neutral">
          {tasks.length} Pending Approval{tasks.length !== 1 ? 's' : ''}
        </span>
      </div>

      {feedback && (
        <div className={`status-banner ${feedback.success ? 'success' : 'warning'} mb-4`}>
          <span className="text-xs">{feedback.message}</span>
        </div>
      )}

      {/* Empty State */}
      {tasks.length === 0 ? (
        <div className="empty-inbox-card">
          <CheckCircle2 size={40} color="#4ade80" className="mb-2" />
          <div className="font-bold text-lg text-white">All Caught Up!</div>
          <div className="text-sm text-muted">
            No pending tasks awaiting approval for role <strong>{currentUser.role}</strong>.
            Switch users in the top-right navbar to test other roles (e.g. Bob - Manager or Charlie - Finance).
          </div>
        </div>
      ) : (
        /* Task Cards List */
        <div className="tasks-grid">
          {tasks.map((t) => {
            const itemKey = `${t.entityType}_${t.entityId}`
            const isApproving = actionLoading === `${itemKey}_APPROVE`
            const isRejecting = actionLoading === `${itemKey}_REJECT`

            return (
              <div key={itemKey} className="task-approval-card">
                <div className="task-card-header">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-workflow font-mono">
                      {t.entityType} #{t.entityId}
                    </span>
                    <span className="badge badge-neutral">
                      Bound to WF #{t.workflowId}
                    </span>
                  </div>
                  <div className="text-xs text-muted flex items-center gap-1">
                    <Clock size={12} />
                    <span>{t.createdOn}</span>
                  </div>
                </div>

                <div className="task-card-body">
                  <div className="task-title">{t.title}</div>
                  <div className="task-subtitle" dangerouslySetInnerHTML={{ __html: t.subtitle }} />
                  <div className="text-xs text-muted mt-2">
                    Submitted by: <strong className="text-slate-300">{t.submittedBy}</strong>
                  </div>

                  {/* Remarks input */}
                  <div className="mt-3">
                    <input
                      type="text"
                      className="text-input text-xs"
                      placeholder="Optional approval remarks or feedback..."
                      value={remarksMap[itemKey] || ''}
                      onChange={(e) =>
                        setRemarksMap({ ...remarksMap, [itemKey]: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="task-card-footer flex justify-end gap-2">
                  <button
                    className="btn btn-danger-outline"
                    onClick={() => handleAction(t, 'REJECT')}
                    disabled={Boolean(actionLoading)}
                  >
                    <XCircle size={14} />
                    <span>{isRejecting ? 'Rejecting...' : 'Reject'}</span>
                  </button>

                  <button
                    className="btn btn-success"
                    onClick={() => handleAction(t, 'APPROVE')}
                    disabled={Boolean(actionLoading)}
                  >
                    <Check size={14} />
                    <span>{isApproving ? 'Approving...' : 'Approve'}</span>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
