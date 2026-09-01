import React, { useState, useEffect } from 'react'
import {
  Sliders,
  Trash2,
  AlertCircle,
  Plus
} from 'lucide-react'
import { workflowStorage } from '../services/workflowStorage'
import TaskDetailsSection from './properties/TaskDetailsSection'
import AssignmentSection from './properties/AssignmentSection'
import ApprovalSection from './properties/ApprovalSection'
import ConditionSection from './properties/ConditionSection'
import NotificationSection from './properties/NotificationSection'
import DbActionSection from './properties/DbActionSection'

export default function PropertiesPanel({
  selectedNode,
  selectedEdge,
  workflowConnectionId = null,
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
          workflowStorage.getMetadataRoles(workflowConnectionId),
          workflowStorage.getMetadataUsers(workflowConnectionId),
          workflowStorage.getMetadataDepartments(workflowConnectionId),
          workflowStorage.getMetadataTables(workflowConnectionId),
          workflowStorage.getMetadataStatuses(null, workflowConnectionId),
          workflowStorage.getMetadataActions()
        ])

        if (isMounted) {
          const roles = results[0].status === 'fulfilled' && Array.isArray(results[0].value) ? results[0].value : []
          const users = results[1].status === 'fulfilled' && Array.isArray(results[1].value) ? results[1].value : []
          const depts = results[2].status === 'fulfilled' && Array.isArray(results[2].value) ? results[2].value : []
          const entities = results[3].status === 'fulfilled' && Array.isArray(results[3].value) ? results[3].value : []
          const statuses = results[4].status === 'fulfilled' && Array.isArray(results[4].value) ? results[4].value : []
          const actions = results[5].status === 'fulfilled' && Array.isArray(results[5].value) ? results[5].value : []

          setBackendRoles(roles.map(r => ({ id: String(r.id), name: r.name })))
          setBackendUsers(users.map(u => ({ id: String(u.id), name: u.name || `User ${u.id}` })))
          setBackendDepartments(depts.map(d => ({ id: String(d.id), name: d.name || `Department ${d.id}` })))
          setBackendEntities(entities.map(e => ({ name: e.name || e.table_name })))
          setBackendStatuses(statuses.map(s => ({ id: String(s.id), name: s.name, type: s.type })))
          setBackendActions(actions.map(a => ({ id: a.action_code || a.id, label: a.name || a.label })))
          setMetadataError(null)
        }
      } catch (err) {
        if (isMounted) {
          setMetadataError('Client Database unavailable. Dynamic metadata cannot be loaded.')
        }
      }
    }

    fetchMasterData()
    return () => { isMounted = false }
  }, [workflowConnectionId])

  // Dynamic field introspection for the selected entity
  const currentEntity = selectedNode?.data?.entity || selectedNode?.data?.table || ''
  useEffect(() => {
    let isMounted = true
    if (currentEntity && currentEntity !== 'Entity') {
      workflowStorage.getMetadataEntityFields(currentEntity, workflowConnectionId)
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
  }, [currentEntity, workflowConnectionId])

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
            <button
              className="wf-btn wf-btn-danger wf-btn-full"
              onClick={() => onDeleteEdge(selectedEdge.id)}
            >
              <Trash2 size={14} />
              <span>Delete Connection</span>
            </button>
          </div>
        </div>
      </aside>
    )
  }

  // 3. Node Properties Helpers
  const nodeType = selectedNode.type || 'generic'
  const data = selectedNode.data || {}
  const name = data.name || data.label || 'Node'
  const description = data.description || ''

  const handleFieldChange = (field, value) => {
    onUpdateNodeData(selectedNode.id, { ...data, [field]: value })
  }

  const handleFieldsChange = (fieldsObj) => {
    onUpdateNodeData(selectedNode.id, { ...data, ...fieldsObj })
  }

  const handleNameChange = (val) => {
    onUpdateNodeData(selectedNode.id, { ...data, name: val, label: val })
  }

  const handleDescriptionChange = (val) => {
    onUpdateNodeData(selectedNode.id, { ...data, description: val })
  }

  const assignment = data.assignment || {}
  const assignmentType = assignment.type || 'role'

  const handleAssignmentTypeChange = (type) => {
    onUpdateNodeData(selectedNode.id, {
      ...data,
      assignment: { ...assignment, type }
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
      if (next.length === 0) next = [visId]
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
      if (next.length === 0) next = [actionId]
    } else {
      next = [...activeActions, actionId]
    }
    handleFieldChange('actions', next)
  }

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

  // Switch cases
  const cases = Array.isArray(data.cases) ? data.cases : ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED']

  const handleAddCase = () => {
    if (!newCaseLabel.trim()) return
    const formatted = newCaseLabel.trim().toUpperCase()
    if (!cases.includes(formatted)) {
      handleFieldChange('cases', [...cases, formatted])
    }
    setNewCaseLabel('')
  }

  const handleRemoveCase = (caseItem) => {
    if (cases.length <= 1) return
    handleFieldChange('cases', cases.filter(c => c !== caseItem))
  }

  // Parallel branches
  const branches = Array.isArray(data.branches) ? data.branches : ['Branch A', 'Branch B']

  const handleAddBranch = () => {
    if (!newBranchName.trim()) return
    if (!branches.includes(newBranchName.trim())) {
      handleFieldChange('branches', [...branches, newBranchName.trim()])
    }
    setNewBranchName('')
  }

  const handleRemoveBranch = (branch) => {
    if (branches.length <= 1) return
    handleFieldChange('branches', branches.filter(b => b !== branch))
  }

  // Record mappings
  const fieldMappings = Array.isArray(data.fieldMappings) ? data.fieldMappings : []
  const handleAddFieldMapping = () => {
    if (!newFieldKey.trim()) return
    const updated = [...fieldMappings, { field: newFieldKey.trim(), value: newFieldValue.trim() }]
    handleFieldChange('fieldMappings', updated)
    setNewFieldKey('')
    setNewFieldValue('')
  }

  const handleRemoveFieldMapping = (idx) => {
    const updated = fieldMappings.filter((_, i) => i !== idx)
    handleFieldChange('fieldMappings', updated)
  }

  // Retrieve fields
  const retrieveFields = Array.isArray(data.retrieveFields) ? data.retrieveFields : (data.fields || ['id', 'status', 'name'])
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

  return (
    <aside className="wf-properties-panel">
      <div className="wf-properties-header">
        <Sliders size={14} color="#818cf8" />
        <span>PROPERTIES</span>
      </div>
      <div className="wf-prop-subtitle">
        {selectedNode.type?.toUpperCase()} NODE • {selectedNode.id}
      </div>

      <div className="wf-properties-scroll">
        {/* COMMON TASK DETAILS */}
        <TaskDetailsSection
          selectedNode={selectedNode}
          data={data}
          name={name}
          description={description}
          handleFieldChange={handleFieldChange}
          handleNameChange={handleNameChange}
          handleDescriptionChange={handleDescriptionChange}
          onUpdateNodeData={onUpdateNodeData}
        />

        {/* START NODE TRIGGER */}
        {nodeType === 'start' && (
          <>
            <div className="wf-section-divider">TRIGGER CONFIGURATION</div>
            <div className="wf-field-group">
              <label className="wf-field-label">Trigger Type</label>
              <select
                className="wf-select"
                value={data.triggerType || 'Manual'}
                onChange={(e) => handleFieldChange('triggerType', e.target.value)}
              >
                <option value="Manual">Manual Trigger (User / API)</option>
                <option value="Database">Database Event (Insert / Update)</option>
                <option value="Schedule">Scheduled Cron Job</option>
                <option value="Webhook">Inbound Webhook</option>
              </select>
            </div>
          </>
        )}

        {/* END NODE OUTCOME */}
        {nodeType === 'end' && (
          <>
            <div className="wf-section-divider">FINAL OUTCOME</div>
            <div className="wf-field-group">
              <label className="wf-field-label">Terminal Outcome</label>
              <select
                className="wf-select"
                value={data.outcome || 'APPROVED'}
                onChange={(e) => handleFieldChange('outcome', e.target.value)}
              >
                <option value="APPROVED">APPROVED (Success)</option>
                <option value="REJECTED">REJECTED (Terminated)</option>
                <option value="CANCELLED">CANCELLED</option>
                <option value="COMPLETED">COMPLETED (Generic)</option>
              </select>
            </div>
          </>
        )}

        {/* USER TASK */}
        {(nodeType === 'userTask' || nodeType === 'generic') && (
          <AssignmentSection
            assignmentType={assignmentType}
            handleAssignmentTypeChange={handleAssignmentTypeChange}
            assignment={assignment}
            backendRoles={backendRoles}
            backendUsers={backendUsers}
            backendDepartments={backendDepartments}
            handleRoleSelect={handleRoleSelect}
            handleUserSelect={handleUserSelect}
            handleDepartmentSelect={handleDepartmentSelect}
            onUpdateNodeData={onUpdateNodeData}
            selectedNode={selectedNode}
            data={data}
            activeVisibility={activeVisibility}
            handleToggleVisibility={handleToggleVisibility}
          />
        )}

        {/* APPROVAL */}
        {nodeType === 'approval' && (
          <ApprovalSection
            data={data}
            backendRoles={backendRoles}
            actions={actions}
            newActionLabel={newActionLabel}
            setNewActionLabel={setNewActionLabel}
            newActionId={newActionId}
            setNewActionId={setNewActionId}
            handleAddAction={handleAddAction}
            handleRemoveAction={handleRemoveAction}
            handleFieldChange={handleFieldChange}
          />
        )}

        {/* CONDITION & SWITCH */}
        {(nodeType === 'condition' || nodeType === 'switch') && (
          <ConditionSection
            nodeType={nodeType}
            data={data}
            handleFieldChange={handleFieldChange}
            cases={cases}
            newCaseLabel={newCaseLabel}
            setNewCaseLabel={setNewCaseLabel}
            handleAddCase={handleAddCase}
            handleRemoveCase={handleRemoveCase}
          />
        )}

        {/* PARALLEL */}
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
          </>
        )}

        {/* COMMUNICATION */}
        {nodeType === 'communication' && (
          <NotificationSection
            data={data}
            name={name}
            backendRoles={backendRoles}
            backendUsers={backendUsers}
            availableFields={availableFields}
            handleFieldChange={handleFieldChange}
            handleFieldsChange={handleFieldsChange}
          />
        )}

        {/* RECORD & ACTION (DB) */}
        {(nodeType === 'record' || nodeType === 'action') && (
          <DbActionSection
            nodeType={nodeType}
            data={data}
            name={name}
            backendEntities={backendEntities}
            availableFields={availableFields}
            fieldMappings={fieldMappings}
            newFieldKey={newFieldKey}
            setNewFieldKey={setNewFieldKey}
            newFieldValue={newFieldValue}
            setNewFieldValue={setNewFieldValue}
            handleAddFieldMapping={handleAddFieldMapping}
            handleRemoveFieldMapping={handleRemoveFieldMapping}
            retrieveFields={retrieveFields}
            newRetrieveField={newRetrieveField}
            setNewRetrieveField={setNewRetrieveField}
            handleAddRetrieveField={handleAddRetrieveField}
            handleRemoveRetrieveField={handleRemoveRetrieveField}
            handleFieldChange={handleFieldChange}
            handleFieldsChange={handleFieldsChange}
          />
        )}

        {/* DELETE NODE ACTION */}
        <div className="wf-delete-section">
          <button
            type="button"
            className="wf-btn wf-btn-danger wf-btn-full"
            onClick={() => onDeleteNode(selectedNode.id)}
          >
            <Trash2 size={14} />
            <span>Delete Node</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
