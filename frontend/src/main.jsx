import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { frontendLogger } from './services/frontendLogger'
import GlobalErrorBoundary from './components/common/GlobalErrorBoundary'

// Initialize Global Frontend Logging & Exception Hooks
frontendLogger.init()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <GlobalErrorBoundary componentName="RootApplication">
      <App />
    </GlobalErrorBoundary>
  </StrictMode>,
)
