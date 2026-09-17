import React, { Component } from 'react';
import { frontendLogger } from '../../services/frontendLogger';

export class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    frontendLogger.error(
      `React Component Crash: ${error?.message || 'Unknown Error'}`,
      error,
      {
        component: this.props.componentName || 'GlobalErrorBoundary',
        componentStack: errorInfo?.componentStack,
      }
    );
  }

  handleReload = () => {
    window.location.reload();
  };

  handleCopyError = () => {
    const errorText = `${this.state.error?.toString()}\n\nStack:\n${this.state.error?.stack}\n\nComponent Stack:\n${this.state.errorInfo?.componentStack}`;
    navigator.clipboard.writeText(errorText).then(() => {
      alert('Error details copied to clipboard.');
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f172a',
          color: '#f8fafc',
          padding: '24px',
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
        }}>
          <div style={{
            maxWidth: '650px',
            width: '100%',
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '12px',
            padding: '32px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                fontWeight: 'bold'
              }}>!</div>
              <div>
                <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>Workflow Studio Error</h2>
                <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: '13px' }}>
                  An unexpected error occurred. The incident has been recorded in the daily audit logs.
                </p>
              </div>
            </div>

            <div style={{
              backgroundColor: '#090d16',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '12px',
              color: '#f87171',
              fontFamily: 'monospace',
              maxHeight: '160px',
              overflowY: 'auto',
              marginBottom: '20px',
              wordBreak: 'break-all'
            }}>
              {this.state.error?.toString()}
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={this.handleCopyError}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: '1px solid #475569',
                  backgroundColor: 'transparent',
                  color: '#e2e8f0',
                  fontSize: '13px',
                  cursor: 'pointer',
                  fontWeight: 500
                }}
              >
                Copy Error
              </button>
              <button
                onClick={this.handleReload}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: '#3b82f6',
                  color: '#ffffff',
                  fontSize: '13px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default GlobalErrorBoundary;
