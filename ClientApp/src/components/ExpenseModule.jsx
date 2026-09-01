import React, { useState } from 'react'
import { CreditCard, Plus, Send, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { workflowClient } from '../services/workflowClient'

export default function ExpenseModule({ currentUser, onDataChanged }) {
  const [expenses, setExpenses] = useState(clientDb.getExpenses())
  const [showModal, setShowModal] = useState(false)
  const [title, setTitle] = useState('')
  const [amount, setAmount] = useState(350)
  const [category, setCategory] = useState('Travel')
  const [loading, setLoading] = useState(false)
  const [workflowFeedback, setWorkflowFeedback] = useState(null)

  // Multi-Workflow Routing Rule:
  const targetWorkflowId = Number(amount) >= 5000 ? 3 : 2
  const targetWorkflowName = Number(amount) >= 5000 
    ? 'Workflow #3 (High-Value CapEx & VP Signoff)' 
    : 'Workflow #2 (Standard Expense 1-Tier Flow)'

  const reloadData = () => {
    setExpenses(clientDb.getExpenses())
    if (onDataChanged) onDataChanged()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setWorkflowFeedback(null)

    // 1. Insert record in local clientDB
    const record = clientDb.createExpense({
      userId: currentUser.id,
      userName: currentUser.name,
      title,
      amount: Number(amount),
      category,
      workflowId: targetWorkflowId
    })

    // 2. Trigger Centralized Workflow Engine over the network
    try {
      const wfResponse = await workflowClient.startWorkflow(targetWorkflowId, {
        entityType: 'ExpenseClaim',
        entityId: record.id,
        userId: currentUser.id,
        variables: {
          title,
          amount: Number(amount),
          category,
          department: currentUser.department
        }
      })

      setWorkflowFeedback({
        success: true,
        message: `Routed to ${targetWorkflowName}! Instance ID: ${wfResponse.instance_id || 'Active'}`
      })
    } catch (err) {
      setWorkflowFeedback({
        success: false,
        message: `Saved in ClientDB, but Workflow Server unreachable: ${err.message}`
      })
    }

    reloadData()
    setLoading(false)
    setShowModal(false)
    setTitle('')
  }

  return (
    <div className="module-container">
      {/* Module Header */}
      <div className="module-header-row">
        <div>
          <h2 className="module-title">💳 Expense Reimbursement Portal</h2>
          <p className="module-subtitle">
            Demonstrating <strong>Multi-Workflow Routing</strong>: Claims &lt; $5,000 trigger <strong>WF-2</strong>, while claims &ge; $5,000 trigger <strong>WF-3</strong>.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          <span>New Expense Claim</span>
        </button>
      </div>

      {workflowFeedback && (
        <div className={`status-banner ${workflowFeedback.success ? 'success' : 'warning'} mb-4`}>
          <span className="text-xs">{workflowFeedback.message}</span>
        </div>
      )}

      {/* Expense Records Table */}
      <div className="card-table-wrapper">
        <table className="enterprise-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Claim Title</th>
              <th>Claimant</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Status in clientDB</th>
              <th>Dynamic Workflow Routing</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((exp) => (
              <tr key={exp.id}>
                <td className="font-mono text-muted">#{exp.id}</td>
                <td>
                  <span className="font-semibold">{exp.title}</span>
                </td>
                <td>{exp.userName}</td>
                <td>
                  <span className="badge badge-neutral">{exp.category}</span>
                </td>
                <td className="font-mono font-bold text-indigo">
                  ${exp.amount.toLocaleString()}
                </td>
                <td>
                  <span className={`status-pill ${
                    exp.status === 'APPROVED' ? 'approved' :
                    exp.status.includes('PENDING') ? 'pending' : 'rejected'
                  }`}>
                    {exp.status === 'APPROVED' && <CheckCircle2 size={11} />}
                    {exp.status.includes('PENDING') && <Clock size={11} />}
                    {exp.status === 'REJECTED' && <XCircle size={11} />}
                    <span>{exp.status}</span>
                  </span>
                </td>
                <td>
                  <span className={`badge ${exp.workflowId === 3 ? 'badge-highvalue' : 'badge-workflow'}`}>
                    {exp.workflowId === 3 ? '⚡ WF #3 (High-Value VP)' : 'WF #2 (Standard Expense)'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal: New Expense Claim */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSubmit}>
              <div className="modal-header">
                <div className="flex items-center gap-2">
                  <CreditCard size={18} color="#818cf8" />
                  <span className="modal-title">New Expense Claim</span>
                </div>
              </div>

              <div className="modal-body">
                <div className="field-group mb-3">
                  <label className="field-label">Expense Description / Title</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Flight tickets to Tech Expo, Client Lunch"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="field-group">
                    <label className="field-label">Claim Amount ($ USD)</label>
                    <input
                      type="number"
                      min={1}
                      className="text-input font-mono font-bold"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      required
                    />
                  </div>
                  <div className="field-group">
                    <label className="field-label">Category</label>
                    <select
                      className="select-input"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                    >
                      <option value="Travel">Travel & Lodging</option>
                      <option value="Meals">Meals & Entertainment</option>
                      <option value="Software">Software & Subscriptions</option>
                      <option value="Hardware">Equipment & Office Supplies</option>
                    </select>
                  </div>
                </div>

                {/* Live Dynamic Workflow Routing Indicator */}
                <div className="routing-preview-box">
                  <div className="text-xs font-semibold text-muted mb-1">
                    TARGET WORKFLOW ROUTE:
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${targetWorkflowId === 3 ? 'badge-highvalue' : 'badge-workflow'}`}>
                      {targetWorkflowName}
                    </span>
                    <span className="text-xs text-muted">
                      {targetWorkflowId === 3 
                        ? 'Amount ≥ $5,000 automatically triggers VP 2-Tier workflow' 
                        : 'Amount < $5,000 triggers standard single manager approval'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-footer flex justify-end gap-2">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowModal(false)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  <Send size={14} />
                  <span>{loading ? 'Routing...' : 'Submit Claim'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
