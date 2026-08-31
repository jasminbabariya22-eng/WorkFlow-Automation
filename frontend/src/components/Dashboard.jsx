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
  Database
} from 'lucide-react'
import ExecutionModal from './ExecutionModal'
import DatabaseConnectionsModal from './DatabaseConnectionsModal'
import { workflowStorage } from '../services/workflowStorage'

function Dashboard({ onOpenDesigner, showToast }) {
  // Feature flag: Set to true if you want to re-enable the Test Run button on the Dashboard
  const ENABLE_DASHBOARD_TEST_RUN = false

  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  
  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [showDbModal, setShowDbModal] = useState(false)
  const [executingWorkflow, setExecutingWorkflow] = useState(null)
  const [dbConnections, setDbConnections] = useState([])

  // Form payloads
  const [newDraft, setNewDraft] = useState({ spec_id: '', name: '', description: '', tags: '', connection_id: '' })
  const [importDraft, setImportDraft] = useState({ spec_id: '', name: '', description: '', tags: '', connection_id: '', file: null })
  const [submitting, setSubmitting] = useState(false)

  // Fetch all workflow definitions & database connections
  const fetchWorkflows = async () => {
    setLoading(true)
    try {
      const [wfData, connData] = await Promise.allSettled([
        workflowStorage.getWorkflows(),
        workflowStorage.getDatabaseConnections()
      ])
      if (wfData.status === 'fulfilled') setWorkflows(wfData.value || [])
      if (connData.status === 'fulfilled') setDbConnections(connData.value || [])
    } catch (error) {
      showToast('Error while loading definitions', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkflows()
  }, [])

  // Create Draft Definition
  const handleCreateDraft = async (e) => {
    e.preventDefault()
    if (!newDraft.spec_id || !newDraft.name) {
      showToast('Specification ID and Name are required.', 'error')
      return
    }
    setSubmitting(true)
    try {
      const created = await workflowStorage.createWorkflow(newDraft)
      showToast('Draft created successfully', 'success')
      setShowCreateModal(false)
      setNewDraft({ spec_id: '', name: '', description: '', tags: '' })
      await fetchWorkflows()
      if (created && created.id) {
        onOpenDesigner(created.id)
      }
    } catch (error) {
      showToast('Failed to create draft', 'error')
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
    e.stopPropagation()
    await workflowStorage.publishWorkflow(id)
    showToast('Workflow published successfully', 'success')
    await fetchWorkflows()
  }

  // Activate Version
  const handleActivate = async (id, e) => {
    e.stopPropagation()
    await workflowStorage.activateWorkflow(id)
    showToast('Workflow version activated', 'success')
    await fetchWorkflows()
  }

  // Deactivate Version
  const handleDeactivate = async (id, e) => {
    e.stopPropagation()
    await workflowStorage.deactivateWorkflow(id)
    showToast('Workflow version deactivated successfully', 'success')
    await fetchWorkflows()
  }

  // Clone/Duplicate Draft
  const handleDuplicate = async (id, e) => {
    e.stopPropagation()
    await workflowStorage.duplicateWorkflow(id)
    showToast('Cloned draft specification successfully', 'success')
    await fetchWorkflows()
  }

  // Delete Version
  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this workflow version? This action is permanent.')) {
      return
    }
    await workflowStorage.deleteWorkflow(id)
    showToast('Deleted successfully', 'success')
    await fetchWorkflows()
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
    const matchesSearch = 
      (wf.spec_id && wf.spec_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (wf.name && wf.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (wf.description && wf.description.toLowerCase().includes(searchQuery.toLowerCase()))
      
    const matchesStatus = statusFilter === '' || wf.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  return (
    <div className="dashboard-view">
      <div className="dashboard-header-actions">
        <div className="search-filter-box">
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--color-text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            <input 
              type="text" 
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
              className="filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="Draft">Draft</option>
              <option value="Published">Published</option>
              <option value="Active">Active</option>
              <option value="Archived">Archived</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowDbModal(true)}
            style={{ borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
            title="Configure and test Client Database connections"
          >
            <Database size={16} />
            <span>Database Connections</span>
          </button>
          <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
            <Upload size={16} />
            <span>Import BPMN</span>
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={18} />
            <span>New Workflow</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <Loader className="spinner" size={32} color="var(--color-accent-secondary)" />
        </div>
      ) : filteredWorkflows.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '80px 0', border: '1px dashed var(--border-glass)', borderRadius: '12px', background: 'var(--bg-card)' }}>
          <FileCode size={48} color="var(--color-text-muted)" style={{ marginBottom: '16px' }} />
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: '500', marginBottom: '8px' }}>No workflows found</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>Create a new draft or import a BPMN file to start designing.</p>
        </div>
      ) : (
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>Specification ID</th>
                <th>Process Name</th>
                <th>Database</th>
                <th>Version</th>
                <th>Status</th>
                <th>Tags</th>
                <th>Last Updated</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredWorkflows.map(wf => (
                <tr key={wf.id} onClick={() => onOpenDesigner(wf.id)}>
                  <td style={{ fontWeight: '600', color: 'var(--color-accent-secondary)' }}>{wf.spec_id}</td>
                  <td style={{ fontWeight: '500' }}>{wf.name}</td>
                  <td>
                    {(() => {
                      const connId = wf.connection_id
                      if (!connId) {
                        return (
                          <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            ★ Default DB
                          </span>
                        )
                      }
                      const conn = dbConnections.find(c => c.connection_id === connId)
                      return (
                        <span style={{ fontSize: '11px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.25)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Database size={10} />
                          {conn ? conn.connection_name : `DB #${connId}`}
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
                  <td style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>
                    {wf.updated_at || wf.updated_on || wf.created_on || '—'}
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
                      <button className="btn btn-danger btn-sm" title="Delete Version" onClick={(e) => handleDelete(wf.id, e)}>
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
                <label className="form-label">Specification ID (unique key)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. RiskApprovalWorkflow"
                  required
                  value={newDraft.spec_id}
                  onChange={(e) => setNewDraft({ ...newDraft, spec_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Friendly Process Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={newDraft.name}
                  onChange={(e) => setNewDraft({ ...newDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="Short explanation of workflow triggers and tasks"
                  value={newDraft.description}
                  onChange={(e) => setNewDraft({ ...newDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="risk, audit, finance"
                  value={newDraft.tags}
                  onChange={(e) => setNewDraft({ ...newDraft, tags: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={13} color="#38bdf8" />
                  <span>Target Client Database Connection</span>
                </label>
                <select 
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
                <label className="form-label">Specification ID</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. RiskApprovalWorkflow"
                  required
                  value={importDraft.spec_id}
                  onChange={(e) => setImportDraft({ ...importDraft, spec_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Friendly Process Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="e.g. Risk Audit Approval Flow"
                  required
                  value={importDraft.name}
                  onChange={(e) => setImportDraft({ ...importDraft, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="Import metadata description"
                  value={importDraft.description}
                  onChange={(e) => setImportDraft({ ...importDraft, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="imported, workflow"
                  value={importDraft.tags}
                  onChange={(e) => setImportDraft({ ...importDraft, tags: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Database size={13} color="#38bdf8" />
                  <span>Target Client Database Connection</span>
                </label>
                <select 
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
                <label className="form-label">BPMN 2.0 File (.bpmn, .xml)</label>
                <input 
                  type="file" 
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
          onClose={() => setShowDbModal(false)}
          showToast={showToast}
        />
      )}
    </div>
  )
}

export default Dashboard
