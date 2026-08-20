import React, { useState, useEffect } from 'react'
import { 
  Sliders, 
  Trash2, 
  Shield, 
  Plus, 
  X,
  AlertCircle
} from 'lucide-react'
import { workflowStorage } from '../services/workflowStorage'

const VISIBILITY_OPTIONS = [
  { id: 'EVERYONE', label: 'Everyone' },
  { id: 'OWNER', label: 'Owner' },
  { id: 'APPROVER', label: 'Approver' }
]

export default function PropertiesPanel({ 
  selectedNode, 
  selectedEdge,
  onUpdateNodeData, 
  onUpdateEdgeData,
  onDeleteNode, 
  onDeleteEdge 
}) {
  // Master data dynamically loaded from Client Database
  const [backendRoles, setBackendRoles] = useState([])
  const [backendUsers, setBackendUsers] = useState([])
  const [backendDepartments, setBackendDepartments] = useState([])
  const [backendEntities, setBackendEntities] = useState([])
  const [backendStatuses, setBackendStatuses] = useState([])
  const [backendActions, setBackendActions] = useState([])
  const [availableFields, setAvailableFields] = useState([])
  const [metadataError, setMetadataError] = useState(null)

  useEffect(() => {
    let isMounted = true
    const fetchMasterData = async () => {
      try {
        const results = await Promise.allSettled([
          workflowStorage.getMetadataRoles(),
          workflowStorage.getMetadataUsers(),
          workflowStorage.getMetadataDepartments(),
          workflowStorage.getMetadataEntities(),
          workflowStorage.getMetadataStatuses(),
          workflowStorage.getMetadataActions()
        ])

        if (isMounted) {
          const roles = results[0].status === 'fulfilled' && Array.isArray(results[0].value) ? results[0].value : []
          const users = results[1].status === 'fulfilled' && Array.isArray(results[1].value) ? results[1].value : []
          const depts = results[2].status === 'fulfilled' && Array.isArray(results[2].value) ? results[2].value : []
          const entities = results[3].status === 'fulfilled' && Array.isArray(results[3].value) ? results[3].value : []
          const statuses = results[4].status === 'fulfilled' && Array.isArray(results[4].value) ? results[4].value : []
          const actions = results[5].status === 'fulfilled' && Array.isArray(results[5].value) ? results[5].value : []

          const anySuccess = results.some(r => r.status === 'fulfilled')
          if (anySuccess && (roles.length > 0 || users.length > 0 || entities.length > 0)) {
            setBackendRoles(roles.map(r => ({ id: String(r.id), name: r.name })))
            setBackendUsers(users.map(u => ({ id: String(u.id), name: u.name || `User ${u.id}` })))
            setBackendDepartments(depts.map(d => ({ id: String(d.id), name: d.name || `Department ${d.id}` })))
            setBackendEntities(entities.map(e => ({ name: e.name || e.table_name })))
            setBackendStatuses(statuses.map(s => ({ id: String(s.id), name: s.name, type: s.type })))
            setBackendActions(actions.map(a => ({ id: a.action_code || a.id, label: a.name || a.label })))
            setMetadataError(null)
          } else {
            setMetadataError('Client Database unavailable. Dynamic metadata cannot be loaded.')
          }
        }
      } catch (err) {
        if (isMounted) {
          setMetadataError('Client Database unavailable. Dynamic metadata cannot be loaded.')
        }
      }
    }

    fetchMasterData()
    return () => { isMounted = false }
  }, [])

  // Dynamic field introspection for the selected entity
  const currentEntity = selectedNode?.data?.entity || (backendEntities[0]?.name || '')
  useEffect(() => {
    let isMounted = true
    if (currentEntity) {
      workflowStorage.getMetadataEntityFields(currentEntity)
        .then(fields => {
          if (isMounted) setAvailableFields(fields || [])
        })
        .catch(() => {
          if (isMounted) setAvailableFields([])
        })
    } else {
      setAvailableFields([])
    }
    return () => { isMounted = false }
  }, [currentEntity])

  // Temporary input states for adding items
  const [newActionId, setNewActionId] = useState('')
  const [newActionLabel, setNewActionLabel] = useState('')
  const [newCaseLabel, setNewCaseLabel] = useState('')
  const [newBranchName, setNewBranchName] = useState('')
  const [newFieldKey, setNewFieldKey] = useState('')
  const [newFieldValue, setNewFieldValue] = useState('')
  const [newRetrieveField, setNewRetrieveField] = useState('')

  // 1. Empty State
  if (!selectedNode && !selectedEdge) {
    return (
      <aside className="wf-properties-panel">
        <div className="wf-properties-header">
          <Sliders size={14} color="#818cf8" />
          <span>PROPERTIES</span>
        </div>
        <div className="wf-empty-properties">
          <div className="wf-empty-icon">
            <Sliders size={28} color="#64748b" />
          </div>
          <div className="wf-empty-title">No Element Selected</div>
          <div className="wf-empty-desc">
            Select a node or connection on the canvas to configure its behavior, assignment, dynamic action outcomes, or routing rules.
          </div>
        </div>
      </aside>
    )
  }

  // 2. Edge Properties
  if (selectedEdge) {
    const edgeData = selectedEdge.data || {}
    const label = edgeData.label || edgeData.action || selectedEdge.sourceHandle || ''

    return (
      <aside className="wf-properties-panel">
        <div className="wf-properties-header">
          <Sliders size={14} color="#818cf8" />
          <span>PROPERTIES</span>
        </div>
        <div className="wf-prop-subtitle">Transition Connection</div>

        <div className="wf-properties-scroll">
          <div className="wf-field-group">
            <label className="wf-field-label">Action / Outcome Label</label>
            <input 
              type="text" 
              className="wf-input"
              value={label}
              onChange={(e) => onUpdateEdgeData(selectedEdge.id, { label: e.target.value, action: e.target.value })}
              placeholder="e.g. Approve, Reject, Force Approve, TRUE"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Source Node Port</label>
            <input type="text" className="wf-input font-mono" value={selectedEdge.sourceHandle || 'Default Output'} disabled />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Target Node Port</label>
            <input type="text" className="wf-input font-mono" value={selectedEdge.targetHandle || 'input'} disabled />
          </div>

          <div className="wf-delete-section">
            <button className="wf-delete-btn" onClick={() => onDeleteEdge(selectedEdge.id)}>
              <Trash2 size={13} />
              <span>Delete Connection</span>
            </button>
          </div>
        </div>
      </aside>
    )
  }

  // 3. Node-Specific Properties
  const data = selectedNode.data || {}
  const nodeType = selectedNode.type || 'generic'
  const name = data.label !== undefined ? data.label : data.name !== undefined ? data.name : ''
  const description = data.description || ''

  const handleFieldChange = (field, value) => {
    onUpdateNodeData(selectedNode.id, {
      ...data,
      [field]: value
    })
  }

  const handleNameChange = (newName) => {
    onUpdateNodeData(selectedNode.id, {
      ...data,
      label: newName,
      name: newName
    })
  }

  // =========================================================================
  // USER TASK HANDLERS (Assignment, Visibility, Actions)
  // =========================================================================
  const assignment = data.assignment || {
    type: (data.assignmentType || 'role').toLowerCase(),
    roleId: data.roleId || '1',
    roleName: data.role || 'Initiator',
    userId: data.userId || '',
    userName: data.user || '',
    departmentId: data.departmentId || '',
    departmentName: data.department || ''
  }
  const assignmentType = (assignment.type || 'role').toLowerCase()

  const handleAssignmentTypeChange = (newType) => {
    let roleId = assignment.roleId || ''
    let roleName = assignment.roleName || ''
    let userId = assignment.userId || ''
    let userName = assignment.userName || ''
    let departmentId = assignment.departmentId || ''
    let departmentName = assignment.departmentName || ''

    if (newType === 'role' && !roleId && backendRoles.length > 0) {
      roleId = backendRoles[0].id
      roleName = backendRoles[0].name
    } else if (newType === 'user' && !userId && backendUsers.length > 0) {
      userId = backendUsers[0].id
      userName = backendUsers[0].name
    } else if (newType === 'department' && !departmentId && backendDepartments.length > 0) {
      departmentId = backendDepartments[0].id
      departmentName = backendDepartments[0].name
    }

    handleFieldChange('assignment', {
      type: newType,
      roleId,
      roleName,
      userId,
      userName,
      departmentId,
      departmentName
    })
  }

  const handleRoleSelect = (selectedRoleId) => {
    const found = backendRoles.find(r => String(r.id) === String(selectedRoleId))
    onUpdateNodeData(selectedNode.id, {
      ...data,
      role: found ? found.name : '',
      roleId: selectedRoleId,
      assignment: {
        ...assignment,
        type: 'role',
        roleId: selectedRoleId,
        roleName: found ? found.name : ''
      }
    })
  }

  const handleUserSelect = (selectedUserId) => {
    const found = backendUsers.find(u => String(u.id) === String(selectedUserId))
    onUpdateNodeData(selectedNode.id, {
      ...data,
      user: found ? found.name : '',
      userId: selectedUserId,
      assignment: {
        ...assignment,
        type: 'user',
        userId: selectedUserId,
        userName: found ? found.name : ''
      }
    })
  }

  const handleDepartmentSelect = (selectedDeptId) => {
    const found = backendDepartments.find(d => String(d.id) === String(selectedDeptId))
    onUpdateNodeData(selectedNode.id, {
      ...data,
      department: found ? found.name : '',
      departmentId: selectedDeptId,
      assignment: {
        ...assignment,
        type: 'department',
        departmentId: selectedDeptId,
        departmentName: found ? found.name : ''
      }
    })
  }

  const activeVisibility = Array.isArray(data.visibility) && data.visibility.length > 0 
    ? data.visibility 
    : ['APPROVER']

  const handleToggleVisibility = (visId) => {
    let next
    if (activeVisibility.includes(visId)) {
      next = activeVisibility.filter(v => v !== visId)
      if (next.length === 0) next = [visId] // keep at least one
    } else {
      next = [...activeVisibility, visId]
    }
    handleFieldChange('visibility', next)
  }

  const rawActions = Array.isArray(data.actions) && data.actions.length > 0
    ? data.actions
    : ['APPROVE', 'REJECT']
  const activeActions = rawActions.map(a => typeof a === 'string' ? a.toUpperCase() : (a.id || a.label).toUpperCase())

  const handleToggleAction = (actionId) => {
    let next
    if (activeActions.includes(actionId)) {
      next = activeActions.filter(a => a !== actionId)
      if (next.length === 0) next = [actionId] // keep at least one action
    } else {
      next = [...activeActions, actionId]
    }
    handleFieldChange('actions', next)
  }

  // Generic action handler for other nodes
  const actions = Array.isArray(data.actions) ? data.actions : []
  
  const handleAddAction = () => {
    if (!newActionLabel.trim()) return
    const id = newActionId.trim() 
      ? newActionId.trim().toUpperCase().replace(/\s+/g, '_')
      : newActionLabel.trim().toUpperCase().replace(/\s+/g, '_')
    
    const exists = actions.some(a => (typeof a === 'string' ? a : a.id) === id)
    if (!exists) {
      const next = [...actions, { id, label: newActionLabel.trim() }]
      handleFieldChange('actions', next)
    }
    setNewActionId('')
    setNewActionLabel('')
  }

  const handleRemoveAction = (actionId) => {
    const next = actions.filter(a => (typeof a === 'string' ? a : a.id) !== actionId)
    handleFieldChange('actions', next)
  }


  // =========================================================================
  // SWITCH CASES HANDLERS
  // =========================================================================
  const cases = Array.isArray(data.cases) ? data.cases : ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED']
  
  const handleAddCase = () => {
    if (!newCaseLabel.trim()) return
    const formatted = newCaseLabel.trim().toUpperCase()
    if (!cases.includes(formatted)) {
      handleFieldChange('cases', [...cases, formatted])
    }
    setNewCaseLabel('')
  }

  const handleRemoveCase = (c) => {
    handleFieldChange('cases', cases.filter(item => item !== c))
  }

  // =========================================================================
  // PARALLEL BRANCHES HANDLERS
  // =========================================================================
  const branches = Array.isArray(data.branches) ? data.branches : ['Branch 1', 'Branch 2']
  
  const handleAddBranch = () => {
    if (!newBranchName.trim()) return
    handleFieldChange('branches', [...branches, newBranchName.trim()])
    setNewBranchName('')
  }

  const handleRemoveBranch = (b) => {
    handleFieldChange('branches', branches.filter(item => item !== b))
  }

  // =========================================================================
  // FIELD MAPPINGS (CREATE / UPDATE RECORD)
  // =========================================================================
  const fieldMappings = Array.isArray(data.fieldMappings) 
    ? data.fieldMappings 
    : [{ field: 'status', value: 'APPROVED' }]

  const handleAddFieldMapping = () => {
    if (!newFieldKey.trim()) return
    const next = [...fieldMappings, { field: newFieldKey.trim(), value: newFieldValue.trim() || '' }]
    handleFieldChange('fieldMappings', next)
    setNewFieldKey('')
    setNewFieldValue('')
  }

  const handleRemoveFieldMapping = (idx) => {
    handleFieldChange('fieldMappings', fieldMappings.filter((_, i) => i !== idx))
  }

  // =========================================================================
  // READ RECORD RETRIEVE FIELDS
  // =========================================================================
  const retrieveFields = Array.isArray(data.retrieveFields) 
    ? data.retrieveFields 
    : ['score', 'category', 'department', 'owner', 'status']

  const handleAddRetrieveField = () => {
    if (!newRetrieveField.trim()) return
    if (!retrieveFields.includes(newRetrieveField.trim())) {
      handleFieldChange('retrieveFields', [...retrieveFields, newRetrieveField.trim()])
    }
    setNewRetrieveField('')
  }

  const handleRemoveRetrieveField = (f) => {
    handleFieldChange('retrieveFields', retrieveFields.filter(item => item !== f))
  }

  // Category Banner tag helper
  let nodeCategoryTag = 'EXECUTION NODE'
  if (nodeType === 'start' || nodeType === 'end') nodeCategoryTag = 'BOUNDARY NODE'
  if (nodeType === 'condition' || nodeType === 'switch' || nodeType === 'parallel') nodeCategoryTag = 'CONTROL-FLOW NODE'

  return (
    <aside className="wf-properties-panel">
      <div className="wf-properties-header">
        <Sliders size={14} color="#818cf8" />
        <span>PROPERTIES</span>
      </div>
      <div className="wf-prop-subtitle">
        <span className="wf-type-badge-pill">{nodeCategoryTag}</span>
        <span className="font-semibold text-primary">{nodeType.toUpperCase()}</span>
      </div>

      <div className="wf-properties-scroll">
        {metadataError && (
          <div className="wf-alert wf-alert-error mb-3" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '8px 12px', borderRadius: '6px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{metadataError}</span>
          </div>
        )}

        {/* =========================================================================
            COMMON: BASIC PROPERTIES
           ========================================================================= */}
        <div className="wf-field-group">
          <label className="wf-field-label">Node Name</label>
          <input 
            type="text" 
            className="wf-input"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="Enter custom node name..."
          />
        </div>

        <div className="wf-field-group">
          <label className="wf-field-label">Description</label>
          <textarea 
            className="wf-textarea"
            rows={2}
            value={description}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            placeholder="Short description of this step"
          />
        </div>

        {/* =========================================================================
            1. START NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'start' && (
          <div className="wf-field-group">
            <label className="wf-field-label">Trigger</label>
            <input 
              type="text" 
              className="wf-input font-medium"
              value={data.trigger || 'Workflow Activated'}
              readOnly
              disabled
            />
          </div>
        )}

        {/* =========================================================================
            2. END NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'end' && (
          <div className="wf-field-group">
            <label className="wf-field-label">Outcome Label (Optional)</label>
            <input 
              type="text" 
              className="wf-input font-medium uppercase"
              value={data.outcome || ''}
              onChange={(e) => handleFieldChange('outcome', e.target.value.toUpperCase())}
              placeholder="e.g. COMPLETED"
            />
          </div>
        )}

        {/* =========================================================================
            3. USER TASK NODE PROPERTIES (Human Checkpoint)
           ========================================================================= */}
        {nodeType === 'userTask' && (
          <>
            <div className="wf-section-divider">TASK CONFIGURATION</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Task Code</label>
              <input 
                type="text" 
                className="wf-input font-mono uppercase"
                value={data.taskCode || data.task_code || selectedNode.id || ''}
                onChange={(e) => handleFieldChange('taskCode', e.target.value.toUpperCase())}
                placeholder="e.g. USER_REVIEW, MANAGER_APPROVAL"
              />
            </div>

            <div className="wf-section-divider">ASSIGNMENT</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Assignment Type</label>
              <div className="wf-type-toggle-buttons">
                {['user', 'role', 'department'].map(t => (
                  <button
                    key={t}
                    type="button"
                    className={`wf-preset-btn ${assignmentType === t ? 'active' : ''}`}
                    onClick={() => handleAssignmentTypeChange(t)}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {assignmentType === 'role' && (
              <div className="wf-field-group">
                <label className="wf-field-label">Role</label>
                <select 
                  className="wf-select"
                  value={assignment.roleId || ''}
                  onChange={(e) => handleRoleSelect(e.target.value)}
                >
                  <option value="">-- Select Role --</option>
                  {backendRoles.map(r => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>
            )}

            {assignmentType === 'user' && (
              <div className="wf-field-group">
                <label className="wf-field-label">User</label>
                <select 
                  className="wf-select"
                  value={assignment.userId || ''}
                  onChange={(e) => handleUserSelect(e.target.value)}
                >
                  <option value="">-- Select User --</option>
                  {backendUsers.map(u => (
                    <option key={u.id} value={u.id}>{u.name}</option>
                  ))}
                </select>
              </div>
            )}

            {assignmentType === 'department' && (
              <div className="wf-field-group">
                <label className="wf-field-label">Department</label>
                <select 
                  className="wf-select"
                  value={assignment.departmentId || ''}
                  onChange={(e) => handleDepartmentSelect(e.target.value)}
                >
                  <option value="">-- Select Department --</option>
                  {backendDepartments.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="wf-section-divider">VISIBILITY</div>
            <div className="wf-visibility-buttons-row">
              {VISIBILITY_OPTIONS.map(v => {
                const isSelected = activeVisibility.includes(v.id)
                return (
                  <button
                    key={v.id}
                    type="button"
                    className={`wf-vis-btn ${isSelected ? 'active' : ''}`}
                    onClick={() => handleToggleVisibility(v.id)}
                  >
                    {v.label}
                  </button>
                )
              })}
            </div>

            <div className="wf-section-divider">ACTIONS (CLIENT DB TRANSITIONS)</div>
            <div className="wf-actions-checklist">
              {backendActions.map(act => {
                const isChecked = activeActions.includes(act.id)
                return (
                  <label key={act.id} className="wf-checkbox-label">
                    <input 
                      type="checkbox" 
                      checked={isChecked}
                      onChange={() => handleToggleAction(act.id)}
                    />
                    <span className="wf-action-opt-name">{act.label}</span>
                  </label>
                )
              })}
            </div>
          </>
        )}

        {/* =========================================================================
            4. APPROVAL NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'approval' && (
          <>
            <div className="wf-section-divider">ASSIGNMENT</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Assignment Type</label>
              <select 
                className="wf-select"
                value={data.assignmentType || 'Role'}
                onChange={(e) => handleFieldChange('assignmentType', e.target.value)}
              >
                <option value="Role">Role</option>
                <option value="User">User</option>
                <option value="Department">Department</option>
              </select>
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">
                <Shield size={12} color="#818cf8" />
                <span>Approver Role / Group (Client DB)</span>
              </label>
              <select 
                className="wf-select"
                value={data.role || ''}
                onChange={(e) => handleFieldChange('role', e.target.value)}
              >
                <option value="">-- Select Client Role --</option>
                {backendRoles.map(r => (
                  <option key={r.id} value={r.name}>{r.name}</option>
                ))}
              </select>
            </div>

            <div className="wf-section-divider">ACTIONS / OUTCOMES (DECISION HANDLES)</div>
            <p className="wf-hint-text">Each action generates a decision outcome port on the node:</p>

            <div className="wf-action-tag-list">
              {actions.map((act) => {
                const actionId = typeof act === 'string' ? act : act.id
                const label = typeof act === 'string' ? act.replace(/_/g, ' ') : act.label
                return (
                  <div key={actionId} className={`wf-action-port-chip ${actionId === 'APPROVE' ? 'approve' : actionId === 'REJECT' ? 'reject' : 'force'}`}>
                    <span className="wf-action-chip-label">{label}</span>
                    <span className="wf-action-chip-id">({actionId})</span>
                    <button type="button" onClick={() => handleRemoveAction(actionId)}>
                      <X size={12} />
                    </button>
                  </div>
                )
              })}
            </div>

            <div className="wf-add-action-box">
              <input 
                type="text" 
                className="wf-input wf-input-sm"
                placeholder="e.g. Force Approve"
                value={newActionLabel}
                onChange={(e) => setNewActionLabel(e.target.value)}
              />
              <input 
                type="text" 
                className="wf-input wf-input-sm font-mono uppercase"
                placeholder="ID (e.g. FORCE_APPROVE)"
                value={newActionId}
                onChange={(e) => setNewActionId(e.target.value)}
              />
              <button type="button" className="wf-btn wf-btn-sm wf-btn-primary" onClick={handleAddAction}>
                <Plus size={13} />
                <span>Add Action</span>
              </button>
            </div>

            <div className="wf-section-divider">APPROVAL RULES</div>
            <div className="wf-toggle-list">
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={data.commentOnReject !== false} 
                  onChange={(e) => handleFieldChange('commentOnReject', e.target.checked)} 
                />
                <span>Require comment on Reject</span>
              </label>
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={Boolean(data.commentOnApprove)} 
                  onChange={(e) => handleFieldChange('commentOnApprove', e.target.checked)} 
                />
                <span>Require comment on Approve</span>
              </label>
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={data.commentOnForceApprove !== false} 
                  onChange={(e) => handleFieldChange('commentOnForceApprove', e.target.checked)} 
                />
                <span>Require comment on Force Approve</span>
              </label>
            </div>

            <div className="wf-section-divider">NOTIFICATIONS</div>
            <div className="wf-toggle-list">
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={data.notifyOnAssign !== false} 
                  onChange={(e) => handleFieldChange('notifyOnAssign', e.target.checked)} 
                />
                <span>On Assignment</span>
              </label>
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={data.notifyOnApprove !== false} 
                  onChange={(e) => handleFieldChange('notifyOnApprove', e.target.checked)} 
                />
                <span>On Approve</span>
              </label>
              <label className="wf-checkbox-label">
                <input 
                  type="checkbox" 
                  checked={data.notifyOnReject !== false} 
                  onChange={(e) => handleFieldChange('notifyOnReject', e.target.checked)} 
                />
                <span>On Reject</span>
              </label>
            </div>
          </>
        )}

        {/* =========================================================================
            5. CONDITION / ROUTING NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'condition' && (
          <>
            <div className="wf-section-divider">CONDITION RULE CONFIGURATION</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Field / Variable</label>
              <input 
                type="text" 
                className="wf-input font-mono"
                value={data.field || ''}
                onChange={(e) => handleFieldChange('field', e.target.value)}
                placeholder="e.g. priority, amount, status"
              />
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">Operator</label>
              <select 
                className="wf-select"
                value={data.operator || 'equals'}
                onChange={(e) => handleFieldChange('operator', e.target.value)}
              >
                <option value="equals">equals (==)</option>
                <option value="not_equals">not_equals (!=)</option>
                <option value="greater_than">greater_than (&gt;)</option>
                <option value="less_than">less_than (&lt;)</option>
                <option value="greater_than_or_equals">greater_than_or_equals (&gt;=)</option>
                <option value="less_than_or_equals">less_than_or_equals (&lt;=)</option>
                <option value="contains">contains</option>
              </select>
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">Expected Value</label>
              <input 
                type="text" 
                className="wf-input font-mono"
                value={data.value !== undefined ? data.value : ''}
                onChange={(e) => handleFieldChange('value', e.target.value)}
                placeholder="e.g. HIGH, 50000, true"
              />
            </div>

            <div className="wf-section-divider">BRANCHING ROUTES</div>
            <p className="wf-hint-text">
              The workflow engine routes execution based on the evaluated condition:
            </p>

            <div className="wf-action-tag-list mt-2">
              <div className="wf-action-port-chip approve">
                <span className="wf-action-chip-label font-bold">TRUE (Match Route)</span>
                <span className="wf-action-chip-id">(TRUE)</span>
              </div>
              <div className="wf-action-port-chip reject">
                <span className="wf-action-chip-label font-bold">FALSE (Default Route)</span>
                <span className="wf-action-chip-id">(FALSE)</span>
              </div>
            </div>
          </>
        )}

        {/* =========================================================================
            6. SWITCH NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'switch' && (
          <>
            <div className="wf-section-divider">EXPRESSION</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Source Entity (Client DB)</label>
              <select 
                className="wf-select"
                value={data.source || (backendEntities[0]?.name || '')}
                onChange={(e) => handleFieldChange('source', e.target.value)}
              >
                <option value="">-- Select Source Entity --</option>
                {backendEntities.map(ent => (
                  <option key={ent.name} value={ent.name}>{ent.name}</option>
                ))}
              </select>
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">Match Field / Column</label>
              {availableFields.length > 0 ? (
                <select 
                  className="wf-select font-mono"
                  value={data.field || ''}
                  onChange={(e) => handleFieldChange('field', e.target.value)}
                >
                  <option value="">-- Select Column --</option>
                  {availableFields.map(f => (
                    <option key={f.name} value={f.name}>{f.name} ({f.type})</option>
                  ))}
                </select>
              ) : (
                <input 
                  type="text" 
                  className="wf-input font-mono"
                  value={data.field || ''}
                  onChange={(e) => handleFieldChange('field', e.target.value)}
                  placeholder="e.g. status, priority"
                />
              )}
            </div>

            <div className="wf-section-divider">CASES (OUTPUT PORTS)</div>
            <div className="wf-tag-list">
              {cases.map((c) => (
                <span key={c} className="wf-tag-item">
                  <code>{c}</code>
                  <button type="button" onClick={() => handleRemoveCase(c)}>×</button>
                </span>
              ))}
            </div>

            <div className="wf-custom-add-row mt-2">
              <input 
                type="text" 
                className="wf-input wf-input-sm uppercase font-mono"
                placeholder="Add Case (e.g. ESCALATED)"
                value={newCaseLabel}
                onChange={(e) => setNewCaseLabel(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddCase()}
              />
              <button type="button" className="wf-btn wf-btn-sm wf-btn-primary" onClick={handleAddCase}>
                <Plus size={13} />
              </button>
            </div>
          </>
        )}

        {/* =========================================================================
            7. PARALLEL NODE PROPERTIES
           ========================================================================= */}
        {nodeType === 'parallel' && (
          <>
            <div className="wf-section-divider">PARALLEL BRANCHES</div>

            <div className="wf-tag-list">
              {branches.map((b) => (
                <span key={b} className="wf-tag-item">
                  <span>{b}</span>
                  <button type="button" onClick={() => handleRemoveBranch(b)}>×</button>
                </span>
              ))}
            </div>

            <div className="wf-custom-add-row mt-2">
              <input 
                type="text" 
                className="wf-input wf-input-sm"
                placeholder="Add branch name"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddBranch()}
              />
              <button type="button" className="wf-btn wf-btn-sm wf-btn-primary" onClick={handleAddBranch}>
                <Plus size={13} />
              </button>
            </div>

            <div className="wf-section-divider">COMPLETION RULE</div>
            <div className="wf-field-group">
              <select 
                className="wf-select"
                value={data.completionRule || 'All'}
                onChange={(e) => handleFieldChange('completionRule', e.target.value)}
              >
                <option value="All">All Branches Complete</option>
                <option value="Any">Any Branch Completes</option>
                <option value="N of M">N of M Branches Complete</option>
              </select>
            </div>
          </>
        )}

        {/* =========================================================================
            8. EMAIL & NOTIFICATION PROPERTIES
           ========================================================================= */}
        {nodeType === 'communication' && (
          <>
            <div className="wf-section-divider">RECIPIENTS</div>

            <div className="wf-field-group">
              <label className="wf-field-label">To (Context Variable or Email)</label>
              <input 
                type="text" 
                className="wf-input font-mono text-xs"
                value={data.to || data.recipient || '{{user.email}}'}
                onChange={(e) => handleFieldChange('to', e.target.value)}
                placeholder="e.g. {{user.email}}, manager@company.com"
              />
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">CC</label>
              <input 
                type="text" 
                className="wf-input font-mono text-xs"
                value={data.cc || ''}
                onChange={(e) => handleFieldChange('cc', e.target.value)}
              />
            </div>

            <div className="wf-section-divider">MESSAGE CONTENT</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Subject / Title</label>
              <input 
                type="text" 
                className="wf-input"
                value={data.subject || data.title || 'Task Action Required: {{workflow.name}}'}
                onChange={(e) => handleFieldChange('subject', e.target.value)}
              />
            </div>

            <div className="wf-field-group">
              <label className="wf-field-label">Message Body</label>
              <textarea 
                className="wf-textarea"
                rows={4}
                value={data.body || data.message || 'Hello {{user.name}}, a task is pending your review.'}
                onChange={(e) => handleFieldChange('body', e.target.value)}
              />
            </div>
          </>
        )}

        {/* =========================================================================
            9. RECORD OPERATIONS (CREATE / UPDATE / READ)
           ========================================================================= */}
        {nodeType === 'record' && (
          <>
            <div className="wf-section-divider">DATABASE OPERATION</div>
            <div className="wf-field-group">
              <label className="wf-field-label">Operation</label>
              <select 
                className="wf-select"
                value={data.subType || data.actionType || 'UPDATE_RECORD'}
                onChange={(e) => {
                  handleFieldChange('subType', e.target.value)
                  handleFieldChange('actionType', e.target.value)
                }}
              >
                <option value="UPDATE_RECORD">UPDATE (DB_UPDATE)</option>
                <option value="CREATE_RECORD">CREATE (DB_CREATE)</option>
                <option value="READ_RECORD">READ (DB_READ)</option>
              </select>
            </div>

            <div className="wf-section-divider">ENTITY TARGET</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Target Entity (Client Table)</label>
              <select 
                className="wf-select"
                value={data.entity || data.table || (backendEntities[0]?.name || '')}
                onChange={(e) => {
                  handleFieldChange('entity', e.target.value)
                  handleFieldChange('table', e.target.value)
                }}
              >
                <option value="">-- Select Client Table --</option>
                {backendEntities.map(ent => (
                  <option key={ent.name} value={ent.name}>{ent.name}</option>
                ))}
              </select>
            </div>

            {(data.subType === 'UPDATE_RECORD' || data.subType === 'READ_RECORD') && (
              <div className="wf-field-group">
                <label className="wf-field-label">Record Identifier</label>
                <input 
                  type="text" 
                  className="wf-input font-mono text-xs"
                  value={data.recordId || '{{workflow.entity_id}}'}
                  onChange={(e) => handleFieldChange('recordId', e.target.value)}
                  placeholder="e.g. {{workflow.entity_id}}"
                />
              </div>
            )}

            {data.subType !== 'READ_RECORD' ? (
              <>
                <div className="wf-section-divider">FIELD MAPPINGS</div>
                <div className="wf-field-mapping-list">
                  {fieldMappings.map((m, idx) => (
                    <div key={idx} className="wf-mapping-row">
                      <span className="wf-map-key">{m.field}</span>
                      <span className="wf-map-arrow">➔</span>
                      <span className="wf-map-val">{m.value}</span>
                      <button 
                        className="wf-mapping-del"
                        onClick={() => handleRemoveFieldMapping(idx)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>

                <div className="wf-add-mapping-box">
                  {availableFields.length > 0 ? (
                    <select
                      className="wf-select text-xs font-mono"
                      value={newFieldKey}
                      onChange={(e) => setNewFieldKey(e.target.value)}
                    >
                      <option value="">-- Select Column --</option>
                      {availableFields.map(f => (
                        <option key={f.name} value={f.name}>{f.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input 
                      type="text" 
                      className="wf-input text-xs" 
                      placeholder="Field name (e.g. status)"
                      value={newFieldKey}
                      onChange={(e) => setNewFieldKey(e.target.value)}
                    />
                  )}
                  <input 
                    type="text" 
                    className="wf-input text-xs" 
                    placeholder="Value (e.g. APPROVED)"
                    value={newFieldValue}
                    onChange={(e) => setNewFieldValue(e.target.value)}
                  />
                  <button 
                    className="wf-add-action-btn"
                    onClick={handleAddFieldMapping}
                  >
                    Add Mapping
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="wf-section-divider">RETRIEVE FIELDS</div>
                <div className="wf-tag-list">
                  {retrieveFields.map((f) => (
                    <span key={f} className="wf-tag-item">
                      <span>{f}</span>
                      <button 
                        className="wf-tag-remove" 
                        onClick={() => handleRemoveRetrieveField(f)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>

                <div className="wf-add-action-box">
                  {availableFields.length > 0 ? (
                    <select
                      className="wf-select text-xs font-mono"
                      value={newRetrieveField}
                      onChange={(e) => setNewRetrieveField(e.target.value)}
                    >
                      <option value="">-- Select Column --</option>
                      {availableFields.map(f => (
                        <option key={f.name} value={f.name}>{f.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input 
                      type="text" 
                      className="wf-input text-xs" 
                      placeholder="Field to read (e.g. status)"
                      value={newRetrieveField}
                      onChange={(e) => setNewRetrieveField(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddRetrieveField()}
                    />
                  )}
                  <button 
                    className="wf-add-action-btn"
                    onClick={handleAddRetrieveField}
                  >
                    Add Field
                  </button>
                </div>

                <div className="wf-field-group mt-3">
                  <label className="wf-field-label">Output Variable Name</label>
                  <input 
                    type="text" 
                    className="wf-input font-mono"
                    value={data.outputVariable || 'entity_data'}
                    onChange={(e) => handleFieldChange('outputVariable', e.target.value)}
                  />
                </div>
              </>
            )}
          </>
        )}

        {/* =========================================================================
            10. API CALL / DATABASE ACTION PROPERTIES
           ========================================================================= */}
        {nodeType === 'action' && (
          <>
            {data.subType === 'API' ? (
              <>
                <div className="wf-section-divider">REST REQUEST</div>

                <div className="wf-field-group">
                  <label className="wf-field-label">HTTP Method</label>
                  <select 
                    className="wf-select"
                    value={data.method || 'POST'}
                    onChange={(e) => handleFieldChange('method', e.target.value)}
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="PATCH">PATCH</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>

                <div className="wf-field-group">
                  <label className="wf-field-label">URL Endpoint</label>
                  <input 
                    type="text" 
                    className="wf-input font-mono text-xs"
                    value={data.url || 'https://api.internal/v1/event'}
                    onChange={(e) => handleFieldChange('url', e.target.value)}
                  />
                </div>

                <div className="wf-field-group">
                  <label className="wf-field-label">Headers</label>
                  <input 
                    type="text" 
                    className="wf-input font-mono text-xs"
                    value={data.headers || 'Content-Type: application/json'}
                    onChange={(e) => handleFieldChange('headers', e.target.value)}
                  />
                </div>

                <div className="wf-field-group">
                  <label className="wf-field-label">Request Body (JSON)</label>
                  <textarea 
                    className="wf-textarea font-mono text-xs"
                    rows={4}
                    value={data.body || '{\n  "entity_id": "{{workflow.entity_id}}"\n}'}
                    onChange={(e) => handleFieldChange('body', e.target.value)}
                  />
                </div>
              </>
            ) : (
              <>
                <div className="wf-section-divider">DATABASE OPERATION</div>

                <div className="wf-field-group">
                  <label className="wf-field-label">Operation</label>
                  <select 
                    className="wf-select"
                    value={data.operation || 'Stored Procedure'}
                    onChange={(e) => handleFieldChange('operation', e.target.value)}
                  >
                    <option value="Stored Procedure">Stored Procedure</option>
                    <option value="Query">Query</option>
                    <option value="Transactional Action">Transactional Action</option>
                  </select>
                </div>

                <div className="wf-field-group">
                  <label className="wf-field-label">Procedure / Entity Name</label>
                  <input 
                    type="text" 
                    className="wf-input font-mono"
                    value={data.procedure || 'update_status'}
                    onChange={(e) => handleFieldChange('procedure', e.target.value)}
                  />
                </div>

                <div className="wf-field-group">
                  <label className="wf-field-label">Parameters (Mapping)</label>
                  <textarea 
                    className="wf-textarea font-mono text-xs"
                    rows={3}
                    value={data.parameters || 'entity_id = {{workflow.entity_id}}\nuser_id = {{current_user.id}}'}
                    onChange={(e) => handleFieldChange('parameters', e.target.value)}
                  />
                </div>
              </>
            )}
          </>
        )}

        {/* Delete Node Action */}
        <div className="wf-delete-section">
          <button className="wf-delete-btn" onClick={() => onDeleteNode(selectedNode.id)}>
            <Trash2 size={13} />
            <span>Delete Selected Node</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
