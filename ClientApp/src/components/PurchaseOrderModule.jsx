import React, { useState } from 'react'
import { Package, Plus, Send, CheckCircle2, Clock, XCircle } from 'lucide-react'
import { clientDb } from '../services/clientDb'
import { workflowClient } from '../services/workflowClient'

export default function PurchaseOrderModule({ currentUser, onDataChanged }) {
  const [orders, setOrders] = useState(clientDb.getPurchaseOrders())
  const [showModal, setShowModal] = useState(false)
  const [vendor, setVendor] = useState('')
  const [totalCost, setTotalCost] = useState(2500)
  const [itemsCount, setItemsCount] = useState(3)
  const [department, setDepartment] = useState(currentUser.department)
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const reloadData = () => {
    setOrders(clientDb.getPurchaseOrders())
    if (onDataChanged) onDataChanged()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setFeedback(null)

    // 1. Save in clientDB
    const record = clientDb.createPurchaseOrder({
      userId: currentUser.id,
      userName: currentUser.name,
      vendor,
      department,
      totalCost: Number(totalCost),
      itemsCount: Number(itemsCount),
      workflowId: 4 // Bound to Workflow #4 (Purchase Order Signoff)
    })

    // 2. Trigger Workflow over network
    try {
      const res = await workflowClient.startWorkflow(4, {
        entityType: 'PurchaseOrder',
        entityId: record.id,
        userId: currentUser.id,
        variables: { vendor, department, totalCost: Number(totalCost) }
      })
      setFeedback({ success: true, message: `Workflow #4 initiated for PO #${record.id}! (${res.instance_id || 'Active'})` })
    } catch (err) {
      setFeedback({ success: false, message: `PO saved in ClientDB. Server error: ${err.message}` })
    }

    reloadData()
    setLoading(false)
    setShowModal(false)
    setVendor('')
  }

  return (
    <div className="module-container">
      <div className="module-header-row">
        <div>
          <h2 className="module-title">📦 Purchase Order Management</h2>
          <p className="module-subtitle">
            Procurement requests delegate signoff to <strong>Workflow #4 (Purchase Order Signoff Flow)</strong>
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          <span>New Purchase Order</span>
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
              <th>PO #</th>
              <th>Vendor Name</th>
              <th>Requested By</th>
              <th>Department</th>
              <th>Items</th>
              <th>Total Cost</th>
              <th>Status in clientDB</th>
              <th>Workflow Binding</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((po) => (
              <tr key={po.id}>
                <td className="font-mono text-muted">#{po.id}</td>
                <td>
                  <span className="font-semibold">{po.vendor}</span>
                </td>
                <td>{po.userName}</td>
                <td>{po.department}</td>
                <td>{po.itemsCount} Items</td>
                <td className="font-mono font-bold text-indigo">
                  ${po.totalCost.toLocaleString()}
                </td>
                <td>
                  <span className={`status-pill ${
                    po.status === 'APPROVED' ? 'approved' :
                    po.status.includes('PENDING') ? 'pending' : 'rejected'
                  }`}>
                    {po.status === 'APPROVED' && <CheckCircle2 size={11} />}
                    {po.status.includes('PENDING') && <Clock size={11} />}
                    {po.status === 'REJECTED' && <XCircle size={11} />}
                    <span>{po.status}</span>
                  </span>
                </td>
                <td>
                  <span className="badge badge-workflow">
                    Workflow #4 &bull; Procurement
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
                  <Package size={18} color="#818cf8" />
                  <span className="modal-title">Create Purchase Order</span>
                </div>
              </div>

              <div className="modal-body">
                <div className="field-group mb-3">
                  <label className="field-label">Vendor / Supplier Name</label>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="e.g. Cisco Systems, AWS Cloud Services"
                    value={vendor}
                    onChange={(e) => setVendor(e.target.value)}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="field-group">
                    <label className="field-label">Total Cost ($ USD)</label>
                    <input
                      type="number"
                      min={1}
                      className="text-input font-mono font-bold"
                      value={totalCost}
                      onChange={(e) => setTotalCost(e.target.value)}
                      required
                    />
                  </div>
                  <div className="field-group">
                    <label className="field-label">Items Count</label>
                    <input
                      type="number"
                      min={1}
                      className="text-input font-mono"
                      value={itemsCount}
                      onChange={(e) => setItemsCount(e.target.value)}
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
                  <span>{loading ? 'Submitting...' : 'Submit PO'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
