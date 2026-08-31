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
  ThumbsDown,
  Hash,
  ChevronDown,
  ChevronRight
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

export default function ExecutionModal({ workflowId, workflowSpec, onClose, showToast }) {
  // Primary Entity ID input
  const [entityIdInput, setEntityIdInput] = useState('5213')
  
  // Advanced JSON input
  const [showAdvancedJson, setShowAdvancedJson] = useState(false)
  const [extraVariables, setExtraVariables] = useState('{\n  "priority": "HIGH",\n  "remarks": "Test execution"\n}')
  const [jsonError, setJsonError] = useState(null)
  
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState(null)
  const [activeTab, setActiveTab] = useState('tasks') // 'tasks' | 'variables' | 'logs'
  
  // Task completion state
  const [taskPayloads, setTaskPayloads] = useState({})
  const [completingTaskId, setCompletingTaskId] = useState(null)

  // Validate JSON on change
  const handleJsonChange = (val) => {
    setExtraVariables(val)
    try {
      if (val.trim()) JSON.parse(val)
      setJsonError(null)
    } catch (err) {
      setJsonError(err.message)
    }
  }

  // Trigger Execution
  const handleRunWorkflow = async () => {
    const rawId = entityIdInput.trim()
    if (!rawId) {
      showToast?.('Please enter a valid Entity ID (Record ID).', 'error')
      return
    }

    const numericId = isNaN(Number(rawId)) ? rawId : Number(rawId)

    let parsedExtra = {}
    if (showAdvancedJson && extraVariables.trim()) {
      try {
        parsedExtra = JSON.parse(extraVariables)
      } catch (err) {
        showToast?.('Invalid JSON in advanced variables', 'error')
        return
      }
    }

    const payload = {
      entity_id: numericId,
      record_id: numericId,
      ...parsedExtra
    }

    setExecuting(true)
    try {
      const result = await workflowStorage.executeWorkflow(workflowId, payload)
      setExecutionResult(result)
      showToast?.('Workflow execution started successfully!', 'success')
      if (result.status === 'Completed') {
        setActiveTab('logs')
      } else {
        setActiveTab('tasks')
      }
    } catch (err) {
      showToast?.('Execution simulation failed: ' + (err.message || ''), 'error')
    } finally {
      setExecuting(false)
    }
  }

  // Complete a pending Human Task
  const handleCompleteTask = async (taskId, action = 'APPROVE') => {
    setCompletingTaskId(taskId)
    try {
      const rawId = entityIdInput.trim()
      const numericId = isNaN(Number(rawId)) ? rawId : Number(rawId)
      const payloadData = taskPayloads[taskId] || {}
      
      const vars = {
        entity_id: numericId,
        record_id: numericId,
        instance_id: executionResult?.instance_id,
        action: action,
        approved: action === 'APPROVE',
        ...payloadData
      }

      const taskResult = await workflowStorage.completeTask(taskId, action, vars, `Action ${action} submitted via Test Runner`, workflowId)
      showToast?.(`Task completed successfully with ${action}!`, 'success')

      setExecutionResult(prev => ({
        ...prev,
        status: taskResult.instance_status || 'Completed',
        current_task_code: taskResult.next_task || 'End',
        ready_tasks: (taskResult.instance_status === 'Completed' || action === 'REJECT') ? [] : (taskResult.ready_tasks || []),
        variables: { ...(prev?.variables || {}), ...(taskResult.variables || {}), last_action: action },
        logs: taskResult.logs || [
          ...(prev?.logs || []),
          {
            id: Date.now(),
            activity_name: `User Task: ${action}`,
            activity_type: 'USER_TASK',
            status: 'COMPLETED',
            timestamp: new Date().toISOString()
          }
        ]
      }))

      if (taskResult.instance_status === 'Completed') {
        setActiveTab('logs')
      }
    } catch (err) {
      showToast?.('Error completing task: ' + (err.message || ''), 'error')
    } finally {
      setCompletingTaskId(null)
    }
  }

  // Refresh instance state
  const refreshInstanceState = async (instanceId) => {
    if (!instanceId) return
    const details = await workflowStorage.getInstanceDetails(instanceId)
    setExecutionResult(prev => ({
      ...prev,
      variables: details.variables,
      logs: details.logs
    }))
    showToast?.('Instance state refreshed', 'success')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content execution-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '640px' }}>
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
          <div className="runner-config-card" style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '16px' }}>
            
            {/* Direct Entity ID Input */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#f8fafc', textTransform: 'uppercase', marginBottom: '6px' }}>
                Entity ID / Target Record ID
              </label>
              
              <div style={{ display: 'flex', gap: '8px' }}>
                <div style={{ position: 'relative', flexGrow: 1 }}>
                  <Hash size={14} style={{ position: 'absolute', left: '12px', top: '12px', color: '#64748b' }} />
                  <input
                    type="text"
                    value={entityIdInput}
                    onChange={e => setEntityIdInput(e.target.value)}
                    placeholder="Enter Record ID (e.g. 5213)"
                    style={{
                      width: '100%',
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      borderRadius: '8px',
                      padding: '8px 12px 8px 32px',
                      fontSize: '14px',
                      fontWeight: '600',
                      color: '#38bdf8',
                      outline: 'none'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '11px', padding: '4px 8px' }}
                    onClick={() => setEntityIdInput('5213')}
                    title="Risk HR-2536"
                  >
                    #5213
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '11px', padding: '4px 8px' }}
                    onClick={() => setEntityIdInput('273')}
                  >
                    #273
                  </button>
                </div>
              </div>
              <span style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px', display: 'block' }}>
                The workflow will dynamically execute against this database record.
              </span>
            </div>

            {/* Advanced JSON Toggle */}
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => setShowAdvancedJson(!showAdvancedJson)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '11px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: 0
                }}
              >
                {showAdvancedJson ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span>Advanced Process Variables (Optional JSON)</span>
              </button>

              {showAdvancedJson && (
                <div style={{ marginTop: '8px' }}>
                  <textarea
                    className={`runner-code-editor ${jsonError ? 'error-border' : ''}`}
                    rows={3}
                    value={extraVariables}
                    onChange={e => handleJsonChange(e.target.value)}
                    placeholder='{\n  "priority": "HIGH"\n}'
                    style={{ width: '100%', fontFamily: 'monospace', fontSize: '12px', background: 'rgba(0,0,0,0.5)', borderRadius: '6px', padding: '8px', color: '#cbd5e1' }}
                  />
                  {jsonError && (
                    <span style={{ color: '#ef4444', fontSize: '11px', marginTop: '4px', display: 'block' }}>
                      {jsonError}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Start Button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button 
                className="btn btn-primary" 
                disabled={executing || !entityIdInput.trim() || !!jsonError}
                onClick={handleRunWorkflow}
                style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 18px', fontSize: '13px', fontWeight: '700' }}
              >
                {executing ? (
                  <>
                    <Loader size={14} className="spinner" />
                    <span>Executing Workflow...</span>
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
            <div className="runner-results-card" style={{ marginTop: '16px' }}>
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
                      <span className={`status-badge ${(executionResult.status || 'Running').toLowerCase()}`}>
                        {executionResult.status}
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                      Current Activity: <strong>{executionResult.current_task_code || 'End'}</strong>
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
                      <div className="empty-tasks-state" style={{ padding: '24px', textAlign: 'center' }}>
                        {executionResult.status === 'Completed' ? (
                          <span style={{ color: '#10b981', fontWeight: '600' }}>
                            ✅ Workflow execution completed successfully! No pending tasks.
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
                                <span className="task-step-name">{task.task_name || task.task_spec_id}</span>
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
                          <span className={`log-badge ${(l.status || 'SUCCESS').toLowerCase()}`}>{l.status || 'SUCCESS'}</span>
                          <span className="log-name">{l.activity_name || l.activity_id}</span>
                          <span className="log-type">{l.activity_type}</span>
                          <span className="log-time">{l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : (l.created_on || '—')}</span>
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
