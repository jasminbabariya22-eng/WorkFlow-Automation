import React, { useState } from 'react'
import { ShieldCheck, Plus, Send, CheckCircle2, Clock, XCircle } from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { workflowClient } from '../services/workflowClient'

export default function KycModule({ currentUser, onDataChanged }) {
  const [cases, setCases] = useState(clientDb.getKycCases())
  const [showModal, setShowModal] = useState(false)
  const [customerName, setCustomerName] = useState('')
  const [documentType, setDocumentType] = useState('Certificate of Incorporation')
  const [riskScore, setRiskScore] = useState(15)
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const reloadData = () => {
    setCases(clientDb.getKycCases())
    if (onDataChanged) onDataChanged()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setFeedback(null)

    const record = clientDb.createKycCase({
      customerName,
      documentType,
      riskScore: Number(riskScore),
      workflowId: 6 // Bound to Workflow #6 (Customer KYC & Anti-Money Laundering Flow)
    })

    try {
      const res = await workflowClient.startWorkflow(6, {
        entityType: 'CustomerKyc',
        entityId: record.id,
        userId: currentUser.id,
        variables: { customerName, riskScore: Number(riskScore) }
      })
      setFeedback({ success: true, message: `Workflow #6 initiated for ${customerName}! (${res.instance_id || 'Active'})` })
    } catch (err) {
      setFeedback({ success: false, message: `KYC Case saved in ClientDB. Server error: ${err.message}` })
    }

    reloadData()
    setLoading(false)
    setShowModal(false)
    setCustomerName('')
  }

  return (
    <div className="module-container">
      <div className="module-header-row">
        <div>
          <h2 className="module-title">👤 Customer KYC & Compliance Verification</h2>
          <p className="module-subtitle">
            Customer onboarding and AML risk rating delegate verification to <strong>Workflow #6</strong>
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          <span>New Customer KYC</span>
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
              <th>Case #</th>
              <th>Customer / Entity Name</th>
              <th>Documentation</th>
              <th>Risk Score</th>
              <th>Status in clientDB</th>
              <th>Workflow Binding</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td className="font-mono text-muted">#{c.id}</td>
                <td>
                  <span className="font-semibold">{c.customerName}</span>
                </td>
                <td>{c.documentType}</td>
                <td>
                  <span className={`badge ${c.riskScore > 50 ? 'badge-highvalue' : 'badge-neutral'}`}>
                    Risk: {c.riskScore}/100
                  </span>
                </td>
                <td>
                  <span className={`status-pill ${
                    c.status === 'APPROVED' ? 'approved' :
                    c.status.includes('PENDING') ? 'pending' : 'rejected'
                  }`}>
                    {c.status === 'APPROVED' && <CheckCircle2 size={11} />}
                    {c.status.includes('PENDING') && <Clock size={11} />}
                    {c.status === 'REJECTED' && <XCircle size={11} />}
                    <span>{c.status}</span>
                  </span>
                </td>
                <td>
                  <span className="badge badge-workflow">
                    Workflow #6 &bull; Compliance Flow
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
                  <ShieldCheck size={18} color="#818cf8" />
                  <span className="modal-title">New KYC Onboarding Case</span>
                </div>
              </div>

              <div className="modal-body">
                <div className="field-group mb-3">
                  <label className="field-label">Customer Legal Name</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Apex Global Logistics LLC"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="field-group">
                    <label className="field-label">Primary Document</label>
                    <select
                      className="select-input"
                      value={documentType}
                      onChange={(e) => setDocumentType(e.target.value)}
                    >
                      <option value="Certificate of Incorporation">Certificate of Incorporation</option>
                      <option value="Audited Financial Statements">Audited Financial Statements</option>
                      <option value="Director Passport / ID Proof">Director Passport / ID Proof</option>
                    </select>
                  </div>

                  <div className="field-group">
                    <label className="field-label">Automated Risk Score (0-100)</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      className="text-input font-mono"
                      value={riskScore}
                      onChange={(e) => setRiskScore(e.target.value)}
                      required
                    />
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
                  <span>{loading ? 'Submitting...' : 'Submit to Compliance Flow'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
