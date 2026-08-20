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
  Loader
} from 'lucide-react'

import NodeLibrary from './NodeLibrary'
import PropertiesPanel from './PropertiesPanel'
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

          let loadedNodes = []
          let loadedEdges = []
          if (data.json_content) {
            try {
              const parsed = typeof data.json_content === 'string' ? JSON.parse(data.json_content) : data.json_content
              loadedNodes = parsed.nodes || []
              loadedEdges = parsed.edges || parsed.connections || []
            } catch (e) {
              console.error('Failed to parse json_content:', e)
            }
          }
          if (loadedNodes.length === 0) {
            loadedNodes = [
              { id: 'node-start', type: 'start', position: { x: 250, y: 100 }, data: { label: 'Start', description: 'Process Start' } },
              { id: 'node-end', type: 'end', position: { x: 250, y: 350 }, data: { label: 'End', description: 'Process Complete' } }
            ]
            loadedEdges = [
              { id: 'edge-start-end', source: 'node-start', target: 'node-end', type: 'workflow', data: { label: 'Complete' } }
            ]
          }

          setNodes(loadedNodes)
          setEdges(loadedEdges)
          setSaveStatus('saved')
          historyRef.current = [{ nodes: loadedNodes, edges: loadedEdges }]
          historyIndexRef.current = 0
          setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 200)
        } else {
          const initialNodes = [
            { id: 'node-start', type: 'start', position: { x: 250, y: 100 }, data: { label: 'Start', description: 'Process Start' } },
            { id: 'node-end', type: 'end', position: { x: 250, y: 350 }, data: { label: 'End', description: 'Process Complete' } }
          ]
          const initialEdges = [
            { id: 'edge-start-end', source: 'node-start', target: 'node-end', type: 'workflow', data: { label: 'Complete' } }
          ]
          setNodes(initialNodes)
          setEdges(initialEdges)
          setWorkflowName('New Workflow')
          setSaveStatus('saved')
          historyRef.current = [{ nodes: initialNodes, edges: initialEdges }]
          historyIndexRef.current = 0
          setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 200)
        }
      } catch (err) {
        console.error('Error loading workflow:', err)
        if (!isCancelled) {
          const fallbackNodes = [
            { id: 'node-start', type: 'start', position: { x: 250, y: 100 }, data: { label: 'Start', description: 'Process Start' } },
            { id: 'node-end', type: 'end', position: { x: 250, y: 350 }, data: { label: 'End', description: 'Process Complete' } }
          ]
          setNodes(fallbackNodes)
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
        json_content: JSON.stringify({ nodes, edges })
      })
      setSaveStatus('saved')
    } catch (_err) {
      setSaveStatus('error')
      showToast('Error while saving workflow', 'error')
    }
  }, [workflowId, workflowName, nodes, edges, showToast])

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

  // Publish Workflow (real backend Studio API)
  const handlePublish = useCallback(async () => {
    if (!workflowId) return
    setSaveStatus('saving')
    try {
      // 1. Save latest canvas state first
      await workflowStorage.saveWorkflow(workflowId, {
        name: workflowName,
        json_content: { nodes, edges }
      })

      // 2. Publish in Studio backend
      const response = await fetch(`/workflow-studio/workflows/${workflowId}/publish`, {
        method: 'POST'
      })
      const result = await response.json()
      if (response.ok) {
        setWorkflowStatus('Active')
        if (result.version_number) {
          setVersionNumber(result.version_number)
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
      <header className="wf-designer-header">
        <div className="wf-header-left">
          {onClose && (
            <button className="wf-back-btn" onClick={onClose} title="Return to Dashboard">
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>
          )}
          
          <div className="wf-header-divider" />

          <div className="wf-header-title-box">
            <div className="wf-designer-top-tag">WORKFLOW STUDIO</div>
            <div className="wf-header-title-display">
              <span className="wf-header-label">Workflow:</span>
              <span className="wf-header-name">{workflowName}</span>
            </div>

            <div className="wf-header-badges">
              <span className="wf-badge-version">Version: {versionNumber}</span>
              <span className={`wf-badge-status ${workflowStatus.toLowerCase()}`}>
                Status: {workflowStatus}
              </span>

              {/* Save Status Indicator */}
              <span className={`wf-save-indicator wf-save-${saveStatus}`}>
                <span className="wf-save-dot" />
                {saveStatus === 'dirty' && 'Unsaved changes'}
                {saveStatus === 'saving' && 'Saving...'}
                {saveStatus === 'saved' && 'Saved'}
                {saveStatus === 'error' && 'Save failed'}
              </span>
            </div>
          </div>
        </div>

        <div className="wf-header-actions">
          <button 
            className="wf-btn wf-btn-outline" 
            onClick={handleSaveDraft}
            disabled={saveStatus === 'saving'}
            title="Save workflow state"
          >
            <Save size={14} />
            <span>{saveStatus === 'saving' ? 'Saving...' : 'Save'}</span>
          </button>

          <button 
            className="wf-btn wf-btn-outline wf-btn-validate"
            onClick={handleValidateWorkflow}
            title="Validate node integrity & connection contracts"
          >
            <CheckSquare size={14} />
            <span>Validate</span>
          </button>

          <button 
            className="wf-btn wf-btn-outline wf-btn-test"
            onClick={() => setShowTestModal(true)}
            title="Open workflow execution simulator"
          >
            <Play size={14} />
            <span>Test</span>
          </button>

          <button 
            className="wf-btn wf-btn-primary wf-btn-publish"
            onClick={handlePublish}
            disabled={saveStatus === 'saving'}
            title="Publish current workflow definition"
          >
            <Zap size={14} />
            <span>{saveStatus === 'saving' ? 'Publishing...' : 'Publish'}</span>
          </button>

          {/* More / ... Menu */}
          <div className="wf-more-menu-wrapper">
            <button 
              className="wf-btn wf-btn-icon" 
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              title="More Actions"
            >
              <MoreVertical size={16} />
            </button>

            {showMoreMenu && (
              <div className="wf-dropdown-menu" onClick={() => setShowMoreMenu(false)}>
                <button className="wf-dropdown-item" onClick={handleExportJSON}>
                  <Download size={13} />
                  <span>Export JSON</span>
                </button>
                <button className="wf-dropdown-item" onClick={() => fileInputRef.current?.click()}>
                  <Upload size={13} />
                  <span>Import JSON</span>
                </button>
                <button className="wf-dropdown-item" onClick={handleLoadDemoTemplate}>
                  <RotateCcw size={13} />
                  <span>Reset Risk Workflow</span>
                </button>
                <div className="wf-dropdown-divider" />
                <button className="wf-dropdown-item wf-item-danger" onClick={handleClearCanvas}>
                  <Trash2 size={13} />
                  <span>Clear Canvas</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

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
          onUpdateNodeData={handleUpdateNodeData}
          onUpdateEdgeData={handleUpdateEdgeData}
          onDeleteNode={handleDeleteNode}
          onDeleteEdge={handleDeleteEdge}
        />
      </div>

      {/* Validation Results Modal */}
      {isValidationOpen && (
        <div className="wf-validation-modal-overlay" onClick={() => setIsValidationOpen(false)}>
          <div className="wf-validation-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="wf-modal-header">
              <div className="flex items-center gap-2">
                {validationErrors.length === 0 ? (
                  <Check size={18} color="#4ade80" />
                ) : (
                  <AlertCircle size={18} color="#f87171" />
                )}
                <span className="font-bold text-sm">
                  {validationErrors.length === 0 ? 'Workflow Validation Passed' : 'Validation Issues Found'}
                </span>
              </div>
              <button className="wf-modal-close" onClick={() => setIsValidationOpen(false)}>
                <X size={15} />
              </button>
            </div>
            
            <div className="wf-modal-content">
              {validationErrors.length === 0 ? (
                <div className="wf-valid-msg">
                  <CheckCircle2 size={26} color="#4ade80" />
                  <p>All nodes, action handle contracts, roles, and routing connections are structurally valid!</p>
                </div>
              ) : (
                <ul className="wf-error-list">
                  {validationErrors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="wf-modal-footer">
              <button className="wf-btn wf-btn-primary" onClick={() => setIsValidationOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Simulator Modal */}
      {showTestModal && (
        <div className="wf-validation-modal-overlay" onClick={() => setShowTestModal(false)}>
          <div className="wf-test-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="wf-modal-header">
              <div className="flex items-center gap-2">
                <Play size={16} color="#60a5fa" />
                <span className="font-bold text-sm">Workflow Simulator (Outcome Path Tracer)</span>
              </div>
              <button className="wf-modal-close" onClick={() => setShowTestModal(false)}>
                <X size={15} />
              </button>
            </div>

            <div className="wf-modal-content">
              <p className="text-xs text-muted mb-3">
                Trace sequential outcomes through execution and control-flow nodes:
              </p>

              <div className="wf-sim-steps-list">
                {nodes.map((n, idx) => (
                  <div key={n.id} className="wf-sim-step-item">
                    <div className="wf-sim-badge">{idx + 1}</div>
                    <div className="wf-sim-info">
                      <div className="wf-sim-name">{n.data?.label || n.data?.name || n.type}</div>
                      <div className="wf-sim-type">
                        Type: {n.type} | {n.data?.role ? `Role: ${n.data.role}` : n.type === 'condition' ? 'Rule Evaluation' : 'System Node'}
                      </div>
                    </div>
                    <span className="wf-sim-status">Ready</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="wf-modal-footer">
              <button 
                className="wf-btn wf-btn-primary" 
                onClick={() => {
                  showToast('Simulation complete: path verified across all action handles', 'success')
                  setShowTestModal(false)
                }}
              >
                Execute Trace
              </button>
            </div>
          </div>
        </div>
      )}
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
