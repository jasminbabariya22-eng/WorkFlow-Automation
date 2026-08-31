import React, { useState, useEffect } from 'react'
import { 
  X, 
  Database, 
  Plus, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  Edit3, 
  Star, 
  Activity, 
  Zap, 
  Loader, 
  Server, 
  Lock, 
  RefreshCw,
  Layers,
  ArrowRight
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

export default function DatabaseConnectionsModal({ onClose, showToast }) {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('list') // 'list' | 'form'
  
  // Form State
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    connection_name: '',
    db_type: 'postgresql',
    host: 'localhost',
    port: 5432,
    database_name: '',
    default_schema: 'ers',
    username: 'postgres',
    password: '',
    ssl_mode: 'disable',
    pool_size: 10,
    is_default: false
  })

  // Testing status
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testingCardId, setTestingCardId] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Fetch connections
  const loadConnections = async () => {
    setLoading(true)
    try {
      const list = await workflowStorage.getDatabaseConnections()
      setConnections(list)
    } catch (err) {
      showToast?.('Failed to load database connections: ' + err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConnections()
  }, [])

  // Open Create Form
  const handleOpenCreate = () => {
    setEditingId(null)
    setFormData({
      connection_name: '',
      db_type: 'postgresql',
      host: 'localhost',
      port: 5432,
      database_name: '',
      default_schema: 'ers',
      username: 'postgres',
      password: '',
      ssl_mode: 'disable',
      pool_size: 10,
      is_default: connections.length === 0
    })
    setTestResult(null)
    setView('form')
  }

  // Open Edit Form
  const handleOpenEdit = (conn) => {
    setEditingId(conn.connection_id)
    setFormData({
      connection_name: conn.connection_name,
      db_type: conn.db_type || 'postgresql',
      host: conn.host || 'localhost',
      port: conn.port || 5432,
      database_name: conn.database_name || '',
      default_schema: conn.default_schema || 'ers',
      username: conn.username || 'postgres',
      password: '', // leave empty unless changing
      ssl_mode: conn.ssl_mode || 'disable',
      pool_size: conn.pool_size || 10,
      is_default: conn.is_default
    })
    setTestResult(null)
    setView('form')
  }

  // Test live connection in Form
  const handleTestConnection = async () => {
    if (!formData.database_name.trim()) {
      showToast?.('Please enter a Database Name to test', 'error')
      return
    }

    setTesting(true)
    setTestResult(null)
    try {
      const res = await workflowStorage.testDatabaseConnection({
        db_type: formData.db_type,
        host: formData.host,
        port: Number(formData.port),
        database_name: formData.database_name,
        default_schema: formData.default_schema,
        username: formData.username,
        password: formData.password,
        ssl_mode: formData.ssl_mode
      })
      setTestResult(res)
      if (res.success) {
        showToast?.(`Connection successful! (${res.latency_ms}ms)`, 'success')
      } else {
        showToast?.('Connection failed: ' + res.error, 'error')
      }
    } catch (err) {
      setTestResult({ success: false, error: err.message, message: err.message })
      showToast?.('Connection failed: ' + err.message, 'error')
    } finally {
      setTesting(false)
    }
  }

  // Quick Test from List Card
  const handleTestCard = async (conn) => {
    setTestingCardId(conn.connection_id)
    try {
      const res = await workflowStorage.getConnectionTables(conn.connection_id, conn.default_schema)
      showToast?.(`✅ Connected to '${conn.connection_name}' (${res.tables?.length || 0} tables discovered)`, 'success')
    } catch (err) {
      showToast?.(`❌ Failed connecting to '${conn.connection_name}': ${err.message}`, 'error')
    } finally {
      setTestingCardId(null)
    }
  }

  // Save / Submit Form
  const handleSaveConnection = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const payload = {
        ...formData,
        port: Number(formData.port),
        pool_size: Number(formData.pool_size)
      }

      if (editingId) {
        await workflowStorage.updateDatabaseConnection(editingId, payload)
        showToast?.('Database connection updated successfully!', 'success')
      } else {
        await workflowStorage.createDatabaseConnection(payload)
        showToast?.('New database connection created!', 'success')
      }

      await loadConnections()
      setView('list')
    } catch (err) {
      showToast?.(err.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Set as Default Connection
  const handleSetDefault = async (connId) => {
    try {
      await workflowStorage.setDefaultDatabaseConnection(connId)
      showToast?.('Default Client Database updated successfully!', 'success')
      await loadConnections()
    } catch (err) {
      showToast?.(err.message, 'error')
    }
  }

  // Delete Connection
  const handleDelete = async (connId, isDefault) => {
    if (isDefault) {
      showToast?.('Cannot delete the default active connection.', 'error')
      return
    }
    if (!window.confirm('Are you sure you want to delete this database connection?')) return

    try {
      await workflowStorage.deleteDatabaseConnection(connId)
      showToast?.('Database connection deleted.', 'success')
      await loadConnections()
    } catch (err) {
      showToast?.(err.message, 'error')
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content execution-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '780px', width: '92%' }}>
        {/* Header */}
        <div className="modal-header" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="runner-icon-badge" style={{ background: 'rgba(56, 189, 248, 0.15)', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
              <Database size={20} color="#38bdf8" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '700' }}>
                Client Database Connectors
              </h3>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                Configure and switch Client Database connections directly from the UI
              </span>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* View Switcher Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', background: 'rgba(15, 23, 42, 0.4)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className={`btn btn-sm ${view === 'list' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setView('list')}
            >
              <Server size={13} />
              <span>Saved Connections ({connections.length})</span>
            </button>
            <button 
              className={`btn btn-sm ${view === 'form' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={handleOpenCreate}
            >
              <Plus size={13} />
              <span>Add New Connection</span>
            </button>
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            onClick={loadConnections} 
            disabled={loading}
            title="Refresh list"
          >
            <RefreshCw size={12} className={loading ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ maxHeight: '68vh', overflowY: 'auto', padding: '20px' }}>
          {/* ======================================================== */}
          {/* 1. LIST VIEW */}
          {/* ======================================================== */}
          {view === 'list' && (
            <div>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <Loader size={24} className="spinner" />
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', marginTop: '8px' }}>Loading database connection profiles...</p>
                </div>
              ) : connections.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', border: '1px dashed rgba(255,255,255,0.1)' }}>
                  <Database size={32} color="#64748b" style={{ margin: '0 auto 12px' }} />
                  <h4 style={{ margin: '0 0 6px 0', color: '#f8fafc' }}>No Database Connections Configured</h4>
                  <p style={{ color: '#94a3b8', fontSize: '13px', maxWidth: '400px', margin: '0 auto 16px' }}>
                    Connect your PostgreSQL, MySQL, or SQL Server database to enable dynamic workflow operations.
                  </p>
                  <button className="btn btn-primary btn-sm" onClick={handleOpenCreate}>
                    <Plus size={14} />
                    <span>Add First Connection</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {connections.map(conn => (
                    <div 
                      key={conn.connection_id}
                      style={{
                        background: conn.is_default ? 'rgba(56, 189, 248, 0.05)' : 'rgba(30, 41, 59, 0.4)',
                        border: conn.is_default ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '10px',
                        padding: '16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '16px'
                      }}
                    >
                      {/* Info */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{
                          width: '42px',
                          height: '42px',
                          borderRadius: '8px',
                          background: conn.is_default ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          border: '1px solid rgba(255, 255, 255, 0.08)'
                        }}>
                          <Database size={20} color={conn.is_default ? '#38bdf8' : '#94a3b8'} />
                        </div>

                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: '700', fontSize: '15px', color: '#f8fafc' }}>
                              {conn.connection_name}
                            </span>
                            {conn.is_default && (
                              <span style={{
                                background: 'rgba(56, 189, 248, 0.2)',
                                border: '1px solid rgba(56, 189, 248, 0.4)',
                                color: '#38bdf8',
                                fontSize: '10px',
                                fontWeight: '700',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                textTransform: 'uppercase'
                              }}>
                                ★ Active Default
                              </span>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '14px', marginTop: '4px', fontSize: '12px', color: '#94a3b8' }}>
                            <span><strong>Type:</strong> {conn.db_type?.toUpperCase()}</span>
                            <span><strong>Host:</strong> {conn.host}:{conn.port}</span>
                            <span><strong>Database:</strong> {conn.database_name}</span>
                            <span><strong>Schema:</strong> {conn.default_schema}</span>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button 
                          className="btn btn-secondary btn-sm"
                          style={{ borderColor: 'rgba(56, 189, 248, 0.3)', color: '#38bdf8' }}
                          onClick={() => handleTestCard(conn)}
                          disabled={testingCardId === conn.connection_id}
                          title="Live Test Connection & Inspect Tables"
                        >
                          {testingCardId === conn.connection_id ? (
                            <Loader size={12} className="spinner" />
                          ) : (
                            <Zap size={12} />
                          )}
                          <span>Test</span>
                        </button>

                        {!conn.is_default && (
                          <button 
                            className="btn btn-secondary btn-sm"
                            style={{ borderColor: 'rgba(250, 204, 21, 0.3)', color: '#facc15' }}
                            onClick={() => handleSetDefault(conn.connection_id)}
                            title="Set as Default Active Database"
                          >
                            <Star size={12} />
                            <span>Set Default</span>
                          </button>
                        )}

                        <button 
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleOpenEdit(conn)}
                          title="Edit Profile"
                        >
                          <Edit3 size={12} />
                        </button>

                        {!conn.is_default && (
                          <button 
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDelete(conn.connection_id, conn.is_default)}
                            title="Delete Profile"
                          >
                            <Trash2 size={12} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* 2. ADD / EDIT FORM VIEW */}
          {/* ======================================================== */}
          {view === 'form' && (
            <form onSubmit={handleSaveConnection}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                {/* Connection Name */}
                <div style={{ gridColumn: 'span 2' }}>
                  <label className="form-label">Connection Friendly Name</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. Production PostgreSQL ERS" 
                    required 
                    value={formData.connection_name}
                    onChange={e => setFormData({ ...formData, connection_name: e.target.value })}
                  />
                </div>

                {/* DB Type */}
                <div>
                  <label className="form-label">Database Engine</label>
                  <select 
                    className="form-control"
                    value={formData.db_type}
                    onChange={e => {
                      const t = e.target.value
                      setFormData({ 
                        ...formData, 
                        db_type: t, 
                        port: t === 'mysql' ? 3306 : (t === 'mssql' ? 1433 : 5432) 
                      })
                    }}
                  >
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL / MariaDB</option>
                    <option value="mssql">Microsoft SQL Server</option>
                    <option value="sqlite">SQLite</option>
                  </select>
                </div>

                {/* Host */}
                <div>
                  <label className="form-label">Host / IP Address</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="localhost or 192.168.1.100" 
                    required 
                    value={formData.host}
                    onChange={e => setFormData({ ...formData, host: e.target.value })}
                  />
                </div>

                {/* Port */}
                <div>
                  <label className="form-label">Port</label>
                  <input 
                    type="number" 
                    className="form-control" 
                    required 
                    value={formData.port}
                    onChange={e => setFormData({ ...formData, port: e.target.value })}
                  />
                </div>

                {/* Database Name */}
                <div>
                  <label className="form-label">Database Name</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. MassERS" 
                    required 
                    value={formData.database_name}
                    onChange={e => setFormData({ ...formData, database_name: e.target.value })}
                  />
                </div>

                {/* Default Schema */}
                <div>
                  <label className="form-label">Default Schema</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. ers or public" 
                    value={formData.default_schema}
                    onChange={e => setFormData({ ...formData, default_schema: e.target.value })}
                  />
                </div>

                {/* Username */}
                <div>
                  <label className="form-label">Username</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. postgres or root" 
                    value={formData.username}
                    onChange={e => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>

                {/* Password */}
                <div>
                  <label className="form-label">Password {editingId && '(Leave blank to keep current)'}</label>
                  <input 
                    type="password" 
                    className="form-control" 
                    placeholder="••••••••" 
                    value={formData.password}
                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>

                {/* SSL Mode */}
                <div>
                  <label className="form-label">SSL Mode</label>
                  <select 
                    className="form-control"
                    value={formData.ssl_mode}
                    onChange={e => setFormData({ ...formData, ssl_mode: e.target.value })}
                  >
                    <option value="disable">Disable</option>
                    <option value="require">Require</option>
                    <option value="verify-ca">Verify-CA</option>
                  </select>
                </div>
              </div>

              {/* Test Result Box */}
              {testResult && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: testResult.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                  border: testResult.success ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  {testResult.success ? (
                    <CheckCircle2 size={18} color="#10b981" />
                  ) : (
                    <AlertTriangle size={18} color="#ef4444" />
                  )}
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: testResult.success ? '#10b981' : '#ef4444' }}>
                      {testResult.message}
                    </div>
                    {testResult.version && (
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                        Server: {testResult.version}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Form Buttons */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={handleTestConnection}
                  disabled={testing}
                  style={{ borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
                >
                  {testing ? <Loader size={14} className="spinner" /> : <Zap size={14} />}
                  <span>Test Connection</span>
                </button>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button 
                    type="button" 
                    className="btn btn-secondary" 
                    onClick={() => setView('list')}
                  >
                    Cancel
                  </button>
                  
                  <button 
                    type="submit" 
                    className="btn btn-primary"
                    disabled={submitting}
                  >
                    {submitting ? <Loader size={14} className="spinner" /> : <CheckCircle2 size={14} />}
                    <span>{editingId ? 'Update Connection' : 'Save Connection'}</span>
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
