import React, { memo } from 'react'
import { Handle, Position, getBezierPath, BaseEdge, EdgeLabelRenderer } from '@xyflow/react'
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
  Copy, 
  Trash2
} from 'lucide-react'

// Quick Node Action Bar (Duplicate / Delete)
function NodeActionBar({ nodeId, onDuplicate, onDelete }) {
  return (
    <div className="wf-node-action-bar nodrag">
      {onDuplicate && (
        <button 
          className="wf-node-act-btn" 
          onClick={(e) => {
            e.stopPropagation()
            onDuplicate(nodeId)
          }} 
          title="Duplicate Node"
        >
          <Copy size={11} />
        </button>
      )}
      {onDelete && (
        <button 
          className="wf-node-act-btn wf-act-delete" 
          onClick={(e) => {
            e.stopPropagation()
            onDelete(nodeId)
          }} 
          title="Delete Node"
        >
          <Trash2 size={11} />
        </button>
      )}
    </div>
  )
}

// =========================================================================
// 1. START NODE (Boundary Node - Workflow Entry Point)
// =========================================================================
export const StartNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Workflow Start'
  const description = data?.description || 'Entry point of the workflow'
  const trigger = data?.trigger || 'Workflow Activated'

  return (
    <div className={`wf-card wf-card-start ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-green">
          <PlayCircle size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-boundary">START</div>
          <div className="wf-title">{title}</div>
          <div className="wf-card-desc">{description}</div>
        </div>
      </div>

      <div className="wf-start-status-row">
        <span className="wf-status-active-pill">Status: ACTIVE</span>
        <span className="wf-trigger-pill">{trigger}</span>
      </div>

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-port-start-out">
          <span className="wf-port-name font-mono text-xs">WORKFLOW_INITIALIZED</span>
          <Handle 
            type="source" 
            position={Position.Bottom} 
            id="WORKFLOW_INITIALIZED" 
            className="wf-handle wf-handle-green" 
          />
          <Handle type="source" position={Position.Right} id="output" className="wf-handle wf-handle-green opacity-0 pointer-events-none" />
          <Handle type="source" position={Position.Bottom} id="SUBMIT" className="wf-handle wf-handle-green opacity-0 pointer-events-none" />
        </div>
      </div>
    </div>
  )
})

// =========================================================================
// 2. END NODE (Boundary Node - Workflow Termination Point)
// =========================================================================
export const EndNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Workflow End'
  const description = data?.description || 'Workflow terminal point'
  const outcome = data?.outcome || ''

  return (
    <div className={`wf-card wf-card-end ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle 
        type="target" 
        position={Position.Left} 
        id="input" 
        className="wf-handle wf-handle-emerald" 
      />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-emerald">
          <StopCircle size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-boundary">END</div>
          <div className="wf-title">{title}</div>
          <div className="wf-card-desc">{description}</div>
        </div>
      </div>

      {outcome && (
        <div className="wf-end-outcome-row">
          <span className="wf-end-outcome-pill">
            Outcome: {outcome}
          </span>
        </div>
      )}
    </div>
  )
})

// =========================================================================
// 3. USER TASK NODE (Human Checkpoint - Execution Node)
// =========================================================================
export const UserTaskNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'User Task'
  const description = data?.description || ''

  // Assignment from database model
  const assignment = data?.assignment || {}
  const assignmentType = (assignment.type || data?.assignmentType || 'role').toUpperCase()
  const assignmentTarget = assignment.roleName || assignment.userName || assignment.departmentName || 
                           data?.role || data?.user || data?.department || 'Unassigned'

  // Visibility tags (Everyone, Owner, Approver)
  const visibility = Array.isArray(data?.visibility) ? data.visibility : ['APPROVER']

  // 5 Standard Actions
  const rawActions = Array.isArray(data?.actions) && data.actions.length > 0
    ? data.actions
    : ['APPROVE', 'REJECT']

  const actions = rawActions.map(a => {
    if (typeof a === 'string') {
      const id = a.toUpperCase()
      let label = id.replace(/_/g, ' ')
      if (id === 'SAVE_DRAFT') label = 'Save Draft'
      if (id === 'SUBMIT') label = 'Submit'
      if (id === 'APPROVE') label = 'Approve'
      if (id === 'REJECT') label = 'Reject'
      if (id === 'FORCE_APPROVE') label = 'Force Approve'
      return { id, label }
    }
    return { id: a.id || a.label, label: a.label || a.id }
  })

  return (
    <div className={`wf-card wf-card-task ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-blue">
          <User size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-execution">USER TASK</div>
          <div className="wf-title">{title}</div>
          {description && <div className="wf-card-desc">{description}</div>}
        </div>
      </div>

      <div className="wf-assignee-banner">
        <span className="wf-assign-mode">{assignmentType}:</span>
        <span className="wf-assign-value font-semibold">{String(assignmentTarget)}</span>
      </div>

      {visibility.length > 0 && (
        <div className="wf-visibility-tag-row">
          <span className="wf-vis-label">Visibility:</span>
          {visibility.map(v => (
            <span key={v} className="wf-vis-pill">{v}</span>
          ))}
        </div>
      )}

      <div className="wf-node-section-label">CONFIGURED ACTIONS:</div>

      <div className="wf-actions-badge-list">
        {actions.map((act) => {
          const actionId = act.id
          const label = act.label
          let pillClass = 'wf-action-pill-default'
          if (actionId === 'APPROVE') pillClass = 'wf-action-pill-approve'
          else if (actionId === 'REJECT') pillClass = 'wf-action-pill-reject'
          else if (actionId === 'FORCE_APPROVE') pillClass = 'wf-action-pill-force'
          else if (actionId === 'SUBMIT') pillClass = 'wf-action-pill-submit'
          else if (actionId === 'SAVE_DRAFT') pillClass = 'wf-action-pill-draft'

          return (
            <span key={actionId} className={`wf-action-badge-pill ${pillClass}`}>
              {label}
            </span>
          )
        })}
      </div>

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-port-next">
          <span className="wf-port-name font-semibold">Next</span>
          <Handle 
            type="source" 
            position={Position.Right} 
            id="output" 
            className="wf-handle wf-handle-blue" 
          />
          <Handle type="source" position={Position.Right} id="APPROVE" className="wf-handle wf-handle-blue opacity-0 pointer-events-none" />
          <Handle type="source" position={Position.Bottom} id="REJECT" className="wf-handle wf-handle-blue opacity-0 pointer-events-none" />
          <Handle type="source" position={Position.Right} id="SUBMIT" className="wf-handle wf-handle-blue opacity-0 pointer-events-none" />
          <Handle type="source" position={Position.Right} id="SAVE_DRAFT" className="wf-handle wf-handle-blue opacity-0 pointer-events-none" />
        </div>
      </div>
    </div>
  )
})

// =========================================================================
// 4. APPROVAL NODE (Execution Node)
// =========================================================================
export const ApprovalNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Approval'
  const role = data?.role || data?.user || data?.department || 'Function Head'
  const assignmentType = data?.assignmentType || 'Role'

  // Dynamic actions array for outcomes (Approve, Reject, Force Approve)
  const rawActions = data?.actions || [
    { id: 'APPROVE', label: 'Approve', color: '#16a34a' },
    { id: 'REJECT', label: 'Reject', color: '#ef4444' }
  ]
  const actions = rawActions.map(a => {
    if (typeof a === 'string') {
      let label = a.replace(/_/g, ' ')
      if (a === 'APPROVE') return { id: 'APPROVE', label: 'Approve' }
      if (a === 'REJECT') return { id: 'REJECT', label: 'Reject' }
      if (a === 'FORCE_APPROVE') return { id: 'FORCE_APPROVE', label: 'Force Approve' }
      return { id: a, label }
    }
    return a
  })

  return (
    <div className={`wf-card wf-card-approval ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-purple">
          <UserCheck size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-execution">EXECUTION NODE</div>
          <div className="wf-title">{title}</div>
          <div className="wf-assignee-banner">
            <span className="wf-assign-mode">{assignmentType}:</span>
            <span className="wf-assign-value font-semibold">{String(role).replace(/_/g, ' ')}</span>
          </div>
        </div>
      </div>

      <div className="wf-node-section-label">DECISION OUTCOMES:</div>

      <div className="wf-port-list">
        {actions.map((act) => {
          const actionId = act.id || act.label
          const label = act.label || act.id
          const isApprove = actionId === 'APPROVE'
          const isReject = actionId === 'REJECT'
          const isForce = actionId === 'FORCE_APPROVE'

          let badgeClass = 'wf-outcome-neutral'
          let handleClass = 'wf-handle-action'
          if (isApprove) {
            badgeClass = 'wf-outcome-approve'
            handleClass = 'wf-handle-approve'
          } else if (isReject) {
            badgeClass = 'wf-outcome-reject'
            handleClass = 'wf-handle-reject'
          } else if (isForce) {
            badgeClass = 'wf-outcome-force'
            handleClass = 'wf-handle-force'
          }

          return (
            <div key={actionId} className={`wf-port-row wf-port-out ${badgeClass}`}>
              <span className="wf-port-name">{label}</span>
              <Handle 
                type="source" 
                position={Position.Right} 
                id={actionId} 
                className={`wf-handle ${handleClass}`} 
              />
            </div>
          )
        })}
      </div>
    </div>
  )
})

// =========================================================================
// 5. CONDITION / ROUTING NODE (Evaluates generic field / operator / value)
// =========================================================================
export const ConditionNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Condition'
  const description = data?.description || ''
  
  const field = data?.field || data?.config?.field || 'priority'
  const operator = data?.operator || data?.config?.operator || 'equals'
  const value = data?.value !== undefined ? String(data?.value) : (data?.config?.value !== undefined ? String(data?.config?.value) : 'HIGH')
  const exprDisplay = `${field} ${operator} ${value}`

  return (
    <div className={`wf-card wf-card-condition ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-amber">
          <GitFork size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-control">CONDITION / ROUTER</div>
          <div className="wf-title">{title}</div>
          {description && <div className="wf-card-desc">{description}</div>}
        </div>
      </div>

      <div className="wf-eval-expr-box" title={`Condition: ${exprDisplay}`}>
        <span className="wf-eval-label">IF:</span>
        <code>{exprDisplay}</code>
      </div>

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-outcome-approve">
          <span className="wf-port-name font-bold text-xs" style={{ color: '#10b981' }}>TRUE (Match)</span>
          <Handle 
            type="source" 
            position={Position.Right} 
            id="TRUE" 
            className="wf-handle wf-handle-approve" 
          />
        </div>
        <div className="wf-port-row wf-port-out wf-outcome-reject">
          <span className="wf-port-name font-bold text-xs" style={{ color: '#ef4444' }}>FALSE (Default)</span>
          <Handle 
            type="source" 
            position={Position.Right} 
            id="FALSE" 
            className="wf-handle wf-handle-reject" 
          />
        </div>
      </div>
    </div>
  )
})

// =========================================================================
// 6. SWITCH NODE (Control-Flow Node)
// =========================================================================
export const SwitchNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Switch'
  const expr = data?.expression || `${data?.source || 'Entity'}.${data?.field || 'Status'}`
  const cases = Array.isArray(data?.cases) ? data.cases : ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED']
  const hasDefault = data?.hasDefault !== false

  return (
    <div className={`wf-card wf-card-switch ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-amber">
          <Sliders size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-control">CONTROL-FLOW NODE</div>
          <div className="wf-title">{title}</div>
        </div>
      </div>

      <div className="wf-eval-expr-box" title={expr}>
        <span className="wf-eval-label">MATCH:</span>
        <code>{expr}</code>
      </div>

      <div className="wf-port-list">
        {cases.map((c) => {
          const caseId = typeof c === 'object' ? c.id || c.value : c
          const label = typeof c === 'object' ? c.label || c.value : c
          return (
            <div key={caseId} className="wf-port-row wf-port-out">
              <span className="wf-port-name font-mono">{label}</span>
              <Handle type="source" position={Position.Right} id={caseId} className="wf-handle wf-handle-amber" />
            </div>
          )
        })}
        {hasDefault && (
          <div className="wf-port-row wf-port-out wf-port-default">
            <span className="wf-port-name font-mono text-muted">DEFAULT</span>
            <Handle type="source" position={Position.Right} id="DEFAULT" className="wf-handle wf-handle-neutral" />
          </div>
        )}
      </div>
    </div>
  )
})

// =========================================================================
// 7. PARALLEL NODE (Control-Flow Node)
// =========================================================================
export const ParallelNode = memo(({ id, data, selected }) => {
  const title = data?.label || data?.name || 'Parallel'
  const branches = Array.isArray(data?.branches) ? data.branches : ['Branch 1', 'Branch 2']
  const completionRule = data?.completionRule || 'All'

  return (
    <div className={`wf-card wf-card-parallel ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-amber">
          <Layers size={16} color="#ffffff" strokeWidth={2.5} />
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-control">CONTROL-FLOW NODE</div>
          <div className="wf-title">{title}</div>
          <div className="wf-subtitle-row">
            <span className="wf-badge-sub">Join: {completionRule}</span>
          </div>
        </div>
      </div>

      <div className="wf-port-list">
        {branches.map((b, idx) => {
          const branchId = typeof b === 'object' ? b.id : `branch-${idx + 1}`
          const label = typeof b === 'object' ? b.name || b.label : b
          return (
            <div key={branchId} className="wf-port-row wf-port-out">
              <span className="wf-port-name">{label}</span>
              <Handle type="source" position={Position.Right} id={branchId} className="wf-handle wf-handle-amber" />
            </div>
          )
        })}
      </div>
    </div>
  )
})

// =========================================================================
// 8. SEND EMAIL & NOTIFICATION NODES (Execution Nodes)
// =========================================================================
export const CommunicationNode = memo(({ id, data, selected }) => {
  const isEmail = data?.subType === 'EMAIL' || data?.type === 'sendEmail'
  const title = data?.label || data?.name || (isEmail ? 'Send Email' : 'Notification')
  const recipient = isEmail ? (data?.to || '{{user.email}}') : (data?.recipient || 'Assigned Role')
  const subject = data?.subject || data?.title || ''

  return (
    <div className={`wf-card wf-card-comm ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-indigo">
          {isEmail ? <Mail size={16} color="#ffffff" /> : <Bell size={16} color="#ffffff" />}
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-execution">EXECUTION NODE</div>
          <div className="wf-title">{title}</div>
          <div className="wf-info-pill-row">
            <span className="wf-pill-label">To:</span>
            <span className="wf-pill-value truncate max-w-[150px]">{recipient}</span>
          </div>
        </div>
      </div>

      {subject && <div className="wf-card-desc truncate font-medium">"{subject}"</div>}

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-port-success">
          <span className="wf-port-name">Success</span>
          <Handle type="source" position={Position.Right} id="SUCCESS" className="wf-handle wf-handle-approve" />
        </div>
        <div className="wf-port-row wf-port-out wf-port-failure">
          <span className="wf-port-name">Failure</span>
          <Handle type="source" position={Position.Right} id="FAILURE" className="wf-handle wf-handle-reject" />
        </div>
      </div>
    </div>
  )
})

// =========================================================================
// 9. RECORD OPERATIONS (Create / Update / Read Record) (Execution Nodes)
// =========================================================================
export const RecordNode = memo(({ id, data, selected }) => {
  const opType = (data?.subType || data?.type || 'UPDATE_RECORD').toUpperCase()
  const title = data?.label || data?.name || 'Record Operation'
  const entity = data?.entity || 'Entity'
  const recordId = data?.recordId || data?.record || '{{workflow.entity_id}}'

  let icon = <RefreshCw size={15} color="#ffffff" />
  let opBadge = 'UPDATE RECORD'
  if (opType.includes('CREATE')) {
    icon = <FilePlus size={15} color="#ffffff" />
    opBadge = 'CREATE RECORD'
  } else if (opType.includes('READ')) {
    icon = <FileSearch size={15} color="#ffffff" />
    opBadge = 'READ RECORD'
  }

  return (
    <div className={`wf-card wf-card-data ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-cyan">
          {icon}
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-execution">EXECUTION NODE</div>
          <div className="wf-title">{title}</div>
          <div className="wf-subtitle-row">
            <span className="wf-badge-sub font-semibold">{opBadge}</span>
            <span className="wf-badge-sub">Entity: {entity}</span>
          </div>
        </div>
      </div>

      <div className="wf-card-body">
        <div className="wf-info-pill-row">
          <span className="wf-pill-label">Target:</span>
          <span className="wf-pill-value truncate font-mono text-xs">{recordId}</span>
        </div>
      </div>

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-port-success">
          <span className="wf-port-name">Success</span>
          <Handle type="source" position={Position.Right} id="SUCCESS" className="wf-handle wf-handle-approve" />
        </div>
        <div className="wf-port-row wf-port-out wf-port-failure">
          <span className="wf-port-name">Failure</span>
          <Handle type="source" position={Position.Right} id="FAILURE" className="wf-handle wf-handle-reject" />
        </div>
        <Handle type="source" position={Position.Right} id="output" className="wf-handle wf-handle-approve opacity-0 pointer-events-none" />
        <Handle type="source" position={Position.Right} id="NEXT" className="wf-handle wf-handle-approve opacity-0 pointer-events-none" />
      </div>
    </div>
  )
})

// =========================================================================
// 10. ACTION NODES (API Call / Database Action) (Execution Nodes)
// =========================================================================
export const ActionNode = memo(({ id, data, selected }) => {
  const isApi = data?.subType === 'API' || data?.type === 'apiCall' || data?.type === 'action'
  const title = data?.label || data?.name || (isApi ? 'API Call' : 'Database Action')
  const methodOrOp = isApi ? (data?.method || 'POST') : (data?.operation || 'Stored Procedure')
  const target = isApi ? (data?.url || 'https://api.internal/v1/event') : (data?.procedure || data?.entity || 'update_status')

  return (
    <div className={`wf-card wf-card-action ${selected ? 'wf-selected' : ''}`}>
      <NodeActionBar nodeId={id} onDuplicate={data?.onDuplicate} onDelete={data?.onDelete} />
      <Handle type="target" position={Position.Left} id="input" className="wf-handle" />

      <div className="wf-card-header">
        <div className="wf-icon-badge wf-badge-teal">
          {isApi ? <Globe size={15} color="#ffffff" /> : <Database size={15} color="#ffffff" />}
        </div>
        <div className="wf-header-texts">
          <div className="wf-category-tag wf-tag-execution">EXECUTION NODE</div>
          <div className="wf-title">{title}</div>
          <div className="wf-api-method-row">
            <span className="wf-method-badge">{methodOrOp}</span>
            <span className="wf-api-url-text truncate">{target}</span>
          </div>
        </div>
      </div>

      <div className="wf-port-list">
        <div className="wf-port-row wf-port-out wf-port-success">
          <span className="wf-port-name">Success</span>
          <Handle type="source" position={Position.Right} id="SUCCESS" className="wf-handle wf-handle-approve" />
        </div>
        <div className="wf-port-row wf-port-out wf-port-failure">
          <span className="wf-port-name">Failure</span>
          <Handle type="source" position={Position.Right} id="FAILURE" className="wf-handle wf-handle-reject" />
        </div>
        <Handle type="source" position={Position.Right} id="output" className="wf-handle wf-handle-approve opacity-0 pointer-events-none" />
        <Handle type="source" position={Position.Right} id="NEXT" className="wf-handle wf-handle-approve opacity-0 pointer-events-none" />
      </div>
    </div>
  )
})

// =========================================================================
// 11. WORKFLOW EDGE (BEZIER WITH SOURCE HANDLE OUTCOME PILL)
// =========================================================================
export const WorkflowEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  sourceHandleId,
  selected
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetPosition,
    targetX,
    targetY,
  })

  // Display label priority: edge data label -> sourceHandleId
  const label = data?.label || sourceHandleId || ''
  const lower = String(label).toLowerCase()

  let edgeClass = 'wf-edge-default'
  let labelClass = 'wf-edge-pill-default'

  if (lower.includes('approve') && !lower.includes('force')) {
    edgeClass = 'wf-edge-approve'
    labelClass = 'wf-edge-pill-approve'
  } else if (lower.includes('reject') || lower === 'false' || lower === 'failure') {
    edgeClass = 'wf-edge-reject'
    labelClass = 'wf-edge-pill-reject'
  } else if (lower.includes('force')) {
    edgeClass = 'wf-edge-force'
    labelClass = 'wf-edge-pill-force'
  } else if (lower === 'true' || lower === 'success') {
    edgeClass = 'wf-edge-true'
    labelClass = 'wf-edge-pill-true'
  } else if (lower.includes('submit') || lower.includes('resubmit')) {
    edgeClass = 'wf-edge-submit'
    labelClass = 'wf-edge-pill-submit'
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        className={`wf-base-edge ${edgeClass} ${selected ? 'wf-edge-selected' : ''}`}
      />
      {label && label !== 'trigger' && label !== 'input' && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div className={`wf-edge-label-badge ${labelClass} ${selected ? 'selected' : ''}`}>
              {label.replace(/_/g, ' ')}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
})
