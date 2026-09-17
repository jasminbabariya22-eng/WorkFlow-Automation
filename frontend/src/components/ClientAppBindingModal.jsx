import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  Link2,
  Database,
  Table,
  Key,
  CheckCircle2,
  AlertCircle,
  Loader,
  Trash2,
  Layers,
  ArrowRight,
  Code2,
  HelpCircle,
  ChevronDown,
  Search,
  Check,
  Hash,
  Activity,
  Sliders
} from 'lucide-react'
import { workflowStorage } from '../services/workflowStorage'

// =========================================================================
// ULTRA-PREMIUM GENERIC SEARCHABLE DROPDOWN
// =========================================================================
function GenericSearchableSelect({
  label,
  sublabel,
  required,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option...',
  searchPlaceholder = 'Filter options...',
  icon: Icon = Table,
  loading = false,
  badgeText = null,
  emptyMessage = 'No matching items found'
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const dropdownRef = useRef(null)
  const searchInputRef = useRef(null)

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      setTimeout(() => {
        if (searchInputRef.current) searchInputRef.current.focus()
      }, 50)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Normalize options: supports array of strings OR array of { value, label, badge, hint }
  const normalizedOptions = options.map((opt) => {
    if (typeof opt === 'string') {
      return { value: opt, label: opt, badge: null, hint: null }
    }
    return {
      value: String(opt.value),
      label: opt.label || String(opt.value),
      badge: opt.badge || null,
      hint: opt.hint || null
    }
  })

  const filtered = normalizedOptions.filter((opt) =>
    opt.label.toLowerCase().includes(query.toLowerCase()) ||
    (opt.hint && opt.hint.toLowerCase().includes(query.toLowerCase()))
  )

  const selectedOpt = normalizedOptions.find((opt) => opt.value === String(value))

  return (
    <div style={{ position: 'relative', width: '100%' }} ref={dropdownRef}>
      {label && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span>{label}</span>
            {required && <span style={{ color: '#f43f5e' }}>*</span>}
          </label>
          {sublabel && (
            <span style={{ fontSize: '10.5px', color: '#4f46e5', fontWeight: '500' }}>{sublabel}</span>
          )}
        </div>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={loading}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: isOpen ? '#ffffff' : '#ffffff',
          border: isOpen ? '1.5px solid #6366f1' : '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '10px 14px',
          color: selectedOpt ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
          fontSize: '13px',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.18s ease',
          boxShadow: isOpen ? '0 0 0 3px rgba(99, 102, 241, 0.15), 0 4px 12px rgba(0,0,0,0.06)' : '0 1px 2px rgba(0,0,0,0.04)',
          outline: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
          <div style={{
            background: 'rgba(99, 102, 241, 0.1)',
            color: '#4f46e5',
            borderRadius: '6px',
            padding: '5px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <Icon size={14} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', textAlign: 'left' }}>
            {loading ? (
              <span style={{ color: '#64748b', fontStyle: 'italic', fontSize: '12px' }}>Loading...</span>
            ) : selectedOpt ? (
              <>
                <span style={{ fontWeight: '600', color: 'var(--color-text-primary)', fontFamily: selectedOpt.value.includes('_') ? 'monospace' : 'inherit', fontSize: '12.5px' }}>
                  {selectedOpt.label}
                </span>
                {selectedOpt.badge && (
                  <span style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(99, 102, 241, 0.12)',
                    color: '#4338ca',
                    fontWeight: '700',
                    border: '1px solid rgba(99, 102, 241, 0.25)'
                  }}>
                    {selectedOpt.badge}
                  </span>
                )}
              </>
            ) : (
              <span style={{ color: '#94a3b8' }}>{placeholder}</span>
            )}
          </div>
        </div>

        <ChevronDown
          size={16}
          color="#64748b"
          style={{
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
            flexShrink: 0
          }}
        />
      </button>

      {/* Dropdown Popup Menu */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            zIndex: 1000,
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            boxShadow: '0 15px 35px -5px rgba(0, 0, 0, 0.12), 0 0 20px rgba(99, 102, 241, 0.08)',
            overflow: 'hidden',
            animation: 'fadeIn 0.15s ease'
          }}
        >
          {/* Filter Search Input */}
          <div style={{ padding: '8px 10px', borderBottom: '1px solid #f1f5f9', background: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Search size={14} color="#6366f1" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                color: '#0f172a',
                fontSize: '12px',
                outline: 'none',
                padding: '4px 0'
              }}
            />
            {query && (
              <button
                type="button"
                aria-label="Clear filter query"
                title="Clear filter query"
                onClick={() => setQuery('')}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Options List */}
          <div 
            tabIndex={0} 
            role="region" 
            aria-label="Searchable options list" 
            style={{ maxHeight: '210px', overflowY: 'auto', padding: '6px' }}
          >
            {filtered.length === 0 ? (
              <div style={{ padding: '20px 10px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                {emptyMessage}
              </div>
            ) : (
              filtered.map((opt) => {
                const isSelected = opt.value === String(value)
                return (
                  <div
                    key={opt.value}
                    onClick={() => {
                      onChange(opt.value)
                      setIsOpen(false)
                      setQuery('')
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: isSelected ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                      color: isSelected ? '#4338ca' : '#1e293b',
                      transition: 'background 0.12s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.background = '#f1f5f9'
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                      <span style={{
                        fontSize: '12.5px',
                        fontWeight: isSelected ? '700' : '500',
                        fontFamily: opt.value.includes('_') ? 'monospace' : 'inherit',
                        color: isSelected ? '#4338ca' : '#1e293b'
                      }}>
                        {opt.label}
                      </span>
                      {opt.badge && (
                        <span style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#4338ca',
                          fontWeight: '700'
                        }}>
                          {opt.badge}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {opt.hint && (
                        <span style={{ fontSize: '10.5px', color: '#64748b' }}>{opt.hint}</span>
                      )}
                      {isSelected && <Check size={14} color="#4338ca" />}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =========================================================================
// MAIN BINDING MODAL COMPONENT (100% GENERIC FOR ANY PROCESS & ANY TABLE)
// =========================================================================
export default function ClientAppBindingModal({
  isOpen,
  onClose,
  workflow,
  dbConnections = [],
  onBindingUpdated,
  showToast
}) {
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [tables, setTables] = useState([])
  const [loadingTables, setLoadingTables] = useState(false)
  const [tableColumns, setTableColumns] = useState([])
  const [loadingColumns, setLoadingColumns] = useState(false)
  const [existingBinding, setExistingBinding] = useState(null)
  const [showMultiTableInfo, setShowMultiTableInfo] = useState(false)

  const [connectionsList, setConnectionsList] = useState(dbConnections || [])

  // Form State
  const [moduleKey, setModuleKey] = useState('')
  const [title, setTitle] = useState('')
  const [connectionId, setConnectionId] = useState(1)
  const [tableName, setTableName] = useState('')
  const [primaryKey, setPrimaryKey] = useState('id')
  const [statusColumn, setStatusColumn] = useState('status')
  const [defaultStatus, setDefaultStatus] = useState('PENDING')

  // 1. Initialize modal when opened
  useEffect(() => {
    if (!isOpen || !workflow) return

    const init = async () => {
      setLoading(true)
      try {
        // Fetch all available connections if not passed via props
        let conns = dbConnections && dbConnections.length > 0 ? dbConnections : []
        if (conns.length === 0) {
          conns = await workflowStorage.getDbConnections()
          setConnectionsList(conns)
        } else {
          setConnectionsList(conns)
        }

        const bindings = await workflowStorage.getWorkflowBindings()
        const currentWfId = Number(workflow.id || workflow.workflow_id)

        let matched = null
        for (const [key, b] of Object.entries(bindings || {})) {
          if (Number(b.workflow_id) === currentWfId) {
            matched = { ...b, module_key: key }
            break
          }
        }

        // Determine default connection from database profiles (is_default === true)
        const defaultProfile = conns.find(c => c.is_default) || conns[0]
        const fallbackConnId = defaultProfile ? Number(defaultProfile.connection_id) : 1

        // Priority order:
        // 1. Existing Active Binding
        // 2. Workflow's explicitly configured connection_id (e.g. 1 or 4)
        // 3. The system Default Database Connection profile
        const rawWfConn = (workflow.connection_id !== undefined && workflow.connection_id !== null && workflow.connection_id !== 0)
          ? Number(workflow.connection_id)
          : null

        const selectedConnId = matched?.connection_id != null 
          ? Number(matched.connection_id) 
          : (rawWfConn || fallbackConnId)

        setConnectionId(Number(selectedConnId))

        if (matched) {
          setExistingBinding(matched)
          setModuleKey(matched.module_key || '')
          setTitle(matched.title || workflow.name || '')
          setTableName(matched.table_name || '')
          setPrimaryKey(matched.primary_key || 'id')
          setStatusColumn(matched.status_column || 'status')
          setDefaultStatus(matched.default_status || 'PENDING')
        } else {
          setExistingBinding(null)
          // Derive a 100% generic snake_case module key from spec_id or workflow name
          const cleanKey = (workflow.spec_id || workflow.name || 'custom_module')
            .toLowerCase()
            .replace(/_flow$|_wf$|_workflow$/g, '')
            .replace(/[^a-z0-9_]/g, '_')
            .replace(/^_+|_+$/g, '')
          setModuleKey(cleanKey)
          setTitle(workflow.name || cleanKey)
          setTableName('')
          setPrimaryKey('id')
          setStatusColumn('status')
          setDefaultStatus('PENDING')
        }

        await loadTables(selectedConnId, matched?.table_name)
      } catch (err) {
        if (showToast) showToast('Error loading binding catalog: ' + err.message, 'error')
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [isOpen, workflow])

  // 2. Load tables for selected connection (100% Generic Introspection with Smart Auto-Detection)
  const loadTables = async (connId, explicitTable = null) => {
    setLoadingTables(true)
    try {
      const tblList = await workflowStorage.getMetadataTables(connId)
      const names = (tblList || []).map(t => typeof t === 'string' ? t : (t.table_name || t.name))
      setTables(names)

      // Intelligent Auto-Selection: match workflow context to database tables
      let autoSelected = explicitTable || (names.includes(tableName) ? tableName : null)

      if (!autoSelected && workflow) {
        const wfKey = String(workflow.spec_id || workflow.workflow_key || workflow.name || '').toLowerCase()
        const entityType = String(workflow.entity_type || '').toLowerCase()

        // 1. Direct match with entity_type if specified
        if (entityType && names.includes(entityType)) {
          autoSelected = entityType
        } else {
          // 2. Match significant keyword from workflow name/key (e.g. 'leave' -> 'leave_requests')
          const ignoreWords = new Set(['flow', 'wf', 'workflow', 'tracking', 'deduction', 'draft', 'test', 'demo', 'process', 'custom', 'module'])
          const keywords = wfKey.split(/[^a-z0-9]+/).filter(w => w.length > 2 && !ignoreWords.has(w))
          
          for (const tbl of names) {
            const lowerTbl = tbl.toLowerCase()
            const baseTbl = lowerTbl.replace(/s$/, '')
            if (keywords.some(k => lowerTbl.includes(k) || k.includes(baseTbl))) {
              autoSelected = tbl
              break
            }
          }
        }
      }

      const target = autoSelected || names[0] || ''
      if (target) {
        setTableName(target)
        await loadColumns(target, connId)
      }
    } catch (_e) {
      setTables([])
    } finally {
      setLoadingTables(false)
    }
  }

  // 3. Load columns for selected table (Auto-detects Primary Key & Status)
  const loadColumns = async (tbl, connId) => {
    if (!tbl) return
    setLoadingColumns(true)
    try {
      const colInfo = await workflowStorage.getMetadataTableColumns(tbl, connId)
      const cols = colInfo.columns || []
      const colNames = cols.map(c => c.name)
      setTableColumns(colNames)

      // Auto-detect PK from database schema
      if (colInfo.primary_keys && colInfo.primary_keys.length > 0) {
        setPrimaryKey(colInfo.primary_keys[0])
      } else {
        const pkCandidate = colNames.find(c => c === `${tbl.replace(/s$/, '')}_id` || c.endsWith('_id') || c === 'id')
        if (pkCandidate) setPrimaryKey(pkCandidate)
      }

      // Auto-detect Status Column
      const statusCandidate = colNames.find(c => c.includes('status') || c === 'state')
      if (statusCandidate) {
        setStatusColumn(statusCandidate)
      }
    } catch (_e) {
      setTableColumns([])
    } finally {
      setLoadingColumns(false)
    }
  }

  const handleConnectionChange = async (newConnId) => {
    const idNum = Number(newConnId)
    setConnectionId(idNum)
    await loadTables(idNum)
  }

  const handleTableChange = async (newTable) => {
    setTableName(newTable)
    await loadColumns(newTable, connectionId)
  }

  // 4. Save / Upsert Binding
  const handleSave = async (e) => {
    e.preventDefault()
    if (!moduleKey.trim()) {
      showToast('ClientApp Module Key is required.', 'error')
      return
    }
    if (!tableName.trim()) {
      showToast('Target Primary Table is required.', 'error')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        module_key: moduleKey.trim().toLowerCase(),
        title: title.trim() || workflow.name,
        workflow_id: Number(workflow.id || workflow.workflow_id),
        connection_id: Number(connectionId) || 4,
        table_name: tableName.trim(),
        primary_key: primaryKey.trim() || 'id',
        status_column: statusColumn.trim() || 'status',
        default_status: defaultStatus.trim() || 'PENDING'
      }

      await workflowStorage.saveWorkflowBinding(payload)

      if (showToast) {
        showToast(`✓ Workflow #${workflow.id || workflow.workflow_id} bound to ClientApp as '${moduleKey}'`, 'success')
      }

      if (onBindingUpdated) onBindingUpdated()
      onClose()
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to save binding', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // 5. Delete / Disconnect Binding
  const handleDelete = async () => {
    if (!existingBinding || !existingBinding.module_key) return
    if (!window.confirm(`Are you sure you want to disconnect '${existingBinding.module_key}' from ClientApp?`)) {
      return
    }

    setSubmitting(true)
    try {
      await workflowStorage.deleteWorkflowBinding(existingBinding.module_key)
      if (showToast) showToast(`✓ Binding '${existingBinding.module_key}' disconnected`, 'success')
      if (onBindingUpdated) onBindingUpdated()
      onClose()
    } catch (err) {
      if (showToast) showToast(err.message || 'Failed to remove binding', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOpen) return null

  // Dropdown options formatted for GenericSearchableSelect
  const activeConns = connectionsList && connectionsList.length > 0 ? connectionsList : dbConnections
  const connectionOptions = activeConns.map((c) => ({
    value: String(c.connection_id),
    label: c.connection_name,
    badge: c.is_default ? 'DEFAULT' : `ID #${c.connection_id}`,
    hint: c.database_name ? `${c.database_name} (${c.db_type || 'PostgreSQL'})` : (c.db_type || 'PostgreSQL')
  }))

  const tableOptions = tables.map((t) => ({
    value: t,
    label: t,
    badge: 'Table',
    hint: null
  }))

  const columnOptions = tableColumns.map((c) => ({
    value: c,
    label: c,
    badge: c === primaryKey ? 'PK' : c.includes('status') ? 'Status' : null,
    hint: null
  }))

  return (
    <div className="modal-overlay" style={{ zIndex: 9999, background: 'rgba(15, 23, 42, 0.45)', backdropFilter: 'blur(8px)' }}>
      <div 
        className="modal-container" 
        style={{ 
          maxWidth: '680px', 
          width: '94%', 
          background: '#ffffff', 
          border: '1px solid #e2e8f0',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
          padding: '24px',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15))', 
              border: '1px solid rgba(99, 102, 241, 0.3)', 
              padding: '10px', 
              borderRadius: '12px', 
              color: '#4f46e5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Link2 size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '17px', fontWeight: '800', color: '#0f172a', margin: 0, letterSpacing: '-0.02em' }}>
                  Bind Workflow to ClientApp
                </h3>
                {existingBinding ? (
                  <span style={{ fontSize: '11px', fontWeight: '700', color: '#15803d', background: '#dcfce7', border: '1px solid #bbf7d0', padding: '2px 8px', borderRadius: '999px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={11} />
                    <span>Active Bridge</span>
                  </span>
                ) : (
                  <span style={{ fontSize: '11px', color: '#64748b', background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '2px 8px', borderRadius: '999px' }}>
                    Generic Multi-Process Bridge
                  </span>
                )}
              </div>
              <p style={{ fontSize: '12px', color: '#64748b', margin: '2px 0 0 0' }}>
                Connect any workflow process to any client database entity with 0 custom API code
              </p>
            </div>
          </div>
          <button 
            className="btn-icon" 
            onClick={onClose} 
            disabled={submitting}
            aria-label="Close dialog"
            title="Close dialog"
            style={{ color: '#64748b', background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '6px' }}
          >
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center' }}>
            <Loader className="spinner" size={32} color="#6366f1" style={{ margin: '0 auto 12px' }} />
            <span style={{ fontSize: '13px', color: '#64748b', fontWeight: '500' }}>Inspecting database catalog & active bindings...</span>
          </div>
        ) : (
          <form 
            onSubmit={handleSave} 
            tabIndex={0} 
            role="region" 
            aria-label="Workflow client application binding configuration" 
            style={{ marginTop: '16px', maxHeight: '78vh', overflowY: 'auto', paddingRight: '4px' }}
          >
            
            {/* 1. VISUAL INTERACTIVE FLOW ARCHITECTURE */}
            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              padding: '12px 16px',
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px'
            }}>
              {/* Step 1: ClientApp */}
              <div style={{ flex: 1, textAlign: 'center', padding: '8px', background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#0284c7', fontWeight: '800', display: 'block', marginBottom: '2px' }}>
                  1. ClientApp Module
                </span>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#0f172a', fontFamily: 'monospace' }}>
                  '{moduleKey || 'module_key'}'
                </span>
              </div>

              <ArrowRight size={16} color="#6366f1" style={{ flexShrink: 0 }} />

              {/* Step 2: Workflow Engine */}
              <div style={{ flex: 1.2, textAlign: 'center', padding: '8px', background: '#eef2ff', borderRadius: '8px', border: '1px solid #c7d2fe' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#4f46e5', fontWeight: '800', display: 'block', marginBottom: '2px' }}>
                  2. Workflow Engine
                </span>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#312e81' }} title={workflow?.name}>
                  ID #{workflow?.id || workflow?.workflow_id}
                </span>
              </div>

              <ArrowRight size={16} color="#6366f1" style={{ flexShrink: 0 }} />

              {/* Step 3: Client Database */}
              <div style={{ flex: 1, textAlign: 'center', padding: '8px', background: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#16a34a', fontWeight: '800', display: 'block', marginBottom: '2px' }}>
                  3. ClientDB Entity
                </span>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#0f172a', fontFamily: 'monospace' }}>
                  {tableName || 'select table'}
                </span>
              </div>
            </div>

            {/* FORM BODY CARDS */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

              {/* CARD 1: BRIDGE IDENTITY */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <Layers size={15} color="#4f46e5" />
                  <span style={{ fontSize: '13px', fontWeight: '700', color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                    1. ClientApp Bridge Identity
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                      <span>ClientApp Module Key <span style={{ color: '#f43f5e' }}>*</span></span>
                      <span style={{ fontSize: '10.5px', color: '#4f46e5', fontWeight: '500' }}>Generic Keyword</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      value={moduleKey}
                      onChange={(e) => setModuleKey(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                      placeholder="e.g. orders, tickets, leave_requests"
                      required
                      style={{ fontFamily: 'monospace', fontSize: '13px', background: '#ffffff', borderColor: '#cbd5e1' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                      Display Title
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Purchase Order Approval Process"
                      style={{ fontSize: '13px', background: '#ffffff', borderColor: '#cbd5e1' }}
                    />
                  </div>
                </div>
              </div>

              {/* CARD 2: DATABASE & ROOT TRIGGER TABLE */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Database size={15} color="#0284c7" />
                    <span style={{ fontSize: '13px', fontWeight: '700', color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      2. Database & Primary Trigger Table
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowMultiTableInfo(!showMultiTableInfo)}
                    style={{ background: 'transparent', border: 'none', color: '#0284c7', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', padding: 0 }}
                  >
                    <HelpCircle size={12} />
                    <span>Multiple Tables Support?</span>
                  </button>
                </div>

                {/* Multi-table explanation accordion */}
                {showMultiTableInfo && (
                  <div style={{ 
                    background: '#e0f2fe', 
                    border: '1px solid #bae6fd', 
                    borderRadius: '8px', 
                    padding: '10px 12px', 
                    marginBottom: '14px',
                    fontSize: '11.5px',
                    color: '#0369a1',
                    lineHeight: '1.5'
                  }}>
                    <strong>💡 Generic Multi-Table Architecture:</strong>
                    <br />
                    The table selected below is the <strong>Root Entry Table</strong> (e.g. <code>orders</code>, <code>invoices</code>, <code>leave_requests</code>, <code>support_tickets</code>).
                    Inside the workflow canvas, your nodes can insert, read, and update <strong>unlimited secondary tables</strong> (e.g. line items, audit logs, balances, notifications) atomically!
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  {/* Custom Searchable Database Dropdown */}
                  <GenericSearchableSelect
                    label="Client Database Connection"
                    value={String(connectionId)}
                    onChange={handleConnectionChange}
                    options={connectionOptions}
                    placeholder="Select connection..."
                    searchPlaceholder="Search database connections..."
                    icon={Database}
                  />

                  {/* Custom Searchable Table Dropdown */}
                  <GenericSearchableSelect
                    label="Primary Trigger Table"
                    required
                    value={tableName}
                    onChange={handleTableChange}
                    options={tableOptions}
                    placeholder="Select table..."
                    searchPlaceholder="Search tables (orders, tickets...)"
                    icon={Table}
                    loading={loadingTables}
                  />
                </div>
              </div>

              {/* CARD 3: SCHEMA & COLUMN MAPPINGS */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                  <Key size={15} color="#d97706" />
                  <span style={{ fontSize: '13px', fontWeight: '700', color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                    3. Auto-Detected Column Mappings
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 1fr', gap: '12px' }}>
                  {/* Primary Key Dropdown */}
                  <GenericSearchableSelect
                    label="Primary Key"
                    value={primaryKey}
                    onChange={setPrimaryKey}
                    options={columnOptions.length > 0 ? columnOptions : [{ value: primaryKey, label: primaryKey }]}
                    placeholder="Select PK..."
                    searchPlaceholder="Search PK column..."
                    icon={Key}
                    loading={loadingColumns}
                  />

                  {/* Status Column Dropdown */}
                  <GenericSearchableSelect
                    label="Status Column"
                    value={statusColumn}
                    onChange={setStatusColumn}
                    options={columnOptions.length > 0 ? columnOptions : [{ value: statusColumn, label: statusColumn }]}
                    placeholder="Select status col..."
                    searchPlaceholder="Search status col..."
                    icon={CheckCircle2}
                    loading={loadingColumns}
                  />

                  {/* Initial Default Status */}
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#334155', marginBottom: '6px' }}>
                      Initial State
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      value={defaultStatus}
                      onChange={(e) => setDefaultStatus(e.target.value)}
                      placeholder="PENDING"
                      style={{ fontFamily: 'monospace', fontSize: '12.5px', background: '#ffffff', borderColor: '#cbd5e1', padding: '10px 12px' }}
                    />
                  </div>
                </div>
              </div>

              {/* CARD 4: LIVE CODE SNIPPET */}
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Code2 size={13} color="#4f46e5" />
                    <span>How ClientApp triggers this generic process:</span>
                  </span>
                  <span style={{ fontSize: '10.5px', color: '#16a34a', fontWeight: '700' }}>100% Generic API</span>
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '11.5px', color: '#0f172a', background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '6px', overflowX: 'auto' }}>
                  <span style={{ color: '#9333ea', fontWeight: '600' }}>await</span> genericWorkflowApi.<span style={{ color: '#2563eb', fontWeight: '600' }}>submit</span>(<span style={{ color: '#059669' }}>'{moduleKey || 'module_key'}'</span>, formData, currentUser)
                </div>
              </div>

            </div>

            {/* FOOTER ACTIONS */}
            <div 
              style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                marginTop: '20px', 
                paddingTop: '16px', 
                borderTop: '1px solid #e2e8f0' 
              }}
            >
              {existingBinding ? (
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={handleDelete}
                  disabled={submitting}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '8px 14px' }}
                >
                  <Trash2 size={13} />
                  <span>Disconnect</span>
                </button>
              ) : (
                <div />
              )}

              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={onClose}
                  disabled={submitting}
                  style={{ fontSize: '13px', padding: '8px 16px' }}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={submitting}
                  style={{ 
                    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', 
                    borderColor: '#4f46e5', 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px',
                    fontSize: '13px',
                    fontWeight: '700',
                    padding: '8px 22px',
                    boxShadow: '0 4px 14px rgba(99, 102, 241, 0.25)'
                  }}
                >
                  {submitting ? <Loader className="spinner" size={15} /> : <Link2 size={15} />}
                  <span>{existingBinding ? 'Update Binding' : 'Save & Bind to ClientApp'}</span>
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
