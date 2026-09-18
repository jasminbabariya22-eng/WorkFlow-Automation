import React, { useState } from 'react'
import { Mail, Eye, Edit3, X, Users } from 'lucide-react'

export default function EmailNodeSection({
  data,
  backendRoles = [],
  backendUsers = [],
  availableFields = [],
  handleFieldChange,
  handleFieldsChange
}) {
  const [activeTab, setActiveTab] = useState('compose') // 'compose' | 'preview'
  const [showCc, setShowCc] = useState(() => Boolean(data.cc || data.email_cc))
  const [showBcc, setShowBcc] = useState(() => Boolean(data.bcc || data.email_bcc))

  // Strictly filter roles and users from the connected database (connectDB)
  const dbRoles = Array.from(new Set((backendRoles || []).map(r => r.name || r.id).filter(Boolean)))
  const dbUsers = (backendUsers || []).filter(u => u && u.email && u.email.trim())

  // Helper to append recipient (email or role:RoleName) cleanly with comma separation
  const appendRecipient = (fieldName, item) => {
    const currentVal = (data[fieldName] || '').trim()
    if (!currentVal) {
      handleFieldChange(fieldName, item)
    } else {
      const parts = currentVal.split(',').map(s => s.trim()).filter(Boolean)
      if (!parts.includes(item)) {
        handleFieldChange(fieldName, `${currentVal}, ${item}`)
      }
    }
  }

  // Dynamic preview that extracts ANY {placeholder} from text without hardcoding
  const generatePreview = () => {
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
      'email': dbUsers.length > 0 ? dbUsers[0].email : 'jasminbabariya22@gmail.com',
      'user_email': dbUsers.length > 0 ? dbUsers[0].email : 'jasminbabariya22@gmail.com',
      'user_name': dbUsers.length > 0 ? (dbUsers[0].name || dbUsers[0].full_name || 'User') : 'Jasmin',
      'name': dbUsers.length > 0 ? (dbUsers[0].name || dbUsers[0].full_name || 'User') : 'User',
      'created_at': new Date().toLocaleDateString()
    }

    const replaceAllDynamicVars = (text) => {
      if (!text) return ''
      let output = text
      
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

    let resolvedTo = replaceAllDynamicVars(rawTo)
    let resolvedCc = replaceAllDynamicVars(rawCc)
    let resolvedBcc = replaceAllDynamicVars(rawBcc)
    let resolvedSubject = replaceAllDynamicVars(rawSubject)
    let resolvedBody = replaceAllDynamicVars(rawBody)

    // Resolve roles into assigned user emails for preview
    const resolveRolePreview = (recipients) => {
      if (!recipients) return ''
      return recipients.split(',').map(part => {
        const trimmed = part.trim()
        if (trimmed.startsWith('role:')) {
          const roleName = trimmed.replace('role:', '').trim().toLowerCase()
          const matched = dbUsers.filter(u =>
            (u.role_name && u.role_name.toLowerCase() === roleName) ||
            (Array.isArray(u.roles) && u.roles.some(r => String(r).toLowerCase() === roleName))
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
      {/* 1. Header Toolbar & Tab Switcher */}
      <div className="wf-email-toolbar">
        <div className="wf-email-toolbar-title">
          <Mail size={15} className="text-indigo-400" />
          <span>Send Email Configuration</span>
        </div>
        <div className="wf-email-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'compose'}
            className={`wf-email-tab-btn ${activeTab === 'compose' ? 'active' : ''}`}
            onClick={() => setActiveTab('compose')}
          >
            <Edit3 size={13} />
            <span>Compose</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'preview'}
            className={`wf-email-tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
          >
            <Eye size={13} />
            <span>Preview</span>
          </button>
        </div>
      </div>

      {activeTab === 'compose' ? (
        <>
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
                  style={{ maxWidth: '140px' }}
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
                  style={{ maxWidth: '120px' }}
                >
                  <option value="" disabled>+ Add Role...</option>
                  {dbRoles.length > 0 ? (
                    dbRoles.map(r => (
                      <option key={`to-role-${r}`} value={r}>
                        Role: {r}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="ADMIN">Role: ADMIN</option>
                      <option value="MANAGER">Role: MANAGER</option>
                    </>
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
              onChange={(e) => handleFieldChange('to', e.target.value)}
              placeholder="e.g. user@company.com, role:MANAGER, {email}"
            />
          </div>

          {/* CC Field */}
          {showCc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label className="wf-field-label" htmlFor="email-cc-input" style={{ margin: 0 }}>CC (Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
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
                      <option key={`cc-role-${r}`} value={r}>{r}</option>
                    ))}
                  </select>

                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => {
                      setShowCc(false)
                      handleFieldChange('cc', '')
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
                onChange={(e) => handleFieldChange('cc', e.target.value)}
                placeholder="e.g. manager@example.com, role:HR"
              />
            </div>
          )}

          {/* BCC Field */}
          {showBcc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label className="wf-field-label" htmlFor="email-bcc-input" style={{ margin: 0 }}>BCC (Blind Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
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
                      <option key={`bcc-role-${r}`} value={r}>{r}</option>
                    ))}
                  </select>

                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => {
                      setShowBcc(false)
                      handleFieldChange('bcc', '')
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
                onChange={(e) => handleFieldChange('bcc', e.target.value)}
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
              onChange={(e) => handleFieldChange('subject', e.target.value)}
              placeholder="e.g. Request Notification for {name} - #{id}"
            />
          </div>

          {/* Body Field */}
          <div className="wf-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="wf-field-label" htmlFor="email-body-input" style={{ margin: 0 }}>Message Body</label>
              <span style={{ fontSize: '10px', color: '#64748b' }}>Supports dynamic keys like {`{name}`}</span>
            </div>
            <textarea
              id="email-body-input"
              name="email_body"
              aria-label="Email Message Body"
              className="wf-textarea font-sans text-xs"
              rows={6}
              value={data.body || ''}
              onChange={(e) => handleFieldChange('body', e.target.value)}
              placeholder="e.g. Hello {name}, your request has been processed. Status: {status}"
              style={{ lineHeight: '1.5' }}
            />
            {/* Dynamic key usage helper */}
            <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b', lineHeight: 1.5, background: 'var(--wf-surface-card, rgba(248,250,252,0.8))', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(226,232,240,0.8)' }}>
              <span>💡 Write any key like <code style={{ color: '#0284c7', background: 'rgba(2,132,199,0.1)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>{`{name}`}</code> or <code style={{ color: '#0284c7', background: 'rgba(2,132,199,0.1)', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>{`{incident_id}`}</code> directly in Subject or Body. It will be replaced with the values passed in API request parameters.</span>
            </div>
          </div>
        </>
      ) : (
        /* 2. Live Email Mockup Preview */
        <div className="wf-email-preview-container">
          <div className="wf-email-preview-card">
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
    </div>
  )
}
