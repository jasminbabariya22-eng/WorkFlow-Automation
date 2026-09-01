/**
 * WorkflowClient SDK
 * Handles network communication between the Client Application and the Centralized Workflow Engine.
 * Supports configurable remote server URLs (e.g. http://192.168.1.183:8000).
 */

const STORAGE_KEY = 'enterprise_workflow_server_url'
const DEFAULT_URL = 'http://localhost:8000'

class WorkflowClient {
  constructor() {
    this.serverUrl = localStorage.getItem(STORAGE_KEY) || DEFAULT_URL
  }

  getServerUrl() {
    return this.serverUrl
  }

  setServerUrl(url) {
    let clean = (url || '').trim()
    if (clean.endsWith('/')) clean = clean.slice(0, -1)
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'http://' + clean
    }
    this.serverUrl = clean
    localStorage.setItem(STORAGE_KEY, clean)
  }

  // 1. Health Ping / Connectivity Test
  async testConnection(customUrl = null) {
    const target = customUrl || this.serverUrl
    try {
      const res = await fetch(`${target}/health`, {
        signal: AbortSignal.timeout(3500)
      })
      if (res.ok) {
        const data = await res.json()
        return { success: true, message: 'Connected to Workflow Server!', data }
      }
      return { success: false, message: `Server returned status ${res.status}` }
    } catch (err) {
      return { success: false, message: `Connection failed: ${err.message}` }
    }
  }

  // 2. Discover Workflows Available on Central Server
  async listWorkflows() {
    try {
      const res = await fetch(`${this.serverUrl}/workflow-studio/workflows`, {
        signal: AbortSignal.timeout(5000)
      })
      if (!res.ok) return []
      const data = await res.json()
      return Array.isArray(data) ? data : (data.data || [])
    } catch (_err) {
      return []
    }
  }

  // 3. Start a Workflow Instance
  async startWorkflow(workflowId, { entityType, entityId, userId, variables = {} }) {
    const url = `${this.serverUrl}/workflow-studio/workflows/${workflowId}/execute`
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        user_id: userId,
        variables
      }),
      signal: AbortSignal.timeout(8000)
    })

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || errData.message || `Server returned ${res.status}`)
    }
    return await res.json()
  }

  // 4. Submit an Action (Approve, Reject, Force Approve, etc.)
  async executeAction(workflowId, { entityType, entityId, action, userId, remarks = '', variables = {} }) {
    const url = `${this.serverUrl}/workflow-studio/workflows/${workflowId}/action`
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        action,
        user_id: userId,
        remarks,
        variables
      }),
      signal: AbortSignal.timeout(8000)
    })

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || errData.message || `Action failed with ${res.status}`)
    }
    return await res.json()
  }

  // 5. Query Client Database Table Records
  async fetchRecords(tableName = 'leave_requests', connectionId = 4) {
    try {
      const res = await fetch(`${this.serverUrl}/workflow-studio/records?table_name=${tableName}&connection_id=${connectionId}`, {
        signal: AbortSignal.timeout(5000)
      })
      if (!res.ok) return []
      const data = await res.json()
      return data.data || []
    } catch (_err) {
      return []
    }
  }

  // 6. Insert Record into Client Database
  async createRecord(tableName = 'leave_requests', values = {}, connectionId = 4) {
    const res = await fetch(`${this.serverUrl}/workflow-studio/records`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_name: tableName,
        values,
        connection_id: connectionId
      }),
      signal: AbortSignal.timeout(8000)
    })
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || errData.message || `Insert failed with ${res.status}`)
    }
    return await res.json()
  }
}

export const workflowClient = new WorkflowClient()
