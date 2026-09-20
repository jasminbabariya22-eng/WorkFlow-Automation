import React, { useState, useEffect } from 'react'
import { 
  Plus, 
  Search, 
  Filter, 
  FileCode, 
  Trash2, 
  Copy, 
  Download, 
  Upload, 
  Check, 
  Zap,
  Globe,
  Loader,
  X,
  Database,
  Link2
} from 'lucide-react'
import ExecutionModal from './ExecutionModal'
import DatabaseConnectionsModal from './DatabaseConnectionsModal'
import ClientAppBindingModal from './ClientAppBindingModal'
import { workflowStorage } from '../services/workflowStorage'

function Dashboard({ onOpenDesigner, showToast }) {
  // Feature flag: Set to true if you want to re-enable the Test Run button on the Dashboard
  const ENABLE_DASHBOARD_TEST_RUN = false

  // Instant initial load from cache for 0ms render
  const [workflows, setWorkflows] = useState(() => {
    try {
      const stored = localStorage.getItem('workflow_studio_definitions')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.filter(w => !w.is_deleted && w.is_deleted !== 1)
        }
      }
    } catch {}
    return []
  })
  const [loading, setLoading] = useState(() => {
    try {
      const stored = localStorage.getItem('workflow_studio_definitions')
      return !stored
    } catch {
      return true
    }
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortConfig, setSortConfig] = useState({ key: null, direction: null })
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10
  
  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [showDbModal, setShowDbModal] = useState(false)
  const [deleteModalWorkflow, setDeleteModalWorkflow] = useState(null)
  const [executingWorkflow, setExecutingWorkflow] = useState(null)
  const [bindingModalWorkflow, setBindingModalWorkflow] = useState(null)
  const [dbConnections, setDbConnections] = useState([])
  const [activeBindings, setActiveBindings] = useState({})
  const [copiedId, setCopiedId] = useState(null)

  // Form payloads
  const [newDraft, setNewDraft] = useState({ spec_id: '', name: '', description: '', tags: '', connection_id: '' })
  const [importDraft, setImportDraft] = useState({ spec_id: '', name: '', description: '', tags: '', connection_id: '', file: null })
  const [submitting, setSubmitting] = useState(false)

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
    }, 200)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Reset page when search or status filter changes
  useEffect(() => {
    setCurrentPage(1)
  }, [debouncedSearch, statusFilter])

  // Real-time Specification ID sanitizer helper
  const sanitizeSpecId = (val) => String(val || '').toLowerCase().replace(/[^a-z0-9_]/g, '_')

  // Copy Spec ID helper with visual feedback
  const handleCopySpecId = (specId, e) => {
    e.stopPropagation()
    if (!specId) return
    navigator.clipboard.writeText(specId)
    setCopiedId(specId)
    showToast(`Copied '${specId}' to clipboard`, 'success')
    setTimeout(() => setCopiedId(null), 1500)
  }

  // Fetch all workflow definitions & database connections without blocking UI
  const fetchWorkflows = async (showLoadingSpinner = false) => {
    if (showLoadingSpinner) setLoading(true)
    try {
      const [wfList, conns] = await Promise.all([
        workflowStorage.getWorkflows(),
        workflowStorage.getDatabaseConnections(true)
      ])
      if (Array.isArray(wfList)) {
        setWorkflows(wfList)
      }
      if (Array.isArray(conns)) {
        setDbConnections(conns)
      }
    } catch (error) {
      // Non-blocking fallback
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkflows(workflows.length === 0)
  }, [])

  // Create Draft Definition
  const handleCreateDraft = async (e) => {
    e.preventDefault()
    const cleanSpec = sanitizeSpecId(newDraft.spec_id)
    if (!cleanSpec || !String(newDraft.name || '').trim()) {
      showToast('Specification ID and Name are required.', 'error')
      return
    }

    // Frontend validation: Check if Specification ID already exists
    const duplicate = workflows.some(w => sanitizeSpecId(w.spec_id) === cleanSpec)
    if (duplicate) {
      showToast(`Specification ID '${cleanSpec}' already exists. Please enter a unique key.`, 'error')
      return
    }

    setSubmitting(true)
    try {
      const created = await workflowStorage.createWorkflow({ ...newDraft, spec_id: cleanSpec })
      showToast('Draft created successfully', 'success')
      setShowCreateModal(false)
      setNewDraft({ spec_id: '', name: '', description: '', tags: '', connection_id: '' })
      await fetchWorkflows()
      if (created && created.id) {
        onOpenDesigner(created.id)
      }
    } catch (error) {
      showToast(error.message || 'Failed to create draft', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Import BPMN File
  const handleImportBPMN = (e) => {
    e.preventDefault()
    if (!importDraft.spec_id || !importDraft.name || !importDraft.file) {
      showToast('All fields and a BPMN file selection are required.', 'error')
      return
    }
    setSubmitting(true)
    const reader = new FileReader()
    reader.onload = async (event) => {
      try {
        const xmlContent = event.target.result
        const imported = await workflowStorage.importWorkflow(
          importDraft.spec_id,
          importDraft.name,
          importDraft.description,
          importDraft.tags,
          xmlContent
        )
        showToast('BPMN specification imported successfully', 'success')
        setShowImportModal(false)
        setImportDraft({ spec_id: '', name: '', description: '', tags: '', file: null })
        await fetchWorkflows()
        if (imported && imported.id) {
          onOpenDesigner(imported.id)
        }
      } catch (err) {
        showToast('BPMN import failed', 'error')
      } finally {
        setSubmitting(false)
      }
    }
    reader.onerror = () => {
      showToast('Failed to read file', 'error')
      setSubmitting(false)
    }
    reader.readAsText(importDraft.file)
  }

  // Publish Draft
  const handlePublish = async (id, e) => {
    if (e && e.stopPropagation) e.stopPropagation()
    setWorkflows(prev => prev.map(w => (Number(w.id) === Number(id) || Number(w.workflow_id) === Number(id) ? { ...w, status: 'Active', is_active: true } : w)))
    try {
      await workflowStorage.publishWorkflow(id)
      showToast('Workflow published successfully', 'success')
      fetchWorkflows()
    } catch (err) {
      showToast(err.message || 'Failed to publish workflow', 'error')
      fetchWorkflows()
    }
  }

  // Activate Version
  const handleActivate = async (id, e) => {
    if (e && e.stopPropagation) e.stopPropagation()
    // Instant optimistic state update (0ms immediate feedback)
    setWorkflows(prev => prev.map(w => (Number(w.id) === Number(id) || Number(w.workflow_id) === Number(id) ? { ...w, status: 'Active', is_active: true } : w)))
    try {
      await workflowStorage.activateWorkflow(id)
      showToast('Workflow version activated', 'success')
      fetchWorkflows()
    } catch (err) {
      showToast(err.message || 'Failed to activate workflow', 'error')
      fetchWorkflows()
    }
  }

  // Deactivate Version
  const handleDeactivate = async (id, e) => {
    if (e && e.stopPropagation) e.stopPropagation()
    // Instant optimistic state update (0ms immediate feedback)
    setWorkflows(prev => prev.map(w => (Number(w.id) === Number(id) || Number(w.workflow_id) === Number(id) ? { ...w, status: 'Inactive', is_active: false } : w)))
    try {
      await workflowStorage.deactivateWorkflow(id)
      showToast('Workflow version deactivated successfully', 'success')
      fetchWorkflows()
    } catch (err) {
      showToast(err.message || 'Failed to deactivate workflow', 'error')
      fetchWorkflows()
    }
  }


  // Clone/Duplicate Draft
  const handleDuplicate = async (id, e) => {
    e.stopPropagation()
    await workflowStorage.duplicateWorkflow(id)
    showToast('Cloned draft specification successfully', 'success')
    await fetchWorkflows()
  }

  // Delete Version
  const handleDelete = (wf, e) => {
    e.stopPropagation()
    const isActive = typeof wf === 'object' && wf !== null ? Boolean(wf.is_active || wf.status === 'Active' || wf.status === 'ACTIVE') : false

    if (isActive) {
      showToast('Active workflows cannot be deleted. Please deactivate it first.', 'error')
      return
    }

    setDeleteModalWorkflow(wf)
  }

  const confirmDeleteWorkflow = async () => {
    if (!deleteModalWorkflow) return
    const wfId = typeof deleteModalWorkflow === 'object' ? (deleteModalWorkflow.id || deleteModalWorkflow.workflow_id) : deleteModalWorkflow
    try {
      await workflowStorage.deleteWorkflow(wfId)
      showToast('Workflow deleted successfully', 'success')
      setDeleteModalWorkflow(null)
      await fetchWorkflows()
    } catch (err) {
      showToast(err.message || 'Failed to delete workflow', 'error')
    }
  }

  // Export BPMN File
  const handleExport = async (id, specId, version, e) => {
    e.stopPropagation()
    const wf = await workflowStorage.getWorkflowById(id)
    const xmlContent = wf?.xml_content || `<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions id="Definitions_${id}" targetNamespace="http://bpmn.io/schema/bpmn"></bpmn:definitions>`
    const blob = new Blob([xmlContent], { type: 'application/xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${specId}_v${version}.bpmn`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showToast(`Downloaded BPMN diagram for ${specId} v${version}`, 'success')
  }

  // Filters and queries calculations
  const filteredWorkflows = workflows.filter(wf => {
    const q = (debouncedSearch || '').toLowerCase().trim()
    const matchesSearch = !q ||
      (wf.spec_id && wf.spec_id.toLowerCase().includes(q)) ||
      (wf.name && wf.name.toLowerCase().includes(q)) ||
      (wf.description && wf.description.toLowerCase().includes(q))
      
    const matchesStatus = statusFilter === '' || wf.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  const handleSort = (key) => {
    setSortConfig(prev => {
      if (prev.key === key) {
        if (prev.direction === 'asc') return { key, direction: 'desc' }
        if (prev.direction === 'desc') return { key: null, direction: null }
      }
      return { key, direction: 'asc' }
    })
  }

  const sortedWorkflows = [...filteredWorkflows].sort((a, b) => {
    if (!sortConfig.key || !sortConfig.direction) return 0
    let aVal = a[sortConfig.key]
    let bVal = b[sortConfig.key]

    if (sortConfig.key === 'database') {
      const connA = dbConnections.find(c => c.connection_id === a.connection_id)
      const connB = dbConnections.find(c => c.connection_id === b.connection_id)
      aVal = connA ? connA.connection_name : (a.connection_id ? `DB #${a.connection_id}` : 'Default DB')
      bVal = connB ? connB.connection_name : (b.connection_id ? `DB #${b.connection_id}` : 'Default DB')
    } else if (sortConfig.key === 'updated_at') {
      aVal = a.updated_at || a.updated_on || a.created_on || a.created_at || ''
      bVal = b.updated_at || b.updated_on || b.created_on || b.created_at || ''
    } else if (sortConfig.key === 'tags') {
      aVal = Array.isArray(a.tags) ? a.tags.join(',') : (a.tags || '')
      bVal = Array.isArray(b.tags) ? b.tags.join(',') : (b.tags || '')
    }

    if (aVal == null) aVal = ''
    if (bVal == null) bVal = ''

    if (typeof aVal === 'string') {
      const cmp = aVal.localeCompare(String(bVal), undefined, { numeric: true, sensitivity: 'base' })
      return sortConfig.direction === 'asc' ? cmp : -cmp
    } else {
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    }
  })

  // Pagination calculation (10 per page)
  const totalPages = Math.max(1, Math.ceil(sortedWorkflows.length / pageSize))
  const safeCurrentPage = Math.min(currentPage, totalPages)
  const paginatedWorkflows = sortedWorkflows.slice((safeCurrentPage - 1) * pageSize, safeCurrentPage * pageSize)

  const SortIcon = ({ columnKey }) => {
    const isActive = sortConfig.key === columnKey
    const dir = isActive ? sortConfig.direction : null
    return (
      <svg 
        width="8" 
        height="12" 
        viewBox="0 0 8 12" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        style={{ marginLeft: '6px', display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
      >
        <path 
          d="M4 1L7.5 5H0.5L4 1Z" 
          fill={dir === 'asc' ? 'var(--color-accent-primary, #0284c7)' : '#94a3b8'} 
          opacity={dir === 'asc' ? 1 : 0.45}
        />
        <path 
          d="M4 11L0.5 7H7.5L4 11Z" 
          fill={dir === 'desc' ? 'var(--color-accent-primary, #0284c7)' : '#94a3b8'} 
          opacity={dir === 'desc' ? 1 : 0.45}
        />
      </svg>
    )
  }

  return (
    <div className="dashboard-view">
      <div className="dashboard-header-actions">
        <div className="search-filter-box">
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            <input 
              type="text" 
              id="dashboard-search-specs"
              name="dashboard_search_query"
              aria-label="Search workflow specifications"
              placeholder="Search specifications..." 
              className="search-input"
              style={{ paddingLeft: '36px' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={16} color="var(--color-text-muted)" />
            <select 
              id="dashboard-status-filter"
              name="dashboard_status_filter"
              aria-label="Filter workflow specifications by status"
              className="filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="Draft">Draft</option>
              <option value="Active">Active</option>
              <option value="Published">Published</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div className="dashboard-action-buttons" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => setShowDbModal(true)} title="Manage Client Database Connectors">
            <Database size={16} />
            <span>Client Databases ({dbConnections.length})</span>
          </button>
          <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
            <Upload size={16} />
            <span>Import BPMN</span>
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            <span>Create Workflow</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <span>Loading workflow specifications...</span>
        </div>
      ) : sortedWorkflows.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📂</div>
          <p>No workflow definitions match your current filter.</p>
        </div>
      ) : (
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('spec_id')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Specification ID</span>
                    <SortIcon columnKey="spec_id" />
                  </div>
                </th>
                <th onClick={() => handleSort('name')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Process Name</span>
                    <SortIcon columnKey="name" />
                  </div>
                </th>
                <th onClick={() => handleSort('database')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Database</span>
                    <SortIcon columnKey="database" />
                  </div>
                </th>
                <th onClick={() => handleSort('version')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Version</span>
                    <SortIcon columnKey="version" />
                  </div>
                </th>
                <th onClick={() => handleSort('status')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Status</span>
                    <SortIcon columnKey="status" />
                  </div>
                </th>
                <th onClick={() => handleSort('tags')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Tags</span>
                    <SortIcon columnKey="tags" />
                  </div>
                </th>
                <th onClick={() => handleSort('updated_at')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <span>Last Updated</span>
                    <SortIcon columnKey="updated_at" />
                  </div>
                </th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedWorkflows.map(wf => (
                <tr key={wf.id} onClick={() => onOpenDesigner(wf.id)}>
                  <td>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: 'var(--color-accent-secondary)', fontWeight: '500' }}>{wf.spec_id}</span>
                      <button
                        type="button"
                        className="btn-icon-subtle"
                        title="Copy Specification ID"
                        onClick={(e) => handleCopySpecId(wf.spec_id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          padding: '3px 4px',
                          cursor: 'pointer',
                          color: copiedId === wf.spec_id ? '#16a34a' : '#94a3b8',
                          display: 'inline-flex',
                          alignItems: 'center',
                          borderRadius: '4px',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {copiedId === wf.spec_id ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </div>
                  </td>
                  <td>{wf.name}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {(() => {
                      const isEditable = !wf.is_active || wf.status === 'Draft' || wf.status === 'Inactive' || wf.status === 'Published'
                      const connId = wf.connection_id ? Number(wf.connection_id) : null
                      const conn = dbConnections.find(c => Number(c.connection_id) === connId)
                      const activeLabel = conn ? conn.connection_name : (connId ? `DB #${connId}` : 'Default DB')

                      if (isEditable) {
                        return (
                          <div 
                            title={`Client Database: ${activeLabel} (Click to change)`}
                            style={{ 
                              display: 'inline-flex', 
                              alignItems: 'center', 
                              gap: '4px', 
                              maxWidth: '165px',
                              background: connId ? 'rgba(56, 189, 248, 0.08)' : 'rgba(255,255,255,0.04)', 
                              border: connId ? '1px solid rgba(56, 189, 248, 0.28)' : '1px solid rgba(255,255,255,0.1)', 
                              borderRadius: '6px', 
                              padding: '2px 6px',
                              boxSizing: 'border-box'
                            }}
                          >
                            <Database size={11} color={connId ? '#38bdf8' : '#94a3b8'} style={{ flexShrink: 0 }} />
                            <select
                              aria-label={`Select Client Database for ${wf.spec_id}`}
                              value={connId || ''}
                              onChange={async (e) => {
                                const newId = e.target.value ? Number(e.target.value) : null
                                try {
                                  await workflowStorage.saveWorkflow(wf.id, { connection_id: newId })
                                  showToast(`Database updated to ${newId ? (dbConnections.find(c => Number(c.connection_id) === newId)?.connection_name || `DB #${newId}`) : 'Default DB'} for '${wf.spec_id}'`, 'success')
                                  await fetchWorkflows()
                                } catch (err) {
                                  showToast('Failed to update DB: ' + err.message, 'error')
                                }
                              }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: connId ? '#38bdf8' : '#94a3b8',
                                fontSize: '11px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                outline: 'none',
                                maxWidth: '135px',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                paddingRight: '2px'
                              }}
                            >
                              <option value="" style={{ background: '#0f172a', color: '#e2e8f0' }}>★ Default DB</option>
                              {dbConnections.map(c => (
                                <option key={c.connection_id} value={c.connection_id} style={{ background: '#0f172a', color: '#e2e8f0' }}>
                                  {c.connection_name}
                                </option>
                              ))}
                              {connId && !dbConnections.some(c => Number(c.connection_id) === connId) && (
                                <option key={connId} value={connId} style={{ background: '#0f172a', color: '#e2e8f0' }}>
                                  DB #{connId}
                                </option>
                              )}
                            </select>
                          </div>
                        )
                      }

                      if (!connId) {
                        return (
                          <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.08)', display: 'inline-flex', alignItems: 'center', gap: '4px', maxWidth: '165px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            ★ Default DB
                          </span>
                        )
                      }
                      return (
                        <span style={{ fontSize: '11px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.08)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.25)', display: 'inline-flex', alignItems: 'center', gap: '4px', maxWidth: '165px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <Database size={10} style={{ flexShrink: 0 }} />
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {conn ? conn.connection_name : `DB #${connId}`}
                          </span>
                        </span>
                      )
                    })()}
                  </td>
                  <td>v{wf.version}</td>
                  <td>
                    <span className={`status-badge ${wf.status.toLowerCase()}`}>
                      {wf.status}
                    </span>
                  </td>
                  <td>{(() => {
                    const tagsList = Array.isArray(wf.tags) ? wf.tags : (typeof wf.tags === 'string' ? wf.tags.split(',').map(t => t.trim()).filter(Boolean) : [])
                    return tagsList.length > 0 ? tagsList.map((tag, idx) => (
                      <span key={idx} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-glass)', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', marginRight: '4px' }}>
                        {tag}
                      </span>
                    )) : <span style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>—</span>
                  })()}</td>
                  <td style={{ color: 'var(--color-text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                    {(() => {
                      const rawDate = wf.updated_at || wf.updated_on || wf.created_on || wf.created_at
                      if (!rawDate) return '—'
                      const d = new Date(rawDate)
                      if (isNaN(d.getTime())) return String(rawDate)
                      return d.toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                      })
                    })()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyItems: 'flex-end', justifyContent: 'flex-end', gap: '8px' }}>

                      {ENABLE_DASHBOARD_TEST_RUN && (
                        <button 
                          className="btn btn-secondary btn-sm" 
                          style={{ borderColor: 'rgba(0, 229, 255, 0.4)', color: 'var(--color-accent-secondary)' }} 
                          title="Execute / Test Run Workflow" 
                          onClick={(e) => {
                            e.stopPropagation()
                            setExecutingWorkflow(wf)
                          }}
                        >
                          <Zap size={12} />
                          <span>Test Run</span>
                        </button>
                      )}
                      {wf.status === 'Draft' && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(0, 229, 255, 0.3)', color: 'var(--color-accent-secondary)' }} onClick={(e) => handlePublish(wf.id, e)}>
                          <Globe size={12} />
                          <span>Publish</span>
                        </button>
                      )}
                      {!wf.is_active && wf.status !== 'Draft' && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(0, 230, 118, 0.3)', color: 'var(--color-success)' }} onClick={(e) => handleActivate(wf.id, e)}>
                          <Zap size={12} />
                          <span>Activate</span>
                        </button>
                      )}
                      {wf.is_active && (
                        <button className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(255, 171, 0, 0.3)', color: 'var(--color-warning)' }} onClick={(e) => handleDeactivate(wf.id, e)}>
                          <Zap size={12} style={{ opacity: 0.6 }} />
                          <span>Deactivate</span>
                        </button>
                      )}
                      <button className="btn btn-secondary btn-sm" title="Duplicate Specification" onClick={(e) => handleDuplicate(wf.id, e)}>
                        <Copy size={12} />
                      </button>
                      <button className="btn btn-secondary btn-sm" title="Download BPMN File" onClick={(e) => handleExport(wf.id, wf.spec_id, wf.version, e)}>
                        <Download size={12} />
                      </button>
                      <button className="btn btn-danger btn-sm" title="Delete Version" onClick={(e) => handleDelete(wf, e)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer Bar */}
      {!loading && sortedWorkflows.length > 0 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '16px',
          padding: '12px 18px',
          background: 'var(--bg-glass)',
          border: '1px solid var(--border-glass)',
          borderRadius: '12px',
          fontSize: '13px',
          color: 'var(--color-text-muted)'
        }}>
          <div>
            Showing <strong style={{ color: 'var(--color-text-main)' }}>{((safeCurrentPage - 1) * pageSize) + 1}</strong> to <strong style={{ color: 'var(--color-text-main)' }}>{Math.min(safeCurrentPage * pageSize, sortedWorkflows.length)}</strong> of <strong style={{ color: 'var(--color-text-main)' }}>{sortedWorkflows.length}</strong> workflows
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              className="btn btn-secondary btn-sm"
              disabled={safeCurrentPage <= 1}
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              style={{ opacity: safeCurrentPage <= 1 ? 0.4 : 1, cursor: safeCurrentPage <= 1 ? 'not-allowed' : 'pointer' }}
            >
              Previous
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === totalPages || Math.abs(p - safeCurrentPage) <= 1)
              .reduce((acc, p, idx, arr) => {
                if (idx > 0 && p - arr[idx - 1] > 1) {
                  acc.push('ellipsis-' + p)
                }
                acc.push(p)
                return acc
              }, [])
              .map((item, idx) => {
                if (typeof item === 'string') {
                  return <span key={idx} style={{ padding: '0 4px', color: 'var(--color-text-muted)' }}>...</span>
                }
                const isActive = item === safeCurrentPage
                return (
                  <button
                    key={item}
                    onClick={() => setCurrentPage(item)}
                    style={{
                      minWidth: '32px',
                      height: '32px',
                      borderRadius: '6px',
                      border: isActive ? '1px solid #132B6E' : '1px solid var(--border-glass)',
                      background: isActive ? '#132B6E' : 'transparent',
                      color: isActive ? '#ffffff' : 'var(--color-text-main)',
                      fontWeight: isActive ? '700' : '500',
                      fontSize: '12.5px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {item}
                  </button>
                )
              })}

            <button
              className="btn btn-secondary btn-sm"
              disabled={safeCurrentPage >= totalPages}
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              style={{ opacity: safeCurrentPage >= totalPages ? 0.4 : 1, cursor: safeCurrentPage >= totalPages ? 'not-allowed' : 'pointer' }}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Modal: Create Workflow Draft */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <span className="modal-title">Create Workflow Specification</span>
              <X size={18} style={{ cursor: 'pointer', color: 'var(--color-text-muted)' }} onClick={() => setShowCreateModal(false)} />
            </div>
            <form onSubmit={handleCreateDraft}>
              <div className="form-group">
                <label className="form-label" htmlFor="create-spec-id">Specification ID (unique key)</label>
                <input 
                  type="text" 
                  id="create-spec-id"
                  name="spec_id"
                  aria-label="Specification ID (unique key)"
                  className="form-control" 
                  placeholder="e.g. RiskApprovalWorkflow"
                  required
                  value={newDraft.spec_id}
                  onChange={(e) => setNewDraft({ ...newDraft, spec_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="create-spec-name">Friendly Process Name</label>
                <input 
                  type="text" 
                  id="create-spec-name"
                  name="spec_name"
                  aria-label="Friendly Process Name"
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={newDraft.name}
                  onChange={(e) => setNewDraft({ ...newDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="create-spec-desc">Description</label>
                <input 
                  type="text" 
                  id="create-spec-desc"
                  name="spec_description"
                  aria-label="Workflow Description"
                  className="form-control" 
                  placeholder="Short explanation of workflow triggers and tasks"
                  value={newDraft.description}
                  onChange={(e) => setNewDraft({ ...newDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="create-spec-tags">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  id="create-spec-tags"
                  name="spec_tags"
                  aria-label="Tags (comma-separated)"
                  className="form-control" 
                  placeholder="risk, audit, finance"
                  value={newDraft.tags}
                  onChange={(e) => setNewDraft({ ...newDraft, tags: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="create-spec-conn-id" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={13} color="#38bdf8" />
                  <span>Target Client Database Connection</span>
                </label>
                <select 
                  id="create-spec-conn-id"
                  name="connection_id"
                  aria-label="Target Client Database Connection"
                  className="form-control"
                  value={newDraft.connection_id || ''}
                  onChange={(e) => setNewDraft({ ...newDraft, connection_id: e.target.value ? Number(e.target.value) : null })}
                >
                  <option value="">★ Global Default Active Database</option>
                  {dbConnections.map(c => (
                    <option key={c.connection_id} value={c.connection_id}>
                      {c.connection_name} ({c.db_type?.toUpperCase()} — {c.database_name}) {c.is_default ? '★ Default' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <Loader className="spinner" size={14} /> : 'Create Draft'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Import BPMN */}
      {showImportModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <span className="modal-title">Import BPMN 2.0 Specification</span>
              <X size={18} style={{ cursor: 'pointer', color: 'var(--color-text-muted)' }} onClick={() => setShowImportModal(false)} />
            </div>
            <form onSubmit={handleImportBPMN}>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-id">Specification ID</label>
                <input 
                  type="text" 
                  id="import-spec-id"
                  name="import_spec_id"
                  aria-label="Specification ID"
                  className="form-control" 
                  placeholder="e.g. ImportedRiskWorkflow"
                  required
                  value={importDraft.spec_id}
                  onChange={(e) => setImportDraft({ ...importDraft, spec_id: sanitizeSpecId(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-name">Friendly Process Name</label>
                <input 
                  type="text" 
                  id="import-spec-name"
                  name="import_spec_name"
                  aria-label="Friendly Process Name"
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={importDraft.name}
                  onChange={(e) => setImportDraft({ ...importDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-desc">Description</label>
                <input 
                  type="text" 
                  id="import-spec-desc"
                  name="import_spec_desc"
                  aria-label="Workflow Description"
                  className="form-control" 
                  placeholder="Import metadata description"
                  value={importDraft.description}
                  onChange={(e) => setImportDraft({ ...importDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-tags">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  id="import-spec-tags"
                  name="import_spec_tags"
                  aria-label="Tags (comma-separated)"
                  className="form-control" 
                  placeholder="imported, bpmn"
                  value={importDraft.tags}
                  onChange={(e) => setImportDraft({ ...importDraft, tags: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-conn-id" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={13} color="#38bdf8" />
                  <span>Target Client Database Connection</span>
                </label>
                <select 
                  id="import-spec-conn-id"
                  name="import_connection_id"
                  aria-label="Target Client Database Connection"
                  className="form-control"
                  value={importDraft.connection_id || ''}
                  onChange={(e) => setImportDraft({ ...importDraft, connection_id: e.target.value ? Number(e.target.value) : null })}
                >
                  <option value="">★ Global Default Active Database</option>
                  {dbConnections.map(c => (
                    <option key={c.connection_id} value={c.connection_id}>
                      {c.connection_name} ({c.db_type?.toUpperCase()} — {c.database_name}) {c.is_default ? '★ Default' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="import-spec-file">BPMN 2.0 File (.bpmn, .xml)</label>
                <input 
                  type="file" 
                  id="import-spec-file"
                  name="import_bpmn_file"
                  aria-label="BPMN 2.0 File (.bpmn, .xml)"
                  className="form-control" 
                  accept=".bpmn,.xml"
                  required
                  onChange={(e) => setImportDraft({ ...importDraft, file: e.target.files[0] })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowImportModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <Loader className="spinner" size={14} /> : 'Import Spec'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalWorkflow && (
        <div className="modal-overlay" onClick={() => setDeleteModalWorkflow(null)}>
          <div className="modal-content" style={{ maxWidth: '440px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626' }}>
                <Trash2 size={18} />
                <span className="modal-title" style={{ fontSize: '16px', margin: 0, color: '#0f172a' }}>Delete Specification</span>
              </div>
              <X size={18} style={{ cursor: 'pointer', color: 'var(--color-text-muted)' }} onClick={() => setDeleteModalWorkflow(null)} />
            </div>
            <p style={{ fontSize: '13px', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
              Are you sure you want to permanently delete specification <strong style={{ color: '#0f172a' }}>{deleteModalWorkflow.spec_id || deleteModalWorkflow.name}</strong>? All associated graph definitions and drafts will be removed.
            </p>
            <div className="modal-actions" style={{ marginTop: '8px' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setDeleteModalWorkflow(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={confirmDeleteWorkflow}
                style={{ background: '#dc2626', color: '#fff' }}
              >
                <Trash2 size={14} />
                <span>Delete Permanently</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Workflow Execution & Test Runner Modal */}
      {executingWorkflow && (
        <ExecutionModal 
          workflowId={executingWorkflow.id}
          workflowSpec={`${executingWorkflow.name || executingWorkflow.spec_id} (v${executingWorkflow.version})`}
          onClose={() => setExecutingWorkflow(null)}
          showToast={showToast}
        />
      )}

      {/* Client Database Connections & Data Sources Modal */}
      {showDbModal && (
        <DatabaseConnectionsModal 
          onClose={() => {
            setShowDbModal(false)
            fetchWorkflows()
          }}
          showToast={showToast}
        />
      )}

      {/* ClientApp Declarative Binding Modal */}
      {bindingModalWorkflow && (
        <ClientAppBindingModal
          isOpen={Boolean(bindingModalWorkflow)}
          workflow={bindingModalWorkflow}
          dbConnections={dbConnections}
          onClose={() => setBindingModalWorkflow(null)}
          onBindingUpdated={fetchWorkflows}
          showToast={showToast}
        />
      )}
    </div>
  )
}

export default Dashboard
