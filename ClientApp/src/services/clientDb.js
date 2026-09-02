/**
 * clientDb.js
 * In-Memory Directory for PostgreSQL Users & Leave Types.
 * No local persistence or mock storage simulation.
 */

export const USERS = [
  { id: '5', name: 'Jasmin', email: 'jasminbabariya22@gmail.com', role: 'EMPLOYEE', department: 'Engineering', manager_id: '3' },
  { id: '6', name: 'Jatin', email: 'mjatin@gmail.com', role: 'EMPLOYEE', department: 'Engineering', manager_id: '3' },
  { id: '7', name: 'Rahul Mehta', email: 'rahul.mehta@example.com', role: 'EMPLOYEE', department: 'Engineering', manager_id: '4' },
  { id: '3', name: 'Rajesh Kumar', email: 'rajesh.kumar@example.com', role: 'MANAGER', department: 'Engineering', manager_id: null },
  { id: '4', name: 'Priya Sharma', email: 'priya.sharma@example.com', role: 'MANAGER', department: 'People & Culture', manager_id: null }
]

export const LEAVE_TYPES = [
  { id: 1, code: 'ANNUAL', name: 'Annual Leave', maxDays: 20 },
  { id: 2, code: 'CASUAL', name: 'Casual Leave', maxDays: 10 },
  { id: 3, code: 'SICK', name: 'Sick Leave', maxDays: 12 },
  { id: 4, code: 'UNPAID', name: 'Unpaid Leave', maxDays: 60 },
  { id: 5, code: 'WFH', name: 'Work From Home (WFH)', maxDays: 30 }
]

class ClientDatabase {
  constructor() {
    // Clear any legacy storage on startup
    try {
      Object.keys(localStorage).forEach(k => {
        if (k.startsWith('clientdb_')) localStorage.removeItem(k)
      })
    } catch (_e) {}
  }

  getUsers() {
    return USERS
  }

  getUserById(userId) {
    return USERS.find(u => String(u.id) === String(userId)) || null
  }

  getManagerForUser(userId) {
    const user = this.getUserById(userId)
    if (!user || !user.manager_id) return null
    return this.getUserById(user.manager_id)
  }

  getLeaveTypes() {
    return LEAVE_TYPES
  }

  getPendingApprovalsForUser(_currentUser) {
    return []
  }

  getExpenses() {
    return []
  }

  getPurchaseOrders() {
    return []
  }

  getItRequests() {
    return []
  }

  getKycCases() {
    return []
  }
}

export const clientDb = new ClientDatabase()
