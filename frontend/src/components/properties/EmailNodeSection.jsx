import React, { useState, useEffect } from 'react'
import { Mail, Edit3, Eye, X, Server, Send, Settings, ShieldCheck } from 'lucide-react'
import SenderEmailModal from './SenderEmailModal'

export default function EmailNodeSection({
  data = {},
  workflowConnectionId = null,
  backendRoles = [],
  backendUsers = [],
  backendReportsTo = [],
  availableFields = [],
  handleFieldChange,
  handleFieldsChange,
  onUpdate
}) {
  const [activeTab, setActiveTab] = useState('compose') // 'compose' | 'preview'
  const [showCc, setShowCc] = useState(Boolean(data.cc))
  const [showBcc, setShowBcc] = useState(Boolean(data.bcc))
  const [emailServers, setEmailServers] = useState([])
  const [isLoadingServers, setIsLoadingServers] = useState(false)
  const [isSenderModalOpen, setIsSenderModalOpen] = useState(false)

  const effectiveConnId = data.connection_id || workflowConnectionId || ''

  const onFieldChange = (field, value) => {
    if (typeof handleFieldChange === 'function') {
      handleFieldChange(field, value)
    } else if (typeof onUpdate === 'function') {
      onUpdate({ ...data, [field]: value })
    }
  }

  const onFieldsChange = (fieldsObj) => {
    if (typeof handleFieldsChange === 'function') {
      handleFieldsChange(fieldsObj)
    } else if (typeof onUpdate === 'function') {
      onUpdate({ ...data, ...fieldsObj })
    } else if (typeof handleFieldChange === 'function') {
      Object.entries(fieldsObj).forEach(([k, v]) => handleFieldChange(k, v))
    }
  }

  // Fetch available email servers from client database connection
  useEffect(() => {
    let isMounted = true
    const fetchServers = async () => {
      setIsLoadingServers(true)
      try {
        const url = effectiveConnId ? `/workflow-studio/connections/${effectiveConnId}/email-servers` : `/workflow-studio/connections/email-servers`
        const res = await fetch(url)
        if (res.ok) {
          const list = await res.json()
          if (isMounted && Array.isArray(list)) {
            setEmailServers(list)
            if (data.email_server_id) {
              const matched = list.find(s => String(s.email_server_id) === String(data.email_server_id))
              if (matched && (matched.from_email || matched.outgoing_email_user)) {
                const sFrom = matched.from_email || matched.outgoing_email_user
                if (!data.from || data.from !== sFrom) {
                  onFieldChange('from', sFrom)
                }
              }
            } else if (data.from && data.from !== 'j') {
              const matched = list.find(s => (s.from_email || s.outgoing_email_user) === data.from)
              if (matched && matched.email_server_id) {
                onFieldChange('email_server_id', matched.email_server_id)
              }
            } else if (!data.from && list.length > 0) {
              // Pre-select first available valid email only if unset
              const firstEmail = list[0].from_email || list[0].outgoing_email_user
              onFieldsChange({
                from: firstEmail,
                email_server_id: list[0].email_server_id
              })
            }
          }
        }
      } catch (err) {
        console.debug('Email server fetch notice:', err)
      } finally {
        if (isMounted) setIsLoadingServers(false)
      }
    }
    fetchServers()
    return () => { isMounted = false }
  }, [effectiveConnId])

  const dbRoles = Array.from(
    new Set(
      (backendRoles || []).map(r => {
        if (!r) return null
        if (typeof r === 'string') return r
        return r.name || r.role_name || String(r.id || '') || null
      }).filter(Boolean)
    )
  )

  const dbUsers = (backendUsers || []).filter(u => u && u.email && typeof u.email === 'string' && u.email.trim())

  // Helper to append recipient (email or role:RoleName) cleanly with comma separation & Set deduplication
  const appendRecipient = (fieldName, item) => {
    if (!item) return
    const currentVal = String(data[fieldName] || '')
    const existing = currentVal.split(',').map(s => s.trim()).filter(Boolean)
    const newItems = String(item).split(',').map(s => s.trim()).filter(Boolean)

    const existingLower = new Set(existing.map(s => s.toLowerCase()))
    const toAdd = newItems.filter(x => !existingLower.has(x.toLowerCase()))

    if (toAdd.length > 0) {
      const combined = [...existing, ...toAdd]
      onFieldChange(fieldName, combined.join(', '))
    }
  }

  // Dynamic preview that extracts ANY {placeholder} from text without hardcoding
  const generatePreview = () => {
    const defaultFrom = emailServers.length > 0 ? (emailServers[0].from_email || emailServers[0].outgoing_email_user) : 'support@company.com'
    const rawFrom = data.from || defaultFrom
    const rawTo = data.to || 'recipient@example.com'
    const rawCc = data.cc || ''
    const rawBcc = data.bcc || ''
    const rawSubject = data.subject || 'Workflow Notification'
    const rawBody = data.body || 'Your workflow request has been processed.'

    const knownMockDefaults = {
      'id': '1',
      'entity_id': '1',
      'record_id': '1',
      'status': 'APPROVED',
      'from_email': defaultFrom,
      'sender_email': defaultFrom,
      'email': dbUsers.length > 0 ? dbUsers[0].email : 'jasminbabariya22@gmail.com',
      'user_email': dbUsers.length > 0 ? dbUsers[0].email : 'jasminbabariya22@gmail.com',
      'user_name': dbUsers.length > 0 ? (dbUsers[0].name || dbUsers[0].full_name || 'User') : 'Jasmin',
      'name': dbUsers.length > 0 ? (dbUsers[0].name || dbUsers[0].full_name || 'User') : 'Jasmin',
      'created_at': new Date().toLocaleDateString()
    }

    const replaceAllDynamicVars = (text) => {
      if (!text) return ''
      let output = String(text)
      
      // 1. Substitute double braces {{key}}
      output = output.replace(/\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g, (match, key) => {
        const lowerKey = key.toLowerCase()
        if (knownMockDefaults[lowerKey]) return knownMockDefaults[lowerKey]
        return `[${key}]`
      })

      // 2. Substitute single braces {key}
      output = output.replace(/\{([a-zA-Z0-9_.]+)\}/g, (match, key) => {
        const lowerKey = key.toLowerCase()
        if (knownMockDefaults[lowerKey]) return knownMockDefaults[lowerKey]
        return `[${key}]`
      })

      return output
    }

    let resolvedFrom = replaceAllDynamicVars(rawFrom)
    let resolvedTo = replaceAllDynamicVars(rawTo)
    let resolvedCc = replaceAllDynamicVars(rawCc)
    let resolvedBcc = replaceAllDynamicVars(rawBcc)
    let resolvedSubject = replaceAllDynamicVars(rawSubject)
    let resolvedBody = replaceAllDynamicVars(rawBody)

    // Resolve roles into assigned user emails for preview
    const resolveRolePreview = (recipients) => {
      if (!recipients) return ''
      return String(recipients).split(',').map(part => {
        const trimmed = part.trim()
        if (trimmed.startsWith('role:')) {
          const roleName = trimmed.replace('role:', '').trim().toLowerCase()
          const matched = dbUsers.filter(u =>
            (u.role_name && String(u.role_name).toLowerCase() === roleName) ||
            (Array.isArray(u.roles) && u.roles.some(r => String(r && r.name ? r.name : r).toLowerCase() === roleName))
          )
          if (matched.length > 0) {
            return `${trimmed} (${matched.map(u => u.email).join(', ')})`
          }
        }
        return trimmed
      }).join(', ')
    }

    resolvedTo = resolveRolePreview(resolvedTo)
    resolvedCc = resolveRolePreview(resolvedCc)
    resolvedBcc = resolveRolePreview(resolvedBcc)

    return {
      from: resolvedFrom,
      to: resolvedTo,
      cc: resolvedCc,
      bcc: resolvedBcc,
      subject: resolvedSubject,
      body: resolvedBody
    }
  }

  const preview = generatePreview()

  return (
    <div className="wf-email-composer">
      {/* 1. Clean Header & Segmented Tabs */}
      <div className="wf-email-header">
        <div className="wf-email-toolbar-title">
          <Mail size={14} style={{ color: '#6366f1' }} />
          <span>Email Composer</span>
        </div>
        <span style={{ fontSize: '11px', color: '#64748b', background: '#f1f5f9', padding: '2px 7px', borderRadius: '4px', fontWeight: 500 }}>
          {data.action_type === 'SEND_TEMPLATE_EMAIL' ? 'Template' : 'SMTP'}
        </span>
      </div>

      <div className="wf-email-tabs-bar" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'compose'}
          className={`wf-email-tab-pill ${activeTab === 'compose' ? 'active' : ''}`}
          onClick={() => setActiveTab('compose')}
        >
          <Edit3 size={13} />
          <span>Compose</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'preview'}
          className={`wf-email-tab-pill ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          <Eye size={13} />
          <span>Preview</span>
        </button>
      </div>

      {activeTab === 'compose' ? (
        <>
          {/* FROM Field: Sender Email & Client DB Email Server Config */}
          <div className="wf-field-group" style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label className="wf-field-label" htmlFor="email-from-select" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Mail size={13} style={{ color: '#6366f1' }} />
                <span>From (Sender Email)</span> <span style={{ color: '#f43f5e' }}>*</span>
              </label>
              <button
                type="button"
                onClick={() => setIsSenderModalOpen(true)}
                style={{
                  background: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: '#4f46e5',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.15s ease'
                }}
                title="Manage or authenticate email servers in Client DB"
              >
                <Settings size={12} />
                <span>+ Authenticate / Manage</span>
              </button>
            </div>

            {/* Direct select dropdown showing user selected email_id */}
            <div style={{ position: 'relative' }}>
              <select
                id="email-from-select"
                name="email_from"
                aria-label="From Sender Email"
                className="wf-select font-mono"
                value={
                  data.email_server_id && emailServers.some(s => String(s.email_server_id) === String(data.email_server_id))
                    ? String(data.email_server_id)
                    : (data.from || '')
                }
                onChange={(e) => {
                  const val = e.target.value
                  const matched = emailServers.find(s => String(s.email_server_id) === val || (s.from_email || s.outgoing_email_user) === val)
                  if (matched) {
                    onFieldsChange({
                      from: matched.from_email || matched.outgoing_email_user,
                      email_server_id: matched.email_server_id
                    })
                  } else {
                    onFieldsChange({
                      from: val,
                      email_server_id: null
                    })
                  }
                }}
                style={{
                  width: '100%',
                  fontWeight: 500,
                  fontSize: '13px',
                  color: '#0f172a',
                  background: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px',
                  padding: '8px 12px'
                }}
              >
                <option value="" disabled>-- Select Sender Email --</option>
                {emailServers.map(s => {
                  const emailVal = s.from_email || s.outgoing_email_user
                  return (
                    <option key={`opt-srv-${s.connection_id || 'c'}-${s.email_server_id}`} value={String(s.email_server_id)}>
                      {emailVal} ({s.server_name || 'SMTP'} - #{s.email_server_id})
                    </option>
                  )
                })}
                {data.from && !emailServers.some(s => String(s.email_server_id) === String(data.email_server_id) || (s.from_email || s.outgoing_email_user) === data.from) && (
                  <option value={data.email_server_id ? String(data.email_server_id) : data.from}>
                    {data.from} {data.email_server_id ? `(SMTP - #${data.email_server_id})` : ''}
                  </option>
                )}
              </select>
            </div>
          </div>

          {/* TO Field */}
          <div className="wf-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '6px' }}>
              <label className="wf-field-label" htmlFor="email-to-input" style={{ margin: 0 }}>
                To (Recipient) <span style={{ color: '#f43f5e' }}>*</span>
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                {/* User Email Dropdown from connectDB */}
                <select
                  id="email-to-user-dropdown"
                  name="email_to_user_select"
                  aria-label="Add user email to recipient"
                  className="wf-token-dropdown"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      appendRecipient('to', e.target.value)
                      e.target.value = ''
                    }
                  }}
                  title="Select user email from connected database"
                  style={{ maxWidth: '135px' }}
                >
                  <option value="" disabled>+ User Email (DB)...</option>
                  {dbUsers.length > 0 ? (
                    dbUsers.map(u => (
                      <option key={`to-user-${u.id || u.email}`} value={u.email}>
                        {u.name ? `${u.name} (${u.email})` : u.email}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>No DB users with email</option>
                  )}
                </select>

                {/* Role Recipient Dropdown */}
                <select
                  id="email-to-role-dropdown"
                  name="email_to_role_select"
                  aria-label="Add role to recipient"
                  className="wf-token-dropdown"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      appendRecipient('to', `role:${e.target.value}`)
                      e.target.value = ''
                    }
                  }}
                  title="Assign notification to all users having this role"
                  style={{ maxWidth: '115px' }}
                >
                  <option value="" disabled>+ Add Role...</option>
                  {dbRoles.length > 0 ? (
                    dbRoles.map(r => (
                      <option key={`to-role-${String(r)}`} value={String(r)}>
                        Role: {String(r)}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="ADMIN">Role: ADMIN</option>
                      <option value="MANAGER">Role: MANAGER</option>
                    </>
                  )}
                </select>

                {/* Report To Recipient Dropdown */}
                <select
                  id="email-to-reports-to-dropdown"
                  name="email_to_reports_to_select"
                  aria-label="Add Report To recipients"
                  className="wf-token-dropdown"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      appendRecipient('to', e.target.value)
                      e.target.value = ''
                    }
                  }}
                  title="Send to both user and reporting manager (Parent -> User)"
                  style={{ maxWidth: '130px' }}
                >
                  <option value="" disabled>+ Report To...</option>
                  {backendReportsTo.length > 0 ? (
                    backendReportsTo.map((rt, idx) => {
                      const val = rt.both_emails || `${rt.user_email}, ${rt.parent_user_email}`
                      const label = rt.display_label || `${rt.parent_user_name} -> ${rt.user_name} (${rt.user_email} -> ${rt.parent_user_email})`
                      return (
                        <option key={`to-rt-${rt.user_id || idx}`} value={val}>
                          {label}
                        </option>
                      )
                    })
                  ) : (
                    <option value="" disabled>No Report To users found</option>
                  )}
                </select>

                {/* Show CC / BCC toggles */}
                {!showCc && (
                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => setShowCc(true)}
                    style={{ fontSize: '11px', color: '#6366f1' }}
                  >
                    + CC
                  </button>
                )}
                {!showBcc && (
                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => setShowBcc(true)}
                    style={{ fontSize: '11px', color: '#6366f1' }}
                  >
                    + BCC
                  </button>
                )}
              </div>
            </div>
            <input
              id="email-to-input"
              name="email_to"
              aria-label="Recipient Email Address"
              type="text"
              className="wf-input text-xs"
              value={data.to || ''}
              onChange={(e) => onFieldChange('to', e.target.value)}
              placeholder="e.g. user@company.com, role:MANAGER, {email}"
            />
          </div>

          {/* CC Field */}
          {showCc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '6px' }}>
                <label className="wf-field-label" htmlFor="email-cc-input" style={{ margin: 0 }}>CC (Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  <select
                    id="email-cc-user-dropdown"
                    name="email_cc_user_select"
                    aria-label="Add CC user email"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('cc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    style={{ maxWidth: '120px' }}
                  >
                    <option value="" disabled>+ Add User...</option>
                    {dbUsers.map(u => (
                      <option key={`cc-user-${u.id || u.email}`} value={u.email}>{u.name || u.email}</option>
                    ))}
                  </select>

                  <select
                    id="email-cc-role-dropdown"
                    name="email_cc_role_select"
                    aria-label="Add CC role"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('cc', `role:${e.target.value}`)
                        e.target.value = ''
                      }
                    }}
                    style={{ maxWidth: '110px' }}
                  >
                    <option value="" disabled>+ Role...</option>
                    {dbRoles.map(r => (
                      <option key={`cc-role-${String(r)}`} value={String(r)}>{String(r)}</option>
                    ))}
                  </select>

                  <select
                    id="email-cc-reports-to-dropdown"
                    name="email_cc_reports_to_select"
                    aria-label="Add CC Report To"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('cc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    style={{ maxWidth: '120px' }}
                  >
                    <option value="" disabled>+ Report To...</option>
                    {backendReportsTo.map((rt, idx) => {
                      const val = rt.both_emails || `${rt.user_email}, ${rt.parent_user_email}`
                      const label = rt.display_label || `${rt.parent_user_name} -> ${rt.user_name} (${rt.user_email} -> ${rt.parent_user_email})`
                      return (
                        <option key={`cc-rt-${rt.user_id || idx}`} value={val}>
                          {label}
                        </option>
                      )
                    })}
                  </select>

                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => {
                      setShowCc(false)
                      onFieldChange('cc', '')
                    }}
                    style={{ fontSize: '11px', color: '#94a3b8' }}
                    title="Remove CC"
                    aria-label="Remove CC field"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
              <input
                id="email-cc-input"
                name="email_cc"
                aria-label="CC Carbon Copy Recipients"
                type="text"
                className="wf-input text-xs"
                value={data.cc || ''}
                onChange={(e) => onFieldChange('cc', e.target.value)}
                placeholder="e.g. manager@example.com, role:HR"
              />
            </div>
          )}

          {/* BCC Field */}
          {showBcc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '6px' }}>
                <label className="wf-field-label" htmlFor="email-bcc-input" style={{ margin: 0 }}>BCC (Blind Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  <select
                    id="email-bcc-role-dropdown"
                    name="email_bcc_role_select"
                    aria-label="Add BCC role"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('bcc', `role:${e.target.value}`)
                        e.target.value = ''
                      }
                    }}
                    style={{ maxWidth: '110px' }}
                  >
                    <option value="" disabled>+ Role...</option>
                    {dbRoles.map(r => (
                      <option key={`bcc-role-${String(r)}`} value={String(r)}>{String(r)}</option>
                    ))}
                  </select>

                  <select
                    id="email-bcc-reports-to-dropdown"
                    name="email_bcc_reports_to_select"
                    aria-label="Add BCC Report To"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('bcc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    style={{ maxWidth: '120px' }}
                  >
                    <option value="" disabled>+ Report To...</option>
                    {backendReportsTo.map((rt, idx) => {
                      const val = rt.both_emails || `${rt.user_email}, ${rt.parent_user_email}`
                      const label = rt.display_label || `${rt.parent_user_name} -> ${rt.user_name} (${rt.user_email} -> ${rt.parent_user_email})`
                      return (
                        <option key={`bcc-rt-${rt.user_id || idx}`} value={val}>
                          {label}
                        </option>
                      )
                    })}
                  </select>

                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => {
                      setShowBcc(false)
                      onFieldChange('bcc', '')
                    }}
                    style={{ fontSize: '11px', color: '#94a3b8' }}
                    title="Remove BCC"
                    aria-label="Remove BCC field"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
              <input
                id="email-bcc-input"
                name="email_bcc"
                aria-label="BCC Blind Carbon Copy Recipients"
                type="text"
                className="wf-input text-xs"
                value={data.bcc || ''}
                onChange={(e) => onFieldChange('bcc', e.target.value)}
                placeholder="e.g. audit@example.com, role:ADMIN"
              />
            </div>
          )}

          {/* Subject Field */}
          <div className="wf-field-group">
            <label className="wf-field-label" htmlFor="email-subject-input" style={{ marginBottom: '4px' }}>
              Subject <span style={{ color: '#f43f5e' }}>*</span>
            </label>
            <input
              id="email-subject-input"
              name="email_subject"
              aria-label="Email Subject"
              type="text"
              className="wf-input text-xs"
              value={data.subject || ''}
              onChange={(e) => onFieldChange('subject', e.target.value)}
              placeholder="e.g. Request Notification for {name} - #{id}"
            />
          </div>

          {/* Body Field */}
          <div className="wf-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="wf-field-label" htmlFor="email-body-input" style={{ margin: 0 }}>Message Body</label>
              <span style={{ fontSize: '10px', color: '#64748b' }}>Supports dynamic keys like {`{name}`}, {`{status}`}</span>
            </div>
            <textarea
              id="email-body-input"
              name="email_body"
              aria-label="Email Message Body"
              className="wf-textarea font-sans text-xs"
              rows={6}
              value={data.body || ''}
              onChange={(e) => onFieldChange('body', e.target.value)}
              placeholder="e.g. Hello {name}, your workflow request has been processed. Status: {status}"
              style={{ lineHeight: '1.5' }}
            />
            {/* Dynamic key usage helper */}
            <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b', lineHeight: 1.5, background: 'var(--wf-surface-card, rgba(248,250,252,0.8))', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(226,232,240,0.8)' }}>
              <span>💡 Write any key like <code style={{ color: '#0284c7', background: 'rgba(2,132,199,0.1)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>{`{name}`}</code>, <code style={{ color: '#0284c7', background: 'rgba(2,132,199,0.1)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>{`{status}`}</code>, or <code style={{ color: '#0284c7', background: 'rgba(2,132,199,0.1)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>{`{id}`}</code> directly in Subject or Body.</span>
            </div>
          </div>
        </>
      ) : (
        /* 2. Live Email Mockup Preview */
        <div className="wf-email-preview-container">
          <div className="wf-email-preview-card">
            <div className="wf-preview-meta-row">
              <span className="wf-preview-label">From:</span>
              <span className="wf-preview-val font-mono" style={{ color: '#4f46e5', fontWeight: 600 }}>{preview.from || '<default server>'}</span>
            </div>
            <div className="wf-preview-meta-row">
              <span className="wf-preview-label">To:</span>
              <span className="wf-preview-val font-mono">{preview.to || '<empty>'}</span>
            </div>
            {preview.cc && (
              <div className="wf-preview-meta-row">
                <span className="wf-preview-label">CC:</span>
                <span className="wf-preview-val font-mono">{preview.cc}</span>
              </div>
            )}
            {preview.bcc && (
              <div className="wf-preview-meta-row">
                <span className="wf-preview-label">BCC:</span>
                <span className="wf-preview-val font-mono">{preview.bcc}</span>
              </div>
            )}
            <div className="wf-preview-meta-row" style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
              <span className="wf-preview-label">Subject:</span>
              <span className="wf-preview-val font-semibold" style={{ color: '#0f172a' }}>{preview.subject || '<No Subject>'}</span>
            </div>

            {/* Email Body Preview */}
            <div style={{ padding: '14px', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', minHeight: '80px', marginTop: '6px' }}>
              <p style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: '12px', color: '#334155', lineHeight: 1.6 }}>
                {preview.body || 'No message content defined.'}
              </p>
            </div>
          </div>
          <div style={{ marginTop: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '10.5px', color: '#64748b' }}>
              Variables like <code>&#123;&#123;id&#125;&#125;</code> and <code>&#123;&#123;status&#125;&#125;</code> are previewed with live sample data.
            </span>
          </div>
        </div>
      )}

      {/* Dedicated Sender Email Configuration Modal */}
      <SenderEmailModal
        isOpen={isSenderModalOpen}
        onClose={() => setIsSenderModalOpen(false)}
        connectionId={effectiveConnId}
        selectedEmail={data.from}
        selectedServerId={data.email_server_id}
        onSelectSender={(sender) => {
          const emailVal = sender.email || sender.from_email || sender.outgoing_email_user
          onFieldsChange({
            from: emailVal,
            email_server_id: sender.email_server_id,
            ...(sender.connection_id && !data.connection_id ? { connection_id: sender.connection_id } : {})
          })
        }}
      />
    </div>
  )
}

