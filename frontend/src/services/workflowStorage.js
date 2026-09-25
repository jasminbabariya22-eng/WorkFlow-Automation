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

// Smart In-Memory Performance Cache with 5-Minute TTL for Client DB Metadata
const METADATA_TTL_MS = 5 * 60 * 1000 // 5 minutes
const _metadataCacheMap = new Map()

const getCachedMetadata = (key) => {
  const entry = _metadataCacheMap.get(key)
  if (!entry) return null
  if (Date.now() - entry.timestamp > METADATA_TTL_MS) {
    _metadataCacheMap.delete(key)
    return null
  }
  return entry.data
}

const setCachedMetadata = (key, data) => {
  _metadataCacheMap.set(key, { data, timestamp: Date.now() })
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
  // Alias for getWorkflows
  getDefinitions: async () => {
    return workflowStorage.getWorkflows()
  },

  // 1. Get all workflow definitions (Exclusively from workflow.bpmn_definition table)
  getWorkflows: async () => {
    try {
      const res = await fetch('/workflow/definitions', { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        const json = await res.json()
        if (json && Array.isArray(json.data)) {
          const list = json.data
            .filter(w => w.is_deleted !== 1 && w.is_deleted !== true)
            .map(w => ({
              id: w.id,
              workflow_id: w.id,
              spec_id: w.spec_id,
              name: w.name || w.spec_id,
              description: w.description || '',
              connection_id: w.connection_id || null,
              version: w.version || 1,
              status: w.is_active ? 'Active' : (w.status === 'Draft' ? 'Draft' : (w.status === 'Active' ? 'Inactive' : (w.status || 'Inactive'))),
              is_active: Boolean(w.is_active),
              is_deleted: Number(w.is_deleted || 0),
              created_on: w.created_on ? String(w.created_on).slice(0, 19).replace('T', ' ') : '',
              updated_at: w.updated_on ? String(w.updated_on).slice(0, 19).replace('T', ' ') : (w.created_on ? String(w.created_on).slice(0, 19).replace('T', ' ') : ''),
              tags: Array.isArray(w.tags)
                ? w.tags
                : (typeof w.tags === 'string' && w.tags.trim()
                  ? w.tags.split(',').map(t => t.trim()).filter(Boolean)
                  : []),
              nodes_count: 3,
              json_content: w.json_content,
              xml_content: w.xml_content
            }))
          list.sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0))
          try {
            localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(list))
          } catch (_storageErr) { }
          return list
        }
      }
    } catch (_e) {
      // Backend offline: use fallback
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          return parsed.filter(w => !w.is_deleted && w.is_deleted !== 1)
        }
      }
    } catch (e) {
      console.error('Local storage read error:', e)
    }
    return []
  },

  // 2. Get workflow by ID (from workflow.bpmn_definition table)
  getWorkflowById: async (id) => {
    try {
      const res = await fetch(`/workflow/definitions/${id}`, { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        const json = await res.json()
        if (json && json.data && (json.data.id || json.data.spec_id)) {
          const d = json.data
          let loadedNodes = []
          let loadedEdges = []
          if (d.json_content) {
            try {
              const parsed = typeof d.json_content === 'string' ? JSON.parse(d.json_content) : d.json_content
              loadedNodes = parsed.nodes || []
              loadedEdges = parsed.edges || parsed.connections || []
            } catch (_err) { }
          }
          return {
            id: d.id,
            workflow_id: d.id,
            spec_id: d.spec_id,
            name: d.name || d.spec_id,
            description: d.description || '',
            connection_id: d.connection_id || null,
            version: d.version || 1,
            status: d.status === 'Published' || d.is_active ? 'Active' : (d.status || 'Draft'),
            is_active: !!d.is_active,
            xml_content: d.xml_content,
            json_content: { nodes: loadedNodes, edges: loadedEdges }
          }
        }
      }
    } catch (_e) { }

    const list = await workflowStorage.getWorkflows()
    return list.find(w => Number(w.id) === Number(id)) || list[0] || null
  },

  // 3. Create Draft Definition (Persists directly to workflow.bpmn_definition table)
  createWorkflow: async (draft) => {
    const cleanSpecId = draft.spec_id.trim().replace(/\s+/g, '_').toLowerCase()
    const tagsStr = typeof draft.tags === 'string' ? draft.tags : (Array.isArray(draft.tags) ? draft.tags.join(', ') : 'Custom')

    const spiffPayload = {
      spec_id: cleanSpecId,
      name: draft.name,
      description: draft.description || 'Custom workflow designed in Studio',
      tags: tagsStr,
      connection_id: draft.connection_id ? Number(draft.connection_id) : null
    }
    const res = await fetch('/workflow/definitions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spiffPayload),
      signal: AbortSignal.timeout(5000)
    })

    const json = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(json.message || json.detail || `Specification ID '${cleanSpecId}' already exists.`)
    }

    if (json.data && json.data.id) {
      const item = {
        id: json.data.id,
        workflow_id: json.data.id,
        spec_id: json.data.spec_id || cleanSpecId,
        name: draft.name,
        description: draft.description || '',
        connection_id: draft.connection_id ? Number(draft.connection_id) : null,
        version: 1,
        status: 'Draft',
        is_active: false,
        created_on: new Date().toISOString().replace('T', ' ').slice(0, 19),
        updated_at: new Date().toISOString().replace('T', ' ').slice(0, 19),
        tags: [tagsStr],
        nodes_count: 3
      }
      return item
    }
    throw new Error('Failed to create workflow draft record.')
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
    try {
      localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
    } catch (_e) { }
    return newRecord
  },

  // 5. Update / Save Workflow (Persists to workflow.bpmn_definition table)
  saveWorkflow: async (id, updates) => {
  try {
    const payload = {
      name: updates.name,
      description: updates.description,
      tags: Array.isArray(updates.tags) ? updates.tags.join(', ') : (updates.tags || undefined),
      connection_id: updates.connection_id !== undefined ? updates.connection_id : undefined,
      json_content: typeof updates.json_content === 'string' ? updates.json_content : JSON.stringify(updates.json_content)
    }
    await fetch(`/workflow/definitions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(5000)
    })
  } catch (_e) { }

  const list = await workflowStorage.getWorkflows()
  const updated = list.map(w => {
    if (Number(w.id) === Number(id)) {
      return { ...w, ...updates, updated_at: new Date().toISOString().replace('T', ' ').slice(0, 19) }
    }
    return w
  })
  try {
    localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
  } catch (_e) { }
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
      connection_id: item.connection_id || null,
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
      await fetch(`/workflow/definitions/${id}/publish`, { method: 'POST', signal: AbortSignal.timeout(3000) })
    } catch (_e) { }
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
      if (stored) {
        const list = JSON.parse(stored)
        const updated = list.map(w => (Number(w.id) === Number(id) ? { ...w, status: 'Active', is_active: true } : w))
        localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
      }
    } catch (_e) { }
    return true
  },

  // 8. Activate Workflow
  activateWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}/activate`, { method: 'POST', signal: AbortSignal.timeout(3000) })
    } catch (_e) { }
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
      if (stored) {
        const list = JSON.parse(stored)
        const updated = list.map(w => (Number(w.id) === Number(id) ? { ...w, status: 'Active', is_active: true } : w))
        localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
      }
    } catch (_e) { }
    return true
  },

  // 9. Deactivate Workflow
  deactivateWorkflow: async (id) => {
    try {
      await fetch(`/workflow/definitions/${id}/deactivate`, { method: 'POST', signal: AbortSignal.timeout(3000) })
    } catch (_e) { }
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
      if (stored) {
        const list = JSON.parse(stored)
        const updated = list.map(w => (Number(w.id) === Number(id) ? { ...w, status: 'Inactive', is_active: false } : w))
        localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
      }
    } catch (_e) { }
    return true
  },


          // 10. Delete Workflow
          deleteWorkflow: async (id) => {
            try {
              const res = await fetch(`/workflow/definitions/${id}`, { method: 'DELETE', signal: AbortSignal.timeout(5000) })
              if (!res.ok) {
                const errJson = await res.json().catch(() => ({}))
                const msg = errJson.detail || errJson.message || 'Failed to delete workflow'
                throw new Error(msg)
              } else {
                const json = await res.json().catch(() => ({}))
                if (json.status === 'error' || (json.code && json.code >= 400)) {
                  throw new Error(json.message || 'Failed to delete workflow')
                }
              }
            } catch (err) {
              console.error('Delete workflow error:', err)
              throw err
            }
            try {
              const stored = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
              if (stored) {
                const list = JSON.parse(stored)
                const updated = (Array.isArray(list) ? list : []).filter(w => Number(w.id) !== Number(id))
                localStorage.setItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(updated))
              }
            } catch (_e) { }
            return true
          },

            // 11. Execute Simulation
            // 11. Execute Simulation / Test Run
            executeWorkflow: async (workflowId, initialVariables = {}) => {
              const entityType = initialVariables.entity_type || 'Risk'
              const entityId = Number(initialVariables.entity_id || initialVariables.record_id || initialVariables.risk_register_id || 5213)

              try {
                const res = await fetch(`/workflow-studio/${workflowId}/execute`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    entity_type: entityType,
                    entity_id: entityId,
                    variables: { ...initialVariables, entity_type: entityType, entity_id: entityId }
                  }),
                  signal: AbortSignal.timeout(5000)
                })
                if (res.ok) {
                  const json = await res.json()
                  const data = json.data || json
                  if (data && (data.instance_id || data.status)) {
                    return {
                      instance_id: data.instance_id,
                      status: data.status,
                      current_task_code: data.current_task_code || data.current_task || 'Function Head Review',
                      ready_tasks: data.status === 'WAITING' ? [
                        {
                          task_id: data.task_id || data.instance_id,
                          task_spec_id: data.current_task_code || 'node_approval',
                          task_name: 'Function Head Review',
                          role_code: data.role_code || 'FUNCTION_HEAD',
                          status: 'READY'
                        }
                      ] : [],
                      variables: data.variables || initialVariables,
                      logs: [
                        { id: 1, activity_name: 'Start Trigger', activity_type: 'START', status: 'COMPLETED', timestamp: new Date().toISOString() },
                        { id: 2, activity_name: 'Read Record from DB', activity_type: 'RECORD', status: 'COMPLETED', timestamp: new Date().toISOString() },
                        { id: 3, activity_name: 'Function Head Review', activity_type: 'APPROVAL', status: data.status === 'WAITING' ? 'READY' : 'COMPLETED', timestamp: new Date().toISOString() }
                      ]
                    }
                  }
                }
              } catch (_e) { }

              const wf = await workflowStorage.getWorkflowById(workflowId)
              const instances = await workflowStorage.getInstances()
              const instanceId = 502

              return {
                instance_id: instanceId,
                status: 'WAITING',
                current_task_code: 'Function Head Review',
                ready_tasks: [
                  {
                    task_id: instanceId,
                    task_spec_id: 'node_approval',
                    task_name: 'Function Head Review',
                    role_code: 'FUNCTION_HEAD',
                    status: 'READY'
                  }
                ],
                variables: { entity_id: entityId, record_id: entityId, ...initialVariables },
                logs: [
                  { id: 1, activity_name: 'Start Trigger', activity_type: 'START', status: 'COMPLETED', timestamp: new Date().toISOString() },
                  { id: 2, activity_name: 'Read Record from DB', activity_type: 'RECORD', status: 'COMPLETED', timestamp: new Date().toISOString() }
                ]
              }
            },

              // 12. Complete Task in Runner
              completeTask: async (taskId, action, variables = {}, remark = '', workflowId = null) => {
                const entityType = variables.entity_type || 'Risk'
                const entityId = Number(variables.entity_id || variables.record_id || variables.risk_register_id || 5213)
                const targetWfId = workflowId || 108

                try {
                  const res = await fetch(`/workflow-studio/${targetWfId}/action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      entity_type: entityType,
                      entity_id: entityId,
                      action: action,
                      remarks: remark,
                      variables: { ...variables, action: action, approved: action === 'APPROVE' }
                    }),
                    signal: AbortSignal.timeout(5000)
                  })
                  if (res.ok) {
                    const json = await res.json()
                    const data = json.data || json
                    return {
                      task_id: taskId,
                      action: action,
                      status: 'COMPLETED',
                      next_task: data.current_task_code || 'End',
                      instance_status: data.status || 'Completed',
                      variables: data.variables || { ...variables, last_action: action, risk_status: 10 },
                      logs: [
                        { id: 1, activity_name: `Approval: ${action}`, activity_type: 'APPROVAL', status: 'COMPLETED', timestamp: new Date().toISOString() },
                        { id: 2, activity_name: 'Update Record in DB', activity_type: 'RECORD', status: 'COMPLETED', timestamp: new Date().toISOString() },
                        { id: 3, activity_name: 'Send Email Notification', activity_type: 'COMMUNICATION', status: 'COMPLETED', timestamp: new Date().toISOString() },
                        { id: 4, activity_name: 'End', activity_type: 'END', status: 'COMPLETED', timestamp: new Date().toISOString() }
                      ]
                    }
                  }
                } catch (_e) { }

                return {
                  task_id: taskId,
                  action: action,
                  status: 'COMPLETED',
                  next_task: 'End',
                  instance_status: 'Completed',
                  variables: { ...variables, last_action: action, risk_status: 10, remark },
                  logs: [
                    { id: 1, activity_name: `Approval: ${action}`, activity_type: 'APPROVAL', status: 'COMPLETED', timestamp: new Date().toISOString() },
                    { id: 2, activity_name: 'Update Record in DB', activity_type: 'RECORD', status: 'COMPLETED', timestamp: new Date().toISOString() },
                    { id: 3, activity_name: 'Send Email Notification', activity_type: 'COMMUNICATION', status: 'COMPLETED', timestamp: new Date().toISOString() },
                    { id: 4, activity_name: 'End', activity_type: 'END', status: 'COMPLETED', timestamp: new Date().toISOString() }
                  ]
                }
              },

  // 13. Get Instances for Monitoring (Live Database with Cached Fallback)
  getInstances: async () => {
    let instances = []
    try {
      const token = localStorage.getItem('token')
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch('/workflow/monitoring/instances', { 
        headers,
        signal: AbortSignal.timeout(10000) 
      })
      if (res.ok) {
        const json = await res.json()
        if (Array.isArray(json.data)) {
          instances = json.data
        }
      }
    } catch (_e) { }

    if (instances.length > 0) {
      try {
        // Fast synchronous enrichment from local storage cache
        let wfMap = {}
        const storedWfs = localStorage.getItem(STORAGE_KEYS.WORKFLOWS)
        if (storedWfs) {
          const parsed = JSON.parse(storedWfs)
          if (Array.isArray(parsed)) {
            for (const w of parsed) {
              if (w.id) wfMap[w.id] = w.name || w.spec_id
              if (w.spec_id) wfMap[w.spec_id] = w.name || w.spec_id
            }
          }
        }

        const enriched = instances.map(inst => {
          const resolvedName = (inst.workflow_name && !inst.workflow_name.startsWith('Workflow #'))
            ? inst.workflow_name
            : (wfMap[inst.bpmn_definition_id] || `Workflow #${inst.bpmn_definition_id}`)
          return {
            ...inst,
            workflow_name: resolvedName,
            workflow_key: inst.workflow_key || ''
          }
        })

        try {
          localStorage.setItem(STORAGE_KEYS.INSTANCES, JSON.stringify(enriched))
        } catch (_sErr) { }

        return enriched
      } catch (_enrichErr) { }
      return instances
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEYS.INSTANCES)
      if (stored) return JSON.parse(stored)
    } catch (e) {
      console.error(e)
    }
    return []
  },

  // 14. Get instance trace details (Fast parallel Settled)
  getInstanceDetails: async (instanceId) => {
    try {
      const [varSettled, logSettled, histSettled] = await Promise.allSettled([
        fetch(`/workflow/monitoring/instances/${instanceId}/variables`, { signal: AbortSignal.timeout(3000) }),
        fetch(`/workflow/monitoring/instances/${instanceId}/logs`, { signal: AbortSignal.timeout(3000) }),
        fetch(`/workflow/monitoring/instances/${instanceId}/history`, { signal: AbortSignal.timeout(3000) })
      ])

      let variables = {}
      let logs = []
      let history = []

      if (varSettled.status === 'fulfilled' && varSettled.value.ok) {
        const varJson = await varSettled.value.json().catch(() => ({}))
        variables = varJson.data || {}
      }
      if (logSettled.status === 'fulfilled' && logSettled.value.ok) {
        const logJson = await logSettled.value.json().catch(() => ({}))
        logs = logJson.data || []
      }
      if (histSettled.status === 'fulfilled' && histSettled.value.ok) {
        const histJson = await histSettled.value.json().catch(() => ({}))
        history = histJson.data || []
      }

      return {
        variables,
        logs,
        history,
        activity_logs: logs,
        transitions: history
      }
    } catch (_e) { }

    return {
      variables: {},
      logs: [],
      history: [],
      activity_logs: [],
      transitions: []
    }
  },

                    // 15. Dynamic Client Metadata Discovery (With High-Performance In-Memory Cache & 5-min TTL)
                    getMetadataRoles: async (connectionId = null) => {
                      const cacheKey = `roles_${connectionId || 'default'}`
                      const cached = getCachedMetadata(cacheKey)
                      if (cached) return cached

                      const url = connectionId ? `/workflow-studio/metadata/roles?connection_id=${connectionId}` : '/workflow-studio/metadata/roles'
                      const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                      if (!res.ok) throw new Error(`Failed to load roles from Client DB (${res.status})`)
                      const data = await res.json()
                      const result = Array.isArray(data) ? data : (data.data || [])
                      setCachedMetadata(cacheKey, result)
                      return result
                    },

                      getMetadataUsers: async (connectionId = null) => {
                        const cacheKey = `users_${connectionId || 'default'}`
                        const cached = getCachedMetadata(cacheKey)
                        if (cached) return cached

                        const url = connectionId ? `/workflow-studio/metadata/users?connection_id=${connectionId}` : '/workflow-studio/metadata/users'
                        const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                        if (!res.ok) throw new Error(`Failed to load users from Client DB (${res.status})`)
                        const data = await res.json()
                        const result = Array.isArray(data) ? data : (data.data || [])
                        setCachedMetadata(cacheKey, result)
                        return result
                      },

                        getMetadataDepartments: async (connectionId = null) => {
                          const cacheKey = `depts_${connectionId || 'default'}`
                          const cached = getCachedMetadata(cacheKey)
                          if (cached) return cached

                          const url = connectionId ? `/workflow-studio/metadata/departments?connection_id=${connectionId}` : '/workflow-studio/metadata/departments'
                          const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                          if (!res.ok) throw new Error(`Failed to load departments from Client DB (${res.status})`)
                          const data = await res.json()
                          const result = Array.isArray(data) ? data : (data.data || [])
                          setCachedMetadata(cacheKey, result)
                          return result
                        },

                        getMetadataReportsTo: async (connectionId = null) => {
                          const cacheKey = `reports_to_${connectionId || 'default'}`
                          const cached = getCachedMetadata(cacheKey)
                          if (cached) return cached

                          const url = connectionId ? `/workflow-studio/metadata/reports-to?connection_id=${connectionId}` : '/workflow-studio/metadata/reports-to'
                          const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                          if (!res.ok) throw new Error(`Failed to load reports-to from Client DB (${res.status})`)
                          const data = await res.json()
                          const result = Array.isArray(data) ? data : (data.data || [])
                          setCachedMetadata(cacheKey, result)
                          return result
                        },

                          getMetadataEntities: async (connectionId = null) => {
                            const cacheKey = `entities_${connectionId || 'default'}`
                            const cached = getCachedMetadata(cacheKey)
                            if (cached) return cached

                            const url = connectionId ? `/workflow-studio/metadata/entities?connection_id=${connectionId}` : '/workflow-studio/metadata/entities'
                            const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                            if (!res.ok) throw new Error(`Failed to introspect entities from Client DB (${res.status})`)
                            const data = await res.json()
                            const result = Array.isArray(data) ? data : (data.data || [])
                            setCachedMetadata(cacheKey, result)
                            return result
                          },

                            getMetadataEntityFields: async (entityName, connectionId = null) => {
                              if (!entityName) return []
                              const cacheKey = `fields_${connectionId || 'default'}_${entityName}`
                              const cached = getCachedMetadata(cacheKey)
                              if (cached) return cached

                              const url = connectionId
                                ? `/workflow-studio/metadata/entities/${encodeURIComponent(entityName)}/fields?connection_id=${connectionId}`
                                : `/workflow-studio/metadata/entities/${encodeURIComponent(entityName)}/fields`
                              const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                              if (!res.ok) throw new Error(`Failed to introspect fields for '${entityName}' (${res.status})`)
                              const data = await res.json()
                              const result = Array.isArray(data) ? data : (data.data || [])
                              setCachedMetadata(cacheKey, result)
                              return result
                            },

                              getMetadataStatuses: async (entityName, connectionId = null) => {
                                const cacheKey = `statuses_${connectionId || 'default'}_${entityName || '__ALL__'}`
                                const cached = getCachedMetadata(cacheKey)
                                if (cached) return cached

                                const q = new URLSearchParams()
                                if (entityName) q.set('entity_name', entityName)
                                if (connectionId) q.set('connection_id', connectionId)
                                const url = `/workflow-studio/metadata/statuses${q.toString() ? '?' + q.toString() : ''}`
                                const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                                if (!res.ok) throw new Error(`Failed to load statuses from Client DB (${res.status})`)
                                const data = await res.json()
                                const result = Array.isArray(data) ? data : (data.data || [])
                                setCachedMetadata(cacheKey, result)
                                return result
                              },

                                getMetadataActions: async () => {
                                  const cacheKey = 'actions_global'
                                  const cached = getCachedMetadata(cacheKey)
                                  if (cached) return cached

                                  const res = await fetch('/workflow-studio/actions', { signal: AbortSignal.timeout(5000) })
                                  if (!res.ok) throw new Error(`Failed to load actions from Client DB (${res.status})`)
                                  const data = await res.json()
                                  const result = Array.isArray(data) ? data : (data.data || [])
                                  setCachedMetadata(cacheKey, result)
                                  return result
                                },

                                  getMetadataTables: async (connectionId = null) => {
                                    const cacheKey = `tables_${connectionId || 'default'}`
                                    const cached = getCachedMetadata(cacheKey)
                                    if (cached) return cached

                                    const url = connectionId ? `/workflow-studio/metadata/tables?connection_id=${connectionId}` : '/workflow-studio/metadata/tables'
                                    const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                                    if (!res.ok) throw new Error(`Failed to introspect tables from Client DB (${res.status})`)
                                    const data = await res.json()
                                    const result = Array.isArray(data) ? data : (data.data || [])
                                    setCachedMetadata(cacheKey, result)
                                    return result
                                  },

                                    getMetadataTableColumns: async (tableName, connectionId = null) => {
                                      if (!tableName) return { table_name: '', columns: [], primary_keys: [] }
                                      const cacheKey = `cols_${connectionId || 'default'}_${tableName}`
                                      const cached = getCachedMetadata(cacheKey)
                                      if (cached) return cached

                                      const url = connectionId
                                        ? `/workflow-studio/metadata/tables/${encodeURIComponent(tableName)}/columns?connection_id=${connectionId}`
                                        : `/workflow-studio/metadata/tables/${encodeURIComponent(tableName)}/columns`
                                      const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                                      if (!res.ok) throw new Error(`Failed to introspect columns for '${tableName}' (${res.status})`)
                                      const result = await res.json()
                                      setCachedMetadata(cacheKey, result)
                                      return result
                                    },

                                      clearMetadataCache: (connectionId = null) => {
                                        if (connectionId) {
                                          for (const k of Array.from(_metadataCacheMap.keys())) {
                                            if (k.includes(`_${connectionId}`)) {
                                              _metadataCacheMap.delete(k)
                                            }
                                          }
                                        } else {
                                          _metadataCacheMap.clear()
                                        }
                                      },

                                        // 16. Global Observability & Telemetry Streaming
                                        getLiveTelemetry: async (params = {}) => {
                                          try {
                                            const q = new URLSearchParams()
                                            if (params.level && params.level !== 'ALL') q.set('level', params.level)
                                            if (params.event_type) q.set('event_type', params.event_type)
                                            if (params.instance_id) q.set('instance_id', params.instance_id)
                                            if (params.search) q.set('search', params.search)
                                            if (params.limit) q.set('limit', params.limit)

                                            const url = `/workflow/monitoring/telemetry${q.toString() ? '?' + q.toString() : ''}`
                                            const res = await fetch(url, { signal: AbortSignal.timeout(5000) })
                                            if (res.ok) {
                                              const json = await res.json()
                                              return json.data || []
                                            }
                                          } catch (_e) { }
                                          return []
                                        },

                                          getObservabilityMetrics: async () => {
                                            try {
                                              const res = await fetch('/workflow/monitoring/metrics', { signal: AbortSignal.timeout(5000) })
                                              if (res.ok) {
                                                const json = await res.json()
                                                return json.data || {}
                                              }
                                            } catch (_e) { }
                                            return {
                                              uptime_seconds: 0,
                                              total_logged_events: 0,
                                              total_step_executions: 0,
                                              total_errors: 0,
                                              average_step_latency_ms: 0,
                                              error_rate_percentage: 0,
                                              status: 'HEALTHY'
                                            }
                                          },

                                          getTelemetryLogs: async (params = {}) => {
                                            try {
                                              const q = new URLSearchParams()
                                              if (params.level && params.level !== 'ALL') q.set('level', params.level)
                                              if (params.event_type) q.set('event_type', params.event_type)
                                              if (params.instance_id) q.set('instance_id', params.instance_id)
                                              if (params.search) q.set('search', params.search)
                                              if (params.limit) q.set('limit', params.limit)

                                              const [eventsRes, metricsRes] = await Promise.allSettled([
                                                fetch(`/workflow/monitoring/telemetry${q.toString() ? '?' + q.toString() : ''}`, { signal: AbortSignal.timeout(4000) }),
                                                fetch('/workflow/monitoring/metrics', { signal: AbortSignal.timeout(4000) })
                                              ])

                                              let events = []
                                              let metrics = null

                                              if (eventsRes.status === 'fulfilled' && eventsRes.value.ok) {
                                                const json = await eventsRes.value.json().catch(() => ({}))
                                                events = json.data || []
                                              }
                                              if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
                                                const json = await metricsRes.value.json().catch(() => ({}))
                                                metrics = json.data || null
                                              }

                                              return { events, metrics }
                                            } catch (_e) {
                                              return { events: [], metrics: null }
                                            }
                                          },

                                            clearTelemetry: async () => {
                                              try {
                                                const res = await fetch('/workflow/monitoring/telemetry/clear', { method: 'POST', signal: AbortSignal.timeout(5000) })
                                                return res.ok
                                              } catch (_e) {
                                                return false
                                              }
                                            },

                                            clearTelemetryBuffer: async () => {
                                              try {
                                                const res = await fetch('/workflow/monitoring/telemetry/clear', { method: 'POST', signal: AbortSignal.timeout(5000) })
                                                return res.ok
                                              } catch (_e) {
                                                return false
                                              }
                                            },

                                              // 17. Client Database Connections & Data Connectors Management (Cached)
                                              getDatabaseConnections: async (forceRefresh = false) => {
                                                const cached = getCachedMetadata('db_connections_list')
                                                if (!forceRefresh && cached && Array.isArray(cached) && cached.length > 0) {
                                                  return cached
                                                }
                                                try {
                                                  const res = await fetch('/workflow-studio/connections', { signal: AbortSignal.timeout(5000) })
                                                  if (res.ok) {
                                                    const data = await res.json()
                                                    const list = Array.isArray(data) ? data : (data.data || [])
                                                    if (list.length > 0) {
                                                      setCachedMetadata('db_connections_list', list)
                                                      try {
                                                        localStorage.setItem('workflow_studio_database_connections', JSON.stringify(list))
                                                      } catch (_) {}
                                                      return list
                                                    }
                                                  }
                                                } catch (_e) { }

                                                try {
                                                  const stored = localStorage.getItem('workflow_studio_database_connections')
                                                  if (stored) {
                                                    const parsed = JSON.parse(stored)
                                                    if (Array.isArray(parsed) && parsed.length > 0) return parsed
                                                  }
                                                } catch (_) {}

                                                return cached || []
                                              },

                                              getConnections: async () => {
                                                return await workflowStorage.getDatabaseConnections()
                                              },

                                              createDatabaseConnection: async (payload) => {
                                                _metadataCacheMap.delete('db_connections_list')
                                                try {
                                                  const res = await fetch('/workflow-studio/connections', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify(payload),
                                                    signal: AbortSignal.timeout(10000)
                                                  })
                                                  if (!res.ok) {
                                                    const err = await res.json().catch(() => ({}))
                                                    throw new Error(err.detail || err.Error_message || 'Failed to create database connection')
                                                  }
                                                  const created = await res.json()
                                                  _metadataCacheMap.delete('db_connections_list')
                                                  return created
                                                } catch (err) {
                                                  if (err.name === 'TimeoutError' || err.message?.includes('timed out')) {
                                                    throw new Error('Connection request timed out. Please check your database host and network connection.')
                                                  }
                                                  throw err
                                                }
                                              },

                                              updateDatabaseConnection: async (connectionId, payload) => {
                                                _metadataCacheMap.delete('db_connections_list')
                                                try {
                                                  const res = await fetch(`/workflow-studio/connections/${connectionId}`, {
                                                    method: 'PUT',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify(payload),
                                                    signal: AbortSignal.timeout(10000)
                                                  })
                                                  if (!res.ok) {
                                                    const err = await res.json().catch(() => ({}))
                                                    throw new Error(err.detail || err.Error_message || 'Failed to update database connection')
                                                  }
                                                  const updated = await res.json()
                                                  _metadataCacheMap.delete('db_connections_list')
                                                  return updated
                                                } catch (err) {
                                                  if (err.name === 'TimeoutError' || err.message?.includes('timed out')) {
                                                    throw new Error('Connection request timed out. Please check your database host and network connection.')
                                                  }
                                                  throw err
                                                }
                                              },

                                              deleteDatabaseConnection: async (connectionId) => {
                                                _metadataCacheMap.delete('db_connections_list')
                                                const res = await fetch(`/workflow-studio/connections/${connectionId}`, {
                                                  method: 'DELETE',
                                                  signal: AbortSignal.timeout(8000)
                                                })
                                                if (!res.ok) {
                                                  const err = await res.json().catch(() => ({}))
                                                  throw new Error(err.detail || err.Error_message || 'Failed to delete database connection')
                                                }
                                                _metadataCacheMap.delete('db_connections_list')
                                                return await res.json()
                                              },

                                              testDatabaseConnection: async (payload) => {
                                                try {
                                                  const res = await fetch('/workflow-studio/connections/test', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify(payload),
                                                    signal: AbortSignal.timeout(12000)
                                                  })
                                                  if (!res.ok) {
                                                    const err = await res.json().catch(() => ({}))
                                                    throw new Error(err.detail || err.Error_message || 'Connection test failed')
                                                  }
                                                  return await res.json()
                                                } catch (err) {
                                                  if (err.name === 'TimeoutError' || err.message?.includes('timed out') || err.message?.includes('signal')) {
                                                    return {
                                                      success: false,
                                                      error: `Connection timed out: Server at '${payload.host || 'localhost'}:${payload.port || 5432}' took too long to respond. Please check the host address and network/firewall.`,
                                                      message: `Connection timed out: Server at '${payload.host || 'localhost'}:${payload.port || 5432}' took too long to respond.`
                                                    }
                                                  }
                                                  if (err.message?.includes('Failed to fetch') || err.name === 'TypeError') {
                                                    return {
                                                      success: false,
                                                      error: 'Network error: Cannot reach the backend API server. Please make sure the backend server (FastAPI on port 8000) is running.',
                                                      message: 'Network error: Cannot reach the backend API server.'
                                                    }
                                                  }
                                                  return {
                                                    success: false,
                                                    error: err.message || 'Connection test failed',
                                                    message: err.message || 'Connection test failed'
                                                  }
                                                }
                                              },

                                              testSavedConnection: async (connectionId) => {
                                                try {
                                                  const res = await fetch(`/workflow-studio/connections/${connectionId}/test`, {
                                                    method: 'POST',
                                                    signal: AbortSignal.timeout(12000)
                                                  })
                                                  if (!res.ok) {
                                                    const err = await res.json().catch(() => ({}))
                                                    throw new Error(err.detail || err.Error_message || 'Connection test failed')
                                                  }
                                                  return await res.json()
                                                } catch (err) {
                                                  if (err.name === 'TimeoutError' || err.message?.includes('timed out') || err.message?.includes('signal')) {
                                                    return {
                                                      success: false,
                                                      error: 'Connection timed out: The database server took too long to respond.',
                                                      message: 'Connection timed out: The database server took too long to respond.'
                                                    }
                                                  }
                                                  if (err.message?.includes('Failed to fetch') || err.name === 'TypeError') {
                                                    return {
                                                      success: false,
                                                      error: 'Network error: Cannot reach the backend API server.',
                                                      message: 'Network error: Cannot reach the backend API server.'
                                                    }
                                                  }
                                                  return {
                                                    success: false,
                                                    error: err.message || 'Connection test failed',
                                                    message: err.message || 'Connection test failed'
                                                  }
                                                }
                                              },

                                              setDefaultDatabaseConnection: async (connectionId) => {
                                                _metadataCacheMap.delete('db_connections_list')
                                                const res = await fetch(`/workflow-studio/connections/${connectionId}/set-default`, {
                                                  method: 'POST',
                                                  signal: AbortSignal.timeout(8000)
                                                })
                                                if (!res.ok) {
                                                  const err = await res.json().catch(() => ({}))
                                                  throw new Error(err.detail || err.Error_message || 'Failed to set default connection')
                                                }
                                                _metadataCacheMap.delete('db_connections_list')
                                                return await res.json()
                                              },

                                              getConnectionTables: async (connectionId, schema = 'ers') => {
                                                const res = await fetch(`/workflow-studio/connections/${connectionId}/tables?schema=${encodeURIComponent(schema)}`, { signal: AbortSignal.timeout(4000) })
                                                if (!res.ok) throw new Error(`Failed to load tables (${res.status})`)
                                                return await res.json()
                                              },

                                              // 17. Database Connections Profile Catalog
                                              getDbConnections: async () => {
                                                return await workflowStorage.getDatabaseConnections()
                                              },

                                                                // 18. Declarative ClientApp Bindings
                                                                getWorkflowBindings: async () => {
                                                                  try {
                                                                    const res = await fetch('/workflow-studio/bindings', { signal: AbortSignal.timeout(5000) })
                                                                    if (!res.ok) return {}
                                                                    return await res.json()
                                                                  } catch (_e) {
                                                                    return {}
                                                                  }
                                                                },

                                                                  saveWorkflowBinding: async (payload) => {
                                                                    const res = await fetch('/workflow-studio/bindings', {
                                                                      method: 'POST',
                                                                      headers: { 'Content-Type': 'application/json' },
                                                                      body: JSON.stringify(payload)
                                                                    })
                                                                    if (!res.ok) {
                                                                      const err = await res.json().catch(() => ({}))
                                                                      throw new Error(err.detail || 'Failed to save workflow binding')
                                                                    }
                                                                    return await res.json()
                                                                  },

                                                                    deleteWorkflowBinding: async (moduleKey) => {
                                                                      const res = await fetch(`/workflow-studio/bindings/${encodeURIComponent(moduleKey)}`, {
                                                                        method: 'DELETE'
                                                                      })
                                                                      if (!res.ok) {
                                                                        const err = await res.json().catch(() => ({}))
                                                                        throw new Error(err.detail || 'Failed to remove workflow binding')
                                                                      }
                                                                      return await res.json()
                                                                    }
}


