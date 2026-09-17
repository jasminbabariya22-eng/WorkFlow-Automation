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

function format12Hr(val) {
  if (!val) return '—'
  const d = new Date(val)
  if (isNaN(d.getTime())) return String(val)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  })
}

function Monitoring({ showToast }) {
  // Main view mode: 'instances' | 'telemetry'
  const [viewMode, setViewMode] = useState('instances')

  // Instances State (Instant optimistic cache hydration)
  const [instances, setInstances] = useState(() => {
    try {
      const stored = localStorage.getItem('workflow_studio_instances')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed
      }
    } catch {}
    return []
  })
  const [loading, setLoading] = useState(() => {
    try {
      const stored = localStorage.getItem('workflow_studio_instances')
      return !stored
    } catch {
      return true
    }
  })
  const [selectedInstance, setSelectedInstance] = useState(() => {
    try {
      const stored = localStorage.getItem('workflow_studio_instances')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed[0]
      }
    } catch {}
    return null
  })
  const [statusFilter, setStatusFilter] = useState('')
  const [entityFilter, setEntityFilter] = useState('')
  const [visibleCount, setVisibleCount] = useState(60)
  
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

  // 1. Fetch Instances List (Fast non-blocking)
  const fetchInstances = async (showLoadingSpinner = false) => {
    if (showLoadingSpinner) setLoading(true)
    try {
      let data = await workflowStorage.getInstances()
      if (statusFilter) {
        data = (data || []).filter(i => String(i.status || '').toLowerCase() === statusFilter.toLowerCase())
      }
      if (entityFilter) {
        data = (data || []).filter(i => String(i.entity_type || '').toLowerCase() === entityFilter.toLowerCase())
      }
      const list = data || []
      setInstances(list)
      setLoading(false)

      if (list.length > 0) {
        const toSelect = selectedInstance && list.some(i => i.instance_id === selectedInstance.instance_id)
          ? selectedInstance
          : list[0]
        setSelectedInstance(toSelect)
        loadInstanceDetails(toSelect.instance_id, list)
      }
    } catch (e) {
      setLoading(false)
    }
  }

  // 2. Load Selected Instance Details (Decoupled Background Fetch)
  const loadInstanceDetails = async (instanceId, instancesList = instances) => {
    setDetailsLoading(true)
    const instObj = instancesList.find(i => i.instance_id === instanceId)
    if (instObj) setSelectedInstance(instObj)
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
      // Graceful fallback
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
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '12px 20px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)'
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
            boxShadow: '0 2px 8px rgba(14, 165, 233, 0.3)'
          }}>
            <Activity size={20} color="#fff" />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: '700', color: '#0f172a', letterSpacing: '-0.01em' }}>
              Workflow Monitoring & Observability
            </h2>
            <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
              Live execution tracing, distributed telemetry, process variables & audit logs
            </p>
          </div>
        </div>

        {/* Mode Toggle Buttons */}
        <div style={{ display: 'flex', background: '#f1f5f9', padding: '4px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
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
              background: viewMode === 'instances' ? '#ffffff' : 'transparent',
              color: viewMode === 'instances' ? '#0284c7' : '#64748b',
              boxShadow: viewMode === 'instances' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
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
              background: viewMode === 'telemetry' ? '#ffffff' : 'transparent',
              color: viewMode === 'telemetry' ? '#059669' : '#64748b',
              boxShadow: viewMode === 'telemetry' ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            <Radio size={13} />
            <span>Live Observability Stream</span>
            {metrics.total_logged_events > 0 && (
              <span style={{ fontSize: '10px', background: '#e2e8f0', color: '#334155', padding: '1px 5px', borderRadius: '10px' }}>
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
                    aria-label="Refresh active instances"
                    title="Refresh active instances"
                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  >
                    <RefreshCw size={12} />
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select 
                    id="monitoring-status-filter"
                    name="monitoring_status_filter"
                    aria-label="Filter execution instances by status"
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
                    id="monitoring-entity-filter"
                    name="monitoring_entity_filter"
                    aria-label="Filter execution instances by entity"
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
              <div 
                tabIndex={0} 
                role="region" 
                aria-label="Workflow active instances list" 
                style={{ overflowY: 'auto', flexGrow: 1, paddingRight: '2px' }}
              >
                {instances.slice(0, visibleCount).map(inst => (
                  <div 
                    key={inst.instance_id}
                    className={`instance-card ${selectedInstance?.instance_id === inst.instance_id ? 'active' : ''}`}
                    onClick={() => loadInstanceDetails(inst.instance_id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '700', fontSize: '13px', color: '#0284c7' }}>
                        Instance #{inst.instance_id}
                      </span>
                      <span className={`status-badge ${(inst.status || 'Running').toLowerCase()}`} style={{ padding: '2px 6px', fontSize: '10px' }}>
                        {inst.status || 'Running'}
                      </span>
                    </div>

                    {/* Workflow Name Badge */}
                    <div style={{ marginTop: '6px', fontSize: '12.5px', fontWeight: '700', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: '#6366f1', fontSize: '13px' }}>⚡</span>
                      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {inst.workflow_name || `Workflow #${inst.bpmn_definition_id}`}
                      </span>
                    </div>

                    <div style={{ marginTop: '5px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                      Target: <span style={{ color: 'var(--color-text-primary)', fontWeight: '600' }}>{inst.entity_type || 'Entity'}</span> (ID #{inst.entity_id || '—'})
                    </div>
                    <div className="instance-card-meta" style={{ marginTop: '4px' }}>
                      <span>Current Task: <b>{inst.current_task_code || inst.current_task || '—'}</b></span>
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                      Started: {format12Hr(inst.started_on || inst.started_at)}
                    </div>
                  </div>
                ))}

                {instances.length > visibleCount && (
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ width: '100%', marginTop: '8px', fontSize: '11px', padding: '6px' }}
                    onClick={() => setVisibleCount(prev => prev + 60)}
                  >
                    Load More Instances ({instances.length - visibleCount} remaining)
                  </button>
                )}
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
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '17px', fontWeight: '600' }}>
                          Instance #{selectedInstance.instance_id} Execution Trace
                        </h3>
                        <span style={{ fontSize: '11px', background: '#e0e7ff', color: '#4338ca', padding: '2px 8px', borderRadius: '6px', border: '1px solid #c7d2fe', fontWeight: '600' }}>
                          ⚡ {selectedInstance.workflow_name || `Workflow #${selectedInstance.bpmn_definition_id}`}
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '5px' }}>
                        Entity: <span style={{ color: 'var(--color-text-primary)', fontWeight: '600' }}>{selectedInstance.entity_type}</span> (ID #{selectedInstance.entity_id}) | BPMN Spec: {selectedInstance.workflow_key || selectedInstance.bpmn_definition_id}
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
                <div 
                  className="detail-body" 
                  tabIndex={0} 
                  role="region" 
                  aria-label="Instance execution details" 
                  style={{ overflowY: 'auto' }}
                >
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
                                      <td style={{ fontWeight: '600', color: '#0284c7' }}>{k}</td>
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
                                        <span style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
                                          {log.activity_type}
                                        </span>
                                      </td>
                                      <td>
                                        <span className={`status-badge ${(log.status || 'success').toLowerCase()}`} style={{ fontSize: '10px', padding: '2px 6px' }}>
                                          {log.status}
                                        </span>
                                      </td>
                                      <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                        {format12Hr(log.timestamp)}
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
                                        <span style={{ fontSize: '11px', background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
                                          {h.performed_role}
                                        </span>
                                      </td>
                                      <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                                        {format12Hr(h.performed_on)}
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
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Engine Health</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                <ShieldCheck size={16} color={metrics.status === 'HEALTHY' ? '#16a34a' : '#d97706'} />
                <span style={{ fontSize: '15px', fontWeight: '700', color: metrics.status === 'HEALTHY' ? '#16a34a' : '#d97706' }}>
                  {metrics.status}
                </span>
              </div>
            </div>

            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Total Step Runs</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#0284c7', marginTop: '4px' }}>
                {metrics.total_step_executions}
              </div>
            </div>

            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Avg Step Latency</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#7c3aed', marginTop: '4px' }}>
                {metrics.average_step_latency_ms} ms
              </div>
            </div>

            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Error Rate</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: metrics.error_rate_percentage > 0 ? '#dc2626' : '#16a34a', marginTop: '4px' }}>
                {metrics.error_rate_percentage}% ({metrics.total_errors} errors)
              </div>
            </div>

            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Buffer Size</div>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#0f172a', marginTop: '4px' }}>
                {metrics.total_logged_events} / {metrics.buffer_capacity || 500}
              </div>
            </div>
          </div>

          {/* Telemetry Filter & Controls Toolbar */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '10px',
            padding: '10px 16px',
            gap: '12px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
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
                    border: '1px solid transparent',
                    cursor: 'pointer',
                    background: telemetryLevel === lvl ? 
                      (lvl === 'ERROR' ? '#fee2e2' : lvl === 'AUDIT' ? '#dcfce7' : lvl === 'WARN' ? '#fef3c7' : '#e0f2fe') 
                      : '#f1f5f9',
                    color: telemetryLevel === lvl ? 
                      (lvl === 'ERROR' ? '#dc2626' : lvl === 'AUDIT' ? '#15803d' : lvl === 'WARN' ? '#b45309' : '#0369a1') 
                      : '#64748b'
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>

            {/* Search Bar */}
            <div style={{ position: 'relative', flexGrow: 1, maxWidth: '360px' }}>
              <Search size={13} style={{ position: 'absolute', left: '10px', top: '10px', color: '#64748b' }} />
              <input
                id="monitoring-telemetry-search"
                name="telemetry_search"
                aria-label="Search trace, message, and node events"
                type="text"
                placeholder="Search trace, message, node..."
                value={telemetrySearch}
                onChange={(e) => setTelemetrySearch(e.target.value)}
                style={{
                  width: '100%',
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  padding: '6px 10px 6px 30px',
                  fontSize: '12px',
                  color: '#0f172a',
                  outline: 'none'
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label htmlFor="monitoring-auto-refresh-toggle" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#475569', cursor: 'pointer' }}>
                <input
                  id="monitoring-auto-refresh-toggle"
                  name="auto_refresh"
                  aria-label="Toggle auto-refresh every 3 seconds"
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
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '600',
                  background: '#ffffff',
                  border: '1px solid #cbd5e1',
                  color: '#334155',
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
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '600',
                  background: '#fee2e2',
                  border: '1px solid #fecaca',
                  color: '#dc2626',
                  cursor: 'pointer'
                }}
              >
                <Trash2 size={12} />
                <span>Clear</span>
              </button>
            </div>
          </div>

          {/* Telemetry Stream Console */}
          <div 
            tabIndex={0} 
            role="region" 
            aria-label="Telemetry event stream console" 
            style={{
              flexGrow: 1,
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              overflowY: 'auto',
              padding: '12px',
              fontFamily: 'monospace',
              fontSize: '12px',
              boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.02)'
            }}
          >
            {telemetryLogs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
                <Terminal size={32} style={{ marginBottom: '12px' }} />
                <div>No telemetry logs matching the current filter.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {telemetryLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id
                  const levelStyles = 
                    log.level === 'ERROR' ? { color: '#dc2626', bg: '#fee2e2', border: '#fecaca' } :
                    log.level === 'AUDIT' ? { color: '#15803d', bg: '#dcfce7', border: '#bbf7d0' } :
                    log.level === 'WARN' ? { color: '#b45309', bg: '#fef3c7', border: '#fde68a' } :
                    { color: '#0369a1', bg: '#e0f2fe', border: '#bae6fd' }

                  return (
                    <div
                      key={log.id}
                      style={{
                        background: '#ffffff',
                        border: `1px solid ${isExpanded ? '#6366f1' : '#e2e8f0'}`,
                        borderRadius: '8px',
                        padding: '9px 12px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                      }}
                      onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                          {isExpanded ? <ChevronDown size={12} color="#64748b" /> : <ChevronRight size={12} color="#64748b" />}
                          <span style={{ color: '#64748b', fontSize: '11px', whiteSpace: 'nowrap' }}>{log.timestamp}</span>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            background: levelStyles.bg,
                            color: levelStyles.color,
                            border: `1px solid ${levelStyles.border}`
                          }}>
                            {log.level}
                          </span>
                          <span style={{ color: '#0f172a', fontWeight: '500', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                            {log.message}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', whiteSpace: 'nowrap' }}>
                          {log.duration_ms !== null && log.duration_ms !== undefined && (
                            <span style={{ color: '#7c3aed', fontSize: '11px', background: '#f5f3ff', border: '1px solid #ddd6fe', padding: '1px 6px', borderRadius: '4px' }}>
                              ⚡ {log.duration_ms}ms
                            </span>
                          )}
                          <span style={{ color: '#64748b', fontSize: '10px', background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '1px 5px', borderRadius: '3px' }}>
                            {log.trace_id}
                          </span>
                        </div>
                      </div>

                      {/* Expandable JSON Detail Payload */}
                      {isExpanded && (
                        <div style={{
                          marginTop: '8px',
                          padding: '10px',
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          fontSize: '11px'
                        }}>
                          <div style={{ color: '#0284c7', fontWeight: '600', marginBottom: '4px' }}>Structured Telemetry Payload:</div>
                          <pre style={{ margin: 0, color: '#334155', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
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
