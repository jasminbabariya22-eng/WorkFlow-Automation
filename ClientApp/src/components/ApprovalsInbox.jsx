import React, { useState, useEffect } from 'react'
import { Inbox, CheckCircle2, XCircle, AlertCircle, ArrowRight, User, Clock, Check } from 'lucide-react'
import { genericWorkflowApi } from '../services/genericWorkflowApi'

export default function ApprovalsInbox({ currentUser, onDataChanged }) {
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [remarksMap, setRemarksMap] = useState({})
  const [actionLoading, setActionLoading] = useState(null)
  const [feedback, setFeedback] = useState(null)

  const reloadTasks = async () => {
    if (!currentUser?.id) return
    try {
      setIsLoading(true)
      const list = await genericWorkflowApi.fetchMyTasks(currentUser.id)
      setTasks(Array.isArray(list) ? list : [])
      if (onDataChanged) onDataChanged()
    } catch (_e) {
      setTasks([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    reloadTasks()
  }, [currentUser])

  const handleAction = async (task, actionType) => {
    const moduleKey = task.entity_type || 'leave_requests'
    const recordId = task.entity_id || task.task_id
    const actionKey = `${moduleKey}_${recordId}_${actionType}`
    setActionLoading(actionKey)
    setFeedback(null)
    const remarks = remarksMap[`${moduleKey}_${recordId}`] || ''

    try {
      await genericWorkflowApi.executeAction(moduleKey, recordId, actionType, remarks, currentUser)
      setFeedback({
        success: true,
        message: `✓ Task '${task.task_name || 'Approval'}' (${actionType}) completed.`
      })
      await reloadTasks()
    } catch (err) {
      setFeedback({
        success: false,
        message: `Action error: ${err.message}`
      })
    } finally {
      setActionLoading(null)
    }
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
            const entityType = t.entity_type || 'leave_requests'
            const entityId = t.entity_id || t.task_id
            const itemKey = `${entityType}_${entityId}`
            const isApproving = actionLoading === `${itemKey}_APPROVE`
            const isRejecting = actionLoading === `${itemKey}_REJECT`

            return (
              <div key={itemKey} className="task-approval-card">
                <div className="task-card-header">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-workflow font-mono">
                      {entityType} #{entityId}
                    </span>
                    <span className="badge badge-neutral">
                      Role: {t.role_code || currentUser.role}
                    </span>
                  </div>
                  <div className="text-xs text-muted flex items-center gap-1">
                    <Clock size={12} />
                    <span>{t.created_on ? new Date(t.created_on).toLocaleString() : 'Just now'}</span>
                  </div>
                </div>

                <div className="task-card-body">
                  <div className="task-title font-semibold text-white">{t.task_name || 'Manager Approval'}</div>
                  <div className="text-xs text-muted mt-1">
                    Requires action for <strong>{entityType}</strong> record #{entityId}.
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
