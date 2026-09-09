/**
 * genericWorkflowApi.js
 * Clean Client Gateway Integration.
 * Separates Client Business Domain from Workflow Studio / Engine.
 * Provides generic module bindings, entity submissions, actions, user tasks,
 * and parameterized Client DB queries (SELECT / INSERT / UPDATE / DELETE).
 */

const SERVER_URL = 'http://localhost:8000'

class GenericWorkflowApi {
  constructor(baseUrl = SERVER_URL) {
    this.baseUrl = baseUrl
  }

  // 1. Get List of Registered Workflow Modules from Client Gateway
  async getBindings() {
    try {
      const res = await fetch(`${this.baseUrl}/client/bindings`)
      if (!res.ok) {
        // Fallback to legacy endpoint if gateway not reachable
        const fallbackRes = await fetch(`${this.baseUrl}/workflow-studio/bindings`)
        if (!fallbackRes.ok) return {}
        return await fallbackRes.json()
      }
      return await res.json()
    } catch (_e) {
      try {
        const fallbackRes = await fetch(`${this.baseUrl}/workflow-studio/bindings`)
        if (!fallbackRes.ok) return {}
        return await fallbackRes.json()
      } catch (_err) {
        return {}
      }
    }
  }

  // 2. Generic Fetch: Loads records from the bound Client Database table
  async fetchRecords(moduleKey, statusFilter = null) {
    try {
      const url = new URL(`${this.baseUrl}/client/bindings/${moduleKey}/records`)
      if (statusFilter) url.searchParams.append('status', statusFilter)
      const res = await fetch(url.toString())
      if (!res.ok) {
        // Fallback
        const fallbackUrl = new URL(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/records`)
        if (statusFilter) fallbackUrl.searchParams.append('status', statusFilter)
        const fbRes = await fetch(fallbackUrl.toString())
        if (!fbRes.ok) return []
        const fbJson = await fbRes.json()
        return fbJson.data || []
      }
      const json = await res.json()
      return json.data || []
    } catch (_e) {
      return []
    }
  }

  // 3. Generic Submit: Inserts DB record & initiates Workflow Instance
  async submit(moduleKey, data, currentUser, options = {}) {
    const res = await fetch(`${this.baseUrl}/client/bindings/${moduleKey}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data,
        user_id: currentUser?.id ? Number(currentUser.id) : 5,
        user_name: currentUser?.name || 'Employee',
        user_email: currentUser?.email || 'employee@company.com',
        async_execution: options.asyncExecution || false
      })
    })

    if (!res.ok) {
      // Try legacy endpoint if client gateway fails
      const fallbackRes = await fetch(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data,
          user_id: currentUser?.id ? Number(currentUser.id) : 5,
          user_name: currentUser?.name || 'Employee',
          user_email: currentUser?.email || 'employee@company.com'
        })
      })
      if (!fallbackRes.ok) {
        const err = await fallbackRes.json().catch(() => ({}))
        throw new Error(err.detail || `Submission failed with status ${fallbackRes.status}`)
      }
      return await fallbackRes.json()
    }
    return await res.json()
  }

  // 4. Generic Action Execution: (APPROVE / REJECT / etc.)
  async executeAction(moduleKey, recordId, action, remarks, currentUser, extraVariables = {}) {
    const payload = {
      record_id: recordId,
      action: action.toUpperCase(),
      user_id: currentUser?.id ? Number(currentUser.id) : 3,
      role: currentUser?.role || 'MANAGER',
      user_role: currentUser?.role || 'MANAGER',
      remarks: remarks || '',
      variables: {
        ...extraVariables,
        user_role: currentUser?.role || 'MANAGER',
        approved_by: currentUser?.name || 'Manager'
      }
    }

    const res = await fetch(`${this.baseUrl}/client/bindings/${moduleKey}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
      const fbRes = await fetch(`${this.baseUrl}/workflow-studio/bindings/${moduleKey}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!fbRes.ok) {
        const err = await fbRes.json().catch(() => ({}))
        throw new Error(err.detail || `Action execution failed with status ${fbRes.status}`)
      }
      return await fbRes.json()
    }
    return await res.json()
  }

  // 5. Generic Task Inbox: Fetches assigned human tasks across ALL bound workflows
  async fetchMyTasks(userId) {
    try {
      const res = await fetch(`${this.baseUrl}/client/tasks/my-tasks?user_id=${userId}`)
      if (!res.ok) {
        const fbRes = await fetch(`${this.baseUrl}/workflow-studio/tasks/my-tasks?user_id=${userId}`)
        if (!fbRes.ok) return []
        return await fbRes.json()
      }
      return await res.json()
    } catch (_e) {
      return []
    }
  }

  // 6. Generic Client-Side DB Query Gateway (SELECT, INSERT, UPDATE, DELETE)
  async query({
    tableName,
    operation = 'SELECT',
    columns = null,
    filters = null,
    orderBy = null,
    orderDirection = 'ASC',
    limit = 100,
    offset = 0,
    values = null,
    connectionId = null
  }) {
    const res = await fetch(`${this.baseUrl}/client/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_name: tableName,
        operation: operation.toUpperCase(),
        columns,
        filters,
        order_by: orderBy,
        order_direction: orderDirection,
        limit,
        offset,
        values,
        connection_id: connectionId
      })
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.message || `Client query failed with status ${res.status}`)
    }
    return await res.json()
  }
}

export const genericWorkflowApi = new GenericWorkflowApi()
