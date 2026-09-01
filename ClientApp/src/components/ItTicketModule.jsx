import React, { useState } from 'react'
import { Cpu, Plus, Send, CheckCircle2, Clock, XCircle } from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { workflowClient } from '../services/workflowClient'

export default function ItTicketModule({ currentUser, onDataChanged }) {
  const [tickets, setTickets] = useState(clientDb.getItRequests())
  const [showModal, setShowModal] = useState(false)
  const [assetType, setAssetType] = useState('Production VPN Access')
  const [priority, setPriority] = useState('HIGH')
  const [details, setDetails] = useState('')
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const reloadData = () => {
    setTickets(clientDb.getItRequests())
    if (onDataChanged) onDataChanged()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setFeedback(null)

    const record = clientDb.createItRequest({
      userId: currentUser.id,
      userName: currentUser.name,
      assetType,
      priority,
      details,
      workflowId: 5 // Bound to Workflow #5 (IT Asset & Access Provisioning)
    })

    try {
      const res = await workflowClient.startWorkflow(5, {
        entityType: 'ItRequest',
        entityId: record.id,
        userId: currentUser.id,
        variables: { assetType, priority, department: currentUser.department }
      })
      setFeedback({ success: true, message: `Workflow #5 initiated for IT Ticket #${record.id}! (${res.instance_id || 'Active'})` })
    } catch (err) {
      setFeedback({ success: false, message: `Ticket saved in ClientDB. Server error: ${err.message}` })
    }

    reloadData()
    setLoading(false)
    setShowModal(false)
    setDetails('')
  }

  return (
    <div className="module-container">
      <div className="module-header-row">
        <div>
          <h2 className="module-title">💻 IT Asset & Access Provisioning</h2>
          <p className="module-subtitle">
            Hardware, VPN, and credential requests delegate security provisioning to <strong>Workflow #5</strong>
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          <span>New IT Request</span>
        </button>
      </div>

      {feedback && (
        <div className={`status-banner ${feedback.success ? 'success' : 'warning'} mb-4`}>
          <span className="text-xs">{feedback.message}</span>
        </div>
      )}

      <div className="card-table-wrapper">
        <table className="enterprise-table">
          <thead>
            <tr>
              <th>Ticket #</th>
              <th>Asset / Service</th>
              <th>Requested For</th>
              <th>Priority</th>
              <th>Status in clientDB</th>
              <th>Workflow Binding</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id}>
                <td className="font-mono text-muted">#{t.id}</td>
                <td>
                  <span className="font-semibold">{t.assetType}</span>
                </td>
                <td>{t.userName}</td>
                <td>
                  <span className={`badge ${t.priority === 'HIGH' ? 'badge-highvalue' : 'badge-neutral'}`}>
                    {t.priority}
                  </span>
                </td>
                <td>
                  <span className={`status-pill ${
                    t.status === 'APPROVED' ? 'approved' :
                    t.status.includes('REVIEW') ? 'pending' : 'rejected'
                  }`}>
                    {t.status === 'APPROVED' && <CheckCircle2 size={11} />}
                    {t.status.includes('REVIEW') && <Clock size={11} />}
                    {t.status === 'REJECTED' && <XCircle size={11} />}
                    <span>{t.status}</span>
                  </span>
                </td>
                <td>
                  <span className="badge badge-workflow">
                    Workflow #5 &bull; IT Provisioning
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSubmit}>
              <div className="modal-header">
                <div className="flex items-center gap-2">
                  <Cpu size={18} color="#818cf8" />
                  <span className="modal-title">New IT Service Ticket</span>
                </div>
              </div>

              <div className="modal-body">
                <div className="field-group mb-3">
                  <label className="field-label">Asset / Permission Type</label>
                  <select
                    className="select-input"
                    value={assetType}
                    onChange={(e) => setAssetType(e.target.value)}
                  >
                    <option value="Production VPN Access">Production VPN Access</option>
                    <option value="AWS Staging Cloud Credentials">AWS Staging Cloud Credentials</option>
                    <option value="MacBook Pro M3 Max Developer Kit">MacBook Pro M3 Max Developer Kit</option>
                    <option value="Database Read-Only Access">Database Read-Only Access</option>
                  </select>
                </div>

                <div className="field-group mb-3">
                  <label className="field-label">Priority</label>
                  <select
                    className="select-input"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="LOW">LOW (Standard)</option>
                    <option value="MEDIUM">MEDIUM (Sprint Delivery)</option>
                    <option value="HIGH">HIGH (Urgent Blocker)</option>
                  </select>
                </div>

                <div className="field-group mb-2">
                  <label className="field-label">Business Justification</label>
                  <textarea
                    rows={2}
                    className="textarea-input"
                    placeholder="Why is this access required?..."
                    value={details}
                    onChange={(e) => setDetails(e.target.value)}
                  />
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
                  <span>{loading ? 'Submitting...' : 'Submit Request'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
