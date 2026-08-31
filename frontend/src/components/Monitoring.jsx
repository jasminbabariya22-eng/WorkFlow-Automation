import React, { useEffect, useState, useRef } from 'react'
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
  Loader,
  Radio,
  Trash2,
  RefreshCw,
  Zap,
  Terminal,
  ShieldCheck,
  ChevronRight,
  ChevronDown
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

function Monitoring({ showToast }) {
  // Main view mode: 'instances' | 'telemetry'
  const [viewMode, setViewMode] = useState('instances')

  // Instances State
  const [instances, setInstances] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedInstance, setSelectedInstance] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [entityFilter, setEntityFilter] = useState('')
  
  // Instance Detail States
  const [variables, setVariables] = useState({})
  const [logs, setLogs] = useState([])
  const [history, setHistory] = useState([])
  const [detailTab, setDetailTab] = useState('variables')
  const [detailsLoading, setDetailsLoading] = useState(false)

  // Live Telemetry & Observability States
  const [telemetryLogs, setTelemetryLogs] = useState([])
  const [telemetryLoading, setTelemetryLoading] = useState(false)
  const [telemetryLevel, setTelemetryLevel] = useState('ALL')
  const [telemetrySearch, setTelemetrySearch] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [metrics, setMetrics] = useState({
    uptime_seconds: 0,
    total_logged_events: 0,
    total_step_executions: 0,
    total_errors: 0,
    average_step_latency_ms: 0,
    error_rate_percentage: 0,
    status: 'HEALTHY'
  })
  const [expandedLogId, setExpandedLogId] = useState(null)

  // 1. Fetch Instances List
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
      showToast?.('Error while fetching monitoring instances', 'error')
    } finally {
      setLoading(false)
    }
  }

  // 2. Load Selected Instance Details
  const loadInstanceDetails = async (instanceId, instancesList = instances) => {
    setDetailsLoading(true)
    const instObj = instancesList.find(i => i.instance_id === instanceId)
    setSelectedInstance(instObj || { instance_id: instanceId, status: 'Running' })
    try {
      const details = await workflowStorage.getInstanceDetails(instanceId)
      let vars = details.variables || {}
      if (Object.keys(vars).length === 0 && details.logs && details.logs.length > 0) {
        details.logs.forEach(l => {
          if (l.variables && typeof l.variables === 'object') {
            vars = { ...vars, ...l.variables }
          }
        })
      }
      setVariables(vars)
      setLogs(details.logs || [])
      setHistory(details.history || [])
    } catch (e) {
      showToast?.('Failed to load instance variables or trace logs', 'error')
    } finally {
      setDetailsLoading(false)
    }
  }

  // 3. Fetch Live Telemetry & Metrics
  const fetchTelemetryData = async () => {
    setTelemetryLoading(true)
    try {
      const [logsData, metricsData] = await Promise.all([
        workflowStorage.getLiveTelemetry({
          level: telemetryLevel,
          search: telemetrySearch,
          limit: 150
        }),
        workflowStorage.getObservabilityMetrics()
      ])
      setTelemetryLogs(logsData || [])
      if (metricsData) setMetrics(metricsData)
    } catch (e) {
      console.error(e)
    } finally {
      setTelemetryLoading(false)
    }
  }

  const handleClearTelemetry = async () => {
    const ok = await workflowStorage.clearTelemetry()
    if (ok) {
      showToast?.('Telemetry buffer cleared', 'success')
      fetchTelemetryData()
    }
  }

  useEffect(() => {
    fetchInstances()
  }, [statusFilter, entityFilter])

  useEffect(() => {
    if (viewMode === 'telemetry') {
      fetchTelemetryData()
    }
  }, [viewMode, telemetryLevel, telemetrySearch])

  // Auto-refresh interval for telemetry
  useEffect(() => {
    if (viewMode !== 'telemetry' || !autoRefresh) return
    const timer = setInterval(() => {
      fetchTelemetryData()
    }, 3000)
    return () => clearInterval(timer)
  }, [viewMode, autoRefresh, telemetryLevel, telemetrySearch])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
      
      {/* Top Header & View Mode Switcher */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '12px',
        padding: '12px 20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(14, 165, 233, 0.3)'
          }}>
            <Activity size={20} color="#fff" />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#f8fafc', letterSpacing: '-0.01em' }}>
              Workflow Monitoring & Observability
            </h2>
            <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
              Live execution tracing, distributed telemetry, process variables & audit logs
            </p>
          </div>
        </div>

        {/* Mode Toggle Buttons */}
        <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.35)', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <button
            onClick={() => setViewMode('instances')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'instances' ? 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)' : 'transparent',
              color: viewMode === 'instances' ? '#fff' : '#94a3b8',
              transition: 'all 0.15s ease'
            }}
          >
            <Database size={13} />
            <span>Process Instances</span>
          </button>
          <button
            onClick={() => setViewMode('telemetry')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              border: 'none',
              cursor: 'pointer',
              background: viewMode === 'telemetry' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'transparent',
              color: viewMode === 'telemetry' ? '#fff' : '#94a3b8',
              transition: 'all 0.15s ease'
            }}
          >
            <Radio size={13} />
            <span>Live Observability Stream</span>
            {metrics.total_logged_events > 0 && (
              <span style={{ fontSize: '10px', background: 'rgba(255, 255, 255, 0.2)', padding: '1px 5px', borderRadius: '10px' }}>
                {metrics.total_logged_events}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* VIEW 1: PROCESS INSTANCES TRACE VIEW */}
      {viewMode === 'instances' && (
        <div className="monitoring-grid" style={{ flexGrow: 1, minHeight: 0 }}>
          {/* Left Column: Instances List */}
          <div className="sidebar-card-list">
            <div className="list-header" style={{ borderBottom: '1px solid var(--border-glass)', padding: '16px 20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                    Active Instances ({instances.length})
                  </span>
                  <button 
                    onClick={fetchInstances} 
                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  >
                    <RefreshCw size={12} />
                  </button>
                </div>
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
                    {Array.from(new Set(instances.map(i => i.entity_type).filter(Boolean))).map(ent => (
                      <option key={ent} value={ent}>{ent}</option>
                    ))}
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
                No instances found in database.
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
                      <span style={{ fontWeight: '600', fontSize: '13px', color: '#38bdf8' }}>
                        Instance #{inst.instance_id}
                      </span>
                      <span className={`status-badge ${(inst.status || 'Running').toLowerCase()}`} style={{ padding: '2px 6px', fontSize: '10px' }}>
                        {inst.status || 'Running'}
                      </span>
                    </div>
                    <div style={{ marginTop: '6px', fontSize: '12px' }}>
                      <span style={{ color: 'var(--color-text-primary)', fontWeight: '500' }}>{inst.entity_type}</span>: ID {inst.entity_id}
                    </div>
                    <div className="instance-card-meta" style={{ marginTop: '4px' }}>
                      <span>Current Task: <b>{inst.current_task_code || '—'}</b></span>
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
                      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '17px', fontWeight: '600' }}>
                        Instance #{selectedInstance.instance_id} Execution Trace
                      </h3>
                      <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                        Entity: <span style={{ color: 'var(--color-text-primary)', fontWeight: '600' }}>{selectedInstance.entity_type}</span> (ID {selectedInstance.entity_id}) | BPMN Spec ID: {selectedInstance.bpmn_definition_id}
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
                      <span>Process Variables ({Object.keys(variables).length})</span>
                    </div>
                  </button>
                  <button 
                    className={`tab-btn ${detailTab === 'traces' ? 'active' : ''}`}
                    onClick={() => setDetailTab('traces')}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                      <Clock size={14} />
                      <span>Activity Steps Logs ({logs.length})</span>
                    </div>
                  </button>
                  <button 
                    className={`tab-btn ${detailTab === 'transitions' ? 'active' : ''}`}
                    onClick={() => setDetailTab('transitions')}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                      <History size={14} />
                      <span>Approval Audit Trails ({history.length})</span>
                    </div>
                  </button>
                </div>

                {/* Details Content */}
                <div className="detail-body" style={{ overflowY: 'auto' }}>
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
                                    <th style={{ width: '35%' }}>Variable Key</th>
                                    <th>Value / Payload</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {Object.entries(variables).map(([k, v]) => (
                                    <tr key={k}>
                                      <td style={{ fontWeight: '600', color: '#38bdf8' }}>{k}</td>
                                      <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                                        {typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
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
                                      <td style={{ fontWeight: '600' }}>
                                        {log.activity_name || log.activity_id}
                                      </td>
                                      <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                        <span style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                                          {log.activity_type}
                                        </span>
                                      </td>
                                      <td>
                                        <span className={`status-badge ${(log.status || 'success').toLowerCase()}`} style={{ fontSize: '10px', padding: '2px 6px' }}>
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
                              No audit transitions recorded.
                            </div>
                          ) : (
                            <div className="glass-table-container">
                              <table className="glass-table">
                                <thead>
                                  <tr>
                                    <th>Action / Transition</th>
                                    <th>Performed By</th>
                                    <th>Role</th>
                                    <th>Timestamp</th>
                                    <th>Remarks</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {history.map((h, idx) => (
                                    <tr key={idx}>
                                      <td style={{ fontWeight: '600', color: '#10b981' }}>
                                        {h.action_name}
                                      </td>
                                      <td style={{ fontWeight: '500' }}>User #{h.performed_by}</td>
                                      <td>
                                        <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                                          {h.performed_role}
                                        </span>
                                      </td>
                                      <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                        {new Date(h.performed_on).toLocaleString()}
                                      </td>
                                      <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
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
                  Select an execution instance on the left to view full trace
                </h3>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 2: LIVE OBSERVABILITY & TELEMETRY STREAM VIEW */}
      {viewMode === 'telemetry' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flexGrow: 1, minHeight: 0 }}>
          
          {/* Top Observability Metrics Bar */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: '12px'
          }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '700' }}>Engine Health</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                <ShieldCheck size={16} color={metrics.status === 'HEALTHY' ? '#10b981' : '#f59e0b'} />
                <span style={{ fontSize: '15px', fontWeight: '700', color: metrics.status === 'HEALTHY' ? '#10b981' : '#f59e0b' }}>
                  {metrics.status}
                </span>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '700' }}>Total Step Runs</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#38bdf8', marginTop: '4px' }}>
                {metrics.total_step_executions}
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '700' }}>Avg Step Latency</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#a855f7', marginTop: '4px' }}>
                {metrics.average_step_latency_ms} ms
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '700' }}>Error Rate</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: metrics.error_rate_percentage > 0 ? '#ef4444' : '#10b981', marginTop: '4px' }}>
                {metrics.error_rate_percentage}% ({metrics.total_errors} errors)
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '700' }}>Buffer Size</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>
                {metrics.total_logged_events} / {metrics.buffer_capacity || 500}
              </div>
            </div>
          </div>

          {/* Telemetry Filter & Controls Toolbar */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '10px 16px',
            gap: '12px'
          }}>
            {/* Level Filter Pills */}
            <div style={{ display: 'flex', gap: '6px' }}>
              {['ALL', 'INFO', 'AUDIT', 'WARN', 'ERROR'].map(lvl => (
                <button
                  key={lvl}
                  onClick={() => setTelemetryLevel(lvl)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontWeight: '700',
                    border: 'none',
                    cursor: 'pointer',
                    background: telemetryLevel === lvl ? 
                      (lvl === 'ERROR' ? '#ef4444' : lvl === 'AUDIT' ? '#10b981' : lvl === 'WARN' ? '#f59e0b' : '#0284c7') 
                      : 'rgba(255, 255, 255, 0.05)',
                    color: telemetryLevel === lvl ? '#fff' : '#94a3b8'
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>

            {/* Search Bar */}
            <div style={{ position: 'relative', flexGrow: 1, maxWidth: '360px' }}>
              <Search size={13} style={{ position: 'absolute', left: '10px', top: '9px', color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search trace, message, node..."
                value={telemetrySearch}
                onChange={(e) => setTelemetrySearch(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  padding: '6px 10px 6px 30px',
                  fontSize: '12px',
                  color: '#fff',
                  outline: 'none'
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#94a3b8', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                <span>Auto-refresh (3s)</span>
              </label>

              <button
                onClick={fetchTelemetryData}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '600',
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#fff',
                  cursor: 'pointer'
                }}
              >
                <RefreshCw size={12} className={telemetryLoading ? 'spinner' : ''} />
                <span>Refresh</span>
              </button>

              <button
                onClick={handleClearTelemetry}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '600',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  cursor: 'pointer'
                }}
              >
                <Trash2 size={12} />
                <span>Clear</span>
              </button>
            </div>
          </div>

          {/* Telemetry Stream Console */}
          <div style={{
            flexGrow: 1,
            background: '#090d16',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            overflowY: 'auto',
            padding: '12px',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}>
            {telemetryLogs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
                <Terminal size={32} style={{ marginBottom: '12px' }} />
                <div>No telemetry logs matching the current filter.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {telemetryLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id
                  const levelColor = 
                    log.level === 'ERROR' ? '#ef4444' :
                    log.level === 'AUDIT' ? '#10b981' :
                    log.level === 'WARN' ? '#f59e0b' : '#38bdf8'

                  return (
                    <div
                      key={log.id}
                      style={{
                        background: 'rgba(15, 23, 42, 0.65)',
                        border: `1px solid ${isExpanded ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255, 255, 255, 0.05)'}`,
                        borderRadius: '6px',
                        padding: '8px 12px',
                        cursor: 'pointer',
                        transition: 'all 0.1s ease'
                      }}
                      onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                          {isExpanded ? <ChevronDown size={12} color="#94a3b8" /> : <ChevronRight size={12} color="#94a3b8" />}
                          <span style={{ color: '#64748b', fontSize: '11px', whiteSpace: 'nowrap' }}>{log.timestamp}</span>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            padding: '1px 5px',
                            borderRadius: '4px',
                            background: `${levelColor}22`,
                            color: levelColor,
                            border: `1px solid ${levelColor}44`
                          }}>
                            {log.level}
                          </span>
                          <span style={{ color: '#cbd5e1', fontWeight: '500', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                            {log.message}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', whiteSpace: 'nowrap' }}>
                          {log.duration_ms !== null && log.duration_ms !== undefined && (
                            <span style={{ color: '#a855f7', fontSize: '11px', background: 'rgba(168, 85, 247, 0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                              ⚡ {log.duration_ms}ms
                            </span>
                          )}
                          <span style={{ color: '#64748b', fontSize: '10px', background: 'rgba(255, 255, 255, 0.04)', padding: '1px 5px', borderRadius: '3px' }}>
                            {log.trace_id}
                          </span>
                        </div>
                      </div>

                      {/* Expandable JSON Detail Payload */}
                      {isExpanded && (
                        <div style={{
                          marginTop: '8px',
                          padding: '10px',
                          background: 'rgba(0, 0, 0, 0.5)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '6px',
                          fontSize: '11px'
                        }}>
                          <div style={{ color: '#38bdf8', fontWeight: '600', marginBottom: '4px' }}>Structured Telemetry Payload:</div>
                          <pre style={{ margin: 0, color: '#94a3b8', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {JSON.stringify(log, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Monitoring
