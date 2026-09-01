/**
 * genericWorkflowApi.js
 * 100% Generic Frontend Workflow Client.
 * Communicates with the Python Declarative Binding Gateway.
 * Zero hardcoded workflow logic per module.
 */

const SERVER_URL = 'http://localhost:8000'

class GenericWorkflowApi {
  constructor(baseUrl = SERVER_URL) {
    this.baseUrl = baseUrl
  }

  // 1. Get List of Registered Workflow Modules from Python Backend
  async getBindings() {
    try {
      const res = await fetch(`${this.baseUrl}/workflow-studio/bindings`)
      if (!res.ok) return {}
      return await res.json()
    } catch (_e) {
      return {}
    }
  }

  // 2. Generic Fetch: Loads records from the bound Client Database table
  async fetchRecords(moduleKey) {
    try {
      const res = await fetch(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/records`)
      if (!res.ok) return []
      const json = await res.json()
      return json.data || []
    } catch (_e) {
      return []
    }
  }

  // 3. Generic Submit: Inserts DB record & initiates Workflow Instance
  async submit(moduleKey, data, currentUser) {
    const res = await fetch(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data,
        user_id: currentUser?.id ? Number(currentUser.id) : 5,
        user_name: currentUser?.name || 'Employee',
        user_email: currentUser?.email || 'employee@company.com'
      })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Submission failed with status ${res.status}`)
    }
    return await res.json()
  }

  // 4. Generic Action Execution: (APPROVE / REJECT / etc.)
  async executeAction(moduleKey, recordId, action, remarks, currentUser, extraVariables = {}) {
    const res = await fetch(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        record_id: recordId,
        action: action.toUpperCase(),
        user_id: currentUser?.id ? Number(currentUser.id) : 3,
        remarks: remarks || '',
        variables: {
          ...extraVariables,
          user_role: currentUser?.role || 'MANAGER',
          approved_by: currentUser?.name || 'Manager'
        }
      })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Action execution failed with status ${res.status}`)
    }
    return await res.json()
  }

  // 5. Generic Task Inbox: Fetches assigned human tasks across ALL bound workflows
  async fetchMyTasks(userId) {
    try {
      const res = await fetch(`${this.baseUrl}/workflow-studio/tasks/my-tasks?user_id=${userId}`)
      if (!res.ok) return []
      return await res.json()
    } catch (_e) {
      return []
    }
  }
}

export const genericWorkflowApi = new GenericWorkflowApi()
