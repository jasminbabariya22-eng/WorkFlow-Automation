import React, { useState, useEffect } from 'react'
import {
  FilePlus,
  Sparkles,
  Upload,
  Database,
  Search,
  ArrowRight,
  GitBranch,
  X,
  Layers,
  ChevronRight,
  CheckCircle2,
  Clock
} from 'lucide-react'
import { workflowStorage } from '../../services/workflowStorage'

export default function WorkflowSuggestionModal({
  isOpen,
  onClose,
  onSelectWorkflow,
  onCreateBlank,
  onLoadTemplate,
  onTriggerImport,
  activeWorkflowId
}) {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [dbConnections, setDbConnections] = useState([])

  useEffect(() => {
    if (!isOpen) return
    let isMounted = true
    setLoading(true)

    const fetchWorkflows = typeof workflowStorage.getWorkflows === 'function'
      ? workflowStorage.getWorkflows()
      : (typeof workflowStorage.getDefinitions === 'function' ? workflowStorage.getDefinitions() : Promise.resolve([]))

    const fetchConns = typeof workflowStorage.getDatabaseConnections === 'function'
      ? workflowStorage.getDatabaseConnections()
      : (typeof workflowStorage.getDbConnections === 'function' ? workflowStorage.getDbConnections() : Promise.resolve([]))

    Promise.all([fetchWorkflows, fetchConns])
      .then(([wfList, conns]) => {
        if (isMounted) {
          setWorkflows(Array.isArray(wfList) ? wfList : [])
          setDbConnections(Array.isArray(conns) ? conns : [])
          setLoading(false)
        }
      })
      .catch((err) => {
        console.error('Error fetching workflows in suggestion modal:', err)
        if (isMounted) setLoading(false)
      })

    return () => { isMounted = false }
  }, [isOpen])

  if (!isOpen) return null

  const filteredWorkflows = workflows.filter(wf => {
    const term = searchTerm.toLowerCase()
    const name = String(wf.name || '').toLowerCase()
    const spec = String(wf.spec_id || '').toLowerCase()
    return name.includes(term) || spec.includes(term)
  })

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(15, 23, 42, 0.45)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        boxShadow: '0 20px 40px -15px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05)',
        width: '100%',
        maxWidth: '860px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'wfModalIn 0.15s cubic-bezier(0.16, 1, 0.3, 1)'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#f8fafc'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)'
            }}>
              <GitBranch size={20} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#0f172a' }}>
                Workflow Designer
              </h2>
              <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#64748b' }}>
                Select an existing workflow to inspect/edit or start a new automation
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close dialog"
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

        {/* Modal Body */}
        <div style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Section 1: Quick Start Actions */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
              Quick Start Options
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
              
              {/* Option 1: Create Blank */}
              <div 
                onClick={onCreateBlank}
                style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#0284c7'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 16px rgba(2, 132, 199, 0.1)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e2e8f0'
                  e.currentTarget.style.transform = 'none'
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.02)'
                }}
              >
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: '#e0f2fe',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#0284c7'
                }}>
                  <FilePlus size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '14px', color: '#0f172a' }}>New Blank Canvas</div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px', lineHeight: '1.4' }}>
                    Start from an empty canvas and build custom steps from scratch
                  </div>
                </div>
              </div>

              {/* Option 2: 3-Tier Template */}
              <div 
                onClick={onLoadTemplate}
                style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#6366f1'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 16px rgba(99, 102, 241, 0.1)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e2e8f0'
                  e.currentTarget.style.transform = 'none'
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.02)'
                }}
              >
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: '#eef2ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#6366f1'
                }}>
                  <Sparkles size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '14px', color: '#0f172a' }}>Approval Flow Template</div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px', lineHeight: '1.4' }}>
                    Load a pre-configured multi-tier initiator & review flow
                  </div>
                </div>
              </div>

              {/* Option 3: Import BPMN/JSON */}
              <div 
                onClick={onTriggerImport}
                style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#10b981'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 16px rgba(16, 185, 129, 0.1)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e2e8f0'
                  e.currentTarget.style.transform = 'none'
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.02)'
                }}
              >
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: '#dcfce7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#15803d'
                }}>
                  <Upload size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '14px', color: '#0f172a' }}>Import BPMN / JSON</div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px', lineHeight: '1.4' }}>
                    Import an existing BPMN 2.0 XML or JSON specification
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* Section 2: Available Workflows in System */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ fontSize: '12px', fontWeight: '700', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Available Workflows ({workflows.length})
              </div>

              {/* Search Box */}
              <div style={{ position: 'relative', width: '260px' }}>
                <Search size={13} style={{ position: 'absolute', left: '10px', top: '9px', color: '#94a3b8' }} />
                <input
                  type="text"
                  placeholder="Filter by name or spec ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px 6px 30px',
                    fontSize: '12px',
                    background: '#f8fafc',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    outline: 'none',
                    color: '#0f172a'
                  }}
                />
              </div>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#64748b', fontSize: '13px' }}>
                Loading available workflows...
              </div>
            ) : filteredWorkflows.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '36px', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '13px' }}>
                No workflows match your search query.
              </div>
            ) : (
              <div style={{
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                overflow: 'hidden',
                maxHeight: '260px',
                overflowY: 'auto'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
                  <thead style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', position: 'sticky', top: 0, zIndex: 1 }}>
                    <tr>
                      <th style={{ padding: '10px 14px', fontWeight: '700', color: '#475569' }}>Process Name / Spec</th>
                      <th style={{ padding: '10px 14px', fontWeight: '700', color: '#475569' }}>Database</th>
                      <th style={{ padding: '10px 14px', fontWeight: '700', color: '#475569' }}>Version</th>
                      <th style={{ padding: '10px 14px', fontWeight: '700', color: '#475569' }}>Status</th>
                      <th style={{ padding: '10px 14px', fontWeight: '700', color: '#475569', textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredWorkflows.map((wf) => {
                      const isCurrent = Number(wf.id) === Number(activeWorkflowId)
                      const conn = dbConnections.find(c => c.connection_id === wf.connection_id)

                      return (
                        <tr 
                          key={wf.id}
                          style={{
                            borderBottom: '1px solid #f1f5f9',
                            background: isCurrent ? '#f0f9ff' : '#ffffff',
                            cursor: 'pointer',
                            transition: 'background 0.1s ease'
                          }}
                          onMouseEnter={(e) => { if (!isCurrent) e.currentTarget.style.background = '#f8fafc' }}
                          onMouseLeave={(e) => { if (!isCurrent) e.currentTarget.style.background = '#ffffff' }}
                          onClick={() => onSelectWorkflow(wf.id)}
                        >
                          <td style={{ padding: '10px 14px' }}>
                            <div style={{ fontWeight: '600', color: '#0f172a' }}>{wf.name || wf.spec_id}</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>{wf.spec_id}</div>
                          </td>
                          <td style={{ padding: '10px 14px' }}>
                            <span style={{
                              fontSize: '11px',
                              background: wf.connection_id ? '#e0f2fe' : '#f1f5f9',
                              color: wf.connection_id ? '#0284c7' : '#64748b',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontWeight: '600'
                            }}>
                              <Database size={10} />
                              {conn ? conn.connection_name : (wf.connection_id ? `DB #${wf.connection_id}` : 'Default DB')}
                            </span>
                          </td>
                          <td style={{ padding: '10px 14px', color: '#64748b' }}>
                            v{wf.version || 1}
                          </td>
                          <td style={{ padding: '10px 14px' }}>
                            <span style={{
                              fontSize: '11px',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontWeight: '600',
                              background: String(wf.status || '').toLowerCase() === 'active' || String(wf.status || '').toLowerCase() === 'published' ? '#dcfce7' : '#f1f5f9',
                              color: String(wf.status || '').toLowerCase() === 'active' || String(wf.status || '').toLowerCase() === 'published' ? '#15803d' : '#64748b'
                            }}>
                              {wf.status || 'Draft'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                onSelectWorkflow(wf.id)
                              }}
                              style={{
                                padding: '5px 12px',
                                fontSize: '11.5px',
                                fontWeight: '600',
                                background: isCurrent ? '#0284c7' : '#ffffff',
                                color: isCurrent ? '#ffffff' : '#0284c7',
                                border: '1px solid #0284c7',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              <span>{isCurrent ? 'Current' : 'Open'}</span>
                              {!isCurrent && <ChevronRight size={12} />}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#f8fafc'
        }}>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Tip: You can reopen this selection dialog anytime by clicking <b>"Open Workflow"</b> in the top bar.
          </span>
          <button
            onClick={onClose}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: '600',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              color: '#334155',
              cursor: 'pointer'
            }}
          >
            Continue to Canvas
          </button>
        </div>
      </div>
    </div>
  )
}
