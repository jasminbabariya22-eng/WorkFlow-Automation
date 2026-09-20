import React, { useState, useEffect } from 'react'
import {
  Server,
  Mail,
  Plus,
  Check,
  X,
  Lock,
  Eye,
  EyeOff,
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldCheck,
  ArrowRight
} from 'lucide-react'

export default function SenderEmailModal({
  isOpen,
  onClose,
  connectionId,
  selectedEmail,
  selectedServerId,
  onSelectSender
}) {
  const [activeTab, setActiveTab] = useState('existing') // 'existing' | 'new'
  const [servers, setServers] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [fetchError, setFetchError] = useState(null)

  // New Server Form state
  const [formData, setFormData] = useState({
    outgoing_email_user: '',
    outgoing_email_password: '',
    outgoing_server_ip: 'smtp.gmail.com',
    outgoing_email_port: 587,
    outgoing_email_encryption: 1, // 1=STARTTLS, 2=SSL, 0=None
    server_name: 'SMTP Server'
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState(null) // { success: bool, message: str }
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Load existing servers
  const loadServers = async () => {
    setIsLoading(true)
    setFetchError(null)
    try {
      const url = connectionId
        ? `/workflow-studio/connections/${connectionId}/email-servers`
        : `/workflow-studio/connections/email-servers`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setServers(Array.isArray(data) ? data : [])
      } else {
        setFetchError('Failed to load email servers from client database.')
      }
    } catch (err) {
      setFetchError(err.message || 'Error connecting to database.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadServers()
      setTestResult(null)
      setSaveError(null)
    }
  }, [isOpen, connectionId])

  if (!isOpen) return null

  const handleTestConnection = async () => {
    if (!formData.outgoing_email_user || !formData.outgoing_email_password || !formData.outgoing_server_ip) {
      setTestResult({ success: false, message: 'Please provide Email, Password, and SMTP Host before testing.' })
      return
    }

    setIsTesting(true)
    setTestResult(null)
    try {
      const url = connectionId
        ? `/workflow-studio/connections/${connectionId}/email-servers/test`
        : `/workflow-studio/connections/email-servers/test`

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setTestResult({ success: true, message: data.message || 'SMTP Authentication Successful!' })
      } else {
        setTestResult({ success: false, message: data.message || 'SMTP Authentication Failed. Check credentials.' })
      }
    } catch (err) {
      setTestResult({ success: false, message: `Connection error: ${err.message}` })
    } finally {
      setIsTesting(false)
    }
  }

  const handleSaveAndSelect = async (e) => {
    e.preventDefault()
    if (!formData.outgoing_email_user || !formData.outgoing_email_password || !formData.outgoing_server_ip) {
      setSaveError('Please fill in all required fields.')
      return
    }

    setIsSaving(true)
    setSaveError(null)
    try {
      const url = connectionId
        ? `/workflow-studio/connections/${connectionId}/email-servers`
        : `/workflow-studio/connections/email-servers`

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (!res.ok) {
        const errJson = await res.json()
        throw new Error(errJson.detail || 'Failed to authenticate and save email server.')
      }

      const created = await res.json()
      // Refresh list
      await loadServers()
      // Select newly created server and close
      onSelectSender({
        email: created.from_email || created.outgoing_email_user,
        email_server_id: created.email_server_id,
        server_name: created.server_name
      })
      onClose()
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          background: '#ffffff',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(226, 232, 240, 0.8)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh'
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#fafafa'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 2px 4px rgba(99, 102, 241, 0.25)'
              }}
            >
              <Server size={16} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>
                Sender Email Configuration
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
                Manage Client Database <code>email_server</code> credentials & sender accounts
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#94a3b8',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', background: '#f8fafc', padding: '0 16px' }}>
          <button
            type="button"
            onClick={() => setActiveTab('existing')}
            style={{
              padding: '12px 16px',
              fontSize: '13px',
              fontWeight: 600,
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: activeTab === 'existing' ? '#4f46e5' : '#64748b',
              borderBottom: activeTab === 'existing' ? '2px solid #4f46e5' : '2px solid transparent',
              marginBottom: '-1px'
            }}
          >
            <Mail size={14} />
            <span>Select Existing Sender ({servers.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('new')}
            style={{
              padding: '12px 16px',
              fontSize: '13px',
              fontWeight: 600,
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: activeTab === 'new' ? '#4f46e5' : '#64748b',
              borderBottom: activeTab === 'new' ? '2px solid #4f46e5' : '2px solid transparent',
              marginBottom: '-1px'
            }}
          >
            <Plus size={14} />
            <span>+ Authenticate New Sender</span>
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'existing' ? (
            <div>
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '36px 0', color: '#64748b' }}>
                  <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px auto', color: '#6366f1' }} />
                  <p style={{ margin: 0, fontSize: '13px' }}>Loading authenticated email servers from Client DB...</p>
                </div>
              ) : fetchError ? (
                <div style={{ padding: '14px', background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: '8px', color: '#be123c', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={16} />
                  <span>{fetchError}</span>
                </div>
              ) : servers.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px 16px', background: '#f8fafc', borderRadius: '10px', border: '1px dashed #cbd5e1' }}>
                  <Mail size={32} style={{ color: '#94a3b8', margin: '0 auto 10px auto' }} />
                  <h4 style={{ margin: '0 0 4px 0', color: '#1e293b', fontSize: '14px' }}>No Email Servers Found</h4>
                  <p style={{ margin: '0 0 16px 0', color: '#64748b', fontSize: '12px' }}>
                    No authenticated email servers exist in this Client Database yet.
                  </p>
                  <button
                    type="button"
                    onClick={() => setActiveTab('new')}
                    style={{
                      padding: '8px 16px',
                      background: '#4f46e5',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Plus size={14} />
                    <span>Authenticate New Sender Now</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: '#64748b' }}>
                      Choose which email address to send notifications from:
                    </span>
                    <span style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
                      🔒 Fernet Encrypted
                    </span>
                  </div>

                  {servers.map((s) => {
                    const isSelected =
                      String(s.email_server_id) === String(selectedServerId) ||
                      (s.from_email && s.from_email.toLowerCase() === (selectedEmail || '').toLowerCase())

                    return (
                      <div
                        key={`srv-card-${s.connection_id || 'def'}-${s.email_server_id}`}
                        onClick={() => {
                          onSelectSender({
                            email: s.from_email || s.outgoing_email_user,
                            email_server_id: s.email_server_id,
                            server_name: s.server_name,
                            connection_id: s.connection_id
                          })
                          onClose()
                        }}
                        style={{
                          padding: '14px 16px',
                          borderRadius: '10px',
                          border: isSelected ? '2px solid #4f46e5' : '1px solid #e2e8f0',
                          background: isSelected ? '#f5f3ff' : '#ffffff',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          transition: 'all 0.15s ease',
                          boxShadow: isSelected ? '0 4px 6px -1px rgba(79, 70, 229, 0.1)' : 'none'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div
                            style={{
                              width: '36px',
                              height: '36px',
                              borderRadius: '8px',
                              background: isSelected ? '#4f46e5' : '#f1f5f9',
                              color: isSelected ? '#ffffff' : '#64748b',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                          >
                            <Mail size={18} />
                          </div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>
                                {s.from_email || s.outgoing_email_user}
                              </span>
                              <span
                                style={{
                                  fontSize: '10.5px',
                                  padding: '2px 7px',
                                  borderRadius: '12px',
                                  background: '#e0e7ff',
                                  color: '#4338ca',
                                  fontWeight: 600
                                }}
                              >
                                {s.server_name || 'SMTP'} (#{s.email_server_id})
                              </span>
                              {s.connection_name && (
                                <span
                                  style={{
                                    fontSize: '10.5px',
                                    padding: '2px 7px',
                                    borderRadius: '12px',
                                    background: '#f1f5f9',
                                    color: '#475569',
                                    fontWeight: 500
                                  }}
                                >
                                  DB: {s.connection_name}
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '2px' }}>
                              Host: <code>{s.outgoing_server_ip}:{s.outgoing_email_port}</code> &bull; Encryption: {s.outgoing_email_encryption === 2 ? 'SSL' : s.outgoing_email_encryption === 1 ? 'STARTTLS' : 'Plain'}
                            </div>
                          </div>
                        </div>

                        <div>
                          {isSelected ? (
                            <div
                              style={{
                                width: '24px',
                                height: '24px',
                                borderRadius: '50%',
                                background: '#4f46e5',
                                color: '#ffffff',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}
                            >
                              <Check size={14} />
                            </div>
                          ) : (
                            <button
                              type="button"
                              style={{
                                padding: '6px 12px',
                                fontSize: '12px',
                                fontWeight: 500,
                                background: '#f8fafc',
                                border: '1px solid #cbd5e1',
                                borderRadius: '6px',
                                color: '#334155',
                                cursor: 'pointer'
                              }}
                            >
                              Use
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Tab 2: Authenticate New Sender */
            <form onSubmit={handleSaveAndSelect}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ padding: '10px 14px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <ShieldCheck size={18} style={{ color: '#16a34a', flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ fontSize: '12px', color: '#166534', lineHeight: 1.5 }}>
                    <strong>Fernet Encrypted Storage:</strong> This sender will be saved into your Client DB <code>email_server</code> table with 256-bit encryption.
                  </div>
                </div>

                {saveError && (
                  <div style={{ padding: '10px 14px', background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: '8px', color: '#be123c', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertCircle size={15} />
                    <span>{saveError}</span>
                  </div>
                )}

                {/* Email User / From Address */}
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Sender Email Address (Username) <span style={{ color: '#f43f5e' }}>*</span>
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. notifications@company.com or yourname@gmail.com"
                    value={formData.outgoing_email_user}
                    onChange={(e) => setFormData({ ...formData, outgoing_email_user: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      fontSize: '13px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '6px',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                {/* Password / App Password */}
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Email Password / App Password <span style={{ color: '#f43f5e' }}>*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="Enter password or 16-character Google App Password"
                      value={formData.outgoing_email_password}
                      onChange={(e) => setFormData({ ...formData, outgoing_email_password: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '8px 36px 8px 12px',
                        fontSize: '13px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        boxSizing: 'border-box'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: 'absolute',
                        right: '8px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#94a3b8'
                      }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  <span style={{ fontSize: '11px', color: '#64748b', display: 'block', marginTop: '3px' }}>
                    For Gmail, use a 16-character <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: '#4f46e5' }}>Google App Password</a>.
                  </span>
                </div>

                {/* Server Name & Host Row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Server Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Gmail SMTP"
                      value={formData.server_name}
                      onChange={(e) => setFormData({ ...formData, server_name: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        fontSize: '13px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      SMTP Host / Server IP <span style={{ color: '#f43f5e' }}>*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="smtp.gmail.com"
                      value={formData.outgoing_server_ip}
                      onChange={(e) => setFormData({ ...formData, outgoing_server_ip: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        fontSize: '13px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>
                </div>

                {/* Port & Encryption Row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Port
                    </label>
                    <select
                      value={formData.outgoing_email_port}
                      onChange={(e) => {
                        const port = Number(e.target.value)
                        setFormData({
                          ...formData,
                          outgoing_email_port: port,
                          outgoing_email_encryption: port === 465 ? 2 : 1
                        })
                      }}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        fontSize: '13px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        boxSizing: 'border-box',
                        background: '#ffffff'
                      }}
                    >
                      <option value={587}>587 (STARTTLS - Recommended)</option>
                      <option value={465}>465 (SSL/TLS)</option>
                      <option value={25}>25 (Plain / Unencrypted)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Encryption Protocol
                    </label>
                    <select
                      value={formData.outgoing_email_encryption}
                      onChange={(e) => setFormData({ ...formData, outgoing_email_encryption: Number(e.target.value) })}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        fontSize: '13px',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        boxSizing: 'border-box',
                        background: '#ffffff'
                      }}
                    >
                      <option value={1}>STARTTLS</option>
                      <option value={2}>SSL / TLS</option>
                      <option value={0}>None</option>
                    </select>
                  </div>
                </div>

                {/* Test Connection Banner */}
                {testResult && (
                  <div
                    style={{
                      padding: '10px 14px',
                      borderRadius: '8px',
                      fontSize: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      background: testResult.success ? '#f0fdf4' : '#fff1f2',
                      border: testResult.success ? '1px solid #bbf7d0' : '1px solid #fecdd3',
                      color: testResult.success ? '#166534' : '#be123c'
                    }}
                  >
                    {testResult.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                    <span>{testResult.message}</span>
                  </div>
                )}

                {/* Action Buttons */}
                <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={isTesting}
                    style={{
                      flex: 1,
                      padding: '10px 16px',
                      background: '#f8fafc',
                      border: '1px solid #cbd5e1',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: '#334155',
                      cursor: isTesting ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    {isTesting ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} style={{ color: '#eab308' }} />}
                    <span>{isTesting ? 'Testing...' : 'Test SMTP'}</span>
                  </button>

                  <button
                    type="submit"
                    disabled={isSaving}
                    style={{
                      flex: 2,
                      padding: '10px 16px',
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: '#ffffff',
                      cursor: isSaving ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      boxShadow: '0 2px 4px rgba(79, 70, 229, 0.25)'
                    }}
                  >
                    {isSaving ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
                    <span>{isSaving ? 'Encrypting & Saving...' : 'Save & Select Sender'}</span>
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid #f1f5f9',
            background: '#fafafa',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            Connected DB ID: <strong>#{connectionId || 'Default'}</strong>
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 500,
              background: 'transparent',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              color: '#475569',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
