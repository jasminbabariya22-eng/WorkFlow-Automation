/**
 * workflowSocket.js
 * Lightweight Zero-Dependency Native WebSocket Service for ClientApp.
 * Connects directly to the Workflow Engine's real-time event pipeline.
 * Minimum code footprint: 1-line subscription for any module.
 */

class WorkflowSocket {
  constructor() {
    this.ws = null
    this.url = ''
    this.userId = null
    this.reconnectTimer = null
    this.pingTimer = null
    this.isConnected = false
    this.listeners = new Map() // eventType -> Set of callbacks
    this.anyListeners = new Set() // generic event listeners
    this.statusListeners = new Set()
  }

  /**
   * Derives ws:// or wss:// URL from standard http server URL
   */
  resolveWsUrl(serverHttpUrl) {
    const base = (serverHttpUrl || 'http://localhost:8000').trim().replace(/\/+$/, '')
    const wsProto = base.startsWith('https') ? 'wss://' : 'ws://'
    const host = base.replace(/^https?:\/\//, '')
    return `${wsProto}${host}/ws/workflow`
  }

  /**
   * Connects to the backend workflow WebSocket
   */
  connect(options = {}) {
    const serverUrl = options.serverUrl || localStorage.getItem('workflow_server_url') || 'http://localhost:8000'
    this.userId = options.userId || null
    this.url = this.resolveWsUrl(serverUrl)

    if (options.onEvent) {
      this.onAny(options.onEvent)
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return () => {
        if (options.onEvent) this.offAny(options.onEvent)
      }
    }

    this._initSocket()

    return () => {
      if (options.onEvent) this.offAny(options.onEvent)
    }
  }

  _initSocket() {
    try {
      const fullUrl = this.userId ? `${this.url}?user_id=${encodeURIComponent(this.userId)}` : this.url
      this.ws = new WebSocket(fullUrl)

      this.ws.onopen = () => {
        this.isConnected = true
        this._notifyStatus(true)
        this._startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return
          const payload = JSON.parse(event.data)
          this._dispatch(payload)
        } catch (_e) {
          // Non-JSON message, ignore
        }
      }

      this.ws.onclose = () => {
        this._cleanup()
        this._scheduleReconnect()
      }

      this.ws.onerror = () => {
        this._cleanup()
        this._scheduleReconnect()
      }
    } catch (_err) {
      this._scheduleReconnect()
    }
  }

  _cleanup() {
    this.isConnected = false
    this._stopHeartbeat()
    this._notifyStatus(false)
  }

  _scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this._initSocket()
    }, 3000)
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 25000)
  }

  _stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  _notifyStatus(status) {
    this.statusListeners.forEach((cb) => {
      try {
        cb(status)
      } catch (_e) {}
    })
  }

  _dispatch(eventPayload) {
    const type = eventPayload.type || 'WORKFLOW_EVENT'
    const specific = this.listeners.get(type)
    if (specific) {
      specific.forEach((cb) => {
        try {
          cb(eventPayload)
        } catch (_e) {}
      })
    }

    this.anyListeners.forEach((cb) => {
      try {
        cb(eventPayload)
      } catch (_e) {}
    })
  }

  /**
   * Listen to a specific event type (e.g. 'TASK_READY', 'WORKFLOW_STARTED')
   */
  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)
    return () => this.off(eventType, callback)
  }

  off(eventType, callback) {
    const s = this.listeners.get(eventType)
    if (s) s.delete(callback)
  }

  /**
   * Listen to ANY workflow event (for auto-refreshing UI lists & badges)
   */
  onAny(callback) {
    this.anyListeners.add(callback)
    return () => this.offAny(callback)
  }

  offAny(callback) {
    this.anyListeners.delete(callback)
  }

  /**
   * Listen to connection status changes (connected = true/false)
   */
  onStatusChange(callback) {
    this.statusListeners.add(callback)
    callback(this.isConnected)
    return () => this.statusListeners.delete(callback)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this._stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
    this._notifyStatus(false)
  }
}

export const workflowSocket = new WorkflowSocket()
