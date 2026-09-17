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
  Zap, 
  Loader, 
  Server, 
  RefreshCw,
  Layers,
  Check
} from 'lucide-react'

import { workflowStorage } from '../services/workflowStorage'

// Supported Database Engines Configuration
const DB_ENGINES = [
  {
    id: 'postgresql',
    name: 'PostgreSQL',
    category: 'Relational SQL',
    badgeColor: '#0284c7',
    badgeBg: '#e0f2fe',
    badgeBorder: '#bae6fd',
    defaultPort: 5432,
    defaultSchema: 'ers',
    defaultUser: 'postgres',
    desc: 'Advanced enterprise relational database'
  },
  {
    id: 'mysql',
    name: 'MySQL / MariaDB',
    category: 'Relational SQL',
    badgeColor: '#d97706',
    badgeBg: '#fef3c7',
    badgeBorder: '#fde68a',
    defaultPort: 3306,
    defaultSchema: '',
    defaultUser: 'root',
    desc: 'High-speed open source SQL database'
  },
  {
    id: 'mssql',
    name: 'MS SQL Server',
    category: 'Enterprise SQL',
    badgeColor: '#4f46e5',
    badgeBg: '#eef2ff',
    badgeBorder: '#c7d2fe',
    defaultPort: 1433,
    defaultSchema: 'dbo',
    defaultUser: 'sa',
    desc: 'Microsoft enterprise relational database'
  },
  {
    id: 'oracle',
    name: 'Oracle Database',
    category: 'Enterprise DB',
    badgeColor: '#dc2626',
    badgeBg: '#fee2e2',
    badgeBorder: '#fecaca',
    defaultPort: 1521,
    defaultSchema: 'SYSTEM',
    defaultUser: 'system',
    desc: 'High-availability enterprise database'
  },
  {
    id: 'sqlite',
    name: 'SQLite (Embedded)',
    category: 'File-based DB',
    badgeColor: '#059669',
    badgeBg: '#d1fae5',
    badgeBorder: '#a7f3d0',
    defaultPort: 0,
    defaultSchema: 'main',
    defaultUser: '',
    desc: 'Zero-configuration standalone database file'
  }
]

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
      const list = await workflowStorage.getDatabaseConnections(true)
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

  // Handle Engine Switch with Smart Defaults
  const handleEngineChange = (engineId) => {
    const engine = DB_ENGINES.find(e => e.id === engineId) || DB_ENGINES[0]
    setFormData(prev => ({
      ...prev,
      db_type: engine.id,
      port: engine.defaultPort,
      default_schema: engine.defaultSchema,
      username: engine.defaultUser || prev.username,
      database_name: engine.id === 'sqlite' ? (prev.database_name || './data/workflow.db') : (prev.database_name || 'MassERS'),
      host: engine.id === 'sqlite' ? '' : (prev.host || 'localhost')
    }))
    setTestResult(null)
  }

  // Open Create Form
  const handleOpenCreate = () => {
    setEditingId(null)
    setFormData({
      connection_name: '',
      db_type: 'postgresql',
      host: 'localhost',
      port: 5432,
      database_name: 'MassERS',
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
      connection_name: conn.connection_name || '',
      db_type: conn.db_type || 'postgresql',
      host: conn.host || 'localhost',
      port: conn.port || 5432,
      database_name: conn.database_name || '',
      default_schema: conn.default_schema || '',
      username: conn.username || '',
      password: '', // leave blank unless modifying
      ssl_mode: conn.ssl_mode || 'disable',
      pool_size: conn.pool_size || 10,
      is_default: Boolean(conn.is_default)
    })
    setTestResult(null)
    setView('form')
  }

  // Test live connection in Form
  const handleTestConnection = async () => {
    if (!formData.database_name.trim()) {
      showToast?.(formData.db_type === 'sqlite' ? 'Please enter a SQLite Database File Path' : 'Please enter a Database Name to test', 'error')
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
        showToast?.('Connection failed: ' + (res.error || res.message), 'error')
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
    if (!formData.connection_name.trim()) {
      showToast?.('Connection friendly name is required', 'error')
      return
    }

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
      showToast?.(err.message || 'Failed to save connection', 'error')
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

  const selectedEngine = DB_ENGINES.find(e => e.id === formData.db_type) || DB_ENGINES[0]
  const isSQLite = formData.db_type === 'sqlite'
  const isMySQL = formData.db_type === 'mysql'
  const isOracle = formData.db_type === 'oracle'
  const isMSSQL = formData.db_type === 'mssql'

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 9999, background: 'rgba(15, 23, 42, 0.5)', backdropFilter: 'blur(8px)' }}>
      <div 
        className="modal-content" 
        onClick={e => e.stopPropagation()} 
        style={{ 
          maxWidth: '780px', 
          width: '94%', 
          maxHeight: '90vh', 
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.2), 0 0 25px rgba(99, 102, 241, 0.08)',
          padding: '0',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* 1. Modal Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#ffffff' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(56, 189, 248, 0.15) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#4f46e5'
            }}>
              <Database size={22} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.02em' }}>
                Client Database Connectors
              </h3>
              <p style={{ margin: '3px 0 0 0', fontSize: '12px', color: '#64748b' }}>
                Configure and switch live database connections across PostgreSQL, MySQL, SQL Server, Oracle, and SQLite
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            aria-label="Close dialog" 
            title="Close dialog"
            style={{
              background: '#f1f5f9',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* 2. Top Navigation & Switcher Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 24px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              type="button"
              onClick={() => setView('list')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '8px',
                fontSize: '12.5px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                background: view === 'list' ? '#6366f1' : '#ffffff',
                color: view === 'list' ? '#ffffff' : '#475569',
                border: view === 'list' ? '1px solid #4f46e5' : '1px solid #cbd5e1',
                boxShadow: view === 'list' ? '0 2px 6px rgba(99, 102, 241, 0.3)' : '0 1px 2px rgba(0,0,0,0.04)'
              }}
            >
              <Server size={14} />
              <span>Saved Profiles ({connections.length})</span>
            </button>

            <button 
              type="button"
              onClick={handleOpenCreate}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '8px',
                fontSize: '12.5px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                background: view === 'form' ? '#6366f1' : '#ffffff',
                color: view === 'form' ? '#ffffff' : '#475569',
                border: view === 'form' ? '1px solid #4f46e5' : '1px solid #cbd5e1',
                boxShadow: view === 'form' ? '0 2px 6px rgba(99, 102, 241, 0.3)' : '0 1px 2px rgba(0,0,0,0.04)'
              }}
            >
              <Plus size={14} />
              <span>Add New Connector</span>
            </button>
          </div>

          <button 
            type="button"
            onClick={loadConnections} 
            disabled={loading}
            title="Refresh database profiles"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: '500',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              color: '#64748b',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={12} className={loading ? 'wf-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        {/* 3. Modal Scrollable Content Body */}
        <div 
          tabIndex={0} 
          role="region" 
          aria-label="Database connection profiles content" 
          style={{ maxHeight: 'calc(90vh - 145px)', overflowY: 'auto', padding: '22px 24px' }}
        >
          {/* ======================================================== */}
          {/* VIEW 1: SAVED CONNECTIONS LIST */}
          {/* ======================================================== */}
          {view === 'list' && (
            <div>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '48px 20px' }}>
                  <Loader size={26} className="wf-spin" style={{ color: '#6366f1', margin: '0 auto 10px' }} />
                  <p style={{ color: '#64748b', fontSize: '13px', margin: 0, fontWeight: '500' }}>
                    Loading database connection profiles...
                  </p>
                </div>
              ) : connections.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '48px 24px', background: '#f8fafc', borderRadius: '12px', border: '1.5px dashed #cbd5e1' }}>
                  <Database size={36} color="#94a3b8" style={{ margin: '0 auto 12px' }} />
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '16px', fontWeight: '700', color: '#0f172a' }}>
                    No Database Connections Configured
                  </h4>
                  <p style={{ color: '#64748b', fontSize: '13px', maxWidth: '420px', margin: '0 auto 18px', lineHeight: '1.5' }}>
                    Connect your PostgreSQL, MySQL, SQL Server, Oracle, or SQLite database to enable real-time workflow database actions.
                  </p>
                  <button 
                    type="button"
                    onClick={handleOpenCreate}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 18px',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: '700',
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      color: '#ffffff',
                      border: 'none',
                      cursor: 'pointer',
                      boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                    }}
                  >
                    <Plus size={15} />
                    <span>Configure First Connection</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {connections.map(conn => {
                    const engine = DB_ENGINES.find(e => e.id === (conn.db_type || '').toLowerCase()) || DB_ENGINES[0]
                    return (
                      <div 
                        key={conn.connection_id}
                        style={{
                          background: conn.is_default ? '#f0f9ff' : '#ffffff',
                          border: conn.is_default ? '1.5px solid #38bdf8' : '1px solid #e2e8f0',
                          borderRadius: '12px',
                          padding: '16px 18px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '16px',
                          boxShadow: conn.is_default ? '0 4px 12px rgba(56, 189, 248, 0.12)' : '0 1px 3px rgba(0,0,0,0.04)',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {/* Profile Info */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', overflow: 'hidden' }}>
                          <div style={{
                            width: '44px',
                            height: '44px',
                            borderRadius: '10px',
                            background: engine.badgeBg,
                            border: `1px solid ${engine.badgeBorder}`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: engine.badgeColor,
                            flexShrink: 0
                          }}>
                            <Database size={22} />
                          </div>

                          <div style={{ overflow: 'hidden' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontWeight: '700', fontSize: '15px', color: '#0f172a' }}>
                                {conn.connection_name}
                              </span>

                              <span style={{
                                background: engine.badgeBg,
                                border: `1px solid ${engine.badgeBorder}`,
                                color: engine.badgeColor,
                                fontSize: '10px',
                                fontWeight: '700',
                                padding: '2px 7px',
                                borderRadius: '4px',
                                textTransform: 'uppercase'
                              }}>
                                {engine.name}
                              </span>

                              {conn.is_default && (
                                <span style={{
                                  background: '#dcfce7',
                                  border: '1px solid #bbf7d0',
                                  color: '#15803d',
                                  fontSize: '10px',
                                  fontWeight: '700',
                                  padding: '2px 7px',
                                  borderRadius: '4px',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '3px'
                                }}>
                                  <CheckCircle2 size={10} />
                                  <span>Active Default</span>
                                </span>
                              )}
                            </div>

                            <div style={{ display: 'flex', gap: '14px', marginTop: '5px', fontSize: '12px', color: '#64748b', flexWrap: 'wrap' }}>
                              {conn.db_type === 'sqlite' ? (
                                <span><strong>File:</strong> <code>{conn.database_name}</code></span>
                              ) : (
                                <>
                                  <span><strong>Host:</strong> {conn.host}:{conn.port}</span>
                                  <span><strong>Database:</strong> <code>{conn.database_name}</code></span>
                                  {conn.default_schema && <span><strong>Schema:</strong> {conn.default_schema}</span>}
                                  {conn.username && <span><strong>User:</strong> {conn.username}</span>}
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                          <button 
                            type="button"
                            onClick={() => handleTestCard(conn)}
                            disabled={testingCardId === conn.connection_id}
                            title="Live Test Connection & Inspect Tables"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 11px',
                              borderRadius: '7px',
                              fontSize: '12px',
                              fontWeight: '600',
                              background: '#ffffff',
                              border: '1px solid #38bdf8',
                              color: '#0284c7',
                              cursor: 'pointer'
                            }}
                          >
                            {testingCardId === conn.connection_id ? (
                              <Loader size={12} className="wf-spin" />
                            ) : (
                              <Zap size={12} />
                            )}
                            <span>Test</span>
                          </button>

                          {!conn.is_default && (
                            <button 
                              type="button"
                              onClick={() => handleSetDefault(conn.connection_id)}
                              title="Set as Default Active Database"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '6px 11px',
                                borderRadius: '7px',
                                fontSize: '12px',
                                fontWeight: '600',
                                background: '#ffffff',
                                border: '1px solid #fde047',
                                color: '#b45309',
                                cursor: 'pointer'
                              }}
                            >
                              <Star size={12} />
                              <span>Set Default</span>
                            </button>
                          )}

                          <button 
                            type="button"
                            onClick={() => handleOpenEdit(conn)}
                            title="Edit Profile"
                            aria-label={`Edit ${conn.connection_name} profile`}
                            style={{
                              background: '#ffffff',
                              border: '1px solid #cbd5e1',
                              borderRadius: '7px',
                              padding: '6px 9px',
                              color: '#475569',
                              cursor: 'pointer'
                            }}
                          >
                            <Edit3 size={13} />
                          </button>

                          {!conn.is_default && (
                            <button 
                              type="button"
                              onClick={() => handleDelete(conn.connection_id, conn.is_default)}
                              title="Delete Profile"
                              aria-label={`Delete ${conn.connection_name} profile`}
                              style={{
                                background: '#ffffff',
                                border: '1px solid #fecaca',
                                borderRadius: '7px',
                                padding: '6px 9px',
                                color: '#dc2626',
                                cursor: 'pointer'
                              }}
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* VIEW 2: DYNAMIC ADD / EDIT FORM BASED ON DATABASE ENGINE */}
          {/* ======================================================== */}
          {view === 'form' && (
            <form onSubmit={handleSaveConnection}>
              
              {/* SECTION 1: DATABASE ENGINE SELECTOR CARDS */}
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
                  1. Select Database Engine
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
                  {DB_ENGINES.map(engine => {
                    const isSelected = formData.db_type === engine.id
                    return (
                      <div
                        key={engine.id}
                        onClick={() => handleEngineChange(engine.id)}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '10px',
                          border: isSelected ? '2px solid #6366f1' : '1px solid #e2e8f0',
                          background: isSelected ? '#eef2ff' : '#ffffff',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          boxShadow: isSelected ? '0 2px 8px rgba(99, 102, 241, 0.18)' : '0 1px 2px rgba(0,0,0,0.03)'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            padding: '1px 5px',
                            borderRadius: '4px',
                            background: engine.badgeBg,
                            color: engine.badgeColor
                          }}>
                            {engine.category}
                          </span>
                          {isSelected && <Check size={13} color="#4f46e5" strokeWidth={3} />}
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: '700', color: isSelected ? '#4338ca' : '#0f172a' }}>
                          {engine.name}
                        </div>
                        <div style={{ fontSize: '10.5px', color: '#64748b', marginTop: '2px', lineHeight: '1.2' }}>
                          {engine.id === 'sqlite' ? 'File DB' : `Port ${engine.defaultPort}`}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* SECTION 2: CONNECTION IDENTITY & DETAILS */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '14px' }}>
                  <Layers size={15} color="#4f46e5" />
                  <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    2. Connector Identity & Profile
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  {/* Connection Friendly Name */}
                  <div style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                      Connection Friendly Name <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder={`e.g. Production ${selectedEngine.name} ERS`} 
                      required 
                      value={formData.connection_name}
                      onChange={e => setFormData({ ...formData, connection_name: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 3: DYNAMIC NETWORK & DATABASE SETTINGS */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '14px' }}>
                  <Database size={15} color="#0284c7" />
                  <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    3. {selectedEngine.name} Specific Parameters
                  </span>
                </div>

                {/* --- A. SQLITE DYNAMIC FIELDS --- */}
                {isSQLite ? (
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                      SQLite Database File Path <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" 
                        className="form-control" 
                        placeholder="./data/workflow.db or D:/databases/ers.db" 
                        required 
                        value={formData.database_name}
                        onChange={e => setFormData({ ...formData, database_name: e.target.value })}
                        style={{ fontFamily: 'monospace' }}
                      />
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
                      💡 Relative paths resolve from backend root. Absolute paths (e.g. <code>C:/data/app.db</code>) are supported.
                    </div>
                  </div>
                ) : (
                  /* --- B. NETWORK DATABASE DYNAMIC FIELDS (Postgres, MySQL, MSSQL, Oracle) --- */
                  <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 0.6fr', gap: '14px' }}>
                    {/* Host / Server */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        {isOracle ? 'Host / Oracle Server' : (isMSSQL ? 'Host / SQL Server Instance' : 'Host / IP Address')} <span style={{ color: '#ef4444' }}>*</span>
                      </label>
                      <input 
                        type="text" 
                        className="form-control" 
                        placeholder="localhost, 127.0.0.1, or 192.168.1.50" 
                        required 
                        value={formData.host}
                        onChange={e => setFormData({ ...formData, host: e.target.value })}
                      />
                    </div>

                    {/* Port */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        Port <span style={{ color: '#ef4444' }}>*</span>
                      </label>
                      <input 
                        type="number" 
                        className="form-control" 
                        required 
                        value={formData.port}
                        onChange={e => setFormData({ ...formData, port: e.target.value })}
                      />
                    </div>

                    {/* Database Name / Service Name */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        {isOracle ? 'Service Name / SID' : 'Database Name'} <span style={{ color: '#ef4444' }}>*</span>
                      </label>
                      <input 
                        type="text" 
                        className="form-control" 
                        placeholder={isOracle ? 'e.g. ORCL or XEPDB1' : (isMySQL ? 'e.g. app_database' : 'e.g. MassERS')} 
                        required 
                        value={formData.database_name}
                        onChange={e => setFormData({ ...formData, database_name: e.target.value })}
                      />
                    </div>

                    {/* Default Schema (Shown for Postgres, MSSQL, Oracle) */}
                    {!isMySQL && (
                      <div>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                          Default Schema
                        </label>
                        <input 
                          type="text" 
                          className="form-control" 
                          placeholder={isMSSQL ? 'dbo' : (isOracle ? 'SYSTEM' : 'ers or public')} 
                          value={formData.default_schema}
                          onChange={e => setFormData({ ...formData, default_schema: e.target.value })}
                        />
                      </div>
                    )}

                    {/* Username */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        Username <span style={{ color: '#ef4444' }}>*</span>
                      </label>
                      <input 
                        type="text" 
                        className="form-control" 
                        placeholder={selectedEngine.defaultUser || 'username'} 
                        required
                        value={formData.username}
                        onChange={e => setFormData({ ...formData, username: e.target.value })}
                      />
                    </div>

                    {/* Password */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        Password {editingId && '(Leave blank to retain)'}
                      </label>
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
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        SSL Security Mode
                      </label>
                      <select 
                        className="form-control"
                        value={formData.ssl_mode}
                        onChange={e => setFormData({ ...formData, ssl_mode: e.target.value })}
                      >
                        <option value="disable">Disable (Standard Local / VPC)</option>
                        <option value="require">Require (Encrypted SSL)</option>
                        <option value="verify-ca">Verify CA Certificate</option>
                        <option value="prefer">Prefer SSL if available</option>
                      </select>
                    </div>

                    {/* Pool Size */}
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                        Max Connection Pool
                      </label>
                      <input 
                        type="number" 
                        className="form-control" 
                        value={formData.pool_size}
                        min="1"
                        max="50"
                        onChange={e => setFormData({ ...formData, pool_size: e.target.value })}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* LIVE TEST CONNECTION RESULT BANNER */}
              {testResult && (
                <div style={{
                  marginBottom: '16px',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  background: testResult.success ? '#f0fdf4' : '#fef2f2',
                  border: testResult.success ? '1.5px solid #86efac' : '1.5px solid #fca5a5',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.03)'
                }}>
                  {testResult.success ? (
                    <CheckCircle2 size={20} color="#16a34a" />
                  ) : (
                    <AlertTriangle size={20} color="#dc2626" />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: testResult.success ? '#15803d' : '#b91c1c' }}>
                      {testResult.message || (testResult.success ? 'Database connection established successfully!' : 'Connection failed')}
                    </div>
                    {testResult.version && (
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        Engine Version: <strong>{testResult.version}</strong> {testResult.latency_ms && `(Latency: ${testResult.latency_ms}ms)`}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* FOOTER ACTIONS */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
                <button 
                  type="button" 
                  onClick={handleTestConnection}
                  disabled={testing}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '12.5px',
                    fontWeight: '700',
                    background: '#f0f9ff',
                    border: '1.5px solid #38bdf8',
                    color: '#0284c7',
                    cursor: testing ? 'not-allowed' : 'pointer'
                  }}
                >
                  {testing ? <Loader size={14} className="wf-spin" /> : <Zap size={14} />}
                  <span>Test Connection</span>
                </button>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button 
                    type="button" 
                    onClick={() => setView('list')}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '8px',
                      fontSize: '12.5px',
                      fontWeight: '600',
                      background: '#ffffff',
                      border: '1px solid #cbd5e1',
                      color: '#475569',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                  
                  <button 
                    type="submit" 
                    disabled={submitting}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '7px',
                      padding: '8px 22px',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: '700',
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      border: 'none',
                      color: '#ffffff',
                      cursor: submitting ? 'not-allowed' : 'pointer',
                      boxShadow: '0 4px 12px rgba(99, 102, 241, 0.35)'
                    }}
                  >
                    {submitting ? <Loader size={14} className="wf-spin" /> : <CheckCircle2 size={15} />}
                    <span>{editingId ? 'Update Connection' : 'Save Connection Profile'}</span>
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
