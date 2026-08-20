import React, { useState, useEffect } from 'react'
import { 
  LayoutDashboard, 
  GitBranch, 
  Activity, 
  User, 
  CheckCircle2, 
  AlertTriangle,
  X 
} from 'lucide-react'
import Dashboard from './components/Dashboard'
import Designer from './components/Designer'
import Monitoring from './components/Monitoring'

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
  }


  // Ensure valid state on mount and sync
  useEffect(() => {
    if (currentView === 'designer' && !selectedWorkflowId) {
      const list = JSON.parse(localStorage.getItem('workflow_studio_definitions') || '[]')
      const defaultId = list[0]?.id || 1
      setSelectedWorkflowId(defaultId)
      localStorage.setItem('studio_active_wf_id', defaultId)
      window.history.replaceState({}, '', `?view=designer&id=${defaultId}`)
    }
  }, [currentView, selectedWorkflowId])

  if (currentView === 'designer') {
    const activeWfId = selectedWorkflowId || 1
    return (
      <div className="app-container-fullscreen">
        <ErrorBoundary>
          <Designer 
            workflowId={activeWfId} 
            onClose={() => navigateTo('dashboard', null)} 
            showToast={showToast}
          />
        </ErrorBoundary>
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
          <div className="brand-section">
            <div className="brand-logo">
              <GitBranch size={20} color="#fff" />
            </div>
            <span className="brand-name">Studio</span>
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
                if (selectedWorkflowId) {
                  navigateTo('designer', selectedWorkflowId)
                } else {
                  showToast('Select a workflow from the Dashboard first', 'info')
                }
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

        <div className="user-tag">
          <User size={14} color="#8b949e" />
          <span>Administrator</span>
        </div>
      </div>

      {/* Main Workspace Pane */}
      <div className="main-content">
        <div className="top-bar">
          <span className="view-title">
            {currentView === 'dashboard' && 'Workflow Specifications'}
            {currentView === 'monitoring' && 'Workflow Monitoring & Traces'}
          </span>
          <div className="user-tag" style={{ border: 'none', background: 'rgba(0,229,255,0.06)', color: 'var(--color-accent-secondary)' }}>
            <span>Engine Version: SpiffWorkflow 3.x</span>
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
