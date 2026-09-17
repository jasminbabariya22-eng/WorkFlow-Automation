/**
 * frontendLogger.js
 * Production-grade Global Frontend Observability, Daily Log Storage, 30-Day Retention,
 * Error Interception, and Backend Sync Service.
 */

const STORAGE_PREFIX = 'workflow_fe_log_';
const MAX_LOGS_PER_DAY = 500;
const RETENTION_DAYS = 30;
const FLUSH_INTERVAL_MS = 5000;
const BATCH_SIZE_LIMIT = 50;

class FrontendLoggerService {
  constructor() {
    this.buffer = [];
    this.isInitialized = false;
    this.flushTimer = null;
    this.apiEndpoint = '/api/logs/frontend';
  }

  /**
   * Initializes global error hooks and automatic periodic sync.
   */
  init(options = {}) {
    if (this.isInitialized) return;
    if (options.apiEndpoint) {
      this.apiEndpoint = options.apiEndpoint;
    }

    // 1. Hook unhandled runtime window errors
    window.addEventListener('error', (event) => {
      this.error(
        `Unhandled Window Error: ${event.message}`,
        event.error || {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
        { source: 'window.onerror' }
      );
    });

    // 2. Hook unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason;
      const errorMsg = reason instanceof Error ? reason.message : String(reason);
      const errorStack = reason instanceof Error ? reason.stack : undefined;
      this.error(
        `Unhandled Promise Rejection: ${errorMsg}`,
        { message: errorMsg, stack: errorStack },
        { source: 'window.onunhandledrejection' }
      );
    });

    // 3. Periodic log flusher
    this.flushTimer = setInterval(() => {
      this.flushToBackend();
    }, FLUSH_INTERVAL_MS);

    // 4. Flush on tab close / unload
    window.addEventListener('beforeunload', () => {
      this.flushToBackend(true);
    });

    // 5. Initial cleanup of old local storage logs
    this.cleanupOldLogs();

    this.isInitialized = true;
    this.info('Frontend Global Observability Logger initialized.');
  }

  /**
   * Formats and logs an entry.
   */
  log(level, message, details = {}, error = null) {
    const now = new Date();
    const dateStr = this.getTodayDateString(now);
    const isoTimestamp = now.toISOString();

    let stack = null;
    if (error instanceof Error) {
      stack = error.stack;
    } else if (error && error.stack) {
      stack = error.stack;
    }

    const logEntry = {
      level: level.toUpperCase(),
      message,
      timestamp: isoTimestamp,
      url: window.location.href,
      component: details?.component || null,
      user_id: details?.user_id || details?.userId || null,
      stack,
      details: {
        ...details,
        userAgent: navigator.userAgent,
      },
    };

    // Console output with styled tag
    this.consoleOutput(logEntry);

    // Save to daily localStorage partition
    this.saveToLocalStorage(dateStr, logEntry);

    // Queue for backend sync
    this.buffer.push(logEntry);

    // If critical error, flush immediately
    if (level.toUpperCase() === 'ERROR') {
      this.flushToBackend();
    }

    return logEntry;
  }

  info(message, details = {}) {
    return this.log('INFO', message, details);
  }

  warn(message, details = {}) {
    return this.log('WARN', message, details);
  }

  error(message, error = null, details = {}) {
    return this.log('ERROR', message, details, error);
  }

  debug(message, details = {}) {
    return this.log('DEBUG', message, details);
  }

  logAction(actionName, details = {}) {
    return this.log('INFO', `User Action: ${actionName}`, { ...details, action: actionName });
  }

  /**
   * Styled browser console outputs
   */
  consoleOutput(entry) {
    const time = entry.timestamp.split('T')[1].split('.')[0];
    const prefix = `[WorkflowClient ${time}]`;
    const style =
      entry.level === 'ERROR'
        ? 'color: #ef4444; font-weight: bold;'
        : entry.level === 'WARN'
        ? 'color: #f59e0b; font-weight: bold;'
        : 'color: #3b82f6; font-weight: bold;';

    if (entry.level === 'ERROR') {
      console.error(`%c${prefix} [${entry.level}] ${entry.message}`, style, entry.details || '', entry.stack || '');
    } else if (entry.level === 'WARN') {
      console.warn(`%c${prefix} [${entry.level}] ${entry.message}`, style, entry.details || '');
    } else {
      console.log(`%c${prefix} [${entry.level}] ${entry.message}`, style, entry.details || '');
    }
  }

  /**
   * Persists log entries into localStorage partitioned by date (workflow_fe_log_YYYY-MM-DD).
   */
  saveToLocalStorage(dateStr, logEntry) {
    try {
      const storageKey = `${STORAGE_PREFIX}${dateStr}`;
      const existingRaw = localStorage.getItem(storageKey);
      let dayLogs = [];
      if (existingRaw) {
        dayLogs = JSON.parse(existingRaw);
      }
      dayLogs.push(logEntry);

      // Keep within max logs limit per day
      if (dayLogs.length > MAX_LOGS_PER_DAY) {
        dayLogs = dayLogs.slice(dayLogs.length - MAX_LOGS_PER_DAY);
      }

      localStorage.setItem(storageKey, JSON.stringify(dayLogs));
    } catch (e) {
      // LocalStorage quota exceeded or private mode
    }
  }

  /**
   * Removes logs older than 30 days from browser localStorage.
   */
  cleanupOldLogs() {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - RETENTION_DAYS);
      const cutoffStr = this.getTodayDateString(cutoffDate);

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(STORAGE_PREFIX)) {
          const datePart = key.replace(STORAGE_PREFIX, '');
          if (datePart < cutoffStr) {
            localStorage.removeItem(key);
          }
        }
      }
    } catch (e) {
      // Ignore storage errors
    }
  }

  /**
   * Flushes queued logs to the backend API.
   */
  async flushToBackend(isUnload = false) {
    if (this.buffer.length === 0) return;

    const itemsToSend = this.buffer.splice(0, BATCH_SIZE_LIMIT);
    const payload = JSON.stringify({ logs: itemsToSend });

    if (isUnload && navigator.sendBeacon) {
      const blob = new Blob([payload], { type: 'application/json' });
      navigator.sendBeacon(this.apiEndpoint, blob);
      return;
    }

    try {
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: payload,
      });

      if (!response.ok) {
        // Requeue on server error
        this.buffer.unshift(...itemsToSend.slice(0, 20));
      }
    } catch (err) {
      // Offline or network error: requeue small portion
      this.buffer.unshift(...itemsToSend.slice(0, 20));
    }
  }

  /**
   * Retrieves logs for a specific date from local storage.
   */
  getLogsForDate(dateStr = this.getTodayDateString()) {
    try {
      const storageKey = `${STORAGE_PREFIX}${dateStr}`;
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  /**
   * Downloads a plain-text log file for a given date.
   */
  downloadLogs(dateStr = this.getTodayDateString()) {
    const logs = this.getLogsForDate(dateStr);
    if (!logs || logs.length === 0) {
      alert(`No frontend logs recorded for ${dateStr}.`);
      return;
    }

    const lines = logs.map((l) => {
      let line = `${l.timestamp} | ${l.level.padEnd(7)} | [FRONTEND] ${l.message}`;
      if (l.component) line += ` | Component: <${l.component}>`;
      if (l.url) line += ` | URL: ${l.url}`;
      if (l.stack) line += `\n  Stack: ${l.stack}`;
      return line;
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `frontend_${dateStr}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  getTodayDateString(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
}

export const frontendLogger = new FrontendLoggerService();
export default frontendLogger;
