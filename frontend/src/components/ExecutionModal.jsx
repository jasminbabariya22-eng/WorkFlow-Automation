import React, { useState, useEffect } from 'react'
import { 
  X, 
  Zap, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ArrowRight, 
  RefreshCw, 
  UserCheck, 
  Code, 
  Layers, 
  Loader,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

export default function ExecutionModal({ workflowId, workflowSpec, onClose, showToast }) {
  const [initialVariables, setInitialVariables] = useState(
    JSON.stringify({ entity_id: 101, priority: "HIGH", description: "Automated test execution" }, null, 2)
  )
  const [jsonError, setJsonError] = useState(null)
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState(null)
  const [activeTab, setActiveTab] = useState('tasks') // 'tasks' | 'variables' | 'logs'
  
  // Task completion state
  const [taskPayloads, setTaskPayloads] = useState({})
  const [completingTaskId, setCompletingTaskId] = useState(null)

  // Validate JSON on change
  const handleJsonChange = (val) => {
    setInitialVariables(val)
    try {
      JSON.parse(val)
      setJsonError(null)
    } catch (err) {
      setJsonError(err.message)
    }
  }

  // Trigger Execution
  const handleRunWorkflow = async () => {
    let parsedVars = {}
    if (initialVariables.trim()) {
      try {
        parsedVars = JSON.parse(initialVariables)
      } catch (err) {
        showToast('Invalid JSON input variables', 'error')
        return
      }
    }

    setExecuting(true)
    try {
      const result = await workflowStorage.executeWorkflow(workflowId, parsedVars)
      setExecutionResult(result)
      showToast('Workflow execution started successfully!', 'success')
    } catch (err) {
      showToast('Execution simulation failed', 'error')
    } finally {
      setExecuting(false)
    }
  }

  // Complete a pending Human Task
  const handleCompleteTask = async (taskId, action = 'APPROVE') => {
    setCompletingTaskId(taskId)
    try {
      const payloadData = taskPayloads[taskId] || {}
      const vars = {
        action: action,
        approved: action === 'APPROVE',
        ...payloadData
      }

      const taskResult = await workflowStorage.completeTask(taskId, action, vars, `Action ${action} submitted via Studio Runner`)
      showToast(`Task completed successfully with ${action}!`, 'success')

      setExecutionResult(prev => ({
        ...prev,
        status: taskResult.instance_status,
        current_task_code: taskResult.next_task,
        ready_tasks: action === 'APPROVE' ? [
          {
            task_id: taskId + 1,
            task_spec_id: 'Task_Next',
            task_name: 'Manager Review',
            candidate_role: 'MANAGER',
            assigned_user: 'Operational Reviewer',
            status: 'READY'
          }
        ] : [],
        variables: { ...(prev?.variables || {}), ...vars },
        logs: [
          ...(prev?.logs || []),
          {
            id: Date.now(),
            activity_name: `User Task: ${action}`,
            activity_type: 'USER_TASK',
            status: 'COMPLETED',
            created_on: new Date().toLocaleTimeString(),
            duration: '350ms'
          }
        ]
      }))
    } catch (err) {
      showToast('Error completing task', 'error')
    } finally {
      setCompletingTaskId(null)
    }
  }

  // Refresh instance status, ready tasks, variables and logs
  const refreshInstanceState = async (instanceId) => {
    if (!instanceId) return
    const details = await workflowStorage.getInstanceDetails(instanceId)
    setExecutionResult(prev => ({
      ...prev,
      variables: details.variables,
      logs: details.logs
    }))
    showToast('Instance state refreshed', 'success')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content execution-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="runner-icon-badge">
              <Zap size={18} color="var(--color-accent-secondary)" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '700' }}>
                Workflow Test Execution Runner
              </h3>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                {workflowSpec || `Workflow ID #${workflowId}`}
              </span>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body execution-body">
          {/* Input Section */}
          <div className="runner-config-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: '600', color: 'var(--color-text-primary)' }}>
                Initial Process Variables (JSON)
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button 
                  className="btn btn-secondary" 
                  style={{ fontSize: '11px', padding: '2px 8px' }}
                  onClick={() => setInitialVariables(JSON.stringify({ amount: 75000, priority: "HIGH", department: "Finance" }, null, 2))}
                >
                  Preset: High Value
                </button>
                <button 
                  className="btn btn-secondary" 
                  style={{ fontSize: '11px', padding: '2px 8px' }}
                  onClick={() => setInitialVariables(JSON.stringify({ amount: 15000, priority: "LOW", department: "Operations" }, null, 2))}
                >
                  Preset: Standard
                </button>
              </div>
            </div>

            <textarea 
              className={`runner-code-editor ${jsonError ? 'error-border' : ''}`}
              rows={4}
              value={initialVariables}
              onChange={e => handleJsonChange(e.target.value)}
              placeholder='{\n  "risk_score": 85\n}'
            />
            {jsonError && (
              <span style={{ color: 'var(--color-error)', fontSize: '11px', marginTop: '4px', display: 'block' }}>
                {jsonError}
              </span>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
              <button 
                className="btn btn-primary" 
                disabled={executing || !!jsonError}
                onClick={handleRunWorkflow}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                {executing ? (
                  <>
                    <Loader size={14} className="spinner" />
                    <span>Executing SpiffWorkflow...</span>
                  </>
                ) : (
                  <>
                    <Play size={14} fill="currentColor" />
                    <span>Start Test Execution</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Execution Result Area */}
          {executionResult && (
            <div className="runner-results-card">
              {/* Status Header */}
              <div className="runner-status-banner">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {executionResult.status === 'Completed' ? (
                    <div className="status-indicator completed">
                      <CheckCircle2 size={16} />
                    </div>
                  ) : (
                    <div className="status-indicator running">
                      <Clock size={16} className="spinner-slow" />
                    </div>
                  )}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '14px', fontWeight: '700' }}>
                        Instance #{executionResult.instance_id}
                      </span>
                      <span className={`status-badge ${executionResult.status.toLowerCase()}`}>
                        {executionResult.status}
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                      Current Activity: <strong>{executionResult.current_task_code || 'None'}</strong>
                    </span>
                  </div>
                </div>

                <button 
                  className="btn btn-secondary" 
                  style={{ fontSize: '12px', padding: '4px 10px', gap: '6px' }}
                  onClick={() => refreshInstanceState(executionResult.instance_id)}
                  title="Refresh State"
                >
                  <RefreshCw size={13} />
                  <span>Refresh</span>
                </button>
              </div>

              {/* Tabs */}
              <div className="runner-tabs">
                <button 
                  className={`runner-tab ${activeTab === 'tasks' ? 'active' : ''}`}
                  onClick={() => setActiveTab('tasks')}
                >
                  <UserCheck size={14} />
                  <span>Ready Human Tasks ({executionResult.ready_tasks?.length || 0})</span>
                </button>
                <button 
                  className={`runner-tab ${activeTab === 'variables' ? 'active' : ''}`}
                  onClick={() => setActiveTab('variables')}
                >
                  <Code size={14} />
                  <span>Process Variables</span>
                </button>
                <button 
                  className={`runner-tab ${activeTab === 'logs' ? 'active' : ''}`}
                  onClick={() => setActiveTab('logs')}
                >
                  <Layers size={14} />
                  <span>Activity Logs ({executionResult.logs?.length || 0})</span>
                </button>
              </div>

              {/* Tab Contents */}
              <div className="runner-tab-body">
                {/* 1. Human Tasks Tab */}
                {activeTab === 'tasks' && (
                  <div>
                    {(!executionResult.ready_tasks || executionResult.ready_tasks.length === 0) ? (
                      <div className="empty-tasks-state">
                        {executionResult.status === 'Completed' ? (
                          <span style={{ color: 'var(--color-success)', fontWeight: '600' }}>
                            Workflow execution completed successfully! No pending tasks.
                          </span>
                        ) : (
                          <span style={{ color: 'var(--color-text-muted)' }}>
                            No active Human Tasks blocking execution.
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="tasks-list">
                        {executionResult.ready_tasks.map(task => (
                          <div key={task.task_id} className="task-action-card">
                            <div className="task-action-header">
                              <div>
                                <span className="task-step-name">{task.task_spec_id}</span>
                                <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                                  <span className="role-tag">Role: {task.role_code}</span>
                                  <span className="status-tag">Task #{task.task_id}</span>
                                </div>
                              </div>
                              <span className="task-ready-badge">READY</span>
                            </div>

                            <div className="task-action-buttons">
                              <button 
                                className="btn btn-approve"
                                disabled={completingTaskId === task.task_id}
                                onClick={() => handleCompleteTask(task.task_id, 'APPROVE')}
                              >
                                <ThumbsUp size={13} />
                                <span>Approve & Continue</span>
                              </button>
                              <button 
                                className="btn btn-reject"
                                disabled={completingTaskId === task.task_id}
                                onClick={() => handleCompleteTask(task.task_id, 'REJECT')}
                              >
                                <ThumbsDown size={13} />
                                <span>Reject</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Process Variables Tab */}
                {activeTab === 'variables' && (
                  <div className="runner-code-box">
                    <pre>
                      {JSON.stringify(executionResult.variables || {}, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 3. Activity Trace Logs Tab */}
                {activeTab === 'logs' && (
                  <div className="runner-logs-list">
                    {(!executionResult.logs || executionResult.logs.length === 0) ? (
                      <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                        No activity traces recorded yet.
                      </span>
                    ) : (
                      executionResult.logs.map((l, idx) => (
                        <div key={idx} className="runner-log-row">
                          <span className={`log-badge ${l.status.toLowerCase()}`}>{l.status}</span>
                          <span className="log-name">{l.activity_name || l.activity_id}</span>
                          <span className="log-type">{l.activity_type}</span>
                          <span className="log-time">{new Date(l.timestamp).toLocaleTimeString()}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
