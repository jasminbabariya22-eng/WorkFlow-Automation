
import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Background,
  MiniMap,
  useReactFlow
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import {
  ArrowLeft,
  Save,
  Check,
  CheckSquare,
  Play,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Undo2,
  Redo2,
  Sparkles,
  Trash2,
  Zap,
  AlertCircle,
  X,
  Grid,
  MoreVertical,
  Download,
  Upload,
  RotateCcw,
  CheckCircle2,
  Loader,
  RefreshCw,
  Database,
  Clock,
  ChevronRight,
  Activity,
  FileText,
  CheckCircle,
  XCircle,
  GitFork
} from 'lucide-react'

import NodeLibrary from './NodeLibrary'
import PropertiesPanel from './PropertiesPanel'
import DesignerHeader from './designer/DesignerHeader'
import DesignerValidationModal from './designer/DesignerValidationModal'
import DesignerTestRunnerModal from './designer/DesignerTestRunnerModal'
import { workflowStorage } from '../services/workflowStorage'
import {
  StartNode,
  EndNode,
  UserTaskNode,
  ApprovalNode,
  ConditionNode,
  SwitchNode,
  ParallelNode,
  CommunicationNode,
  RecordNode,
  ActionNode,
  WorkflowEdge
} from './nodes/CustomNodes'

// Register all generic Node Types
const nodeTypes = {
  start: StartNode,
  end: EndNode,
  userTask: UserTaskNode,
  approval: ApprovalNode,
  condition: ConditionNode,
  switch: SwitchNode,
  parallel: ParallelNode,
  communication: CommunicationNode,
  email: CommunicationNode,
  sendEmail: CommunicationNode,
  sendTask: CommunicationNode,
  notification: CommunicationNode,
  record: RecordNode,
  action: ActionNode,
  generic: UserTaskNode
}

// Register Custom Edge Types
const edgeTypes = {
  workflow: WorkflowEdge
}

// Generic 3-Tier Enterprise Approval Process Template (Loaded explicitly on user action)
const GENERIC_APPROVAL_TEMPLATE_NODES = [
  {
    id: 'node-start',
    type: 'start',
    position: { x: 260, y: 20 },
    data: {
      label: 'Start',
      description: 'Workflow activation entry point',
      trigger: 'Workflow Activated'
    }
  },
  {
    id: 'node-submit',
    type: 'userTask',
    position: { x: 240, y: 150 },
    data: {
      label: 'Submit Request',
      assignment: {
        type: 'role',
        roleId: '1',
        roleName: 'Initiator'
      },
      visibility: ['OWNER'],
      actions: ['SAVE_DRAFT', 'SUBMIT'],
      description: 'Initiator submits process payload'
    }
  },
  {
    id: 'node-cond-submit',
    type: 'condition',
    position: { x: 240, y: 350 },
    data: {
      label: 'Action Router (Submit)',
      description: 'Route Draft or Submit action',
      actions: ['SAVE_DRAFT', 'SUBMIT']
    }
  },
  {
    id: 'node-manager-review',
    type: 'userTask',
    position: { x: 580, y: 350 },
    data: {
      label: 'Manager Review',
      assignment: {
        type: 'role',
        roleId: '2',
        roleName: 'MANAGER'
      },
      visibility: ['APPROVER'],
      actions: ['APPROVE', 'REJECT'],
      description: 'Manager review & validation gate'
    }
  },
  {
    id: 'node-cond-manager',
    type: 'condition',
    position: { x: 240, y: 550 },
    data: {
      label: 'Action Router (Manager)',
      description: 'Route Manager Approve or Reject action',
      actions: ['APPROVE', 'REJECT']
    }
  },
  {
    id: 'node-exec-approval',
    type: 'userTask',
    position: { x: 580, y: 550 },
    data: {
      label: 'Executive Signoff',
      assignment: {
        type: 'role',
        roleId: '3',
        roleName: 'EXECUTIVE'
      },
      visibility: ['APPROVER'],
      actions: ['APPROVE', 'REJECT'],
      description: 'Final executive authorization'
    }
  },
  {
    id: 'node-cond-exec',
    type: 'condition',
    position: { x: 240, y: 770 },
    data: {
      label: 'Action Router (Executive)',
      description: 'Route Executive Approve or Reject action',
      actions: ['APPROVE', 'REJECT']
    }
  },
  {
    id: 'node-end',
    type: 'end',
    position: { x: 580, y: 770 },
    data: {
      label: 'Workflow Complete',
      description: 'Workflow execution formally completed',
      outcome: 'APPROVED'
    }
  }
]

const GENERIC_APPROVAL_TEMPLATE_EDGES = [
  {
    id: 'e-start-submit',
    source: 'node-start',
    sourceHandle: 'WORKFLOW_INITIALIZED',
    target: 'node-submit',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Activate', action: 'WORKFLOW_INITIALIZED' }
  },
  {
    id: 'e-submit-cond',
    source: 'node-submit',
    sourceHandle: 'output',
    target: 'node-cond-submit',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Next', action: 'output' }
  },
  {
    id: 'e-cond-submit-draft',
    source: 'node-cond-submit',
    sourceHandle: 'SAVE_DRAFT',
    target: 'node-submit',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Draft', action: 'SAVE_DRAFT' }
  },
  {
    id: 'e-cond-submit-action',
    source: 'node-cond-submit',
    sourceHandle: 'SUBMIT',
    target: 'node-manager-review',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Submit', action: 'SUBMIT' }
  },
  {
    id: 'e-manager-cond',
    source: 'node-manager-review',
    sourceHandle: 'output',
    target: 'node-cond-manager',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Next', action: 'output' }
  },
  {
    id: 'e-cond-manager-reject',
    source: 'node-cond-manager',
    sourceHandle: 'REJECT',
    target: 'node-submit',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Reject', action: 'REJECT' }
  },
  {
    id: 'e-cond-manager-approve',
    source: 'node-cond-manager',
    sourceHandle: 'APPROVE',
    target: 'node-exec-approval',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Approve', action: 'APPROVE' }
  },
  {
    id: 'e-exec-cond',
    source: 'node-exec-approval',
    sourceHandle: 'output',
    target: 'node-cond-exec',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Next', action: 'output' }
  },
  {
    id: 'e-cond-exec-reject',
    source: 'node-cond-exec',
    sourceHandle: 'REJECT',
    target: 'node-submit',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Reject', action: 'REJECT' }
  },
  {
    id: 'e-cond-exec-approve',
    source: 'node-cond-exec',
    sourceHandle: 'APPROVE',
    target: 'node-end',
    targetHandle: 'input',
    type: 'workflow',
    data: { label: 'Approve', action: 'APPROVE' }
  }
]

function DesignerCanvas({ workflowId, onClose, showToast }) {
  const reactFlowWrapper = useRef(null)
  const fileInputRef = useRef(null)
  const { screenToFlowPosition, fitView, zoomIn, zoomOut, getViewport } = useReactFlow()

  // Primary Canvas State (empty by default on initial page load / refresh)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Selection state
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedEdge, setSelectedEdge] = useState(null)

  // Workflow metadata (read-only from backend)
  const [workflowName, setWorkflowName] = useState('New Workflow')
  const [versionNumber, setVersionNumber] = useState(1)
  const [workflowStatus, setWorkflowStatus] = useState('Draft')
  const [workflowConnectionId, setWorkflowConnectionId] = useState(null)

  // Loading & Save State
  const [isLoading, setIsLoading] = useState(false)
  const [saveStatus, setSaveStatus] = useState('idle') // idle | dirty | saving | saved | error
  const isInitializingRef = useRef(true)
  const saveInFlightRef = useRef(false)
  const saveQueuedRef = useRef(false)
  const autoSaveTimerRef = useRef(null)

  // Canvas Settings
  const [showGrid, setShowGrid] = useState(true)
  const [showMoreMenu, setShowMoreMenu] = useState(false)

  // Modals & Panels
  const [showTestModal, setShowTestModal] = useState(false)
  const [validationErrors, setValidationErrors] = useState([])
  const [isValidationOpen, setIsValidationOpen] = useState(false)

  // ==========================================
  // Generic Live Test Runner & DB Inspector State
  // ==========================================
  const [testRecordId, setTestRecordId] = useState(273)
  const [testRecordData, setTestRecordData] = useState(null)
  const [testLoading, setTestLoading] = useState(false)
  const [testSubTab, setTestSubTab] = useState('interactive') // 'interactive' | 'transactions'
  const [testTxLogs, setTestTxLogs] = useState([])

  // Generic Workflow Graph Traversal Engine
  const [simActiveNodeId, setSimActiveNodeId] = useState(null)
  const [simHistory, setSimHistory] = useState([])
  const [simStatus, setSimStatus] = useState('IDLE') // 'IDLE' | 'RUNNING' | 'COMPLETED' | 'REJECTED'
  const [simVars, setSimVars] = useState({})

  const fetchRecordState = useCallback(async (recId) => {
    const idToFetch = recId !== undefined ? recId : testRecordId
    if (!idToFetch) return
    setTestLoading(true)
    try {
      const foundNode = nodes.find(n => n.data?.table || n.data?.table_name || n.data?.target_entity || n.data?.entity)
      const rawTbl = foundNode ? (foundNode.data?.table || foundNode.data?.table_name || foundNode.data?.target_entity || foundNode.data?.entity) : ''
      const canvasTable = (rawTbl && String(rawTbl).trim() !== 'undefined' && String(rawTbl).trim() !== 'null') ? String(rawTbl).trim() : 'leave_requests'
      const connParam = workflowConnectionId ? `&connection_id=${workflowConnectionId}` : ''
      const res = await fetch(`/workflow-studio/test/record-state?record_id=${idToFetch}&table_name=${encodeURIComponent(canvasTable)}${connParam}`)
      const data = await res.json()
      if (res.ok && data.success) {
        setTestRecordData(data)
        if (data.primary_key_val && Number(data.primary_key_val) !== Number(idToFetch)) {
          setTestRecordId(data.primary_key_val)
        }
      } else {
        showToast(data.detail || 'Failed to load record state', 'error')
      }
    } catch (err) {
      showToast('Error connecting to Client Database: ' + err.message, 'error')
    } finally {
      setTestLoading(false)
    }
  }, [testRecordId, nodes, workflowConnectionId])

  const handleResetTestRecord = useCallback(async () => {
    if (!testRecordId) return
    setTestLoading(true)
    try {
      const foundNode = nodes.find(n => n.data?.table || n.data?.table_name || n.data?.target_entity || n.data?.entity)
      const rawTbl = foundNode ? (foundNode.data?.table || foundNode.data?.table_name || foundNode.data?.target_entity || foundNode.data?.entity) : ''
      const canvasTable = (rawTbl && String(rawTbl).trim() !== 'undefined' && String(rawTbl).trim() !== 'null') ? String(rawTbl).trim() : 'leave_requests'
      const res = await fetch('/workflow-studio/test/reset-record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          record_id: Number(testRecordId),
          table_name: canvasTable,
          connection_id: workflowConnectionId
        })
      })
      const data = await res.json()
      if (res.ok && data.success) {
        showToast(`Record #${testRecordId} in '${canvasTable}' successfully reset`, 'success')
        await fetchRecordState(testRecordId)
        setTestTxLogs(prev => [
          {
            timestamp: new Date().toLocaleTimeString(),
            action: 'RESET_RECORD',
            sql: `UPDATE ${canvasTable} SET status=PENDING WHERE primary_key=${testRecordId}`,
            status: 'COMMITTED',
            duration: '7.2ms',
            message: `Record #${testRecordId} in '${canvasTable}' reset to initial state`
          },
          ...prev
        ])
        // Re-initialize generic simulation
        startGenericSimulation()
      } else {
        showToast(data.detail || 'Reset failed', 'error')
      }
    } catch (err) {
      showToast('Error resetting record: ' + err.message, 'error')
    } finally {
      setTestLoading(false)
    }
  }, [testRecordId, nodes, workflowConnectionId, fetchRecordState])

  // Initialize Generic Workflow Simulation from Start Node
  const startGenericSimulation = useCallback(() => {
    const startNode = nodes.find(n => n.type === 'start' || n.type === 'startevent' || n.id.startsWith('start')) || nodes[0]
    if (!startNode) {
      showToast('No start node found in workflow diagram', 'error')
      return
    }

    const outgoing = edges.filter(e => e.source === startNode.id)
    const firstTarget = outgoing.length > 0 ? nodes.find(n => n.id === outgoing[0].target) : null

    setSimVars({ entity_id: testRecordId, user_id: 1 })
    setSimStatus('RUNNING')
    setSimHistory([
      {
        nodeId: startNode.id,
        nodeName: startNode.data?.label || startNode.data?.name || 'Start Process',
        nodeType: 'start',
        timestamp: new Date().toLocaleTimeString(),
        message: 'Process execution started'
      }
    ])

    if (firstTarget) {
      setSimActiveNodeId(firstTarget.id)
    } else {
      setSimActiveNodeId(startNode.id)
    }
  }, [nodes, edges, testRecordId, showToast])

  // Execute an action on the currently active node and advance dynamically
  const handleGenericNodeAction = useCallback(async (currentNode, actionChosen) => {
    if (!currentNode) return
    setTestLoading(true)

    const updatedVars = { ...simVars }
    if (actionChosen) {
      updatedVars.action = actionChosen
    }
    const currentType = currentNode.type
    const nodeLabel = currentNode.data?.label || currentNode.data?.name || currentType

    let stepLog = {
      nodeId: currentNode.id,
      nodeName: nodeLabel,
      nodeType: currentType,
      action: actionChosen || 'EXECUTE',
      timestamp: new Date().toLocaleTimeString()
    }

    try {
      // 1. Database Update Node
      if (currentType === 'record' || currentType === 'dbUpdate') {
        const mappings = currentNode.data?.fieldMappings || []
        const table = currentNode.data?.table || currentNode.data?.table_name || 'leave_requests'

        const res = await fetch('/workflow-studio/test/execute-generic-node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            record_id: Number(testRecordId),
            table_name: table,
            field_mappings: mappings,
            node_id: currentNode.id,
            node_name: nodeLabel,
            node_type: currentType,
            action: actionChosen || 'UPDATE',
            connection_id: workflowConnectionId
          })
        })
        const data = await res.json()
        if (res.ok && data.success) {
          stepLog.sql = data.sql_executed ? data.sql_executed.join('; ') : ''
          stepLog.diff = data.diff_fields
          stepLog.status = 'COMMITTED'
          stepLog.duration = `${data.duration_ms}ms`
          stepLog.message = data.message
          await fetchRecordState(testRecordId)
        }
      }
      // 2. Notification / Email Node
      else if (currentType === 'communication' || currentType === 'notification' || currentType === 'email') {
        const to = currentNode.data?.to || currentNode.data?.recipient || '{{employee_email}}'
        const subject = currentNode.data?.subject || `Notification for Record #{{workflow.entity_id}}`
        const body = currentNode.data?.body || 'Your request #{{workflow.entity_id}} has been processed successfully.'

        const res = await fetch('/workflow-studio/test/execute-generic-node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            record_id: Number(testRecordId),
            node_id: currentNode.id,
            node_name: nodeLabel,
            node_type: 'communication',
            to: to,
            subject: subject,
            body: body,
            action: actionChosen || 'SEND',
            connection_id: workflowConnectionId
          })
        })
        const data = await res.json()
        if (res.ok && data.success) {
          stepLog.sql = data.sql_executed ? data.sql_executed.join('; ') : ''
          stepLog.status = 'DISPATCHED'
          stepLog.duration = `${data.duration_ms}ms`
          stepLog.message = `📧 Dispatched Email to: ${data.email_job?.email_to || to} (Subject: "${subject}")`
          await fetchRecordState(testRecordId)
        } else {
          stepLog.message = `📧 Notification to: ${to} (Subject: "${subject}")`
          stepLog.status = 'SENT'
        }
      }
      // 3. User Task or Approval Node
      else if (currentType === 'userTask' || currentType === 'approval') {
        stepLog.message = `User Task '${nodeLabel}' submitted by ${currentNode.data?.role || 'Reviewer'} with action: [${actionChosen}]`
        stepLog.status = 'SUBMITTED'
      }
      // 4. Condition / Decision Gateway Node
      else if (currentType === 'condition') {
        const field = currentNode.data?.field || 'action'
        const expected = currentNode.data?.value || 'APPROVE'
        const actual = updatedVars[field]
        const isMatch = String(actual || '').toUpperCase() === String(expected || '').toUpperCase()
        stepLog.message = `Evaluated condition (${field} == '${expected}'): Result = ${isMatch ? 'TRUE' : 'FALSE'}`
        stepLog.result = isMatch ? 'TRUE' : 'FALSE'
      }

      setTestTxLogs(prev => [stepLog, ...prev])
      setSimHistory(prev => [...prev, stepLog])
      setSimVars(updatedVars)

      // Determine Next Connected Node dynamically based on outgoing edges
      const outgoingEdges = edges.filter(e => e.source === currentNode.id)
      let nextEdge = null

      if (currentType === 'condition') {
        const field = currentNode.data?.field || 'action'
        const expected = currentNode.data?.value || 'APPROVE'
        const actual = updatedVars[field]
        const isMatch = String(actual || '').toUpperCase() === String(expected || '').toUpperCase()

        nextEdge = outgoingEdges.find(e => {
          const sh = (e.sourceHandle || '').toUpperCase()
          const lbl = (e.label || e.data?.label || '').toUpperCase()
          if (isMatch) {
            return sh === 'TRUE' || lbl.includes('TRUE') || lbl.includes('APPROVE')
          } else {
            return sh === 'FALSE' || lbl.includes('FALSE') || lbl.includes('REJECT')
          }
        }) || outgoingEdges[0]
      } else if (actionChosen) {
        nextEdge = outgoingEdges.find(e => {
          const sh = (e.sourceHandle || '').toUpperCase()
          const lbl = (e.label || e.data?.label || '').toUpperCase()
          const act = (actionChosen || '').toUpperCase()
          return sh === act || lbl.includes(act)
        }) || outgoingEdges[0]
      } else {
        nextEdge = outgoingEdges[0]
      }

      if (nextEdge) {
        const nextNode = nodes.find(n => n.id === nextEdge.target)
        if (nextNode) {
          setSimActiveNodeId(nextNode.id)
          if (nextNode.type === 'end') {
            const endLabel = (nextNode.data?.label || nextNode.data?.name || '').toLowerCase()
            setSimStatus(endLabel.includes('reject') || endLabel.includes('terminate') ? 'REJECTED' : 'COMPLETED')
          }
        } else {
          setSimStatus('COMPLETED')
        }
      } else {
        setSimStatus('COMPLETED')
      }
    } catch (err) {
      showToast('Simulation step error: ' + err.message, 'error')
    } finally {
      setTestLoading(false)
    }
  }, [simVars, edges, nodes, testRecordId, fetchRecordState, showToast])

  useEffect(() => {
    if (showTestModal) {
      fetchRecordState(testRecordId)
      startGenericSimulation()
    }
  }, [showTestModal])

  // Undo / Redo History Stack
  const historyRef = useRef([{ nodes: [], edges: [] }])
  const historyIndexRef = useRef(0)
  const isHistoryActionRef = useRef(false)

  const pushHistoryState = useCallback((newNodes, newEdges) => {
    if (isHistoryActionRef.current) return
    const nextHistory = historyRef.current.slice(0, historyIndexRef.current + 1)
    nextHistory.push({ nodes: newNodes, edges: newEdges })
    historyRef.current = nextHistory
    historyIndexRef.current = nextHistory.length - 1
  }, [])

  const handleUndo = useCallback(() => {
    if (historyIndexRef.current > 0) {
      isHistoryActionRef.current = true
      historyIndexRef.current -= 1
      const state = historyRef.current[historyIndexRef.current]
      setNodes(state.nodes)
      setEdges(state.edges)
      setSelectedNode(null)
      setSelectedEdge(null)
      setTimeout(() => { isHistoryActionRef.current = false }, 50)
      showToast('Undo action', 'info')
    }
  }, [setNodes, setEdges, showToast])

  const handleRedo = useCallback(() => {
    if (historyIndexRef.current < historyRef.current.length - 1) {
      isHistoryActionRef.current = true
      historyIndexRef.current += 1
      const state = historyRef.current[historyIndexRef.current]
      setNodes(state.nodes)
      setEdges(state.edges)
      setSelectedNode(null)
      setSelectedEdge(null)
      setTimeout(() => { isHistoryActionRef.current = false }, 50)
      showToast('Redo action', 'info')
    }
  }, [setNodes, setEdges, showToast])

  // =========================================================================
  // WORKFLOW LOADING FROM LOCAL STORAGE / DEFINITIONS
  // =========================================================================
  useEffect(() => {
    let isCancelled = false
    setIsLoading(true)
    isInitializingRef.current = true

    const doLoad = async () => {
      try {
        const data = workflowId ? await workflowStorage.getWorkflowById(workflowId) : null
        if (isCancelled) return

        if (data) {
          setWorkflowName(data.name || data.spec_id || 'Untitled Workflow')
          setVersionNumber(data.version || 1)
          setWorkflowStatus(data.status || 'Draft')
          setWorkflowConnectionId(data.connection_id || null)

          let loadedNodes = []
          let loadedEdges = []
          if (data.json_content) {
            try {
              const parsed = typeof data.json_content === 'string' ? JSON.parse(data.json_content) : data.json_content
              const rawNodes = parsed.nodes || []
              loadedNodes = rawNodes.map((n, idx) => ({
                id: String(n.id || `node-${idx}`),
                type: n.type || 'generic',
                position: {
                  x: n.position?.x ?? (n.position_x ?? 250 + (idx % 2) * 200),
                  y: n.position?.y ?? (n.position_y ?? 50 + idx * 120)
                },
                data: {
                  label: n.data?.label || n.name || n.id,
                  name: n.data?.name || n.name || n.id,
                  ...(n.data || n.config || {})
                }
              }))
              loadedEdges = (parsed.edges || parsed.connections || []).map((e, idx) => ({
                id: e.id || `e-${e.source}-${e.target}-${idx}`,
                source: String(e.source),
                target: String(e.target),
                type: e.type || 'workflow',
                data: e.data || { label: e.label || e.condition || '' }
              }))
            } catch (e) {
              console.error('Failed to parse json_content:', e)
            }
          }
          setNodes(loadedNodes)
          setEdges(loadedEdges)
          setSaveStatus('saved')
          historyRef.current = [{ nodes: loadedNodes, edges: loadedEdges }]
          historyIndexRef.current = 0
          setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 200)
        } else {
          setNodes([])
          setEdges([])
          setWorkflowName('New Workflow')
          setWorkflowConnectionId(null)
          setSaveStatus('saved')
          historyRef.current = [{ nodes: [], edges: [] }]
          historyIndexRef.current = 0
          setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 200)
        }
      } catch (err) {
        console.error('Error loading workflow:', err)
        if (!isCancelled) {
          setNodes([])
          setEdges([])
          setSaveStatus('saved')
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
          setTimeout(() => { isInitializingRef.current = false }, 500)
        }
      }
    }

    doLoad()
    return () => { isCancelled = true }
  }, [workflowId, fitView, setNodes, setEdges])

  // =========================================================================
  // UNIFIED SAVE FUNCTION (used by both manual save and auto-save)
  // =========================================================================
  const saveWorkflow = useCallback(async () => {
    if (!workflowId) return
    setSaveStatus('saving')

    try {
      await workflowStorage.saveWorkflow(workflowId, {
        name: workflowName,
        connection_id: workflowConnectionId,
        json_content: JSON.stringify({ nodes, edges })
      })
      setSaveStatus('saved')
    } catch (_err) {
      setSaveStatus('error')
      showToast('Error while saving workflow', 'error')
    }
  }, [workflowId, workflowName, workflowConnectionId, nodes, edges, showToast])

  // =========================================================================
  // AUTO-SAVE WITH DEBOUNCE (1000ms)
  // =========================================================================
  useEffect(() => {
    // Skip during initialization (workflow loading)
    if (isInitializingRef.current) return
    // Skip if canvas is empty (no meaningful changes)
    if (nodes.length === 0 && edges.length === 0) return

    // Mark as dirty
    setSaveStatus('dirty')

    // Clear previous debounce timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current)
    }

    // Set new debounce timer
    autoSaveTimerRef.current = setTimeout(() => {
      saveWorkflow()
    }, 1000)

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [nodes, edges, saveWorkflow])

  // =========================================================================
  // UNSAVED CHANGES WARNING (beforeunload)
  // =========================================================================
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (saveStatus === 'dirty' || saveStatus === 'saving') {
        e.preventDefault()
        e.returnValue = 'You have unsaved changes.'
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [saveStatus])


  const handleDeleteNode = useCallback((nodeId) => {
    setNodes((nds) => {
      const filtered = nds.filter((n) => n.id !== nodeId)
      setEdges((eds) => {
        const filteredEdges = eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
        pushHistoryState(filtered, filteredEdges)
        return filteredEdges
      })
      return filtered
    })
    setSelectedNode((curr) => (curr && curr.id === nodeId ? null : curr))
    showToast('Node removed from canvas', 'info')
  }, [setNodes, setEdges, pushHistoryState, showToast])

  // Duplicate Node
  const handleDuplicateNode = useCallback((nodeId) => {
    const targetNode = nodes.find(n => n.id === nodeId)
    if (!targetNode) return

    const newId = `${targetNode.type}-${Date.now()}`
    const duplicatedNode = {
      ...targetNode,
      id: newId,
      position: {
        x: targetNode.position.x + 30,
        y: targetNode.position.y + 30
      },
      selected: true,
      data: {
        ...targetNode.data,
        label: `${targetNode.data?.label || targetNode.data?.name || 'Node'} (Copy)`
      }
    }

    setNodes((nds) => {
      const nextNodes = nds.map(n => ({ ...n, selected: false })).concat(duplicatedNode)
      pushHistoryState(nextNodes, edges)
      return nextNodes
    })
    setSelectedNode(duplicatedNode)
    setSelectedEdge(null)
    showToast(`Duplicated ${targetNode.data?.label || 'node'}`, 'success')
  }, [nodes, edges, setNodes, pushHistoryState, showToast])

  // Attach node callbacks and dynamic Action Router derivation for Condition nodes
  const enrichedNodes = useMemo(() => {
    return nodes.map(node => {
      let derivedActions = node.data?.actions || ['APPROVE', 'REJECT']
      let upstreamTaskName = null

      if (node.type === 'condition') {
        const incomingEdge = edges.find(e => e.target === node.id)
        if (incomingEdge) {
          const upstreamNode = nodes.find(n => n.id === incomingEdge.source)
          if (upstreamNode && upstreamNode.type === 'userTask') {
            upstreamTaskName = upstreamNode.data?.label || upstreamNode.data?.name || 'User Task'
            if (Array.isArray(upstreamNode.data?.actions) && upstreamNode.data.actions.length > 0) {
              derivedActions = upstreamNode.data.actions
            }
          }
        }
      }

      return {
        ...node,
        data: {
          ...node.data,
          derivedActions,
          upstreamTaskName,
          onDuplicate: handleDuplicateNode,
          onDelete: handleDeleteNode
        }
      }
    })
  }, [nodes, edges, handleDuplicateNode, handleDeleteNode])

  // Current selected node with enriched data
  const selectedEnrichedNode = useMemo(() => {
    if (!selectedNode) return null
    return enrichedNodes.find(n => n.id === selectedNode.id) || selectedNode
  }, [selectedNode, enrichedNodes])

  // Connection validator
  const isValidConnection = useCallback((connection) => {
    // 1. Start node cannot have incoming connections
    const targetNode = nodes.find(n => n.id === connection.target)
    if (targetNode && targetNode.type === 'start') {
      return false
    }
    // 2. Condition node accepts only 1 incoming connection
    if (targetNode && targetNode.type === 'condition') {
      const existingIncoming = edges.filter(e => e.target === connection.target)
      if (existingIncoming.length >= 1) {
        return false
      }
    }
    // 3. End node cannot have outgoing connections
    const sourceNode = nodes.find(n => n.id === connection.source)
    if (sourceNode && sourceNode.type === 'end') {
      return false
    }
    // 4. Start and User Task nodes can only have one outgoing connection
    if (sourceNode && (sourceNode.type === 'start' || sourceNode.type === 'userTask')) {
      const existingOutgoing = edges.filter(e => e.source === connection.source)
      if (existingOutgoing.length >= 1) {
        return false
      }
    }
    // 5. Condition node cannot have duplicate outgoing connections from the same sourceHandle
    if (sourceNode && sourceNode.type === 'condition') {
      const existingSameHandle = edges.filter(e => e.source === connection.source && e.sourceHandle === connection.sourceHandle)
      if (existingSameHandle.length >= 1) {
        return false
      }
    }
    return true
  }, [nodes, edges])

  // Handle Connections between Nodes (stores sourceHandle as outcome action)
  const onConnect = useCallback((params) => {
    const targetNode = nodes.find(n => n.id === params.target)
    if (targetNode && targetNode.type === 'start') {
      showToast('Start node cannot have incoming connections', 'error')
      return
    }
    if (targetNode && targetNode.type === 'condition') {
      const existingIncoming = edges.filter(e => e.target === params.target)
      if (existingIncoming.length >= 1) {
        showToast('Condition node accepts only one incoming connection', 'error')
        return
      }
    }
    const sourceNode = nodes.find(n => n.id === params.source)
    if (sourceNode && sourceNode.type === 'end') {
      showToast('End node cannot have outgoing connections', 'error')
      return
    }
    if (sourceNode && sourceNode.type === 'start') {
      const existingOutgoing = edges.filter(e => e.source === params.source)
      if (existingOutgoing.length >= 1) {
        showToast('Start node can only have one outgoing connection', 'error')
        return
      }
    }
    if (sourceNode && sourceNode.type === 'userTask') {
      const existingOutgoing = edges.filter(e => e.source === params.source)
      if (existingOutgoing.length >= 1) {
        showToast('User Task can only have one outgoing connection', 'error')
        return
      }
    }
    if (sourceNode && sourceNode.type === 'condition') {
      const existingSameHandle = edges.filter(e => e.source === params.source && e.sourceHandle === params.sourceHandle)
      if (existingSameHandle.length >= 1) {
        showToast(`Action "${params.sourceHandle}" already has an outgoing connection`, 'error')
        return
      }
    }

    let actionLabel = params.sourceHandle || 'Next'
    if (actionLabel === 'output') actionLabel = 'Next'
    if (actionLabel === 'WORKFLOW_INITIALIZED' || actionLabel === 'trigger') actionLabel = 'WORKFLOW_INITIALIZED'
    if (actionLabel === 'SAVE_DRAFT') actionLabel = 'Save Draft'
    if (actionLabel === 'SUBMIT') actionLabel = 'Submit'
    if (actionLabel === 'APPROVE') actionLabel = 'Approve'
    if (actionLabel === 'REJECT') actionLabel = 'Reject'
    if (actionLabel === 'FORCE_APPROVE') actionLabel = 'Force Approve'
    if (actionLabel.includes('_') && actionLabel !== 'WORKFLOW_INITIALIZED') actionLabel = actionLabel.replace(/_/g, ' ')

    const newEdge = {
      ...params,
      id: `e-${params.source}-${params.sourceHandle || 'main'}-${params.target}-${Date.now()}`,
      type: 'workflow',
      data: { label: actionLabel, action: params.sourceHandle }
    }
    setEdges((eds) => {
      const nextEdges = addEdge(newEdge, eds)
      pushHistoryState(nodes, nextEdges)
      return nextEdges
    })
    showToast(`Connected action route: ${actionLabel}`, 'success')
  }, [nodes, edges, setEdges, pushHistoryState, showToast])

  // Handle Node Selection
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
    setSelectedEdge(null)
  }, [])

  // Handle Edge Selection
  const onEdgeClick = useCallback((event, edge) => {
    setSelectedEdge(edge)
    setSelectedNode(null)
  }, [])

  // Handle Canvas Background Click (Deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedEdge(null)
  }, [])

  // Drag and Drop from Node Library
  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((event) => {
    event.preventDefault()

    const rawData = event.dataTransfer.getData('application/reactflow')
    if (!rawData) return

    try {
      const item = JSON.parse(rawData)
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      const newNodeId = `${item.type}-${Date.now()}`
      const defaultLabel = item.defaultData?.label || item.name || 'Node'
      const newNode = {
        id: newNodeId,
        type: item.type,
        position,
        selected: true,
        data: {
          ...item.defaultData,
          label: defaultLabel,
          name: defaultLabel
        }
      }

      setNodes((nds) => {
        const nextNodes = nds.map(n => ({ ...n, selected: false })).concat(newNode)
        pushHistoryState(nextNodes, edges)
        return nextNodes
      })
      setSelectedNode(newNode)
      setSelectedEdge(null)
      showToast(`Added ${defaultLabel} to canvas`, 'success')
    } catch (e) {
      console.error('Failed to parse dropped node', e)
    }
  }, [screenToFlowPosition, setNodes, edges, pushHistoryState, showToast])

  // Click-to-add node in viewport center
  const handleAddNodeFromClick = useCallback((item) => {
    const viewport = getViewport()
    const x = -viewport.x / viewport.zoom + 250
    const y = -viewport.y / viewport.zoom + 150

    const newNodeId = `${item.type}-${Date.now()}`
    const defaultLabel = item.defaultData?.label || item.name || 'Node'
    const newNode = {
      id: newNodeId,
      type: item.type,
      position: { x, y },
      selected: true,
      data: {
        ...item.defaultData,
        label: defaultLabel,
        name: defaultLabel
      }
    }

    setNodes((nds) => {
      const nextNodes = nds.map(n => ({ ...n, selected: false })).concat(newNode)
      pushHistoryState(nextNodes, edges)
      return nextNodes
    })
    setSelectedNode(newNode)
    setSelectedEdge(null)
    showToast(`Added ${defaultLabel} to canvas`, 'success')
  }, [getViewport, setNodes, edges, pushHistoryState, showToast])

  // Update Node Data from Properties Panel
  const handleUpdateNodeData = useCallback((nodeId, nextData) => {
    setNodes((nds) => {
      const nextNodes = nds.map((node) => {
        if (node.id === nodeId) {
          const updatedType = nextData.nodeType || node.type
          return {
            ...node,
            type: updatedType,
            data: {
              ...node.data,
              ...nextData
            }
          }
        }
        return node
      })
      pushHistoryState(nextNodes, edges)
      return nextNodes
    })
    setSelectedNode((prev) => (prev && prev.id === nodeId ? { ...prev, data: { ...prev.data, ...nextData } } : prev))
  }, [setNodes, edges, pushHistoryState])

  // Update Edge Data from Properties Panel
  const handleUpdateEdgeData = useCallback((edgeId, nextData) => {
    setEdges((eds) => {
      const nextEdges = eds.map((edge) => {
        if (edge.id === edgeId) {
          return {
            ...edge,
            data: { ...edge.data, ...nextData }
          }
        }
        return edge
      })
      pushHistoryState(nodes, nextEdges)
      return nextEdges
    })
    setSelectedEdge((prev) => (prev && prev.id === edgeId ? { ...prev, data: { ...prev.data, ...nextData } } : prev))
  }, [setEdges, nodes, pushHistoryState])

  // Delete Edge
  const handleDeleteEdge = useCallback((edgeId) => {
    setEdges((eds) => {
      const filtered = eds.filter((e) => e.id !== edgeId)
      pushHistoryState(nodes, filtered)
      return filtered
    })
    setSelectedEdge(null)
    showToast('Connection arrow deleted', 'info')
  }, [setEdges, nodes, pushHistoryState, showToast])

  // Load Generic Enterprise Workflow Template (Explicit Button Trigger)
  const handleLoadDemoTemplate = useCallback(() => {
    setNodes(GENERIC_APPROVAL_TEMPLATE_NODES)
    setEdges(GENERIC_APPROVAL_TEMPLATE_EDGES)
    setWorkflowName('General Approval Process')
    setVersionNumber(1)
    setWorkflowStatus('Draft')
    setSelectedNode(null)
    setSelectedEdge(null)
    pushHistoryState(GENERIC_APPROVAL_TEMPLATE_NODES, GENERIC_APPROVAL_TEMPLATE_EDGES)
    setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 100)
    showToast('Loaded Generic Approval Workflow Template', 'success')
  }, [setNodes, setEdges, fitView, pushHistoryState, showToast])

  // Clear Canvas
  const handleClearCanvas = useCallback(() => {
    setNodes([])
    setEdges([])
    setSelectedNode(null)
    setSelectedEdge(null)
    pushHistoryState([], [])
    showToast('Canvas cleared', 'info')
    setShowMoreMenu(false)
  }, [setNodes, setEdges, pushHistoryState, showToast])

  // Export Workflow JSON
  const handleExportJSON = useCallback(() => {
    const payload = {
      id: workflowId || 'wf-definition-1',
      name: workflowName,
      version: versionNumber,
      status: workflowStatus,
      nodes,
      connections: edges
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${workflowName.toLowerCase().replace(/\s+/g, '_')}_v${versionNumber}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('Exported workflow specification JSON', 'success')
    setShowMoreMenu(false)
  }, [workflowId, workflowName, versionNumber, workflowStatus, nodes, edges, showToast])

  // Import Workflow JSON
  const handleImportJSON = useCallback((e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result)
        if (parsed.nodes && Array.isArray(parsed.nodes)) {
          setNodes(parsed.nodes)
        }
        if (parsed.connections && Array.isArray(parsed.connections)) {
          setEdges(parsed.connections)
        } else if (parsed.edges && Array.isArray(parsed.edges)) {
          setEdges(parsed.edges)
        }
        if (parsed.name) setWorkflowName(parsed.name)
        if (parsed.version) setVersionNumber(parsed.version)
        if (parsed.status) setWorkflowStatus(parsed.status)

        pushHistoryState(parsed.nodes || [], parsed.connections || parsed.edges || [])
        setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 100)
        showToast('Imported workflow configuration', 'success')
      } catch (err) {
        showToast('Invalid JSON file format', 'error')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
    setShowMoreMenu(false)
  }, [setNodes, setEdges, fitView, pushHistoryState, showToast])

  // Node-Specific Validation Check
  const handleValidateWorkflow = useCallback(() => {
    const errors = []

    if (nodes.length === 0) {
      errors.push('Workflow canvas is empty.')
    }

    const startNodes = nodes.filter(n => n.type === 'start')
    const endNodes = nodes.filter(n => n.type === 'end')

    if (startNodes.length === 0) {
      errors.push('Start Node: Workflow requires a Start node.')
    } else if (startNodes.length > 1) {
      errors.push('Start Node: Workflow must contain at most one Start node.')
    }
    if (endNodes.length === 0) {
      errors.push('End Node: Workflow requires at least one End boundary node.')
    }

    nodes.forEach(node => {
      const nodeLabel = node.data?.label || node.id
      const incoming = edges.filter(e => e.target === node.id)
      const outgoing = edges.filter(e => e.source === node.id)

      if (node.type === 'start') {
        if (incoming.length > 0) {
          errors.push(`Start Node "${nodeLabel}": Cannot have incoming connections.`)
        }
        if (outgoing.length === 0) {
          errors.push(`Start Node "${nodeLabel}": Must have an outgoing connection to initialize workflow execution.`)
        } else if (outgoing.length > 1) {
          errors.push(`Start Node "${nodeLabel}": Can have at most one outgoing connection.`)
        }
      }
      if (node.type === 'end') {
        if (outgoing.length > 0) {
          errors.push(`End Node "${nodeLabel}": Cannot have outgoing connections.`)
        }
        if (incoming.length === 0) {
          errors.push(`End Node "${nodeLabel}": Must have at least one incoming connection.`)
        }
        if (!node.data?.label && !node.data?.name) {
          errors.push(`End Node "${node.id}": Name is required.`)
        }
      }
      if (node.type === 'userTask') {
        if (!node.data?.label && !node.data?.name) {
          errors.push(`User Task "${node.id}": Name is required.`)
        }
        const assignment = node.data?.assignment || {}
        const assignType = (assignment.type || node.data?.assignmentType || '').toLowerCase()
        if (!['user', 'role', 'department'].includes(assignType)) {
          errors.push(`User Task "${nodeLabel}": Assignment type (User, Role, or Department) is required.`)
        } else {
          if (assignType === 'user' && !assignment.userId && !node.data?.user && !node.data?.userId) {
            errors.push(`User Task "${nodeLabel}": Valid assigned user is required.`)
          }
          if (assignType === 'role' && !assignment.roleId && !node.data?.role && !node.data?.roleId) {
            errors.push(`User Task "${nodeLabel}": Valid assigned role is required.`)
          }
          if (assignType === 'department' && !assignment.departmentId && !node.data?.department && !node.data?.departmentId) {
            errors.push(`User Task "${nodeLabel}": Valid assigned department is required.`)
          }
        }
        const acts = (Array.isArray(node.data?.actions) && node.data.actions.length > 0)
          ? node.data.actions
          : ['APPROVE', 'REJECT']
        if (acts.length === 0) {
          errors.push(`User Task "${nodeLabel}": Must select at least one action.`)
        }
      }
      if (node.type === 'approval') {
        const hasRole = node.data?.role || node.data?.user
        if (!hasRole) errors.push(`Approval Node "${nodeLabel}": Must have an assigned approver role.`)
        const acts = node.data?.actions || []
        if (acts.length === 0) errors.push(`Approval Node "${nodeLabel}": Must define at least one decision action.`)
      }
      if (node.type === 'condition') {
        if (!node.data?.label && !node.data?.name) {
          errors.push(`Action Router "${node.id}": Name is required.`)
        }
        if (incoming.length === 0) {
          errors.push(`Action Router "${nodeLabel}": Must have an incoming connection from a previous User Task.`)
        } else if (incoming.length > 1) {
          errors.push(`Action Router "${nodeLabel}": Can have at most one incoming connection.`)
        }
        if (outgoing.length === 0) {
          errors.push(`Action Router "${nodeLabel}": Must connect at least one action route.`)
        }
      }
      if (node.type === 'switch') {
        const cases = node.data?.cases || []
        if (cases.length === 0) errors.push(`Switch Node "${nodeLabel}": Must have at least one case defined.`)
      }
      if (node.type === 'parallel') {
        const branches = node.data?.branches || []
        if (branches.length < 2) errors.push(`Parallel Node "${nodeLabel}": Must have at least 2 branches.`)
      }
    })

    setValidationErrors(errors)
    setIsValidationOpen(true)

    if (errors.length === 0) {
      showToast('Validation check passed: All graph rules & handle contracts valid', 'success')
    } else {
      showToast(`Validation found ${errors.length} issue(s)`, 'error')
    }
  }, [nodes, edges, showToast])

  // Manual Save (uses workflowStorage.saveWorkflow)
  const handleSaveDraft = useCallback(async () => {
    if (!workflowId) return
    setSaveStatus('saving')
    try {
      await workflowStorage.saveWorkflow(workflowId, {
        name: workflowName,
        json_content: { nodes, edges }
      })
      setSaveStatus('saved')
      showToast('Workflow saved successfully', 'success')
    } catch (err) {
      console.error('Save error:', err)
      setSaveStatus('error')
      showToast('Failed to save workflow', 'error')
    }
  }, [workflowId, workflowName, nodes, edges, showToast])

  // Publish Workflow (real backend bpmn_definition table API)
  const handlePublish = useCallback(async () => {
    if (!workflowId) return
    setSaveStatus('saving')
    try {
      // 1. Save latest canvas state first
      await workflowStorage.saveWorkflow(workflowId, {
        name: workflowName,
        json_content: { nodes, edges }
      })

      // 2. Publish in bpmn_definition backend
      const response = await fetch(`/workflow/definitions/${workflowId}/publish`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok && (result.status === 'success' || !result.Error?.Error)) {
        setWorkflowStatus('Active')
        if (result.data?.version) {
          setVersionNumber(result.data.version)
        }
        setSaveStatus('saved')
        showToast('Workflow published and activated successfully!', 'success')
      } else {
        setSaveStatus('error')
        const errMsg = result?.Error?.Error_message || result?.message || result?.detail || 'Publishing failed'
        showToast(errMsg, 'error')
      }
    } catch (_err) {
      setSaveStatus('error')
      showToast('Network error while publishing', 'error')
    }
  }, [workflowId, workflowName, nodes, edges, showToast])

  // Auto-Layout Algorithm: Organizes graph nodes into a clean left-to-right topological layout
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return

    const inDegree = new Map(nodes.map(n => [n.id, 0]))
    const adj = new Map(nodes.map(n => [n.id, []]))

    edges.forEach(e => {
      if (adj.has(e.source)) adj.get(e.source).push(e.target)
      if (inDegree.has(e.target)) inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1)
    })

    const ranks = new Map()
    const queue = []

    nodes.forEach(n => {
      if ((inDegree.get(n.id) || 0) === 0) {
        queue.push(n.id)
        ranks.set(n.id, 0)
      }
    })

    if (queue.length === 0 && nodes.length > 0) {
      queue.push(nodes[0].id)
      ranks.set(nodes[0].id, 0)
    }

    while (queue.length > 0) {
      const u = queue.shift()
      const currentRank = ranks.get(u) || 0
      const neighbors = adj.get(u) || []
      neighbors.forEach(v => {
        const nextRank = Math.max(ranks.get(v) || 0, currentRank + 1)
        ranks.set(v, nextRank)
        inDegree.set(v, (inDegree.get(v) || 0) - 1)
        if ((inDegree.get(v) || 0) <= 0 && !queue.includes(v)) {
          queue.push(v)
        }
      })
    }

    const rankBuckets = new Map()
    nodes.forEach(n => {
      const r = ranks.get(n.id) || 0
      if (!rankBuckets.has(r)) rankBuckets.set(r, [])
      rankBuckets.get(r).push(n.id)
    })

    const HORIZONTAL_SPACING = 280
    const VERTICAL_SPACING = 140

    const updatedNodes = nodes.map(n => {
      const r = ranks.get(n.id) || 0
      const bucket = rankBuckets.get(r) || [n.id]
      const indexInBucket = bucket.indexOf(n.id)
      const x = 100 + r * HORIZONTAL_SPACING
      const y = 150 + indexInBucket * VERTICAL_SPACING - ((bucket.length - 1) * VERTICAL_SPACING) / 2
      return {
        ...n,
        position: { x, y: Math.max(80, y) }
      }
    })

    setNodes(updatedNodes)
    pushHistoryState(updatedNodes, edges)
    showToast('Auto-layout applied', 'success')
  }, [nodes, edges, setNodes, pushHistoryState, showToast])

  return (
    <div className="wf-designer-fullscreen">
      {/* Loading Overlay */}
      {isLoading && (
        <div className="wf-loading-overlay">
          <Loader className="spinner" size={36} color="var(--color-accent-secondary)" />
          <span style={{ color: 'var(--color-text-muted)', marginTop: '12px', fontSize: '14px' }}>Loading workflow...</span>
        </div>
      )}

      {/* Hidden File Input for JSON Import */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".json"
        onChange={handleImportJSON}
      />

      {/* 1. TOP HEADER */}
      <DesignerHeader
        workflowName={workflowName}
        setWorkflowName={setWorkflowName}
        versionNumber={versionNumber}
        workflowStatus={workflowStatus}
        workflowConnectionId={workflowConnectionId}
        saveStatus={saveStatus}
        saveWorkflow={handleSaveDraft}
        handleUndo={handleUndo}
        handleRedo={handleRedo}
        handleAutoLayout={handleAutoLayout}
        handleResetCanvas={handleClearCanvas}
        handleValidateGraph={handleValidateWorkflow}
        handleOpenTestModal={() => setShowTestModal(true)}
        handleExportJSON={handleExportJSON}
        fileInputRef={fileInputRef}
        handleImportFile={handleImportJSON}
        showMoreMenu={showMoreMenu}
        setShowMoreMenu={setShowMoreMenu}
        onClose={onClose}
      />

      {/* 2. THREE-PANEL WORKSPACE BODY */}
      <div className="wf-workspace-body">
        {/* LEFT: NODE LIBRARY (Execution, Control-Flow, Boundary) */}
        <NodeLibrary
          onAddNode={handleAddNodeFromClick}
          onAddTemplateFlow={handleLoadDemoTemplate}
        />

        {/* CENTER: WORKFLOW CANVAS */}
        <main className="wf-canvas-center" ref={reactFlowWrapper}>
          {/* Floating Canvas Toolbar */}
          <div className="wf-canvas-floating-toolbar">
            <button className="wf-tool-btn" onClick={() => zoomIn({ duration: 300 })} title="Zoom In">
              <ZoomIn size={15} />
            </button>
            <button className="wf-tool-btn" onClick={() => zoomOut({ duration: 300 })} title="Zoom Out">
              <ZoomOut size={15} />
            </button>
            <button className="wf-tool-btn" onClick={() => fitView({ padding: 0.2, duration: 400 })} title="Fit to Viewport">
              <Maximize2 size={14} />
            </button>

            <div className="wf-tool-divider" />

            <button
              className={`wf-tool-btn ${historyIndexRef.current === 0 ? 'disabled' : ''}`}
              onClick={handleUndo}
              title="Undo"
            >
              <Undo2 size={14} />
            </button>
            <button
              className={`wf-tool-btn ${historyIndexRef.current >= historyRef.current.length - 1 ? 'disabled' : ''}`}
              onClick={handleRedo}
              title="Redo"
            >
              <Redo2 size={14} />
            </button>

            <div className="wf-tool-divider" />

            <button
              className={`wf-tool-btn ${showGrid ? 'active' : ''}`}
              onClick={() => setShowGrid(!showGrid)}
              title="Toggle Grid"
            >
              <Grid size={14} />
              <span>Grid</span>
            </button>

            <button
              className="wf-tool-btn wf-tool-auto"
              onClick={handleLoadDemoTemplate}
              title="Reset to Demo 4-Tier Flow"
            >
              <Sparkles size={14} color="#818cf8" />
              <span>Reset Flow</span>
            </button>
          </div>

          <ReactFlow
            nodes={enrichedNodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            isValidConnection={isValidConnection}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{ type: 'workflow' }}
          >
            {showGrid && <Background gap={20} size={1} color="rgba(255, 255, 255, 0.08)" />}
            <MiniMap
              nodeColor={(n) => {
                if (n.type === 'start') return '#22c55e'
                if (n.type === 'end') return '#10b981'
                if (n.type === 'userTask') return '#3b82f6'
                if (n.type === 'approval') return '#a855f7'
                if (n.type === 'condition' || n.type === 'switch' || n.type === 'parallel') return '#f59e0b'
                if (n.type === 'communication') return '#6366f1'
                if (n.type === 'record') return '#06b6d4'
                if (n.type === 'action') return '#14b8a6'
                return '#64748b'
              }}
              maskColor="rgba(15, 18, 25, 0.75)"
              className="wf-minimap"
            />
          </ReactFlow>
        </main>

        {/* RIGHT: DYNAMIC PROPERTIES PANEL */}
        <PropertiesPanel
          selectedNode={selectedEnrichedNode}
          selectedEdge={selectedEdge}
          workflowConnectionId={workflowConnectionId}
          onUpdateNodeData={handleUpdateNodeData}
          onUpdateEdgeData={handleUpdateEdgeData}
          onDeleteNode={handleDeleteNode}
          onDeleteEdge={handleDeleteEdge}
        />
      </div>

      {/* Validation Results Modal */}
      <DesignerValidationModal
        isOpen={isValidationOpen}
        onClose={() => setIsValidationOpen(false)}
        validationErrors={validationErrors}
        onSelectNode={(nodeId) => {
          const targetNode = nodes.find(n => n.id === nodeId)
          if (targetNode) setSelectedNode(targetNode)
        }}
      />

      {/* Dynamic Generic Workflow Test Runner & Database Inspector Modal */}
      <DesignerTestRunnerModal
        isOpen={showTestModal}
        onClose={() => setShowTestModal(false)}
        workflowName={workflowName}
        specId={workflowId}
        nodes={nodes}
        edges={edges}
        testSubTab={testSubTab}
        setTestSubTab={setTestSubTab}
        testRecordId={testRecordId}
        setTestRecordId={setTestRecordId}
        fetchRecordState={fetchRecordState}
        startGenericSimulation={startGenericSimulation}
        handleResetTestRecord={handleResetTestRecord}
        testLoading={testLoading}
        simActiveNodeId={simActiveNodeId}
        setSimActiveNodeId={setSimActiveNodeId}
        simStatus={simStatus}
        simHistory={simHistory}
        testRecordData={testRecordData}
        testTxLogs={testTxLogs}
        handleGenericNodeAction={handleGenericNodeAction}
      />
    </div>
  )
}

export default function Designer(props) {
  return (
    <ReactFlowProvider>
      <DesignerCanvas {...props} />
    </ReactFlowProvider>
  )
}
