import React, { useState, useEffect, Suspense, lazy } from 'react'
import {
  LayoutDashboard,
  GitBranch,
  Activity,
  CheckCircle2,
  AlertTriangle,
  X,
  Loader
} from 'lucide-react'

import capperLogo from '../LOGO/capperlogo.png'
import massCapperLogo from '../LOGO/mass-capper.png'

import Dashboard from './components/Dashboard'
import Designer from './components/Designer'
import Monitoring from './components/Monitoring'

const ViewLoader = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: '#6366f1', gap: '8px' }}>
    <Loader size={20} className="wf-spin" />
    <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>Loading workspace...</span>
  </div>
)

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Studio Error Caught by Boundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', textAlign: 'center' }}>
          <AlertTriangle size={48} color="var(--color-error)" style={{ marginBottom: '16px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>Designer Encountered an Error</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', maxWidth: '500px', marginBottom: '20px' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred while inspecting the node.'}
          </p>
          <button
            className="btn btn-primary"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
          >
            Reload Designer Workspace
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  // Initialize view and workflowId from URL parameters or localStorage
  const getInitialState = () => {
    const params = new URLSearchParams(window.location.search)
    const viewParam = params.get('view')
    const idParam = params.get('id')

    const savedView = localStorage.getItem('studio_active_view') || 'dashboard'
    const savedId = localStorage.getItem('studio_active_wf_id')

    const view = viewParam || (savedId && savedView === 'designer' ? 'designer' : 'dashboard')
    const wfId = idParam ? Number(idParam) : (savedId ? Number(savedId) : null)

    return { view, wfId }
  }

  const initialState = getInitialState()
  const [currentView, setCurrentView] = useState(initialState.view)
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(initialState.wfId)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
  }

  // Synchronize state with URL and localStorage
  const navigateTo = (view, id = null) => {
    setCurrentView(view)
    setSelectedWorkflowId(id)
    localStorage.setItem('studio_active_view', view)
    if (id) {
      localStorage.setItem('studio_active_wf_id', id)
      window.history.replaceState({}, '', `?view=${view}&id=${id}`)
    } else {
      localStorage.removeItem('studio_active_wf_id')
      window.history.replaceState({}, '', `?view=${view}`)
    }
  }

  // Auto-hide toast messages
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null)
      }, 4000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  const renderActiveView = () => {
    return (
      <Suspense fallback={<ViewLoader />}>
        {(() => {
          switch (currentView) {
            case 'dashboard':
              return (
                <Dashboard
                  onOpenDesigner={(id) => {
                    navigateTo('designer', id)
                  }}
                  showToast={showToast}
                />
              )
            case 'designer':
              return (
                <ErrorBoundary>
                  <Designer
                    workflowId={selectedWorkflowId}
                    onClose={() => {
                      navigateTo('dashboard', null)
                    }}
                    showToast={showToast}
                  />
                </ErrorBoundary>
              )
            case 'monitoring':
              return <Monitoring showToast={showToast} />
            default:
              return (
                <Dashboard
                  onOpenDesigner={(id) => {
                    navigateTo('designer', id)
                  }}
                  showToast={showToast}
                />
              )
          }
        })()}
      </Suspense>
    )
  }


  if (currentView === 'designer') {
    return (
      <div className="app-container-fullscreen">
        <Suspense fallback={<ViewLoader />}>
          <ErrorBoundary>
            <Designer
              workflowId={selectedWorkflowId}
              onSelectWorkflow={(id) => navigateTo('designer', id)}
              onClose={() => navigateTo('dashboard', null)}
              showToast={showToast}
            />
          </ErrorBoundary>
        </Suspense>
        {toast && (
          <div className={`toast ${toast.type}`}>
            {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{toast.message}</span>
            <X size={14} style={{ cursor: 'pointer', marginLeft: '8px' }} onClick={() => setToast(null)} />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div>
          <div className="brand-section" style={{ display: 'flex', alignItems: 'center', marginBottom: '36px' }}>
            <img 
              src={capperLogo} 
              alt="Capper" 
              className="brand-logo-img"
              style={{
                height: '32px',
                width: 'auto',
                maxWidth: '150px',
                objectFit: 'contain',
                display: 'block'
              }}
            />
          </div>

          <ul className="nav-links">
            <li
              className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => navigateTo('dashboard', null)}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </li>
            <li
              className={`nav-item ${currentView === 'designer' ? 'active' : ''}`}
              onClick={() => {
                navigateTo('designer', selectedWorkflowId || null)
              }}
            >
              <GitBranch size={18} />
              <span>Designer</span>
            </li>
            <li
              className={`nav-item ${currentView === 'monitoring' ? 'active' : ''}`}
              onClick={() => navigateTo('monitoring', null)}
            >
              <Activity size={18} />
              <span>Monitoring</span>
            </li>

          </ul>
        </div>

        <div style={{
          fontSize: '11px',
          color: '#94a3b8',
          textAlign: 'center',
          lineHeight: '1.4',
          paddingTop: '16px',
          borderTop: '1px solid #f1f5f9',
          userSelect: 'none'
        }}>
          ©Copyright, Alethe Labs India Pvt Ltd
        </div>
      </div>

      {/* Main Workspace Pane */}
      <div className="main-content">
        <div className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src={massCapperLogo} 
              alt="MASSCapper" 
              style={{
                height: '32px',
                width: 'auto',
                objectFit: 'contain',
                display: 'block'
              }}
            />
            {currentView === 'monitoring' && (
              <>
                <div style={{ width: '1px', height: '20px', background: '#e2e8f0' }} />
                <span className="view-title" style={{ fontSize: '15px', fontWeight: '700', color: '#132B6E' }}>
                  Monitoring & Observability
                </span>
              </>
            )}
          </div>
        </div>

        {renderActiveView()}
      </div>

      {/* Global Notifications Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>{toast.message}</span>
          <X size={14} style={{ cursor: 'pointer', marginLeft: '8px' }} onClick={() => setToast(null)} />
        </div>
      )}
    </div>
  )
}

export default App
