import React, { useState, useEffect } from 'react'
import { Inbox, CheckCircle2, XCircle, AlertCircle, ArrowRight, User, Clock, Check } from 'lucide-react'
import { workflowClient } from '../services/workflowClient'

export default function ApprovalsInbox({ currentUser, onDataChanged }) {
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [remarksMap, setRemarksMap] = useState({})
  const [actionLoading, setActionLoading] = useState(null)
  const [feedback, setFeedback] = useState(null)

  const reloadTasks = async () => {
    if (!currentUser?.role) return
    try {
      setIsLoading(true)
      const list = await workflowClient.getPendingTasks(currentUser.role)
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
    const taskId = task.task_id
    const actionKey = `${taskId}_${actionType}`
    setActionLoading(actionKey)
    setFeedback(null)
    const remarks = remarksMap[taskId] || ''

    try {
      if (actionType === 'REJECT') {
        await workflowClient.rejectTask(taskId, remarks, {
          user_id: currentUser.id,
          user_role: currentUser.role,
          rejected_by: currentUser.name
        })
      } else {
        await workflowClient.completeTask(taskId, actionType, remarks, {
          user_id: currentUser.id,
          user_role: currentUser.role,
          approved_by: currentUser.name
        })
      }
      setFeedback({
        success: true,
        message: `✓ Task #${taskId} (${actionType}) completed successfully via Direct Workflow API.`
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
            const taskId = t.task_id
            const itemKey = `task_${taskId}`
            const isApproving = actionLoading === `${taskId}_APPROVE`
            const isRejecting = actionLoading === `${taskId}_REJECT`

            return (
              <div key={itemKey} className="task-approval-card">
                <div className="task-card-header">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-workflow font-mono">
                      Task #{taskId} • Instance #{t.instance_id}
                    </span>
                    <span className="badge badge-neutral">
                      Role: {t.role_code || currentUser.role}
                    </span>
                  </div>
                  <div className="text-xs text-muted flex items-center gap-1">
                    <Clock size={12} />
                    <span>{t.created_on ? new Date(t.created_on).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }) : 'Just now'}</span>
                  </div>
                </div>

                <div className="task-card-body">
                  <div className="task-title font-semibold text-white">{t.task_name || t.task_spec_id || 'Manager Approval'}</div>
                  <div className="text-xs text-muted mt-1">
                    Requires action from <strong>{t.role_code || currentUser.role}</strong> for workflow instance #{t.instance_id}.
                  </div>

                  {/* Remarks input */}
                  <div className="mt-3">
                    <input
                      type="text"
                      className="text-input text-xs"
                      placeholder="Optional approval remarks or feedback..."
                      value={remarksMap[taskId] || ''}
                      onChange={(e) =>
                        setRemarksMap({ ...remarksMap, [taskId]: e.target.value })
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
