import React, { useState } from 'react'
import { 
  PlayCircle, 
  StopCircle, 
  User, 
  UserCheck, 
  Mail, 
  Bell, 
  Database, 
  Globe, 
  GitFork, 
  Sliders, 
  Layers, 
  RefreshCw, 
  FilePlus, 
  FileSearch, 
  Search, 
  GripVertical,
  ChevronDown,
  ChevronRight,
  Plus,
  Sparkles,
  Layers as LayersIcon
} from 'lucide-react'

export const NODE_REGISTRY = [
  {
    category: 'EXECUTION NODES',
    id: 'cat-execution',
    items: [
      {
        id: 'exec-user-task',
        type: 'userTask',
        name: 'User Task',
        description: 'Human task checkpoint requiring assignment and role review',
        icon: <User size={15} color="#3b82f6" />,
        badgeClass: 'wf-badge-blue',
        defaultData: {
          label: 'User Task',
          taskCode: 'USER_TASK_1',
          description: 'Human review checkpoint',
          actions: ['APPROVE', 'REJECT'],
          assignment: {
            type: 'role',
            roleName: 'Initiator'
          }
        }
      },
      {
        id: 'exec-approval',
        type: 'approval',
        name: 'Approval',
        description: 'Review step with human decision outcomes',
        icon: <UserCheck size={15} color="#a855f7" />,
        badgeClass: 'wf-badge-purple',
        defaultData: {
          label: 'Approval Step',
          assignmentType: 'Role',
          role: 'MANAGER',
          actions: [
            { id: 'APPROVE', label: 'Approve' },
            { id: 'REJECT', label: 'Reject' },
            { id: 'FORCE_APPROVE', label: 'Force Approve' }
          ],
          description: 'Review and signoff decision'
        }
      },
      {
        id: 'exec-send-email',
        type: 'communication',
        subType: 'EMAIL',
        name: 'Send Email',
        description: 'Dispatch templated notification email',
        icon: <Mail size={15} color="#6366f1" />,
        badgeClass: 'wf-badge-indigo',
        defaultData: {
          label: 'Send Email',
          subType: 'EMAIL',
          to: '{{process.owner.email}}',
          subject: 'Task Review Required: {{workflow.name}}',
          body: 'Hello {{assignee.name}}, a task is pending your review.'
        }
      },
      {
        id: 'exec-notification',
        type: 'communication',
        subType: 'NOTIFICATION',
        name: 'Notification',
        description: 'Trigger in-app notification alert',
        icon: <Bell size={15} color="#6366f1" />,
        badgeClass: 'wf-badge-indigo',
        defaultData: {
          label: 'Notification',
          subType: 'NOTIFICATION',
          recipient: 'Assigned Role',
          title: 'Task Review Pending',
          message: 'A new workflow item requires your review'
        }
      },
      {
        id: 'exec-create-record',
        type: 'record',
        subType: 'CREATE_RECORD',
        name: 'Create Record',
        description: 'Insert a new business entity record',
        icon: <FilePlus size={15} color="#06b6d4" />,
        badgeClass: 'wf-badge-cyan',
        defaultData: {
          label: 'Create Record',
          subType: 'CREATE_RECORD',
          entity: 'Entity',
          fieldMappings: [
            { field: 'status', value: 'DRAFT' },
            { field: 'created_by', value: '{{current_user.id}}' }
          ]
        }
      },
      {
        id: 'exec-update-record',
        type: 'record',
        subType: 'UPDATE_RECORD',
        name: 'Update Record',
        description: 'Modify existing entity fields',
        icon: <RefreshCw size={15} color="#06b6d4" />,
        badgeClass: 'wf-badge-cyan',
        defaultData: {
          label: 'Update Record',
          subType: 'UPDATE_RECORD',
          entity: 'Entity',
          recordId: '{{workflow.entity_id}}',
          fieldMappings: [
            { field: 'status', value: 'APPROVED' },
            { field: 'approved_at', value: '{{system.current_time}}' }
          ]
        }
      },
      {
        id: 'exec-read-record',
        type: 'record',
        subType: 'READ_RECORD',
        name: 'Read Record',
        description: 'Fetch entity data for downstream conditions',
        icon: <FileSearch size={15} color="#06b6d4" />,
        badgeClass: 'wf-badge-cyan',
        defaultData: {
          label: 'Read Record',
          subType: 'READ_RECORD',
          entity: 'Entity',
          recordId: '{{workflow.entity_id}}',
          retrieveFields: ['status', 'department', 'owner'],
          outputVariable: 'entity_data'
        }
      },
      {
        id: 'exec-api-call',
        type: 'action',
        subType: 'API',
        name: 'API Call',
        description: 'Trigger external REST webhook',
        icon: <Globe size={15} color="#14b8a6" />,
        badgeClass: 'wf-badge-teal',
        defaultData: {
          label: 'API Call',
          subType: 'API',
          method: 'POST',
          url: 'https://api.internal/v1/workflow/event',
          headers: 'Content-Type: application/json',
          body: '{\n  "event": "workflow_event"\n}'
        }
      },
      {
        id: 'exec-database-action',
        type: 'action',
        subType: 'DATABASE',
        name: 'Database Action',
        description: 'Execute stored procedure or controlled query',
        icon: <Database size={15} color="#14b8a6" />,
        badgeClass: 'wf-badge-teal',
        defaultData: {
          label: 'Database Action',
          subType: 'DATABASE',
          operation: 'Stored Procedure',
          procedure: 'update_status',
          parameters: 'entity_id = {{workflow.entity_id}}\nuser_id = {{current_user.id}}'
        }
      }
    ]
  },
  {
    category: 'CONTROL-FLOW NODES',
    id: 'cat-control',
    items: [
      {
        id: 'ctrl-condition',
        type: 'condition',
        name: 'Condition',
        description: 'Branch workflow route based on field/operator/value evaluation',
        icon: <GitFork size={15} color="#f59e0b" />,
        badgeClass: 'wf-badge-amber',
        defaultData: {
          label: 'Check Condition',
          field: 'priority',
          operator: 'equals',
          value: 'HIGH',
          description: 'Evaluate rule and route to TRUE or FALSE branch'
        }
      },
      {
        id: 'ctrl-switch',
        type: 'switch',
        name: 'Switch',
        description: 'Route execution based on multiple possible values',
        icon: <Sliders size={15} color="#f59e0b" />,
        badgeClass: 'wf-badge-amber',
        defaultData: {
          label: 'Status Switch',
          source: 'Entity',
          field: 'Status',
          cases: ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'],
          hasDefault: true
        }
      },
      {
        id: 'ctrl-parallel',
        type: 'parallel',
        name: 'Parallel',
        description: 'Start multiple branches simultaneously',
        icon: <Layers size={15} color="#f59e0b" />,
        badgeClass: 'wf-badge-amber',
        defaultData: {
          label: 'Parallel Review',
          branches: ['Audit Review', 'Finance Review'],
          completionRule: 'All'
        }
      }
    ]
  },
  {
    category: 'BOUNDARY NODES',
    id: 'cat-boundary',
    items: [
      {
        id: 'bound-start',
        type: 'start',
        name: 'Start',
        description: 'Entry point of the workflow',
        icon: <PlayCircle size={15} color="#22c55e" />,
        badgeClass: 'wf-badge-green',
        defaultData: {
          label: 'Workflow Start',
          description: 'Entry point of the workflow',
          trigger: 'Workflow Activated'
        }
      },
      {
        id: 'bound-end',
        type: 'end',
        name: 'End',
        description: 'Workflow terminal point',
        icon: <StopCircle size={15} color="#10b981" />,
        badgeClass: 'wf-badge-emerald',
        defaultData: {
          label: 'Workflow End',
          description: 'Workflow terminal point',
          outcome: 'COMPLETED'
        }
      }
    ]
  }
]

export default function NodeLibrary({ onAddNode, onAddTemplateFlow }) {
  const [search, setSearch] = useState('')
  const [collapsedCats, setCollapsedCats] = useState({})

  const toggleCategory = (catId) => {
    setCollapsedCats(prev => ({
      ...prev,
      [catId]: !prev[catId]
    }))
  }

  const onDragStart = (event, item) => {
    const payload = {
      type: item.type,
      name: item.name,
      subType: item.subType || item.type,
      ...item.defaultData
    }
    event.dataTransfer.setData('application/reactflow', JSON.stringify(payload))
    event.dataTransfer.effectAllowed = 'move'
  }

  const filteredCategories = NODE_REGISTRY.map(cat => {
    const matched = cat.items.filter(item => 
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase()) ||
      cat.category.toLowerCase().includes(search.toLowerCase())
    )
    return { ...cat, items: matched }
  }).filter(cat => cat.items.length > 0)

  return (
    <aside className="wf-node-library-panel">
      {/* Library Title */}
      <div className="wf-library-header">
        <div className="wf-library-title">
          <LayersIcon size={14} color="#818cf8" />
          <span>NODE LIBRARY</span>
        </div>
      </div>

      {/* Search Input */}
      <div className="wf-search-wrapper">
        <Search size={13} className="wf-search-icon" />
        <input 
          type="text" 
          placeholder="Search nodes..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="wf-search-input"
          id="node-library-search"
        />
        {search && (
          <button 
            className="wf-search-clear" 
            onClick={() => setSearch('')}
            title="Clear search"
          >
            ×
          </button>
        )}
      </div>

      {/* Quick Template Helper Button */}
      {onAddTemplateFlow && (
        <div className="wf-quick-template-box">
          <button 
            className="wf-quick-template-btn"
            onClick={onAddTemplateFlow}
            title="Load the standard 3-tier enterprise approval template"
          >
            <Sparkles size={13} color="#818cf8" />
            <span>Load Approval Template</span>
          </button>
        </div>
      )}

      {/* Categories & Node Items */}
      <div className="wf-library-scroll">
        {filteredCategories.length === 0 ? (
          <div className="wf-no-results">
            No nodes matching "{search}"
          </div>
        ) : (
          filteredCategories.map(cat => {
            const isCollapsed = Boolean(collapsedCats[cat.id])
            return (
              <div key={cat.id} className="wf-category-group">
                <div 
                  className="wf-category-title-bar"
                  onClick={() => toggleCategory(cat.id)}
                >
                  <span className="wf-category-chevron">
                    {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                  </span>
                  <span className="wf-category-name">{cat.category}</span>
                  <span className="wf-category-count">{cat.items.length}</span>
                </div>

                {!isCollapsed && (
                  <div className="wf-items-list">
                    {cat.items.map(item => (
                      <div 
                        key={item.id}
                        className="wf-palette-item"
                        draggable
                        onDragStart={(e) => onDragStart(e, item)}
                        title={`${item.name}: ${item.description}`}
                      >
                        <div className={`wf-palette-icon ${item.badgeClass}`}>
                          {item.icon}
                        </div>
                        <div className="wf-palette-info">
                          <div className="wf-palette-name">{item.name}</div>
                          <div className="wf-palette-desc">{item.description}</div>
                        </div>

                        <div className="wf-palette-actions">
                          {onAddNode && (
                            <button 
                              className="wf-add-node-btn"
                              title="Click to add to canvas center"
                              onClick={(e) => {
                                e.stopPropagation()
                                onAddNode({
                                  type: item.type,
                                  name: item.name,
                                  subType: item.subType || item.type,
                                  ...item.defaultData
                                })
                              }}
                            >
                              <Plus size={12} />
                            </button>
                          )}
                          <GripVertical size={13} className="wf-drag-handle" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
