/**
 * clientDb.js
 * Standalone Client Application Database (clientDB)
 * Simulates a real enterprise database (Postgres/MySQL) with persistent localStorage,
 * user-manager hierarchies, and multi-level RBAC enforcement.
 */

const DB_KEYS = {
  USERS: 'clientdb_users_v2',
  LEAVE_TYPES: 'clientdb_leave_types_v2',
  LEAVES: 'clientdb_leaves_v2',
  EXPENSES: 'clientdb_expenses',
  PURCHASE_ORDERS: 'clientdb_purchase_orders',
  IT_REQUESTS: 'clientdb_it_requests',
  KYC_CASES: 'clientdb_kyc_cases',
  AUDIT_LOGS: 'clientdb_audit_logs'
}

const DEFAULT_USERS = [
  { id: '101', name: 'Alice Smith', email: 'alice@company.com', role: 'EMPLOYEE', department: 'Engineering', manager_id: '102' },
  { id: '102', name: 'Bob Roberts', email: 'bob@company.com', role: 'MANAGER', department: 'Engineering', manager_id: null },
  { id: '103', name: 'Charlie Davis', email: 'charlie@company.com', role: 'FINANCE', department: 'Finance', manager_id: '102' },
  { id: '104', name: 'Dana Evans', email: 'dana@company.com', role: 'HR', department: 'People & Culture', manager_id: null },
  { id: '105', name: 'Evan Vance', email: 'evan@company.com', role: 'IT_ADMIN', department: 'Infra', manager_id: '102' }
]

const DEFAULT_LEAVE_TYPES = [
  { id: 1, code: 'ANNUAL', name: 'Annual Leave', maxDays: 20 },
  { id: 2, code: 'CASUAL', name: 'Casual Leave', maxDays: 10 },
  { id: 3, code: 'SICK', name: 'Sick Leave', maxDays: 12 },
  { id: 4, code: 'UNPAID', name: 'Unpaid Leave', maxDays: 60 },
  { id: 5, code: 'PARENTAL', name: 'Maternity / Paternity Leave', maxDays: 90 }
]

const DEFAULT_LEAVES = [
  {
    id: 1008,
    employeeId: '101',
    employeeName: 'Alice Smith',
    managerId: '102',
    managerName: 'Bob Roberts',
    leaveTypeId: 1,
    leaveType: 'Annual Leave',
    startDate: '2026-09-10',
    endDate: '2026-09-12',
    days: 3,
    status: 'PENDING',
    reason: 'Family vacation trip',
    submittedAt: '01 Sep 2026 11:25 AM',
    createdOn: '2026-09-01 11:25:00',
    workflowId: 1,
    history: [
      { type: 'SUBMITTED', title: 'Request submitted', actor: 'Alice Smith', timestamp: '01 Sep 2026 11:25 AM', note: 'Family vacation trip' },
      { type: 'PENDING', title: 'Pending manager approval', actor: 'Bob Roberts', timestamp: '01 Sep 2026 11:25 AM' }
    ]
  },
  {
    id: 1007,
    employeeId: '101',
    employeeName: 'Alice Smith',
    managerId: '102',
    managerName: 'Bob Roberts',
    leaveTypeId: 3,
    leaveType: 'Sick Leave',
    startDate: '2026-08-20',
    endDate: '2026-08-20',
    days: 1,
    status: 'APPROVED',
    reason: 'Medical checkup and dental appointment',
    actionedBy: 'Bob Roberts',
    actionedAt: '20 Aug 2026 09:30 AM',
    approvalComment: 'Approved. Take care and get well soon.',
    submittedAt: '20 Aug 2026 08:30 AM',
    createdOn: '2026-08-20 08:30:00',
    workflowId: 1,
    history: [
      { type: 'SUBMITTED', title: 'Request submitted', actor: 'Alice Smith', timestamp: '20 Aug 2026 08:30 AM', note: 'Medical checkup and dental appointment' },
      { type: 'APPROVED', title: 'Approved', actor: 'Bob Roberts', timestamp: '20 Aug 2026 09:30 AM', note: 'Approved. Take care and get well soon.' }
    ]
  },
  {
    id: 1006,
    employeeId: '101',
    employeeName: 'Alice Smith',
    managerId: '102',
    managerName: 'Bob Roberts',
    leaveTypeId: 2,
    leaveType: 'Casual Leave',
    startDate: '2026-08-15',
    endDate: '2026-08-16',
    days: 2,
    status: 'REJECTED',
    reason: 'Personal errands and travel',
    actionedBy: 'Bob Roberts',
    actionedAt: '14 Aug 2026 02:15 PM',
    rejectionReason: 'Project release sprint deadline during these dates. Please reschedule.',
    submittedAt: '14 Aug 2026 10:00 AM',
    createdOn: '2026-08-14 10:00:00',
    workflowId: 1,
    history: [
      { type: 'SUBMITTED', title: 'Request submitted', actor: 'Alice Smith', timestamp: '14 Aug 2026 10:00 AM', note: 'Personal errands and travel' },
      { type: 'REJECTED', title: 'Rejected', actor: 'Bob Roberts', timestamp: '14 Aug 2026 02:15 PM', note: 'Project release sprint deadline during these dates. Please reschedule.' }
    ]
  }
]

const DEFAULT_EXPENSES = [
  { id: 101, userId: '101', userName: 'Alice Smith', title: 'Client Dinner (Q3 Kickoff)', amount: 450, category: 'Meals', status: 'PENDING_MANAGER', workflowId: 2 },
  { id: 102, userId: '101', userName: 'Alice Smith', title: 'Cloud Infrastructure Annual Subscription', amount: 8500, category: 'Software', status: 'PENDING_FINANCE', workflowId: 3 }
]

const DEFAULT_POS = [
  { id: 501, userId: '102', userName: 'Bob Roberts', vendor: 'Dell Enterprise Systems', department: 'Engineering', totalCost: 14200, itemsCount: 6, status: 'PENDING_APPROVAL', workflowId: 4 },
  { id: 502, userId: '102', userName: 'Bob Roberts', vendor: 'Office Essentials Hub', department: 'Engineering', totalCost: 1200, itemsCount: 15, status: 'APPROVED', workflowId: 4 }
]

const DEFAULT_IT = [
  { id: 701, userId: '101', userName: 'Alice Smith', assetType: 'MacBook Pro M3 Max + Monitor', priority: 'HIGH', status: 'IN_REVIEW', workflowId: 5, details: 'Required for deep learning builds' }
]

const DEFAULT_KYC = [
  { id: 901, customerName: 'Acme Global Holdings Ltd', documentType: 'Certificate of Incorporation', riskScore: 18, status: 'PENDING_COMPLIANCE', workflowId: 6 }
]

function formatDisplayDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  } catch (_e) {
    return dateStr
  }
}

function formatDisplayTimestamp(date = new Date()) {
  const d = typeof date === 'string' ? new Date(date) : date
  const datePart = d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
  const timePart = d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
  return `${datePart} ${timePart}`
}

class ClientDatabase {
  constructor() {
    this.init()
  }

  init() {
    if (!localStorage.getItem(DB_KEYS.USERS)) {
      localStorage.setItem(DB_KEYS.USERS, JSON.stringify(DEFAULT_USERS))
    }
    if (!localStorage.getItem(DB_KEYS.LEAVE_TYPES)) {
      localStorage.setItem(DB_KEYS.LEAVE_TYPES, JSON.stringify(DEFAULT_LEAVE_TYPES))
    }
    if (!localStorage.getItem(DB_KEYS.LEAVES)) {
      localStorage.setItem(DB_KEYS.LEAVES, JSON.stringify(DEFAULT_LEAVES))
    }
    if (!localStorage.getItem(DB_KEYS.EXPENSES)) {
      localStorage.setItem(DB_KEYS.EXPENSES, JSON.stringify(DEFAULT_EXPENSES))
    }
    if (!localStorage.getItem(DB_KEYS.PURCHASE_ORDERS)) {
      localStorage.setItem(DB_KEYS.PURCHASE_ORDERS, JSON.stringify(DEFAULT_POS))
    }
    if (!localStorage.getItem(DB_KEYS.IT_REQUESTS)) {
      localStorage.setItem(DB_KEYS.IT_REQUESTS, JSON.stringify(DEFAULT_IT))
    }
    if (!localStorage.getItem(DB_KEYS.KYC_CASES)) {
      localStorage.setItem(DB_KEYS.KYC_CASES, JSON.stringify(DEFAULT_KYC))
    }
  }

  // --- Users & Relationships ---
  getUsers() {
    return JSON.parse(localStorage.getItem(DB_KEYS.USERS) || '[]')
  }

  getUserById(userId) {
    if (!userId) return null
    const users = this.getUsers()
    return users.find(u => String(u.id) === String(userId)) || null
  }

  getManagerForUser(userId) {
    const user = this.getUserById(userId)
    if (!user || !user.manager_id) return null
    return this.getUserById(user.manager_id)
  }

  // --- Leave Types ---
  getLeaveTypes() {
    return JSON.parse(localStorage.getItem(DB_KEYS.LEAVE_TYPES) || '[]')
  }

  // --- Leaves ---
  getLeaves() {
    return JSON.parse(localStorage.getItem(DB_KEYS.LEAVES) || '[]')
  }

  /**
   * Data-level RBAC: Returns only leave requests owned by the given employee.
   */
  getLeavesForUser(user) {
    if (!user || !user.id) return []
    const all = this.getLeaves()
    return all.filter(r => String(r.employeeId || r.userId) === String(user.id))
  }

  /**
   * Data-level RBAC: Returns pending leave requests assigned to the manager.
   */
  getPendingLeavesForManager(managerUser) {
    if (!managerUser || !managerUser.id) return []
    const all = this.getLeaves()
    return all.filter(r => {
      const isPending = r.status === 'PENDING' || r.status === 'PENDING_MANAGER'
      const isAssigned = String(r.managerId) === String(managerUser.id)
      return isPending && isAssigned
    })
  }

  /**
   * Data-level RBAC: Get single leave request with authorization check.
   */
  getLeaveById(requestId, currentUser) {
    const all = this.getLeaves()
    const item = all.find(r => String(r.id) === String(requestId))
    if (!item) return null

    if (currentUser) {
      const isOwner = String(item.employeeId || item.userId) === String(currentUser.id)
      const isManager = String(item.managerId) === String(currentUser.id)
      const isHR = currentUser.role === 'HR'
      if (!isOwner && !isManager && !isHR) {
        throw new Error('You are not authorized to view this leave request.')
      }
    }
    return item
  }

  /**
   * Create a new leave request. Resolves reporting manager from employee's user record.
   */
  createLeave(data, currentUser) {
    const user = currentUser || this.getUserById(data.employeeId || data.userId)
    if (!user) throw new Error('User session is missing or invalid.')

    const manager = this.getManagerForUser(user.id)
    const list = this.getLeaves()
    const now = new Date()
    const timestampStr = formatDisplayTimestamp(now)
    const nextId = 1000 + (list.length > 0 ? Math.max(...list.map(r => Number(r.id) || 0)) - 1000 + 1 : 1)

    const newRecord = {
      id: nextId,
      employeeId: String(user.id),
      employeeName: user.name,
      managerId: manager ? String(manager.id) : null,
      managerName: manager ? manager.name : 'Unassigned',
      leaveTypeId: data.leaveTypeId || 1,
      leaveType: data.leaveType || 'Annual Leave',
      startDate: data.startDate,
      endDate: data.endDate || data.startDate,
      days: Number(data.days) || 1,
      status: 'PENDING',
      reason: data.reason || '',
      submittedAt: timestampStr,
      createdOn: now.toISOString().replace('T', ' ').slice(0, 19),
      workflowId: 1,
      history: [
        {
          type: 'SUBMITTED',
          title: 'Request submitted',
          actor: user.name,
          timestamp: timestampStr,
          note: data.reason || ''
        },
        {
          type: 'PENDING',
          title: 'Pending manager approval',
          actor: manager ? manager.name : 'Assigned Manager',
          timestamp: timestampStr
        }
      ]
    }

    list.unshift(newRecord)
    localStorage.setItem(DB_KEYS.LEAVES, JSON.stringify(list))
    return newRecord
  }

  /**
   * Action-level RBAC: Approve leave request.
   */
  approveLeave(requestId, currentUser, comment = '') {
    if (!currentUser || !currentUser.id) {
      throw new Error('You must be logged in to approve leave requests.')
    }
    if (currentUser.role !== 'MANAGER' && currentUser.role !== 'HR') {
      throw new Error('Unauthorized: Only managers can approve leave requests.')
    }

    const list = this.getLeaves()
    const item = list.find(r => String(r.id) === String(requestId))
    if (!item) {
      throw new Error('Leave request not found.')
    }

    // Security check: Manager can only approve requests assigned to them
    if (currentUser.role === 'MANAGER' && String(item.managerId) !== String(currentUser.id)) {
      throw new Error('Unauthorized: You can only approve leave requests assigned to you.')
    }

    // Concurrency / Stale check
    if (item.status !== 'PENDING' && item.status !== 'PENDING_MANAGER') {
      throw new Error('This leave request has already been processed.')
    }

    const now = new Date()
    const timestampStr = formatDisplayTimestamp(now)

    item.status = 'APPROVED'
    item.actionedBy = currentUser.name
    item.actionedAt = timestampStr
    item.approvalComment = comment || ''

    if (!Array.isArray(item.history)) item.history = []
    item.history.push({
      type: 'APPROVED',
      title: 'Approved',
      actor: currentUser.name,
      timestamp: timestampStr,
      note: comment || ''
    })

    localStorage.setItem(DB_KEYS.LEAVES, JSON.stringify(list))
    return item
  }

  /**
   * Action-level RBAC: Reject leave request.
   */
  rejectLeave(requestId, currentUser, reason = '') {
    if (!currentUser || !currentUser.id) {
      throw new Error('You must be logged in to reject leave requests.')
    }
    if (currentUser.role !== 'MANAGER' && currentUser.role !== 'HR') {
      throw new Error('Unauthorized: Only managers can reject leave requests.')
    }
    if (!reason || !reason.trim()) {
      throw new Error('Rejection reason is mandatory.')
    }

    const list = this.getLeaves()
    const item = list.find(r => String(r.id) === String(requestId))
    if (!item) {
      throw new Error('Leave request not found.')
    }

    // Security check: Manager can only reject requests assigned to them
    if (currentUser.role === 'MANAGER' && String(item.managerId) !== String(currentUser.id)) {
      throw new Error('Unauthorized: You can only reject leave requests assigned to you.')
    }

    // Concurrency / Stale check
    if (item.status !== 'PENDING' && item.status !== 'PENDING_MANAGER') {
      throw new Error('This leave request has already been processed.')
    }

    const now = new Date()
    const timestampStr = formatDisplayTimestamp(now)

    item.status = 'REJECTED'
    item.actionedBy = currentUser.name
    item.actionedAt = timestampStr
    item.rejectionReason = reason.trim()

    if (!Array.isArray(item.history)) item.history = []
    item.history.push({
      type: 'REJECTED',
      title: 'Rejected',
      actor: currentUser.name,
      timestamp: timestampStr,
      note: reason.trim()
    })

    localStorage.setItem(DB_KEYS.LEAVES, JSON.stringify(list))
    return item
  }

  updateLeaveStatus(id, newStatus, remarks = '') {
    const list = this.getLeaves()
    const item = list.find(r => String(r.id) === String(id))
    if (item) {
      item.status = newStatus
      if (remarks) item.remarks = remarks
      localStorage.setItem(DB_KEYS.LEAVES, JSON.stringify(list))
    }
    return item
  }

  // --- Expenses ---
  getExpenses() {
    return JSON.parse(localStorage.getItem(DB_KEYS.EXPENSES) || '[]')
  }

  createExpense(data) {
    const list = this.getExpenses()
    const newRecord = {
      id: Date.now() % 100000,
      status: 'PENDING_MANAGER',
      createdOn: new Date().toISOString().replace('T', ' ').slice(0, 19),
      ...data
    }
    list.unshift(newRecord)
    localStorage.setItem(DB_KEYS.EXPENSES, JSON.stringify(list))
    return newRecord
  }

  updateExpenseStatus(id, newStatus, remarks = '') {
    const list = this.getExpenses()
    const item = list.find(r => r.id === Number(id))
    if (item) {
      item.status = newStatus
      if (remarks) item.remarks = remarks
      localStorage.setItem(DB_KEYS.EXPENSES, JSON.stringify(list))
    }
    return item
  }

  // --- Purchase Orders ---
  getPurchaseOrders() {
    return JSON.parse(localStorage.getItem(DB_KEYS.PURCHASE_ORDERS) || '[]')
  }

  createPurchaseOrder(data) {
    const list = this.getPurchaseOrders()
    const newRecord = {
      id: Date.now() % 100000,
      status: 'PENDING_APPROVAL',
      createdOn: new Date().toISOString().replace('T', ' ').slice(0, 19),
      ...data
    }
    list.unshift(newRecord)
    localStorage.setItem(DB_KEYS.PURCHASE_ORDERS, JSON.stringify(list))
    return newRecord
  }

  updatePOStatus(id, newStatus, remarks = '') {
    const list = this.getPurchaseOrders()
    const item = list.find(r => r.id === Number(id))
    if (item) {
      item.status = newStatus
      if (remarks) item.remarks = remarks
      localStorage.setItem(DB_KEYS.PURCHASE_ORDERS, JSON.stringify(list))
    }
    return item
  }

  // --- IT Requests ---
  getItRequests() {
    return JSON.parse(localStorage.getItem(DB_KEYS.IT_REQUESTS) || '[]')
  }

  createItRequest(data) {
    const list = this.getItRequests()
    const newRecord = {
      id: Date.now() % 100000,
      status: 'IN_REVIEW',
      createdOn: new Date().toISOString().replace('T', ' ').slice(0, 19),
      ...data
    }
    list.unshift(newRecord)
    localStorage.setItem(DB_KEYS.IT_REQUESTS, JSON.stringify(list))
    return newRecord
  }

  updateItStatus(id, newStatus, remarks = '') {
    const list = this.getItRequests()
    const item = list.find(r => r.id === Number(id))
    if (item) {
      item.status = newStatus
      if (remarks) item.remarks = remarks
      localStorage.setItem(DB_KEYS.IT_REQUESTS, JSON.stringify(list))
    }
    return item
  }

  // --- KYC ---
  getKycCases() {
    return JSON.parse(localStorage.getItem(DB_KEYS.KYC_CASES) || '[]')
  }

  createKycCase(data) {
    const list = this.getKycCases()
    const newRecord = {
      id: Date.now() % 100000,
      status: 'PENDING_COMPLIANCE',
      createdOn: new Date().toISOString().replace('T', ' ').slice(0, 19),
      ...data
    }
    list.unshift(newRecord)
    localStorage.setItem(DB_KEYS.KYC_CASES, JSON.stringify(list))
    return newRecord
  }

  updateKycStatus(id, newStatus, remarks = '') {
    const list = this.getKycCases()
    const item = list.find(r => r.id === Number(id))
    if (item) {
      item.status = newStatus
      if (remarks) item.remarks = remarks
      localStorage.setItem(DB_KEYS.KYC_CASES, JSON.stringify(list))
    }
    return item
  }

  // --- Unified pending tasks across all modules for a given role/user ---
  getPendingApprovalsForUser(user) {
    if (!user) return []
    const pending = []

    // 1. Leaves (Enforce manager assignment RBAC: only requests assigned to this user)
    this.getLeaves().forEach(r => {
      const isPending = r.status === 'PENDING' || r.status === 'PENDING_MANAGER'
      const isAssigned = String(r.managerId) === String(user.id) || (user.role === 'HR' && !r.managerId)

      if (isPending && (user.role === 'MANAGER' || user.role === 'HR') && isAssigned) {
        pending.push({
          entityType: 'LeaveRequest',
          entityId: r.id,
          title: `${r.employeeName || r.userName} - ${r.leaveType} (${r.days} Day${r.days > 1 ? 's' : ''})`,
          subtitle: `Reason: ${r.reason || 'Not specified'} &bull; Manager: ${r.managerName || 'Assigned'}`,
          submittedBy: r.employeeName || r.userName,
          workflowId: r.workflowId || 1,
          status: r.status,
          createdOn: r.submittedAt || r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
    })

    // 2. Expenses
    this.getExpenses().forEach(r => {
      if (r.status === 'PENDING_MANAGER' && (user.role === 'MANAGER' || user.role === 'FINANCE')) {
        pending.push({
          entityType: 'ExpenseClaim',
          entityId: r.id,
          title: `${r.userName} - ${r.title}`,
          subtitle: `$${r.amount} &bull; Category: ${r.category}`,
          submittedBy: r.userName,
          workflowId: r.workflowId || 2,
          status: r.status,
          createdOn: r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
      if (r.status === 'PENDING_FINANCE' && user.role === 'FINANCE') {
        pending.push({
          entityType: 'ExpenseClaim',
          entityId: r.id,
          title: `[HIGH VALUE] ${r.userName} - ${r.title}`,
          subtitle: `$${r.amount} &bull; VP Approval Gate`,
          submittedBy: r.userName,
          workflowId: r.workflowId || 3,
          status: r.status,
          createdOn: r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
    })

    // 3. Purchase Orders
    this.getPurchaseOrders().forEach(r => {
      if (r.status === 'PENDING_APPROVAL' && (user.role === 'FINANCE' || user.role === 'MANAGER')) {
        pending.push({
          entityType: 'PurchaseOrder',
          entityId: r.id,
          title: `PO #${r.id} - ${r.vendor}`,
          subtitle: `$${r.totalCost.toLocaleString()} &bull; Dept: ${r.department}`,
          submittedBy: r.userName,
          workflowId: r.workflowId || 4,
          status: r.status,
          createdOn: r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
    })

    // 4. IT Requests
    this.getItRequests().forEach(r => {
      if (r.status === 'IN_REVIEW' && (user.role === 'IT_ADMIN' || user.role === 'MANAGER')) {
        pending.push({
          entityType: 'ItRequest',
          entityId: r.id,
          title: `IT #${r.id} - ${r.assetType}`,
          subtitle: `Priority: ${r.priority} &bull; User: ${r.userName}`,
          submittedBy: r.userName,
          workflowId: r.workflowId || 5,
          status: r.status,
          createdOn: r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
    })

    // 5. KYC Cases
    this.getKycCases().forEach(r => {
      if (r.status === 'PENDING_COMPLIANCE' && (user.role === 'HR' || user.role === 'FINANCE')) {
        pending.push({
          entityType: 'CustomerKyc',
          entityId: r.id,
          title: `KYC - ${r.customerName}`,
          subtitle: `Risk Score: ${r.riskScore}/100 &bull; ${r.documentType}`,
          submittedBy: 'Onboarding Pipeline',
          workflowId: r.workflowId || 6,
          status: r.status,
          createdOn: r.createdOn || 'Recent',
          actions: ['APPROVE', 'REJECT']
        })
      }
    })

    return pending
  }
}

export const clientDb = new ClientDatabase()
