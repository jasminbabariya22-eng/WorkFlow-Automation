/**
 * workflowSocket.js
 * Native WebSocket Service for ClientApp.
 * Completely passive - does not connect automatically when disconnected.
 */

class WorkflowSocket {
  constructor() {
    this.ws = null
    this.url = ''
    this.userId = null
    this.reconnectTimer = null
    this.pingTimer = null
    this.isConnected = false
    this.listeners = new Map()
    this.anyListeners = new Set()
    this.statusListeners = new Set()
  }

  resolveWsUrl(serverHttpUrl) {
    if (!serverHttpUrl) return ''
    const base = serverHttpUrl.trim().replace(/\/+$/, '')
    const wsProto = base.startsWith('https') ? 'wss://' : 'ws://'
    const host = base.replace(/^https?:\/\//, '')
    return `${wsProto}${host}/ws/workflow`
  }

  connect(options = {}) {
    const rawUrl = options.serverUrl !== undefined ? options.serverUrl : localStorage.getItem('workflow_server_url')
    if (!rawUrl || !rawUrl.trim()) {
      this.disconnect()
      if (options.onEvent) this.onAny(options.onEvent)
      return () => {
        if (options.onEvent) this.offAny(options.onEvent)
      }
    }

    const serverUrl = rawUrl.trim()
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
    if (!this.url) return
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
        } catch (_e) {}
      }

      this.ws.onclose = () => {
        this._cleanup()
      }

      this.ws.onerror = () => {
        this._cleanup()
      }
    } catch (_err) {
      this._cleanup()
    }
  }

  _cleanup() {
    this.isConnected = false
    this._stopHeartbeat()
    this._notifyStatus(false)
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

  onAny(callback) {
    this.anyListeners.add(callback)
    return () => this.offAny(callback)
  }

  offAny(callback) {
    this.anyListeners.delete(callback)
  }

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
