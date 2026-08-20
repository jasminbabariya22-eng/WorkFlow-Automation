import React, { useEffect, useState } from 'react'
import { 
  Activity, 
  Search, 
  Filter, 
  Clock, 
  Database, 
  History, 
  FileText, 
  CheckCircle2, 
  AlertTriangle,
  Play,
  Loader
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

function Monitoring({ showToast }) {
  const [instances, setInstances] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedInstance, setSelectedInstance] = useState(null)
  
  // Search/Filters
  const [statusFilter, setStatusFilter] = useState('')
  const [entityFilter, setEntityFilter] = useState('')
  
  // Instance Detail States
  const [variables, setVariables] = useState({})
  const [logs, setLogs] = useState([])
  const [history, setHistory] = useState([])
  const [detailTab, setDetailTab] = useState('variables')
  const [detailsLoading, setDetailsLoading] = useState(false)

  // Fetch instances list
  const fetchInstances = async () => {
    setLoading(true)
    try {
      let data = await workflowStorage.getInstances()
      if (statusFilter) {
        data = data.filter(i => i.status === statusFilter)
      }
      if (entityFilter) {
        data = data.filter(i => i.entity_type === entityFilter)
      }
      setInstances(data || [])
      if (data && data.length > 0 && !selectedInstance) {
        await loadInstanceDetails(data[0].instance_id, data)
      }
    } catch (e) {
      showToast('Error while fetching monitoring instances', 'error')
    } finally {
      setLoading(false)
    }
  }

  // Load selected instance details
  const loadInstanceDetails = async (instanceId, instancesList = instances) => {
    setDetailsLoading(true)
    const instObj = instancesList.find(i => i.instance_id === instanceId)
    setSelectedInstance(instObj || { instance_id: instanceId, status: 'Running' })
    try {
      const details = await workflowStorage.getInstanceDetails(instanceId)
      setVariables(details.variables || {})
      setLogs(details.logs || [])
      setHistory(details.history || [])
    } catch (e) {
      showToast('Failed to load instance variables or trace logs', 'error')
    } finally {
      setDetailsLoading(false)
    }
  }

  useEffect(() => {
    fetchInstances()
  }, [statusFilter, entityFilter])

  // Recalculate variables when selectedInstance changes
  useEffect(() => {
    if (selectedInstance && instances.length > 0) {
      loadInstanceDetails(selectedInstance.instance_id)
    }
  }, [instances.length])

  return (
    <div className="monitoring-grid">
      {/* Left Column: Instances List */}
      <div className="sidebar-card-list">
        <div className="list-header" style={{ borderBottom: '1px solid var(--border-glass)', padding: '16px 20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Execution Instances
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <select 
                className="filter-select"
                style={{ padding: '6px 8px', fontSize: '12px', flex: 1 }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="Running">Running</option>
                <option value="Completed">Completed</option>
                <option value="Failed">Failed</option>
              </select>
              <select 
                className="filter-select"
                style={{ padding: '6px 8px', fontSize: '12px', flex: 1 }}
                value={entityFilter}
                onChange={(e) => setEntityFilter(e.target.value)}
              >
                <option value="">All Entities</option>
                <option value="Risk">Risk Entity</option>
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
            <Loader className="spinner" size={20} color="var(--color-accent-secondary)" />
          </div>
        ) : instances.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '13px' }}>
            No instances found.
          </div>
        ) : (
          <div style={{ overflowY: 'auto', flexGrow: 1 }}>
            {instances.map(inst => (
              <div 
                key={inst.instance_id}
                className={`instance-card ${selectedInstance?.instance_id === inst.instance_id ? 'active' : ''}`}
                onClick={() => loadInstanceDetails(inst.instance_id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: '600', fontSize: '14px', color: 'var(--color-accent-secondary)' }}>
                    Instance #{inst.instance_id}
                  </span>
                  <span className={`status-badge ${(inst.status || 'Running').toLowerCase()}`} style={{ padding: '2px 6px', fontSize: '10px' }}>
                    {inst.status || 'Running'}
                  </span>
                </div>
                <div style={{ marginTop: '6px', fontSize: '12px' }}>
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: '500' }}>{inst.entity_type}</span>: ID {inst.entity_id}
                </div>
                <div className="instance-card-meta">
                  <span>Current Task: {inst.current_task_code || '—'}</span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                  Started: {new Date(inst.started_on).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Column: Detail View */}
      <div className="monitoring-detail-pane">
        {selectedInstance ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Header */}
            <div className="detail-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: '600' }}>
                    Execution Trace Details
                  </h3>
                  <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                    Entity: <span style={{ color: 'var(--color-text-primary)', fontWeight: '500' }}>{selectedInstance.entity_type}</span> (ID {selectedInstance.entity_id}) | Definition ID: {selectedInstance.bpmn_definition_id}
                  </p>
                </div>
                <span className={`status-badge ${(selectedInstance?.status || 'Running').toLowerCase()}`}>
                  {selectedInstance?.status || 'Running'}
                </span>
              </div>
            </div>

            {/* Tabs */}
            <div className="pane-tabs">
              <button 
                className={`tab-btn ${detailTab === 'variables' ? 'active' : ''}`}
                onClick={() => setDetailTab('variables')}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <Database size={14} />
                  <span>Process Variables</span>
                </div>
              </button>
              <button 
                className={`tab-btn ${detailTab === 'traces' ? 'active' : ''}`}
                onClick={() => setDetailTab('traces')}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <Clock size={14} />
                  <span>Activity Steps Logs</span>
                </div>
              </button>
              <button 
                className={`tab-btn ${detailTab === 'transitions' ? 'active' : ''}`}
                onClick={() => setDetailTab('transitions')}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <History size={14} />
                  <span>Approval Audit Trails</span>
                </div>
              </button>
            </div>

            {/* Details Content */}
            <div className="detail-body">
              {detailsLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
                  <Loader className="spinner" size={24} color="var(--color-accent-secondary)" />
                </div>
              ) : (
                <div>
                  {/* Variables Tab */}
                  {detailTab === 'variables' && (
                    <div>
                      {Object.keys(variables).length === 0 ? (
                        <div style={{ color: 'var(--color-text-muted)', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
                          No variables stored in process data scopes.
                        </div>
                      ) : (
                        <div className="glass-table-container">
                          <table className="glass-table">
                            <thead>
                              <tr>
                                <th>Variable Name</th>
                                <th>Data Value / Scope</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(variables).map(([k, v]) => (
                                <tr key={k}>
                                  <td style={{ fontWeight: '600', color: 'var(--color-accent-secondary)' }}>{k}</td>
                                  <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Activity Traces Tab */}
                  {detailTab === 'traces' && (
                    <div>
                      {logs.length === 0 ? (
                        <div style={{ color: 'var(--color-text-muted)', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
                          No activity step traces logged for this execution.
                        </div>
                      ) : (
                        <div className="glass-table-container">
                          <table className="glass-table">
                            <thead>
                              <tr>
                                <th>Step Name</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Completed On</th>
                              </tr>
                            </thead>
                            <tbody>
                              {logs.map((log, idx) => (
                                <tr key={idx}>
                                  <td style={{ fontWeight: '500' }}>
                                    {log.activity_name || log.activity_id}
                                  </td>
                                  <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{log.activity_type}</td>
                                  <td>
                                    <span className={`status-badge ${log.status === 'COMPLETED' ? 'active' : 'archived'}`} style={{ fontSize: '10px', padding: '2px 6px' }}>
                                      {log.status}
                                    </span>
                                  </td>
                                  <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                    {new Date(log.timestamp).toLocaleString()}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Transition Audit History */}
                  {detailTab === 'transitions' && (
                    <div>
                      {history.length === 0 ? (
                        <div style={{ color: 'var(--color-text-muted)', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
                          No transitions recorded.
                        </div>
                      ) : (
                        <div className="glass-table-container">
                          <table className="glass-table">
                            <thead>
                              <tr>
                                <th>Action / Transition</th>
                                <th>Performed By</th>
                                <th>Assigned Role</th>
                                <th>Date Performed</th>
                                <th>Remarks</th>
                              </tr>
                            </thead>
                            <tbody>
                              {history.map((h, idx) => (
                                <tr key={idx}>
                                  <td style={{ fontWeight: '500', color: 'var(--color-accent-secondary)' }}>
                                    {h.action_name}
                                  </td>
                                  <td style={{ fontWeight: '500' }}>User ID {h.performed_by}</td>
                                  <td>{h.performed_role}</td>
                                  <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                    {new Date(h.performed_on).toLocaleString()}
                                  </td>
                                  <td style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                                    {h.remarks || '—'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, justifyContent: 'center', alignItems: 'center', padding: '40px' }}>
            <Activity size={48} color="var(--color-text-muted)" style={{ marginBottom: '16px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: '500', color: 'var(--color-text-muted)' }}>
              Select an execution instance to view traces
            </h3>
          </div>
        )}
      </div>
    </div>
  )
}

export default Monitoring
