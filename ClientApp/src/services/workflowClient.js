/**
 * workflowClient.js
 * Workflow Engine Client for ClientApp.
 * Disconnected by default (No automatic backend connection).
 */

class WorkflowClient {
  constructor() {
    this.serverUrl = localStorage.getItem('workflow_server_url') ?? 'http://192.168.1.183:8000'
  }

  getServerUrl() {
    try {
      const stored = localStorage.getItem('workflow_server_url')
      if (stored && stored.trim()) return stored.trim().replace(/\/+$/, '')
    } catch (_e) {}
    return this.serverUrl || 'http://192.168.1.183:8000'
  }

  isConnected() {
    const url = this.getServerUrl()
    return Boolean(url && url.trim().length > 0)
  }

  setServerUrl(url) {
    if (!url || !url.trim()) {
      this.serverUrl = ''
      localStorage.setItem('workflow_server_url', '')
      return
    }
    this.serverUrl = url.trim().replace(/\/+$/, '')
    localStorage.setItem('workflow_server_url', this.serverUrl)
  }

  disconnect() {
    this.serverUrl = ''
    localStorage.setItem('workflow_server_url', '')
  }

  async testConnection(customUrl) {
    try {
      const target = (customUrl !== undefined ? customUrl : this.getServerUrl()).trim().replace(/\/+$/, '')
      if (!target) {
        return { success: false, isDisconnected: true, message: 'No server configured (Disconnected / Standalone mode)' }
      }
      const res = await fetch(`${target}/health`, { method: 'GET', signal: AbortSignal.timeout(3000) })
      return { success: res.ok, message: res.ok ? 'Connected successfully' : 'Server responded with error' }
    } catch (err) {
      return { success: false, message: err.message || 'Cannot reach server' }
    }
  }

  async checkHealth() {
    if (!this.isConnected()) {
      return { success: false, isDisconnected: true, message: 'Disconnected' }
    }
    return await this.testConnection()
  }

  // 1. Direct Workflow Trigger
  async startWorkflow(workflowIdOrKey, payload = {}) {
    const base = this.getServerUrl()
    if (!base) {
      return { success: true, instance_id: `LOCAL-${Date.now()}`, local: true }
    }
    const body = {
      variables: payload.variables || payload
    }
    if (typeof workflowIdOrKey === 'number' || !isNaN(Number(workflowIdOrKey))) {
      body.workflow_id = Number(workflowIdOrKey)
    } else {
      body.workflow_key = String(workflowIdOrKey)
    }
    if (payload.entityId) body.entity_id = payload.entityId
    if (payload.entityType) body.entity_type = payload.entityType

    const res = await fetch(`${base}/workflow/jobs/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.message || `Failed to start workflow (${res.status})`)
    }
    return await res.json()
  }

  // 2. Direct Tasks Fetch
  async getPendingTasks(roleCode = null, status = 'READY') {
    const base = this.getServerUrl()
    if (!base) return []
    try {
      const url = new URL(`${base}/workflow/tasks`)
      if (roleCode) url.searchParams.append('role_code', roleCode)
      if (status) url.searchParams.append('status', status)

      const res = await fetch(url.toString())
      if (!res.ok) return []
      const json = await res.json()
      return json.data || json || []
    } catch (_e) {
      return []
    }
  }

  // 3. Direct Complete Task
  async completeTask(taskId, action = 'APPROVE', remark = '', extraVariables = {}) {
    const base = this.getServerUrl()
    if (!base) return { success: true, local: true }
    const res = await fetch(`${base}/workflow/tasks/${taskId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        remark: remark || `${action} executed`,
        variables: {
          action: action.toUpperCase(),
          ...extraVariables
        }
      })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.message || `Failed to complete task (${res.status})`)
    }
    return await res.json()
  }

  // 4. Direct Reject Task
  async rejectTask(taskId, remark = '', extraVariables = {}) {
    const base = this.getServerUrl()
    if (!base) return { success: true, local: true }
    const res = await fetch(`${base}/workflow/tasks/${taskId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        remark: remark || 'Rejected',
        variables: {
          action: 'REJECT',
          ...extraVariables
        }
      })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.message || `Failed to reject task (${res.status})`)
    }
    return await res.json()
  }

  // 5. Get Job / Workflow Status
  async getJobStatus(jobId) {
    const base = this.getServerUrl()
    if (!base) return null
    try {
      const res = await fetch(`${base}/workflow/jobs/${jobId}/status`)
      if (!res.ok) return null
      return await res.json()
    } catch (_e) {
      return null
    }
  }
}

export const workflowClient = new WorkflowClient()
