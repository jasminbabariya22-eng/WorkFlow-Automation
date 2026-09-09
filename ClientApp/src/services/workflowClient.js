/**
 * workflowClient.js
 * Workflow Server Connection Manager
 */

class WorkflowClient {
  constructor() {
    this.serverUrl = localStorage.getItem('workflow_server_url') || 'http://localhost:8000'
  }

  getServerUrl() {
    return this.serverUrl
  }

  setServerUrl(url) {
    if (!url) return
    this.serverUrl = url.trim().replace(/\/+$/, '')
    localStorage.setItem('workflow_server_url', this.serverUrl)
  }

  async testConnection(customUrl) {
    try {
      const target = customUrl || this.getServerUrl()
      const res = await fetch(`${target}/health`, { method: 'GET', signal: AbortSignal.timeout(3000) })
      return { success: res.ok, message: res.ok ? 'Connected successfully' : 'Server responded with error' }
    } catch (err) {
      return { success: false, message: err.message || 'Cannot reach server' }
    }
  }

  async checkHealth() {
    return await this.testConnection()
  }
}

export const workflowClient = new WorkflowClient()
