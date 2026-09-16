/**
 * genericWorkflowApi.js
 * Universal Workflow Hub API Client for ClientApp.
 * Routes all workflow operations through the single master gateway POST /api/v1/workflow-hub.
 */

const SERVER_URL = 'http://192.168.1.115:8000'

class GenericWorkflowApi {
  constructor(baseUrl = SERVER_URL) {
    this.defaultBaseUrl = baseUrl
  }

  getBaseUrl() {
    try {
      const stored = localStorage.getItem('workflow_server_url')
      if (stored && stored.trim()) return stored.trim().replace(/\/+$/, '')
    } catch (_e) {}
    return this.defaultBaseUrl || 'http://192.168.1.115:8000'
  }

  /**
   * Central request dispatcher to the Master Gateway endpoint.
   */
  async invoke(specId, operation, payload = {}) {
    const base = this.getBaseUrl()
    if (!base) return { local: true }

    const body = {
      spec_id: specId,
      operation: operation.toUpperCase(),
      ...payload
    }

    const res = await fetch(`${base}/api/v1/workflow-hub`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.Error?.Error_message || `Request failed with HTTP status ${res.status}`)
    }

    const json = await res.json()
    return json.data !== undefined ? json.data : json
  }

  // 1. Dynamic Schema Discovery
  async getSchema(specId) {
    return await this.invoke(specId, 'SCHEMA')
  }

  // 2. Fetch Business Records
  async fetchRecords(specId, statusFilter = 'ALL', limit = 100, offset = 0) {
    try {
      const res = await this.invoke(specId, 'FETCH_RECORDS', {
        status_filter: statusFilter,
        limit,
        offset
      })
      return Array.isArray(res) ? res : []
    } catch (_e) {
      return []
    }
  }

  // 3. Submit New Record & Start Workflow
  async submit(specId, data, currentUser, options = {}) {
    return await this.invoke(specId, 'SUBMIT', {
      data,
      user_id: currentUser?.id ? Number(currentUser.id) : 5,
      user_name: currentUser?.name || 'User',
      user_email: currentUser?.email || 'user@example.com',
      ...options
    })
  }

  // 4. Execute Human Approval / Rejection Action
  async executeAction(specId, recordId, action, remarks, currentUser, extraVariables = {}) {
    return await this.invoke(specId, 'ACTION', {
      record_id: Number(recordId),
      action: action.toUpperCase(),
      user_id: currentUser?.id ? Number(currentUser.id) : 3,
      role: currentUser?.role || 'MANAGER',
      remarks: remarks || '',
      variables: extraVariables
    })
  }

  // 5. Fetch Pending Approval Tasks
  async fetchMyTasks(specId = 'all', currentUser = {}) {
    try {
      const res = await this.invoke(specId, 'GET_TASKS', {
        user_id: currentUser?.id ? Number(currentUser.id) : 3,
        role: currentUser?.role || 'MANAGER'
      })
      return Array.isArray(res) ? res : []
    } catch (_e) {
      return []
    }
  }

  // 6. Get Execution Audit Timeline
  async getHistory(specId, recordId) {
    return await this.invoke(specId, 'HISTORY', { record_id: Number(recordId) })
  }

  // 7. List All Available Catalog Workflows
  async getCatalog() {
    try {
      const res = await this.invoke('all', 'CATALOG')
      return Array.isArray(res) ? res : []
    } catch (_e) {
      return []
    }
  }
}

export const genericWorkflowApi = new GenericWorkflowApi()
export default genericWorkflowApi
