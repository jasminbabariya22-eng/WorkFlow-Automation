import React from 'react'
import {
  Activity,
  X,
  Database,
  Clock,
  RefreshCw,
  RotateCcw,
  Play,
  Check,
  GitFork,
  FileText
} from 'lucide-react'

export default function DesignerTestRunnerModal({
  isOpen,
  onClose,
  workflowName,
  specId,
  nodes,
  edges,
  testSubTab,
  setTestSubTab,
  testRecordId,
  setTestRecordId,
  fetchRecordState,
  startGenericSimulation,
  handleResetTestRecord,
  testLoading,
  simActiveNodeId,
  setSimActiveNodeId,
  simStatus,
  simHistory,
  testRecordData,
  testTxLogs,
  handleGenericNodeAction
}) {
  if (!isOpen) return null

  return (
    <div className="wf-validation-modal-overlay" onClick={onClose}>
      <div className="wf-test-modal-card wf-test-modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="wf-modal-header">
          <div className="flex items-center gap-2">
            <Activity size={18} color="#818cf8" />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-white">Dynamic Workflow Test Runner & DB Inspector</span>
                <span className="text-xs text-muted" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: '4px' }}>
                  Generic Engine
                </span>
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                Active Workflow: <strong>{workflowName || specId || 'Custom Workflow'}</strong> ({nodes.length} Nodes, {edges.length} Edges)
              </div>
            </div>
          </div>
          <button className="wf-modal-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Sub Tabs */}
        <div className="wf-test-subtabs">
          <button
            className={`wf-test-subtab-btn ${testSubTab === 'interactive' ? 'active' : ''}`}
            onClick={() => setTestSubTab('interactive')}
          >
            <Database size={14} />
            <span>Interactive Runner & Live DB</span>
          </button>
          <button
            className={`wf-test-subtab-btn ${testSubTab === 'transactions' ? 'active' : ''}`}
            onClick={() => setTestSubTab('transactions')}
          >
            <Clock size={14} />
            <span>Execution Trace & SQL Logs ({testTxLogs.length})</span>
          </button>
        </div>

        <div className="wf-modal-content" style={{ maxHeight: '540px' }}>
          {/* Record Selector Bar */}
          <div className="wf-test-record-bar">
            <div className="wf-test-record-input-group">
              <span style={{ fontSize: '12px', fontWeight: '600', color: '#94a3b8' }}>Target Record ID:</span>
              <input
                type="number"
                className="wf-test-record-input"
                value={testRecordId}
                onChange={(e) => setTestRecordId(e.target.value)}
                placeholder="e.g. 273"
              />
              <button
                className="wf-btn wf-btn-outline"
                style={{ fontSize: '11px', padding: '5px 10px' }}
                onClick={() => { fetchRecordState(testRecordId); startGenericSimulation(); }}
                disabled={testLoading}
              >
                <RefreshCw size={12} className={testLoading ? 'spinner' : ''} />
                <span>Reload Record & Restart</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                className="wf-btn wf-btn-outline"
                style={{ fontSize: '11px', padding: '5px 10px', color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.3)' }}
                onClick={handleResetTestRecord}
                disabled={testLoading}
                title="Reset record to initial pending status"
              >
                <RotateCcw size={12} />
                <span>Reset Record</span>
              </button>
              <button
                className="wf-btn wf-btn-outline"
                style={{ fontSize: '11px', padding: '5px 10px', color: '#60a5fa', borderColor: 'rgba(96, 165, 250, 0.3)' }}
                onClick={startGenericSimulation}
                disabled={testLoading}
                title="Restart flow from Start node"
              >
                <Play size={12} />
                <span>Restart Flow</span>
              </button>
            </div>
          </div>

          {testSubTab === 'interactive' && (
            <div>
              {/* Dynamic Active Step Execution Card */}
              {(() => {
                const activeNode = nodes.find(n => n.id === simActiveNodeId) || nodes[0]
                if (!activeNode) return null

                const nodeType = activeNode.type || 'userTask'
                const nodeLabel = activeNode.data?.label || activeNode.data?.name || activeNode.id
                const nodeRole = activeNode.data?.role || activeNode.data?.roleId || activeNode.data?.roleName
                const nodeActions = activeNode.data?.actions || activeNode.data?.derivedActions || ['APPROVE', 'REJECT']

                return (
                  <div style={{ background: 'rgba(30, 41, 59, 0.8)', border: '1px solid #6366f1', borderRadius: '8px', padding: '14px', marginBottom: '14px', boxShadow: '0 0 20px rgba(99, 102, 241, 0.2)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span style={{ background: '#6366f1', color: '#fff', fontSize: '10px', fontWeight: '800', padding: '2px 7px', borderRadius: '4px', textTransform: 'uppercase' }}>
                          ACTIVE NODE: {nodeType}
                        </span>
                        <span style={{ fontSize: '14px', fontWeight: '700', color: '#f8fafc' }}>
                          {nodeLabel}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                        Status: <strong style={{ color: simStatus === 'COMPLETED' ? '#4ade80' : simStatus === 'REJECTED' ? '#f87171' : '#fbbf24' }}>{simStatus}</strong>
                      </span>
                    </div>

                    {/* Node Details */}
                    <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '12px' }}>
                      {nodeType === 'userTask' || nodeType === 'approval' ? (
                        <div>
                          Assigned Reviewer Role: <code style={{ color: '#60a5fa' }}>{nodeRole || 'MANAGER'}</code>. Please select an action to submit this task:
                        </div>
                      ) : nodeType === 'condition' ? (
                        <div>
                          Rule Evaluation: <code>{activeNode.data?.field || 'action'} {activeNode.data?.operator || 'equals'} '{activeNode.data?.value || 'APPROVE'}'</code>
                        </div>
                      ) : nodeType === 'record' || nodeType === 'dbUpdate' ? (
                        <div>
                          Target Database: <code>{activeNode.data?.table || testRecordData?.table_name || 'leave_requests'}</code> &bull; Pending Updates: {
                            (activeNode.data?.fieldMappings || []).map(f => `${f.field} = ${f.value}`).join(', ') || 'status update'
                          }
                        </div>
                      ) : nodeType === 'communication' || nodeType === 'notification' ? (
                        <div>
                          Email Recipient: <code>{activeNode.data?.to || '{{employee_email}}'}</code> &bull; Subject: <em>{activeNode.data?.subject || 'Workflow Notification'}</em>
                        </div>
                      ) : nodeType === 'end' ? (
                        <div style={{ color: '#4ade80', fontWeight: '600' }}>
                          🎉 Workflow process reached terminal state ({nodeLabel}).
                        </div>
                      ) : (
                        <div>Process Entry Point</div>
                      )}
                    </div>

                    {/* Dynamic Action Buttons */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {nodeType === 'userTask' || nodeType === 'approval' ? (
                        nodeActions.map((act) => {
                          const actName = typeof act === 'string' ? act : (act.label || act.id)
                          const isApprove = actName.toUpperCase().includes('APPROVE')
                          const isReject = actName.toUpperCase().includes('REJECT')

                          return (
                            <button
                              key={actName}
                              className={isApprove ? 'wf-btn-test-approve' : isReject ? 'wf-btn-test-reject' : 'wf-btn wf-btn-primary'}
                              disabled={testLoading}
                              onClick={() => handleGenericNodeAction(activeNode, actName.toUpperCase())}
                            >
                              {isApprove ? <Check size={13} /> : isReject ? <X size={13} /> : <Play size={13} />}
                              <span>{actName}</span>
                            </button>
                          )
                        })
                      ) : nodeType === 'condition' ? (
                        <button
                          className="wf-btn wf-btn-primary"
                          disabled={testLoading}
                          onClick={() => handleGenericNodeAction(activeNode)}
                        >
                          <GitFork size={13} />
                          <span>Evaluate Condition & Advance Branch</span>
                        </button>
                      ) : nodeType === 'record' || nodeType === 'dbUpdate' ? (
                        <button
                          className="wf-btn wf-btn-primary"
                          style={{ background: '#2563eb', borderColor: '#3b82f6' }}
                          disabled={testLoading}
                          onClick={() => handleGenericNodeAction(activeNode, 'UPDATE')}
                        >
                          <Database size={13} />
                          <span>Execute DB Update & Advance</span>
                        </button>
                      ) : nodeType === 'communication' || nodeType === 'notification' ? (
                        <button
                          className="wf-btn wf-btn-primary"
                          style={{ background: '#7c3aed', borderColor: '#8b5cf6' }}
                          disabled={testLoading}
                          onClick={() => handleGenericNodeAction(activeNode, 'SEND')}
                        >
                          <FileText size={13} />
                          <span>Dispatch Notification & Advance</span>
                        </button>
                      ) : nodeType === 'end' ? (
                        <button
                          className="wf-btn wf-btn-outline"
                          onClick={startGenericSimulation}
                        >
                          <RotateCcw size={13} />
                          <span>Run Again from Start</span>
                        </button>
                      ) : (
                        <button
                          className="wf-btn wf-btn-primary"
                          disabled={testLoading}
                          onClick={() => handleGenericNodeAction(activeNode, 'NEXT')}
                        >
                          <Play size={13} />
                          <span>Start Execution Flow</span>
                        </button>
                      )}
                    </div>
                  </div>
                )
              })()}

              {/* Live Database Record Card (100% Generic) */}
              <div style={{ marginBottom: '14px' }}>
                <div className="flex items-center justify-between mb-2">
                  <span style={{ fontSize: '12px', fontWeight: '700', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Database size={13} color="#38bdf8" />
                    <span>Client Database: <code style={{ color: '#38bdf8' }}>{testRecordData?.table_name || 'Target Table'}</code> (Live {testRecordData?.primary_key || 'ID'}: #{testRecordId})</span>
                  </span>
                  {testRecordData && (
                    <div className="flex items-center gap-2">
                      {testRecordData.title_value && (
                        <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px' }}>
                          {String(testRecordData.title_value).slice(0, 30)}
                        </span>
                      )}
                      <span className={`wf-status-tag ${testRecordData.status_value === 10 || String(testRecordData.status_value).toUpperCase().includes('COMPLET') || String(testRecordData.status_value).toUpperCase().includes('APPROV') ? 'completed' :
                          testRecordData.status_value === -1 || String(testRecordData.status_value).toUpperCase().includes('REJECT') ? 'rejected' : 'open'
                        }`}>
                        {testRecordData.status_field ? `${testRecordData.status_field}: ${testRecordData.status_value}` : `Record #${testRecordId}`}
                      </span>
                    </div>
                  )}
                </div>

                {testRecordData?.raw_data ? (
                  <div style={{ overflowX: 'auto', background: 'rgba(0,0,0,0.25)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <table className="wf-live-db-table">
                      <thead>
                        <tr>
                          {Object.keys(testRecordData.raw_data)
                            .filter(k => {
                              const kl = k.toLowerCase()
                              return !kl.includes('description') && !kl.includes('json') && !kl.includes('xml')
                            })
                            .slice(0, 8)
                            .map(col => (
                              <th key={col} style={{ textTransform: 'capitalize' }}>
                                {col.replace(/_/g, ' ')}
                              </th>
                            ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          {Object.entries(testRecordData.raw_data)
                            .filter(([k]) => {
                              const kl = k.toLowerCase()
                              return !kl.includes('description') && !kl.includes('json') && !kl.includes('xml')
                            })
                            .slice(0, 8)
                            .map(([col, val]) => {
                              const valStr = val === null || val === undefined ? '—' : String(val)
                              const isApproved = val === 1 || valStr.toUpperCase().includes('APPROV') || val === 10
                              const isRejected = val === -1 || valStr.toUpperCase().includes('REJECT')

                              return (
                                <td key={col}>
                                  <span style={{
                                    color: isApproved ? '#4ade80' : isRejected ? '#f87171' : col.includes('id') || col.includes('code') ? '#60a5fa' : '#f1f5f9',
                                    fontWeight: isApproved || isRejected || col.includes('id') || col.includes('status') ? '700' : '400'
                                  }}>
                                    {valStr}
                                  </span>
                                </td>
                              )
                            })}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-xs text-muted p-3 text-center" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                    Loading live record from Client Database...
                  </div>
                )}
              </div>

              {/* Live Email Jobs Queue Table */}
              {testRecordData?.latest_email_jobs && testRecordData.latest_email_jobs.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div className="flex items-center justify-between mb-1">
                    <span style={{ fontSize: '11.5px', fontWeight: '700', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <FileText size={12} color="#a78bfa" />
                      <span>Client DB Dispatched Notification Jobs</span>
                    </span>
                    <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>
                      Auto-dispatched by Workflow Notification Node
                    </span>
                  </div>
                  <table className="wf-live-db-table">
                    <thead>
                      <tr>
                        <th style={{ width: '80px' }}>Job ID</th>
                        <th>Recipient (email_to)</th>
                        <th>Subject</th>
                        <th style={{ width: '90px' }}>Status</th>
                        <th style={{ width: '130px' }}>Created On</th>
                      </tr>
                    </thead>
                    <tbody>
                      {testRecordData.latest_email_jobs.slice(0, 3).map((job) => (
                        <tr key={job.email_job_id}>
                          <td style={{ fontWeight: '700', color: '#c084fc' }}>#{job.email_job_id}</td>
                          <td style={{ color: '#38bdf8' }}>{job.email_to}</td>
                          <td>{job.email_subject}</td>
                          <td>
                            <span style={{
                              background: 'rgba(34, 197, 94, 0.15)',
                              color: '#4ade80',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: '700',
                              fontSize: '10.5px'
                            }}>
                              {job.send_status || 'New'}
                            </span>
                          </td>
                          <td style={{ fontSize: '10.5px', color: '#94a3b8' }}>
                            {job.created_on ? new Date(job.created_on).toLocaleTimeString() : 'Just now'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Flow Path Stepper */}
              <div>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#f1f5f9', display: 'block', marginBottom: '8px' }}>
                  Current Process Nodes on Canvas ({nodes.length}):
                </span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {nodes.map((n, idx) => {
                    const isCurrentActive = n.id === simActiveNodeId
                    const wasExecuted = simHistory.some(h => h.nodeId === n.id)

                    return (
                      <div
                        key={n.id}
                        style={{
                          background: isCurrentActive ? 'rgba(99, 102, 241, 0.25)' : wasExecuted ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                          border: isCurrentActive ? '1px solid #818cf8' : wasExecuted ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '11px',
                          cursor: 'pointer'
                        }}
                        onClick={() => setSimActiveNodeId(n.id)}
                        title={`Click to focus node: ${n.data?.label || n.id}`}
                      >
                        <span style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          background: isCurrentActive ? '#6366f1' : wasExecuted ? '#22c55e' : '#334155',
                          color: '#fff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '10px',
                          fontWeight: '700'
                        }}>
                          {idx + 1}
                        </span>
                        <span style={{ color: isCurrentActive ? '#f8fafc' : '#94a3b8', fontWeight: isCurrentActive ? '700' : '500' }}>
                          {n.data?.label || n.data?.name || n.type}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {testSubTab === 'transactions' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#f1f5f9' }}>
                  Real-Time Node Execution Trace & SQL Logs:
                </span>
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Auto-recorded on each step
                </span>
              </div>

              {testTxLogs.length === 0 ? (
                <div className="text-xs text-muted p-4 text-center" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                  No transactions executed in this session yet. Choose an action in the first tab to execute steps!
                </div>
              ) : (
                <div className="wf-tx-log-box">
                  {testTxLogs.map((tx, idx) => (
                    <div key={idx} className="wf-tx-log-entry">
                      <div className="flex items-center justify-between" style={{ marginBottom: '4px' }}>
                        <span style={{ color: '#818cf8', fontWeight: '700' }}>
                          [{tx.timestamp}] {tx.nodeName || tx.action}
                        </span>
                        <div className="flex items-center gap-2">
                          {tx.status && (
                            <span style={{ color: '#4ade80', fontSize: '10.5px', background: 'rgba(34, 197, 94, 0.1)', padding: '1px 5px', borderRadius: '3px' }}>
                              {tx.status}
                            </span>
                          )}
                          {tx.duration && (
                            <span style={{ color: '#94a3b8', fontSize: '10.5px' }}>{tx.duration}</span>
                          )}
                        </div>
                      </div>
                      {tx.message && (
                        <div style={{ color: '#e2e8f0', fontSize: '11.5px', marginBottom: '2px' }}>
                          {tx.message}
                        </div>
                      )}
                      {tx.sql && (
                        <div style={{ color: '#38bdf8', fontSize: '11px', wordBreak: 'break-all' }}>
                          <code>{tx.sql}</code>
                        </div>
                      )}
                      {tx.diff && (
                        <div style={{ marginTop: '4px', fontSize: '11px', color: '#fbbf24' }}>
                          Modified: {Object.entries(tx.diff).map(([k, v]) => `${k} &rarr; ${v.label || v.new} (${v.new})`).join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="wf-modal-footer flex items-center justify-between">
          <span className="text-xs text-muted">
            Engine automatically traverses all node types & updates <code style={{ color: '#38bdf8' }}>Client DB</code>
          </span>
          <button
            className="wf-btn wf-btn-primary"
            onClick={onClose}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
