import React, { useState, useMemo, useEffect } from 'react'
import {
  Calendar,
  Plus,
  Send,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
  User,
  ShieldCheck,
  Eye,
  Check,
  X,
  AlertCircle,
  ArrowRight,
  FileText,
  Building,
  Info
} from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { genericWorkflowApi } from '../services/genericWorkflowApi'

const MODULE_KEY = 'leave_requests'

export default function LeaveModule({ currentUser, onDataChanged }) {
  const [leavesList, setLeavesList] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  // Roles
  const isManager = currentUser?.role === 'MANAGER'
  const isHR = currentUser?.role === 'HR'
  const canApprove = isManager || isHR

  // Subtabs: For Manager, allow switching between 'approvals' and 'my_requests'
  const [activeSubTab, setActiveSubTab] = useState(isManager ? 'approvals' : 'my_requests')

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [typeFilter, setTypeFilter] = useState('ALL')

  // Modals state
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [submissionResult, setSubmissionResult] = useState(null)
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [approveConfirmItem, setApproveConfirmItem] = useState(null)
  const [approvalComment, setApprovalComment] = useState('')
  const [rejectConfirmItem, setRejectConfirmItem] = useState(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [rejectionError, setRejectionError] = useState('')

  // Form State
  const [leaveTypeId, setLeaveTypeId] = useState(1)
  const [startDate, setStartDate] = useState('2026-09-10')
  const [endDate, setEndDate] = useState('2026-09-12')
  const [reason, setReason] = useState('')

  // Action status state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [feedbackBanner, setFeedbackBanner] = useState(null)

  // Leave types from directory
  const leaveTypes = useMemo(() => clientDb.getLeaveTypes(), [])

  // Manager record for current user
  const reportingManager = useMemo(() => {
    return clientDb.getManagerForUser(currentUser?.id)
  }, [currentUser])

  // Generic records fetch from Python Gateway
  const loadRecords = async () => {
    try {
      setIsLoading(true)
      const data = await genericWorkflowApi.fetchRecords(MODULE_KEY)
      if (Array.isArray(data)) {
        const users = clientDb.getUsers()
        const types = clientDb.getLeaveTypes()
        const mapped = data.map(r => {
          const u = users.find(x => String(x.id) === String(r.employee_id))
          const mgr = u ? clientDb.getManagerForUser(u.id) : null
          const lt = types.find(t => Number(t.id) === Number(r.leave_type_id))
          return {
            id: r.leave_request_id,
            employeeId: String(r.employee_id),
            employeeName: u ? u.name : `Employee #${r.employee_id}`,
            employeeEmail: u ? u.email : 'employee@company.com',
            managerId: mgr ? String(mgr.id) : (u?.manager_id ? String(u.manager_id) : '3'),
            managerName: mgr ? mgr.name : 'Rajesh Kumar',
            leaveTypeId: r.leave_type_id,
            leaveType: lt ? lt.name : 'Annual Leave',
            startDate: r.start_date,
            endDate: r.end_date || r.start_date,
            days: 2,
            status: String(r.status || 'PENDING').toUpperCase(),
            reason: r.reason || 'Leave Request',
            submittedAt: r.submitted_at ? new Date(r.submitted_at).toLocaleString() : 'Recent'
          }
        })
        setLeavesList(mapped)
      } else {
        setLeavesList([])
      }
    } catch (_e) {
      setLeavesList([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadRecords()
  }, [currentUser])

  // Data Slices
  const myRequests = useMemo(() => {
    return leavesList.filter(r => String(r.employeeId) === String(currentUser?.id))
  }, [leavesList, currentUser])

  const pendingApprovals = useMemo(() => {
    return canApprove
      ? leavesList.filter(r => (r.status === 'PENDING' || r.status === 'PENDING_MANAGER') && String(r.managerId) === String(currentUser?.id))
      : []
  }, [leavesList, currentUser, canApprove])

  // Auto-calculate Duration
  const calculatedDays = useMemo(() => {
    if (!startDate || !endDate) return 1
    const start = new Date(startDate)
    const end = new Date(endDate)
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return 1
    const diffTime = end.getTime() - start.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1
    return diffDays > 0 ? diffDays : 1
  }, [startDate, endDate])

  // Summary Metrics
  const summaryMetrics = useMemo(() => {
    const list = myRequests
    const total = list.length
    const pending = list.filter(r => r.status === 'PENDING' || r.status === 'PENDING_MANAGER').length
    const approved = list.filter(r => r.status === 'APPROVED').length
    const rejected = list.filter(r => r.status === 'REJECTED').length
    return { total, pending, approved, rejected }
  }, [myRequests])

  // Filtered My Requests
  const filteredMyRequests = useMemo(() => {
    return myRequests.filter(item => {
      const formattedId = `LR-${item.id}`
      const matchesSearch =
        !searchQuery ||
        formattedId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.leaveType || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.reason || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.managerName || '').toLowerCase().includes(searchQuery.toLowerCase())

      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'PENDING' && (item.status === 'PENDING' || item.status === 'PENDING_MANAGER')) ||
        item.status === statusFilter

      const matchesType = typeFilter === 'ALL' || item.leaveType === typeFilter

      return matchesSearch && matchesStatus && matchesType
    })
  }, [myRequests, searchQuery, statusFilter, typeFilter])

  // Handlers
  const handleOpenApplyModal = () => {
    setShowApplyModal(true)
    setSubmissionResult(null)
    setStartDate('2026-09-10')
    setEndDate('2026-09-12')
    setReason('')
    setLeaveTypeId(1)
  }

  const handleSubmitLeave = async (e) => {
    e.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    setFeedbackBanner(null)

    const selectedTypeObj = leaveTypes.find(t => t.id === Number(leaveTypeId))
    const typeName = selectedTypeObj ? selectedTypeObj.name : 'Annual Leave'

    try {
      // 1. Generic submission through Python Gateway
      const res = await genericWorkflowApi.submit(MODULE_KEY, {
        employee_id: Number(currentUser.id) || 5,
        leave_type_id: Number(leaveTypeId) || 1,
        start_date: startDate,
        end_date: endDate,
        reason: reason || 'Leave Request',
        status: 'PENDING'
      }, currentUser)

      await loadRecords()

      setSubmissionResult({
        id: res.record_id,
        leaveType: typeName,
        startDate,
        endDate,
        days: calculatedDays,
        managerName: reportingManager ? reportingManager.name : 'Rajesh Kumar',
        reason
      })
    } catch (err) {
      setFeedbackBanner({
        type: 'error',
        message: err.message || 'Unable to submit leave request.'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOpenApproveModal = (req, e) => {
    if (e) e.stopPropagation()
    setApproveConfirmItem(req)
    setApprovalComment('')
  }

  const handleConfirmApprove = async () => {
    if (!approveConfirmItem || actionLoadingId) return
    const requestId = approveConfirmItem.id
    setActionLoadingId(requestId)

    try {
      await genericWorkflowApi.executeAction(MODULE_KEY, requestId, 'APPROVE', approvalComment, currentUser, {
        employee_email: approveConfirmItem.employeeEmail
      })

      setFeedbackBanner({
        type: 'success',
        message: `✓ Leave request #LR-${requestId} approved successfully.`
      })

      setApproveConfirmItem(null)
      await loadRecords()
    } catch (err) {
      setFeedbackBanner({ type: 'error', message: err.message })
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleOpenRejectModal = (req, e) => {
    if (e) e.stopPropagation()
    setRejectConfirmItem(req)
    setRejectionReason('')
    setRejectionError('')
  }

  const handleConfirmReject = async () => {
    if (!rejectConfirmItem || actionLoadingId) return
    if (!rejectionReason.trim()) {
      setRejectionError('Rejection reason is mandatory.')
      return
    }

    const requestId = rejectConfirmItem.id
    setActionLoadingId(requestId)

    try {
      await genericWorkflowApi.executeAction(MODULE_KEY, requestId, 'REJECT', rejectionReason, currentUser, {
        employee_email: rejectConfirmItem.employeeEmail
      })

      setFeedbackBanner({
        type: 'success',
        message: `✓ Leave request #LR-${requestId} rejected.`
      })

      setRejectConfirmItem(null)
      await loadRecords()
    } catch (err) {
      setFeedbackBanner({ type: 'error', message: err.message })
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleRequestCancellation = async (req, e) => {
    if (e) e.stopPropagation()
    try {
      await genericWorkflowApi.submit('leave_cancellation', {
        employee_id: Number(currentUser.id),
        leave_type_id: req.leaveTypeId || 1,
        start_date: req.startDate,
        end_date: req.endDate,
        reason: `Cancellation requested for Leave #LR-${req.id}`,
        status: 'PENDING_CANCELLATION'
      }, currentUser)

      setFeedbackBanner({
        type: 'success',
        message: `✓ Leave cancellation requested! Launched 2nd Workflow (Leave_Cancellation_Request #1122).`
      })
      await loadRecords()
    } catch (err) {
      setFeedbackBanner({ type: 'error', message: err.message })
    }
  }

  const handleViewDetails = (req, e) => {
    if (e) e.stopPropagation()
    const item = leavesList.find(x => x.id === req.id)
    setSelectedRequest(item || req)
  }

  // Format Helper
  const getStatusBadge = (status) => {
    const s = (status || '').toUpperCase()
    if (s === 'APPROVED') {
      return (
        <span className="status-pill approved">
          <CheckCircle2 size={12} />
          <span>Approved</span>
        </span>
      )
    }
    if (s === 'REJECTED') {
      return (
        <span className="status-pill rejected">
          <XCircle size={12} />
          <span>Rejected</span>
        </span>
      )
    }
    if (s === 'CANCELLED') {
      return (
        <span className="status-pill badge-neutral">
          <span>Cancelled</span>
        </span>
      )
    }
    return (
      <span className="status-pill pending">
        <Clock size={12} />
        <span>Pending Manager Approval</span>
      </span>
    )
  }

  return (
    <div className="module-container">
      {/* 1. Header Section */}
      <div className="module-header-row">
        <div>
          <h2 className="module-title">🌴 Leave Management</h2>
          <p className="module-subtitle">
            {isManager
              ? 'Review employee leave applications and manage your personal leave requests'
              : 'Request and track your leave applications with your reporting manager'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="btn btn-primary" onClick={handleOpenApplyModal}>
            <Plus size={15} />
            <span>Apply For Leave</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedbackBanner && (
        <div className={`status-banner ${feedbackBanner.type === 'error' ? 'error' : 'success'} mb-4`}>
          {feedbackBanner.type === 'error' ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
          <span className="text-sm font-semibold">{feedbackBanner.message}</span>
        </div>
      )}

      {/* 2. Manager Subtabs Navigation (if user is Manager) */}
      {isManager && (
        <div className="leave-subtabs-row">
          <div className="leave-subtabs">
            <button
              className={`leave-tab-btn ${activeSubTab === 'approvals' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('approvals')}
            >
              <ShieldCheck size={15} />
              <span>Pending Approvals</span>
              {pendingApprovals.length > 0 && (
                <span className="nav-counter-pill">{pendingApprovals.length}</span>
              )}
            </button>
            <button
              className={`leave-tab-btn ${activeSubTab === 'my_requests' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('my_requests')}
            >
              <Calendar size={15} />
              <span>My Requests</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. MANAGER PENDING APPROVALS VIEW */}
      {isManager && activeSubTab === 'approvals' && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-white">
              Assigned Leave Requests ({pendingApprovals.length})
            </div>
            <div className="text-xs text-muted">
              Only requests from your direct reports are shown here.
            </div>
          </div>

          {pendingApprovals.length === 0 ? (
            <div className="empty-inbox-card">
              <CheckCircle2 size={44} color="#4ade80" className="mb-2" />
              <div className="font-bold text-lg text-white">No Pending Leave Approvals</div>
              <div className="text-sm text-muted mt-1">
                You have reviewed all pending leave requests assigned to you as{' '}
                <strong>{currentUser.name}</strong>.
              </div>
            </div>
          ) : (
            <div className="tasks-grid">
              {pendingApprovals.map((req) => {
                const isProcessing = actionLoadingId === req.id
                return (
                  <div key={req.id} className="task-approval-card">
                    <div>
                      <div className="task-card-header">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-muted font-bold">
                            #LR-{req.id}
                          </span>
                          <span className="badge badge-neutral">{req.leaveType}</span>
                        </div>
                        <span className="status-pill pending">
                          <Clock size={11} />
                          <span>Pending Approval</span>
                        </span>
                      </div>

                      <div className="task-card-body">
                        <div className="flex items-center gap-2 mb-2">
                          <User size={15} color="#818cf8" />
                          <span className="font-bold text-white text-base">
                            {req.employeeName}
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs text-muted mb-2">
                          <div>
                            <span className="text-slate-400">Dates: </span>
                            <strong className="text-white">
                              {req.startDate} {req.endDate && req.endDate !== req.startDate ? `→ ${req.endDate}` : ''}
                            </strong>
                          </div>
                          <div>
                            <span className="text-slate-400">Duration: </span>
                            <strong className="text-white">{req.days} Day{req.days > 1 ? 's' : ''}</strong>
                          </div>
                        </div>

                        {req.reason && (
                          <div className="timeline-item-note mb-2 text-xs">
                            <span className="text-slate-400">Reason: </span>
                            <span>{req.reason}</span>
                          </div>
                        )}

                        <div className="text-xs text-muted">
                          Submitted: <span className="text-slate-300">{req.submittedAt || req.createdOn}</span>
                        </div>
                      </div>
                    </div>

                    <div className="task-card-footer flex justify-between items-center">
                      <button
                        className="btn btn-outline text-xs"
                        onClick={(e) => handleViewDetails(req, e)}
                        disabled={isProcessing}
                      >
                        <Eye size={13} />
                        <span>View Details</span>
                      </button>

                      <div className="flex items-center gap-2">
                        <button
                          className="btn btn-danger-outline text-xs"
                          onClick={(e) => handleOpenRejectModal(req, e)}
                          disabled={isProcessing}
                        >
                          <XCircle size={13} />
                          <span>Reject</span>
                        </button>

                        <button
                          className="btn btn-success text-xs"
                          onClick={(e) => handleOpenApproveModal(req, e)}
                          disabled={isProcessing}
                        >
                          <Check size={13} />
                          <span>Approve</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 4. MY REQUESTS & EMPLOYEE DASHBOARD VIEW */}
      {(!isManager || activeSubTab === 'my_requests') && (
        <div>
          {/* Summary Metrics Bar */}
          <div className="stats-summary-grid">
            <div className="stat-card">
              <div className="stat-icon-box total">
                <Calendar size={22} />
              </div>
              <div>
                <div className="stat-value">{summaryMetrics.total}</div>
                <div className="stat-label">Total Requests</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-box pending">
                <Clock size={22} />
              </div>
              <div>
                <div className="stat-value">{summaryMetrics.pending}</div>
                <div className="stat-label">Pending Approval</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-box approved">
                <CheckCircle2 size={22} />
              </div>
              <div>
                <div className="stat-value">{summaryMetrics.approved}</div>
                <div className="stat-label">Approved</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-box rejected">
                <XCircle size={22} />
              </div>
              <div>
                <div className="stat-value">{summaryMetrics.rejected}</div>
                <div className="stat-label">Rejected</div>
              </div>
            </div>
          </div>

          {/* Search and Filters Bar */}
          <div className="leave-filters-bar">
            <div className="search-input-wrapper">
              <Search size={15} />
              <input
                type="text"
                className="text-input text-xs"
                placeholder="Search request #, type, reason, manager..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <select
              className="select-input filter-select text-xs"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>

            <select
              className="select-input filter-select text-xs"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="ALL">All Leave Types</option>
              {leaveTypes.map((t) => (
                <option key={t.id} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>

            {(searchQuery || statusFilter !== 'ALL' || typeFilter !== 'ALL') && (
              <button
                className="btn btn-outline text-xs"
                onClick={() => {
                  setSearchQuery('')
                  setStatusFilter('ALL')
                  setTypeFilter('ALL')
                }}
              >
                Clear Filters
              </button>
            )}
          </div>

          {/* My Requests Table */}
          <div className="card-table-wrapper">
            <table className="enterprise-table">
              <thead>
                <tr>
                  <th>Request #</th>
                  <th>Leave Type</th>
                  <th>Dates</th>
                  <th>Duration</th>
                  <th>Reporting Manager</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredMyRequests.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '36px' }}>
                      <div className="text-muted text-sm">
                        {myRequests.length === 0
                          ? 'No leave requests found.'
                          : 'No requests match the selected filters.'}
                      </div>
                      {myRequests.length === 0 && (
                        <button
                          className="btn btn-primary mt-3 text-xs"
                          onClick={handleOpenApplyModal}
                        >
                          <Plus size={13} />
                          <span>Apply for Leave</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ) : (
                  filteredMyRequests.map((req) => (
                    <tr
                      key={req.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleViewDetails(req)}
                    >
                      <td className="font-mono text-muted font-bold">#LR-{req.id}</td>
                      <td>
                        <span className="font-semibold text-white">{req.leaveType}</span>
                      </td>
                      <td>
                        <span className="text-sm">
                          {req.startDate}{' '}
                          {req.endDate && req.endDate !== req.startDate ? `→ ${req.endDate}` : ''}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-neutral">
                          {req.days} Day{req.days > 1 ? 's' : ''}
                        </span>
                      </td>
                      <td>
                        <span className="text-slate-300 font-medium">
                          {req.managerName || 'Assigned Manager'}
                        </span>
                      </td>
                      <td>{getStatusBadge(req.status)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            className="btn btn-outline text-xs"
                            onClick={(e) => handleViewDetails(req, e)}
                          >
                            <Eye size={12} />
                            <span>View Details</span>
                          </button>
                          {req.status === 'APPROVED' && (
                            <button
                              className="btn btn-danger-outline text-xs"
                              title="Trigger 2nd Workflow: Leave Cancellation"
                              onClick={(e) => handleRequestCancellation(req, e)}
                            >
                              <span>Cancel Leave</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 5. APPLY FOR LEAVE MODAL */}
      {showApplyModal && (
        <div className="modal-overlay" onClick={() => !isSubmitting && setShowApplyModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            {submissionResult ? (
              /* Success confirmation view */
              <div className="modal-body">
                <div className="modal-success-box">
                  <div className="success-circle-icon">
                    <CheckCircle2 size={32} />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-1">✓ Leave Request Submitted</h3>
                  <div className="font-mono text-indigo font-bold text-sm mb-3">
                    Request #LR-{submissionResult.id}
                  </div>
                  <p className="text-sm text-muted text-center max-w-sm mb-4">
                    Your leave request for <strong>{submissionResult.days} day(s)</strong> has been submitted to{' '}
                    <strong className="text-white">{submissionResult.managerName}</strong> for approval.
                  </p>
                  <div className="status-pill pending mb-4">
                    <Clock size={12} />
                    <span>Status: Pending Manager Approval</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="btn btn-outline"
                      onClick={() => {
                        setShowApplyModal(false)
                        setSubmissionResult(null)
                      }}
                    >
                      Close
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() => {
                        const item = submissionResult
                        setShowApplyModal(false)
                        setSubmissionResult(null)
                        handleViewDetails(item)
                      }}
                    >
                      <Eye size={14} />
                      <span>View Request</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Application Form */
              <form onSubmit={handleSubmitLeave}>
                <div className="modal-header">
                  <div className="flex items-center gap-2">
                    <Calendar size={18} color="#818cf8" />
                    <span className="modal-title">Apply For Leave</span>
                  </div>
                  <button
                    type="button"
                    className="icon-btn-sm"
                    onClick={() => setShowApplyModal(false)}
                    disabled={isSubmitting}
                  >
                    <X size={16} />
                  </button>
                </div>

                <div className="modal-body">
                  {/* Leave Type */}
                  <div className="field-group mb-3">
                    <label className="field-label">Leave Type</label>
                    <select
                      className="select-input"
                      value={leaveTypeId}
                      onChange={(e) => setLeaveTypeId(Number(e.target.value))}
                      disabled={isSubmitting}
                      required
                    >
                      {leaveTypes.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Dates: Start & End */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="field-group">
                      <label className="field-label">Start Date</label>
                      <input
                        type="date"
                        className="text-input"
                        value={startDate}
                        onChange={(e) => {
                          setStartDate(e.target.value)
                          if (e.target.value > endDate) setEndDate(e.target.value)
                        }}
                        disabled={isSubmitting}
                        required
                      />
                    </div>
                    <div className="field-group">
                      <label className="field-label">End Date</label>
                      <input
                        type="date"
                        className="text-input"
                        value={endDate}
                        min={startDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        disabled={isSubmitting}
                        required
                      />
                    </div>
                  </div>

                  {/* Duration & Reporting Manager (Both Read-Only) */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="field-group">
                      <label className="field-label">Duration (Calculated)</label>
                      <div className="read-only-field">
                        <Clock size={14} />
                        <span>
                          {calculatedDays} Day{calculatedDays > 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>

                    <div className="field-group">
                      <label className="field-label">Reporting Manager</label>
                      <div className="read-only-field">
                        <User size={14} />
                        <span className="text-white font-semibold">
                          {reportingManager ? reportingManager.name : 'Bob Roberts (Default)'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Reason */}
                  <div className="field-group mb-2">
                    <label className="field-label">Reason / Notes</label>
                    <textarea
                      rows={3}
                      className="textarea-input"
                      placeholder="Please provide a brief reason for your leave request..."
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      disabled={isSubmitting}
                      required
                    />
                  </div>
                </div>

                <div className="modal-footer flex justify-end gap-2">
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => setShowApplyModal(false)}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isSubmitting}
                  >
                    <Send size={14} />
                    <span>{isSubmitting ? 'Submitting...' : 'Submit Leave Request'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* 6. REQUEST DETAILS MODAL */}
      {selectedRequest && (
        <div className="modal-overlay" onClick={() => setSelectedRequest(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '580px' }}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <FileText size={18} color="#818cf8" />
                <span className="modal-title font-mono">
                  Leave Request #LR-{selectedRequest.id}
                </span>
              </div>
              <button
                type="button"
                className="icon-btn-sm"
                onClick={() => setSelectedRequest(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              {/* Top Status */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-muted uppercase font-bold">Current Status:</span>
                <div>{getStatusBadge(selectedRequest.status)}</div>
              </div>

              {/* Meta Grid */}
              <div className="detail-meta-grid">
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Employee</span>
                  <span className="detail-meta-value flex items-center gap-1">
                    <User size={14} color="#818cf8" />
                    {selectedRequest.employeeName || selectedRequest.userName}
                  </span>
                </div>

                <div className="detail-meta-item">
                  <span className="detail-meta-label">Leave Type</span>
                  <span className="detail-meta-value">{selectedRequest.leaveType}</span>
                </div>

                <div className="detail-meta-item">
                  <span className="detail-meta-label">Dates</span>
                  <span className="detail-meta-value">
                    {selectedRequest.startDate}{' '}
                    {selectedRequest.endDate && selectedRequest.endDate !== selectedRequest.startDate
                      ? `→ ${selectedRequest.endDate}`
                      : ''}
                  </span>
                </div>

                <div className="detail-meta-item">
                  <span className="detail-meta-label">Duration</span>
                  <span className="detail-meta-value">
                    {selectedRequest.days} Day{selectedRequest.days > 1 ? 's' : ''}
                  </span>
                </div>

                <div className="detail-meta-item">
                  <span className="detail-meta-label">Reporting Manager</span>
                  <span className="detail-meta-value">
                    {selectedRequest.managerName || 'Assigned Manager'}
                  </span>
                </div>

                <div className="detail-meta-item">
                  <span className="detail-meta-label">Submitted</span>
                  <span className="detail-meta-value text-xs">
                    {selectedRequest.submittedAt || selectedRequest.createdOn}
                  </span>
                </div>
              </div>

              {/* Reason */}
              {selectedRequest.reason && (
                <div className="mb-3">
                  <label className="field-label mb-1">Reason</label>
                  <div className="read-only-field" style={{ color: '#e2e8f0' }}>
                    {selectedRequest.reason}
                  </div>
                </div>
              )}

              {/* Action Details (Approved/Rejected) */}
              {selectedRequest.status === 'APPROVED' && selectedRequest.actionedBy && (
                <div className="status-banner success mb-3 text-xs">
                  <div>
                    <strong>Approved By:</strong> {selectedRequest.actionedBy}
                    {selectedRequest.actionedAt && ` on ${selectedRequest.actionedAt}`}
                    {selectedRequest.approvalComment && (
                      <div className="mt-1">
                        <em>"{selectedRequest.approvalComment}"</em>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedRequest.status === 'REJECTED' && selectedRequest.actionedBy && (
                <div className="status-banner error mb-3 text-xs">
                  <div>
                    <strong>Rejected By:</strong> {selectedRequest.actionedBy}
                    {selectedRequest.actionedAt && ` on ${selectedRequest.actionedAt}`}
                    {selectedRequest.rejectionReason && (
                      <div className="mt-1 font-semibold">
                        Rejection Reason: <em>"{selectedRequest.rejectionReason}"</em>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Approval History Timeline */}
              {Array.isArray(selectedRequest.history) && selectedRequest.history.length > 0 && (
                <div className="timeline-section">
                  <div className="timeline-title">Approval History</div>
                  <div className="timeline-list">
                    {selectedRequest.history.map((h, idx) => (
                      <div key={idx} className="timeline-item">
                        <div className={`timeline-dot ${(h.type || '').toLowerCase()}`} />
                        <div className="timeline-item-header">
                          <span>{h.title || h.type}</span>
                          <span className="text-muted font-normal">&bull;</span>
                          <span className="text-slate-300 font-normal">{h.actor}</span>
                        </div>
                        <div className="timeline-item-meta">{h.timestamp}</div>
                        {h.note && <div className="timeline-item-note">{h.note}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="modal-footer flex justify-between items-center">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setSelectedRequest(null)}
              >
                Close
              </button>

              {/* Manager Actions (Only visible if current user is manager of this request and request is PENDING) */}
              {canApprove &&
                String(selectedRequest.managerId) === String(currentUser.id) &&
                (selectedRequest.status === 'PENDING' || selectedRequest.status === 'PENDING_MANAGER') && (
                  <div className="flex items-center gap-2">
                    <button
                      className="btn btn-danger-outline"
                      onClick={() => handleOpenRejectModal(selectedRequest)}
                    >
                      <XCircle size={14} />
                      <span>Reject</span>
                    </button>
                    <button
                      className="btn btn-success"
                      onClick={() => handleOpenApproveModal(selectedRequest)}
                    >
                      <Check size={14} />
                      <span>Approve</span>
                    </button>
                  </div>
                )}
            </div>
          </div>
        </div>
      )}

      {/* 7. APPROVE CONFIRMATION MODAL */}
      {approveConfirmItem && (
        <div className="modal-overlay" onClick={() => !actionLoadingId && setApproveConfirmItem(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={18} color="#34d399" />
                <span className="modal-title">Approve Leave Request?</span>
              </div>
              <button
                type="button"
                className="icon-btn-sm"
                onClick={() => setApproveConfirmItem(null)}
                disabled={Boolean(actionLoadingId)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div className="detail-meta-grid mb-3">
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Employee</span>
                  <span className="detail-meta-value">{approveConfirmItem.employeeName}</span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Leave Type</span>
                  <span className="detail-meta-value">{approveConfirmItem.leaveType}</span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Dates</span>
                  <span className="detail-meta-value">
                    {approveConfirmItem.startDate}{' '}
                    {approveConfirmItem.endDate && approveConfirmItem.endDate !== approveConfirmItem.startDate
                      ? `→ ${approveConfirmItem.endDate}`
                      : ''}
                  </span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Duration</span>
                  <span className="detail-meta-value">
                    {approveConfirmItem.days} Day{approveConfirmItem.days > 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              <div className="field-group mb-2">
                <label className="field-label">Approval Comment (Optional)</label>
                <textarea
                  rows={2}
                  className="textarea-input"
                  placeholder="Add an optional comment for the employee..."
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  disabled={Boolean(actionLoadingId)}
                />
              </div>
            </div>

            <div className="modal-footer flex justify-end gap-2">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setApproveConfirmItem(null)}
                disabled={Boolean(actionLoadingId)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-success"
                onClick={handleConfirmApprove}
                disabled={Boolean(actionLoadingId)}
              >
                <Check size={14} />
                <span>{actionLoadingId ? 'Approving...' : 'Confirm Approval'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. REJECT CONFIRMATION MODAL */}
      {rejectConfirmItem && (
        <div className="modal-overlay" onClick={() => !actionLoadingId && setRejectConfirmItem(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <XCircle size={18} color="#f87171" />
                <span className="modal-title">Reject Leave Request?</span>
              </div>
              <button
                type="button"
                className="icon-btn-sm"
                onClick={() => setRejectConfirmItem(null)}
                disabled={Boolean(actionLoadingId)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div className="detail-meta-grid mb-3">
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Employee</span>
                  <span className="detail-meta-value">{rejectConfirmItem.employeeName}</span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Leave Type</span>
                  <span className="detail-meta-value">{rejectConfirmItem.leaveType}</span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Dates</span>
                  <span className="detail-meta-value">
                    {rejectConfirmItem.startDate}{' '}
                    {rejectConfirmItem.endDate && rejectConfirmItem.endDate !== rejectConfirmItem.startDate
                      ? `→ ${rejectConfirmItem.endDate}`
                      : ''}
                  </span>
                </div>
                <div className="detail-meta-item">
                  <span className="detail-meta-label">Duration</span>
                  <span className="detail-meta-value">
                    {rejectConfirmItem.days} Day{rejectConfirmItem.days > 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              <div className="field-group mb-2">
                <label className="field-label">Rejection Reason *</label>
                <textarea
                  rows={3}
                  className="textarea-input"
                  placeholder="Please state why this request cannot be approved..."
                  value={rejectionReason}
                  onChange={(e) => {
                    setRejectionReason(e.target.value)
                    if (e.target.value.trim()) setRejectionError('')
                  }}
                  disabled={Boolean(actionLoadingId)}
                  required
                />
                {rejectionError && (
                  <span className="text-xs text-danger font-semibold mt-1 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {rejectionError}
                  </span>
                )}
              </div>
            </div>

            <div className="modal-footer flex justify-end gap-2">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setRejectConfirmItem(null)}
                disabled={Boolean(actionLoadingId)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleConfirmReject}
                disabled={Boolean(actionLoadingId)}
              >
                <XCircle size={14} />
                <span>{actionLoadingId ? 'Rejecting...' : 'Reject Request'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
