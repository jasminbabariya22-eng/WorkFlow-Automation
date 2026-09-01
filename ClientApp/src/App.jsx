import React, { useState } from 'react'
import Navbar from './components/Navbar'
import LeaveModule from './components/LeaveModule'
import ExpenseModule from './components/ExpenseModule'
import PurchaseOrderModule from './components/PurchaseOrderModule'
import ItTicketModule from './components/ItTicketModule'
import KycModule from './components/KycModule'
import ApprovalsInbox from './components/ApprovalsInbox'
import ServerConfigModal from './components/ServerConfigModal'
import { clientDb } from './services/clientDb'
import { workflowClient } from './services/workflowClient'

export default function App() {
  const users = clientDb.getUsers()
  const [currentUser, setCurrentUser] = useState(users[0]) // Alice - Employee by default
  const [activeTab, setActiveTab] = useState('leave')
  const [isServerModalOpen, setIsServerModalOpen] = useState(false)
  const [, setTick] = useState(0)

  // Force re-render on database changes
  const triggerRefresh = () => setTick(t => t + 1)

  const pendingApprovals = clientDb.getPendingApprovalsForUser(currentUser)

  return (
    <div className="client-app-layout">
      {/* 1. TOP NAVBAR */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        setCurrentUser={setCurrentUser}
        users={users}
        pendingCount={pendingApprovals.length}
        onOpenServerModal={() => setIsServerModalOpen(true)}
      />

      {/* 2. MAIN CONTENT AREA */}
      <main className="client-app-main">
        {activeTab === 'leave' && (
          <LeaveModule currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
        {activeTab === 'expenses' && (
          <ExpenseModule currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
        {activeTab === 'orders' && (
          <PurchaseOrderModule currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
        {activeTab === 'it' && (
          <ItTicketModule currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
        {activeTab === 'kyc' && (
          <KycModule currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
        {activeTab === 'approvals' && (
          <ApprovalsInbox currentUser={currentUser} onDataChanged={triggerRefresh} />
        )}
      </main>

      {/* 3. FOOTER STATUS BAR */}
      <footer className="client-app-footer">
        <div className="flex items-center gap-4 text-xs text-muted">
          <span>
            🗄️ <strong>clientDB</strong>: Standalone Client Database
          </span>
          <span>&bull;</span>
          <span>
            🌐 <strong>Workflow Server</strong>: {workflowClient.getServerUrl()}
          </span>
          <span>&bull;</span>
          <span>
            👤 <strong>Active User</strong>: {currentUser.name} ({currentUser.role})
          </span>
        </div>
        <div className="text-xs text-muted">
          Multi-Workflow Orchestration Enabled &bull; Port 3000
        </div>
      </footer>

      {/* 4. SERVER CONFIG MODAL */}
      <ServerConfigModal
        isOpen={isServerModalOpen}
        onClose={() => setIsServerModalOpen(false)}
        onServerUpdated={() => triggerRefresh()}
      />
    </div>
  )
}
