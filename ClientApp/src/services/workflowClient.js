/**
 * workflowClient.js
 * Standalone Offline Client Service
 * Disconnected from the central workflow server.
 */

class WorkflowClient {
  constructor() {
    this.serverUrl = 'Offline Mode'
  }

  getServerUrl() {
    return 'Standalone Offline'
  }

  setServerUrl(_url) {}

  async checkHealth() {
    return { ok: true, offline: true }
  }

  async fetchWorkflows() {
    return []
  }

  async startWorkflow(_workflowId, _payload) {
    return { status: 'SUCCESS', offline: true }
  }

  async executeAction(_workflowId, _payload) {
    return { status: 'SUCCESS', offline: true }
  }

  async fetchRecords(_tableName, _connectionId) {
    return []
  }

  async createRecord(_tableName, _values, _connectionId) {
    return { id: Date.now() }
  }

  async fetchMyTasks(_userId) {
    return []
  }
}

export const workflowClient = new WorkflowClient()
