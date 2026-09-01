import React, { useState, useEffect } from 'react'
import {
  Calendar,
  CreditCard,
  Package,
  Cpu,
  ShieldCheck,
  Inbox,
  User,
  Server,
  Settings,
  ChevronDown
} from 'lucide-react'
import { workflowClient } from '../services/workflowClient'

export default function Navbar({
  activeTab,
  setActiveTab,
  currentUser,
  setCurrentUser,
  users,
  pendingCount,
  onOpenServerModal
}) {
  const [serverOnline, setServerOnline] = useState(false)
  const [checking, setChecking] = useState(false)

  const checkHealth = async () => {
    setChecking(true)
    const res = await workflowClient.testConnection()
    setServerOnline(res.success)
    setChecking(false)
  }

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="app-navbar">
      {/* Brand */}
      <div className="nav-brand-box">
        <div className="nav-logo">
          <div className="logo-icon-chip">EP</div>
        </div>
        <div>
          <div className="nav-app-name">Enterprise Portal</div>
          <div className="nav-subtag">Client Application &bull; clientDB</div>
        </div>
      </div>

      {/* Navigation Modules */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'leave' ? 'active' : ''}`}
          onClick={() => setActiveTab('leave')}
        >
          <Calendar size={15} />
          <span>Leave</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'expenses' ? 'active' : ''}`}
          onClick={() => setActiveTab('expenses')}
        >
          <CreditCard size={15} />
          <span>Expenses</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
          onClick={() => setActiveTab('orders')}
        >
          <Package size={15} />
          <span>Purchase Orders</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'it' ? 'active' : ''}`}
          onClick={() => setActiveTab('it')}
        >
          <Cpu size={15} />
          <span>IT Services</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'kyc' ? 'active' : ''}`}
          onClick={() => setActiveTab('kyc')}
        >
          <ShieldCheck size={15} />
          <span>Customer KYC</span>
        </button>

        <button
          className={`nav-tab-btn nav-tab-inbox ${activeTab === 'approvals' ? 'active' : ''}`}
          onClick={() => setActiveTab('approvals')}
        >
          <Inbox size={15} />
          <span>Approvals Inbox</span>
          {pendingCount > 0 && <span className="nav-counter-pill">{pendingCount}</span>}
        </button>
      </nav>

      {/* Right Tools: Server Status & Active User Switcher */}
      <div className="nav-right-actions">
        {/* Remote Server Indicator */}
        <button
          className={`server-status-pill ${serverOnline ? 'online' : 'offline'}`}
          onClick={onOpenServerModal}
          title="Click to configure Central Workflow Server"
        >
          <span className="pulse-dot" />
          <Server size={13} />
          <span className="server-label">
            {workflowClient.getServerUrl().replace('http://', '').replace('https://', '')}
          </span>
          <Settings size={12} className="opacity-60" />
        </button>

        {/* User Switcher Dropdown */}
        <div className="user-dropdown-wrapper">
          <div className="flex items-center gap-2">
            <div className="user-avatar-circle">
              {currentUser.name.charAt(0)}
            </div>
            <div className="user-info-text">
              <span className="user-display-name">{currentUser.name}</span>
              <span className="user-role-tag">{currentUser.role}</span>
            </div>
          </div>
          <select
            className="user-select-overlay"
            value={currentUser.id}
            onChange={(e) => {
              const selected = users.find(u => u.id === e.target.value)
              if (selected) setCurrentUser(selected)
            }}
            title="Switch current simulated user"
          >
            {users.map(u => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.role} - {u.department})
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  )
}
