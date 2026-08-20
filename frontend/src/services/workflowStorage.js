/**
 * Hybrid Workflow Service (Backend API Integration with Resilient Offline Fallback)
 * 
 * When FastAPI backend (port 8000) is online: communicates with real SpiffWorkflow endpoints.
 * When backend is offline: seamlessly falls back to persistent LocalStorage simulation engine.
 */

const STORAGE_KEYS = {
  WORKFLOWS: 'workflow_studio_definitions',
  INSTANCES: 'workflow_studio_instances',
  LOGS: 'workflow_studio_logs',
  VARIABLES: 'workflow_studio_variables',
  HISTORY: 'workflow_studio_history'
}

// In-Memory Performance Cache for Client DB Metadata
const _metadataCache = {
  roles: null,
  users: null,
  departments: null,
  entities: null,
  actions: null,
  tables: null,
  fields: {},
  statuses: {},
  columns: {}
}

const DEFAULT_WORKFLOWS = [
  {
    id: 1,
    spec_id: 'document_approval_process',
    name: 'Multi-Tier Document Approval Process',
    description: 'Enterprise review and approval workflow with Department Lead, Legal Reviewer, and Executive sign-off gates.',
    version: 1,
    status: 'Active',
    is_active: true,
    created_on: '2026-08-18 10:30:00',
    tags: ['Approval', 'Operations', 'Compliance'],
    nodes_count: 6,
    xml_content: `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                  id="Definitions_DocApproval"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="document_approval_process" name="Multi-Tier Document Approval Process" isExecutable="true">
    <bpmn:startEvent id="Start_1" name="Submit Document" />
    <bpmn:userTask id="Task_DeptHead" name="Department Lead Review" camunda:candidateGroups="DEPT_HEAD" />
    <bpmn:userTask id="Task_Legal" name="Legal Review" camunda:candidateGroups="LEGAL" />
    <bpmn:userTask id="Task_Exec" name="Executive Signoff" camunda:candidateGroups="EXECUTIVE" />
    <bpmn:endEvent id="End_Approved" name="Document Approved" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_DeptHead" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_DeptHead" targetRef="Task_Legal" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_Legal" targetRef="Task_Exec" />
    <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_Exec" targetRef="End_Approved" />
  </bpmn:process>
</bpmn:definitions>`
  },
  {
    id: 2,
    spec_id: 'capex_authorization',
    name: 'Capital Expenditure & Procurement Workflow',
    description: 'Budget verification, vendor due-diligence, and CFO dual-approval for expenditure > $50,000.',
    version: 2,
    status: 'Active',
    is_active: true,
    created_on: '2026-08-15 14:15:00',
    tags: ['Finance', 'Procurement', 'Audit'],
    nodes_count: 6,
    xml_content: `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_Capex"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="capex_authorization" name="Capital Expenditure &amp; Procurement Workflow" isExecutable="true">
    <bpmn:startEvent id="Start_Capex" name="PO Submitted" />
    <bpmn:userTask id="Task_Finance" name="Finance Controller Review" />
    <bpmn:userTask id="Task_CFO" name="CFO Signoff" />
    <bpmn:endEvent id="End_Capex" name="Procurement Authorized" />
    <bpmn:sequenceFlow id="f1" sourceRef="Start_Capex" targetRef="Task_Finance" />
    <bpmn:sequenceFlow id="f2" sourceRef="Task_Finance" targetRef="Task_CFO" />
    <bpmn:sequenceFlow id="f3" sourceRef="Task_CFO" targetRef="End_Capex" />
  </bpmn:process>
</bpmn:definitions>`
  },
  {
    id: 3,
    spec_id: 'incident_escalation_protocol',
    name: 'IT Service Request & Incident Escalation',
    description: 'Automated triage, severity matrix assessment, and executive notification dispatch.',
    version: 1,
    status: 'Draft',
    is_active: false,
    created_on: '2026-08-17 09:45:00',
    tags: ['SecOps', 'ITSM', 'Automated'],
    nodes_count: 5,
    xml_content: `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  id="Definitions_Incident"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="incident_escalation_protocol" name="IT Service Request &amp; Incident Escalation" isExecutable="true">
    <bpmn:startEvent id="Start_Inc" name="Ticket Ingested" />
    <bpmn:serviceTask id="Task_Triage" name="Automated Severity Scoring" />
    <bpmn:userTask id="Task_SOC" name="Team Lead Containment" />
    <bpmn:endEvent id="End_Resolved" name="Ticket Resolved" />
    <bpmn:sequenceFlow id="f1" sourceRef="Start_Inc" targetRef="Task_Triage" />
    <bpmn:sequenceFlow id="f2" sourceRef="Task_Triage" targetRef="Task_SOC" />
    <bpmn:sequenceFlow id="f3" sourceRef="Task_SOC" targetRef="End_Resolved" />
  </bpmn:process>
</bpmn:definitions>`
  }
]

const DEFAULT_INSTANCES = [
  {
    instance_id: 'inst-9021',
    spec_id: 'document_approval_process',
    workflow_name: 'Multi-Tier Document Approval Process',
    entity_type: 'ContractDocument',
    entity_id: 104,
    status: 'Waiting',
    current_task: 'Department Lead Review',
    candidate_role: 'DEPT_HEAD',
    started_at: '2026-08-19 11:20:00',
    updated_at: '2026-08-19 11:22:15',
    variables: { doc_id: 'DOC-8891', document_title: 'Enterprise Vendor Agreement', priority: 'HIGH', department: 'Engineering' }
  },
  {
    instance_id: 'inst-9020',
    spec_id: 'capex_authorization',
    workflow_name: 'Capital Expenditure & Procurement Workflow',
    entity_type: 'PurchaseOrder',
    entity_id: 882,
    status: 'Completed',
    current_task: 'Workflow Completed',
    candidate_role: null,
    started_at: '2026-08-18 14:00:00',
    updated_at: '2026-08-18 16:45:00',
    variables: { po_amount: 68000, vendor: 'Cloud Services Ltd', approved_by: 'CFO' }
  },
  {
    instance_id: 'inst-9019',
    spec_id: 'document_approval_process',
    workflow_name: 'Multi-Tier Document Approval Process',
    entity_type: 'PolicyDocument',
    entity_id: 102,
    status: 'Completed',
    current_task: 'Workflow Completed',
    candidate_role: null,
    started_at: '2026-08-17 09:10:00',
    updated_at: '2026-08-17 10:15:00',
    variables: { doc_id: 'DOC-7721', document_title: 'Remote Work Security Policy', priority: 'MEDIUM' }
  }
]

export const workflowStorage = {
  // 1. Get all workflow definitions
  getWorkflows: async () => {
    try {
      const res = await fetch('/workflow-studio/workflows', { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        const list = await res.json()
        if (Array.isArray(list)) {
          const transformed = list.map(w => ({
            id: w.workflow_id,
            workflow_id: w.workflow_id,
            spec_id: w.workflow_key,
            name: w.name,
            description: w.description || '',
            version: w.version_number || 1,
            status: w.status === 'ACTIVE' || w.status === 'PUBLISHED' ? 'Active' : (w.status || 'Draft'),
            is_active: w.status === 'ACTIVE' || w.status === 'PUBLISHED',
            created_on: w.created_at ? w.created_at.slice(0, 19).replace('T', ' ') : '',
            updated_at: w.updated_at ? w.updated_at.slice(0, 19).replace('T', ' ') : '',
            tags: [w.entity_type || 'Custom'],
            nodes_count: w.nodes_count || 3
          }))
          localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(transformed))
          return transformed
        }
      }
    } catch (_e) {
      // Backend offline: use fallback
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
      if (stored) return JSON.parse(stored)
    } catch (e) {
      console.error('Local storage read error:', e)
    }
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(DEFAULT_WORKFLOWS))
    return DEFAULT_WORKFLOWS
  },

  // 2. Get workflow by ID
  getWorkflowById: async (id) => {
    try {
      const res = await fetch(`/workflow-studio/workflows/${id}`, { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        const data = await res.json()
        if (data && (data.workflow_id || data.id)) {
          const loadedNodes = (data.nodes || []).map(n => {
            const rawType = String(n.type || '').toUpperCase()
            let rfType = 'userTask'
            if (rawType === 'START') rfType = 'start'
            else if (rawType === 'END') rfType = 'end'
            else if (rawType === 'USER_TASK' || rawType === 'APPROVAL') rfType = 'userTask'
            else if (rawType === 'CONDITION') rfType = 'condition'
            else if (rawType === 'ACTION' || rawType === 'RECORD') rfType = 'action'
            else if (rawType === 'EMAIL' || rawType === 'NOTIFICATION') rfType = 'communication'

            const cfg = n.config || {}
            return {
              id: n.id,
              type: rfType,
              position: { x: n.position_x || 250, y: n.position_y || 100 },
              data: {
                label: n.name || n.id,
                name: n.name,
                taskCode: cfg.taskCode || n.id,
                description: cfg.description || '',
                assignment: cfg.assignment || {},
                actions: cfg.actions || ['APPROVE', 'REJECT'],
                visibility: cfg.visibility || ['APPROVER'],
                actionType: cfg.actionType || 'DB_UPDATE',
                subType: cfg.actionType || 'UPDATE_RECORD',
                table: cfg.table || '',
                entity: cfg.table || '',
                filters: cfg.filters || [],
                updates: cfg.updates || {},
                values: cfg.values || {},
                resultMapping: cfg.resultMapping || {},
                outcome: cfg.outcome || ''
              }
            }
          })

          const loadedEdges = (data.edges || []).map(e => ({
            id: e.id,
            source: e.source,
            target: e.target,
            sourceHandle: e.config?.sourceHandle || (e.label ? e.label.toUpperCase() : 'output'),
            targetHandle: 'input',
            label: e.label || '',
            type: 'workflow',
            data: { label: e.label, action: e.label, condition: e.condition }
          }))

          return {
            id: data.workflow_id,
            workflow_id: data.workflow_id,
            name: data.name,
            spec_id: data.workflow_key,
            description: data.description,
            version: data.version_number || 1,
            status: data.status === 'PUBLISHED' || data.status === 'ACTIVE' ? 'Active' : (data.status || 'Draft'),
            json_content: { nodes: loadedNodes, edges: loadedEdges }
          }
        }
      }
    } catch (_e) {
      // Backend offline: fallback
    }

    const list = await workflowStorage.getWorkflows()
    return list.find(w => Number(w.id) === Number(id)) || list[0] || null
  },

  // 3. Create Draft Definition
  createWorkflow: async (draft) => {
    try {
      const payload = {
        name: draft.name,
        workflow_key: draft.spec_id.trim().replace(/\s+/g, '_').toLowerCase(),
        description: draft.description || 'Custom workflow designed in Studio',
        entity_type: draft.tags?.[0] || 'Generic'
      }
      const res = await fetch('/workflow-studio/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(5000)
      })
      if (res.ok) {
        const json = await res.json()
        if (json.workflow_id) {
          return {
            id: json.workflow_id,
            workflow_id: json.workflow_id,
            spec_id: json.workflow_key,
            name: json.name,
            description: json.description,
            version: json.version_number || 1,
            status: 'Draft'
          }
        }
      }
    } catch (_e) {
      // Fallback
    }

    const list = await workflowStorage.getWorkflows()
    const newId = Date.now()
    const newRecord = {
      id: newId,
      spec_id: draft.spec_id.trim().replace(/\s+/g, '_').toLowerCase(),
      name: draft.name,
      description: draft.description || 'Custom workflow designed in Studio',
      version: 1,
      status: 'Draft',
      is_active: false,
      created_on: new Date().toISOString().replace('T', ' ').slice(0, 19),
      tags: typeof draft.tags === 'string' ? draft.tags.split(',').map(t => t.trim()).filter(Boolean) : (draft.tags || ['Custom']),
      nodes_count: 3
    }

    const updated = [newRecord, ...list]
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    return newRecord
  },

  // 4. Import BPMN File
  importWorkflow: async (specId, name, description, tags, xmlString) => {
    const list = await workflowStorage.getWorkflows()
    const newId = Date.now()
    const newRecord = {
      id: newId,
      spec_id: specId || `imported_spec_${newId}`,
      name: name || 'Imported BPMN Process',
      description: description || 'Imported from BPMN 2.0 XML diagram',
      version: 1,
      status: 'Draft',
      is_active: false,
      created_on: new Date().toISOString().replace('T', ' ').slice(0, 19),
      tags: typeof tags === 'string' ? tags.split(',').map(t => t.trim()).filter(Boolean) : ['BPMN-Import'],
      nodes_count: 5,
      xml_content: xmlString
    }

    const updated = [newRecord, ...list]
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    return newRecord
  },

  // 5. Update / Save Workflow
  saveWorkflow: async (id, updates) => {
    try {
      let nodes = []
      let edges = []
      if (updates.json_content) {
        const parsed = typeof updates.json_content === 'string' ? JSON.parse(updates.json_content) : updates.json_content
        nodes = (parsed.nodes || []).map(n => ({
          id: n.id,
          type: (n.type || 'userTask').toUpperCase() === 'USERTASK' ? 'USER_TASK' : (n.type || 'USER_TASK').toUpperCase(),
          name: n.data?.name || n.data?.label || n.id,
          position_x: n.position?.x || 100,
          position_y: n.position?.y || 100,
          config: {
            taskCode: n.data?.taskCode || n.id,
            description: n.data?.description || '',
            assignment: n.data?.assignment || {},
            actions: n.data?.actions || ['APPROVE', 'REJECT'],
            visibility: n.data?.visibility || ['APPROVER'],
            actionType: n.data?.actionType || 'DB_UPDATE',
            table: n.data?.table || n.data?.entity || '',
            filters: n.data?.filters || [],
            updates: n.data?.updates || {},
            values: n.data?.values || {},
            resultMapping: n.data?.resultMapping || {},
            outcome: n.data?.outcome || ''
          }
        }))

        edges = (parsed.edges || []).map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || e.data?.label || '',
          condition: e.data?.condition || null,
          config: {
            sourceHandle: e.sourceHandle || e.data?.action || e.label || 'output'
          }
        }))
      }

      const payload = {
        name: updates.name,
        description: updates.description,
        nodes: nodes.length > 0 ? nodes : undefined,
        edges: edges.length > 0 ? edges : undefined
      }

      await fetch(`/workflow-studio/workflows/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(5000)
      })
    } catch (_e) {
      // Fallback
    }

    const list = await workflowStorage.getWorkflows()
    const updated = list.map(w => {
      if (Number(w.id) === Number(id)) {
        return { ...w, ...updates, updated_at: new Date().toISOString().replace('T', ' ').slice(0, 19) }
      }
      return w
    })
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    return updated.find(w => Number(w.id) === Number(id))
  },

  // 6. Duplicate Workflow
  duplicateWorkflow: async (id) => {
    try {
      const res = await fetch(`/workflow/definitions/${id}/duplicate`, { method: 'POST', signal: AbortSignal.timeout(2000) })
      if (res.ok) {
        const json = await res.json()
        if (json.data) return json.data
      }
    } catch (_e) {
      // Fallback
    }

    const list = await workflowStorage.getWorkflows()
    const item = list.find(w => Number(w.id) === Number(id))
    if (!item) return null

    const newId = Date.now()
    const clone = {
      ...item,
      id: newId,
      spec_id: `${item.spec_id}_copy`,
      name: `${item.name} (Copy)`,
      status: 'Draft',
      is_active: false,
      version: 1,
      created_on: new Date().toISOString().replace('T', ' ').slice(0, 19)
    }

    const updated = [clone, ...list]
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    return clone
  },

  // 7. Publish Workflow
  publishWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}/publish`, { method: 'POST', signal: AbortSignal.timeout(2000) })
    } catch (_e) {}
    return workflowStorage.saveWorkflow(id, { status: 'Published', is_active: true })
  },

  // 8. Activate Workflow
  activateWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}/activate`, { method: 'POST', signal: AbortSignal.timeout(2000) })
    } catch (_e) {}
    return workflowStorage.saveWorkflow(id, { status: 'Active', is_active: true })
  },

  // 9. Deactivate Workflow
  deactivateWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}/deactivate`, { method: 'POST', signal: AbortSignal.timeout(2000) })
    } catch (_e) {}
    return workflowStorage.saveWorkflow(id, { status: 'Inactive', is_active: false })
  },

  // 10. Delete Workflow
  deleteWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}`, { method: 'DELETE', signal: AbortSignal.timeout(2000) })
    } catch (_e) {}
    const list = await workflowStorage.getWorkflows()
    const updated = list.filter(w => Number(w.id) !== Number(id))
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    return true
  },

  // 11. Execute Simulation
  executeWorkflow: async (workflowId, initialVariables = {}) => {
    try {
      const res = await fetch(`/workflow/definitions/${workflowId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_variables: initialVariables }),
        signal: AbortSignal.timeout(2500)
      })
      if (res.ok) {
        const json = await res.json()
        if (json.data) return json.data
      }
    } catch (_e) {}

    const wf = await workflowStorage.getWorkflowById(workflowId)
    const instances = await workflowStorage.getInstances()
    const instanceId = `inst-${Math.floor(1000 + Math.random() * 9000)}`

    const newInstance = {
      instance_id: instanceId,
      spec_id: wf?.spec_id || 'workflow_run',
      workflow_name: wf?.name || 'Workflow Instance Run',
      entity_type: 'DirectExecution',
      entity_id: Math.floor(Math.random() * 500),
      status: 'Waiting',
      current_task: 'Functional Head Review',
      candidate_role: 'FUNCTION_HEAD',
      started_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
      updated_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
      variables: initialVariables
    }

    const updatedInstances = [newInstance, ...instances]
    localStorage.setItem(STORAGE_KEYS.INSTANCES, JSON.stringify(updatedInstances))

    return {
      instance_id: instanceId,
      status: 'Waiting',
      current_task: 'Functional Head Review',
      ready_tasks: [
        {
          task_id: Math.floor(100 + Math.random() * 900),
          task_spec_id: 'Task_FH',
          task_name: 'Functional Head Review',
          candidate_role: 'FUNCTION_HEAD',
          assigned_user: 'Department Manager',
          status: 'READY'
        }
      ],
      variables: initialVariables,
      trace_logs: [
        { timestamp: new Date().toLocaleTimeString(), activity: 'Start Node', type: 'START', status: 'COMPLETED' },
        { timestamp: new Date().toLocaleTimeString(), activity: 'Functional Head Review', type: 'USER_TASK', status: 'READY' }
      ]
    }
  },

  // 12. Complete Task in Runner
  completeTask: async (taskId, action, variables = {}, remark = '') => {
    try {
      const res = await fetch(`/workflow/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables, remark }),
        signal: AbortSignal.timeout(2000)
      })
      if (res.ok) {
        const json = await res.json()
        if (json.data) return json.data
      }
    } catch (_e) {}

    return {
      task_id: taskId,
      action: action,
      status: 'COMPLETED',
      next_task: action === 'APPROVE' ? 'Next Approval Step' : 'Rejected',
      instance_status: action === 'APPROVE' ? 'Waiting' : 'Terminated',
      completed_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
      variables: { ...variables, last_action: action, remark }
    }
  },

  // 13. Get Instances for Monitoring
  getInstances: async () => {
    try {
      const res = await fetch('/workflow/monitoring/instances', { signal: AbortSignal.timeout(1500) })
      if (res.ok) {
        const json = await res.json()
        if (Array.isArray(json.data) && json.data.length > 0) {
          localStorage.setItem(STORAGE_KEYS.INSTANCES, JSON.stringify(json.data))
          return json.data
        }
      }
    } catch (_e) {}

    try {
      const stored = localStorage.getItem(STORAGE_KEYS.INSTANCES)
      if (stored) return JSON.parse(stored)
    } catch (e) {
      console.error(e)
    }
    localStorage.setItem(STORAGE_KEYS.INSTANCES, JSON.stringify(DEFAULT_INSTANCES))
    return DEFAULT_INSTANCES
  },

  // 14. Get instance trace details
  getInstanceDetails: async (instanceId) => {
    try {
      const [varRes, logRes, histRes] = await Promise.all([
        fetch(`/workflow/monitoring/instances/${instanceId}/variables`, { signal: AbortSignal.timeout(1500) }),
        fetch(`/workflow/monitoring/instances/${instanceId}/logs`, { signal: AbortSignal.timeout(1500) }),
        fetch(`/workflow/monitoring/instances/${instanceId}/history`, { signal: AbortSignal.timeout(1500) })
      ])
      if (varRes.ok && logRes.ok && histRes.ok) {
        const [varData, logData, histData] = await Promise.all([varRes.json(), logRes.json(), histRes.json()])
        return {
          variables: varData.data || {},
          logs: logData.data || [],
          history: histData.data || []
        }
      }
    } catch (_e) {}

    const instances = await workflowStorage.getInstances()
    const inst = instances.find(i => i.instance_id === instanceId) || instances[0]

    return {
      variables: inst?.variables || { sample_key: 'sample_value', priority: 'HIGH' },
      logs: [
        { id: 1, activity_name: 'Start Trigger', activity_type: 'START', status: 'SUCCESS', created_on: inst?.started_at || '2026-08-19 11:20:00', duration: '12ms' },
        { id: 2, activity_name: 'Validation & Rule Check', activity_type: 'SERVICE', status: 'SUCCESS', created_on: inst?.started_at || '2026-08-19 11:20:01', duration: '45ms' },
        { id: 3, activity_name: inst?.current_task || 'User Task Review', activity_type: 'USER_TASK', status: inst?.status === 'Completed' ? 'COMPLETED' : 'WAITING', created_on: inst?.updated_at || '2026-08-19 11:22:00', duration: 'Pending' }
      ],
      history: [
        { id: 1, from_state: 'START', to_state: 'PENDING_FH', action: 'INITIATE', actor: 'System Auto-Trigger', created_on: inst?.started_at || '2026-08-19 11:20:00' },
        { id: 2, from_state: 'PENDING_FH', to_state: inst?.status === 'Completed' ? 'APPROVED' : 'IN_REVIEW', action: 'APPROVE', actor: 'Admin User', created_on: inst?.updated_at || '2026-08-19 11:22:15' }
      ]
    }
  },

  // 15. Dynamic Client Metadata Discovery (With High-Performance In-Memory Cache)
  getMetadataRoles: async () => {
    if (_metadataCache.roles) return _metadataCache.roles
    const res = await fetch('/workflow-studio/metadata/roles', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to load roles from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.roles = result
    return result
  },

  getMetadataUsers: async () => {
    if (_metadataCache.users) return _metadataCache.users
    const res = await fetch('/workflow-studio/metadata/users', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to load users from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.users = result
    return result
  },

  getMetadataDepartments: async () => {
    if (_metadataCache.departments) return _metadataCache.departments
    const res = await fetch('/workflow-studio/metadata/departments', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to load departments from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.departments = result
    return result
  },

  getMetadataEntities: async () => {
    if (_metadataCache.entities) return _metadataCache.entities
    const res = await fetch('/workflow-studio/metadata/entities', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to introspect entities from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.entities = result
    return result
  },

  getMetadataEntityFields: async (entityName) => {
    if (!entityName) return []
    if (_metadataCache.fields[entityName]) return _metadataCache.fields[entityName]
    const res = await fetch(`/workflow-studio/metadata/entities/${encodeURIComponent(entityName)}/fields`, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to introspect fields for '${entityName}' (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.fields[entityName] = result
    return result
  },

  getMetadataStatuses: async (entityName) => {
    const cacheKey = entityName || '__ALL__'
    if (_metadataCache.statuses[cacheKey]) return _metadataCache.statuses[cacheKey]
    const url = entityName ? `/workflow-studio/metadata/statuses?entity_name=${encodeURIComponent(entityName)}` : '/workflow-studio/metadata/statuses'
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to load statuses from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.statuses[cacheKey] = result
    return result
  },

  getMetadataActions: async () => {
    if (_metadataCache.actions) return _metadataCache.actions
    const res = await fetch('/workflow-studio/actions', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to load actions from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.actions = result
    return result
  },

  getMetadataTables: async () => {
    if (_metadataCache.tables) return _metadataCache.tables
    const res = await fetch('/workflow-studio/metadata/tables', { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to introspect tables from Client DB (${res.status})`)
    const data = await res.json()
    const result = Array.isArray(data) ? data : (data.data || [])
    _metadataCache.tables = result
    return result
  },

  getMetadataTableColumns: async (tableName) => {
    if (!tableName) return { table_name: '', columns: [], primary_keys: [] }
    if (_metadataCache.columns[tableName]) return _metadataCache.columns[tableName]
    const res = await fetch(`/workflow-studio/metadata/tables/${encodeURIComponent(tableName)}/columns`, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) throw new Error(`Failed to introspect columns for '${tableName}' (${res.status})`)
    const result = await res.json()
    _metadataCache.columns[tableName] = result
    return result
  },

  clearMetadataCache: () => {
    _metadataCache.roles = null
    _metadataCache.users = null
    _metadataCache.departments = null
    _metadataCache.entities = null
    _metadataCache.actions = null
    _metadataCache.tables = null
    _metadataCache.fields = {}
    _metadataCache.statuses = {}
    _metadataCache.columns = {}
  }
}
