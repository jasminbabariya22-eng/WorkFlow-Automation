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

  const [customVarInput, setCustomVarInput] = useState('')

  // Dynamically extract columns from the introspected database table with single-brace {field} syntax
  const tableVars = (availableFields || [])
    .filter(f => !['is_deleted'].includes(f.name))
    .map(f => ({ label: f.name, token: `{${f.name}}` }))

  // Standard API request parameters and context variables (matching Image 1 spec)
  const defaultVars = [
    { label: 'Name', token: '{Name}' },
    { label: 'Address', token: '{Address}' },
    { label: 'Incident_Id', token: '{Incident_Id}' },
    { label: 'pocket_no', token: '{pocket_no}' },
    { label: 'id', token: '{id}' },
    { label: 'status', token: '{status}' },
    { label: 'email', token: '{email}' }
  ]

  // Combine table fields with API parameter tokens, avoiding duplicates
  const existingKeys = new Set(tableVars.map(v => v.label.toLowerCase()))
  const mergedVars = [
    ...defaultVars.filter(v => !existingKeys.has(v.label.toLowerCase())),
    ...tableVars
  ]

  const activeVars = mergedVars

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

  // Insert variable token into body or subject
  const insertToken = (fieldName, token) => {
    const currentVal = data[fieldName] || ''
    if (!currentVal) {
      handleFieldChange(fieldName, token)
    } else {
      const separator = ['to', 'cc', 'bcc'].includes(fieldName) ? ', ' : ' '
      handleFieldChange(fieldName, `${currentVal.trim()}${separator}${token}`)
    }
  }

  // Simulated render for live preview (supports both {var} and {{var}})
  const generatePreview = () => {
    const rawTo = data.to || 'recipient@example.com'
    const rawCc = data.cc || ''
    const rawBcc = data.bcc || ''
    const rawSubject = data.subject || 'Workflow Notification'
    const rawBody = data.body || 'Your workflow request has been processed.'

    const mockData = {
      'name': dbUsers.length > 0 ? dbUsers[0].name : 'Ram',
      'address': 'Delhi',
      'add': 'Delhi',
      'pocket_no': '22',
      'pocketno': '22',
      'incident_id': 'INC-1001',
      'incidentid': 'INC-1001',
      'incident': 'INC-1001',
      'id': '1',
      'entity_id': '1',
      'record_id': '1',
      'status': 'APPROVED',
      'email': dbUsers.length > 0 ? dbUsers[0].email : 'jasminbabariya22@gmail.com',
      'created_at': new Date().toLocaleDateString()
    }

    // Add table vars with sample values
    activeVars.forEach(v => {
      const rawK = v.label.toLowerCase()
      if (!mockData[rawK]) {
        mockData[rawK] = rawK.includes('id') ? '1' : rawK.includes('status') ? 'APPROVED' : `[${v.label}]`
      }
    })

    const replaceAllVars = (text) => {
      if (!text) return ''
      let output = text
      Object.entries(mockData).forEach(([k, val]) => {
        // Replace {{k}} and {k} case-insensitively
        const reDouble = new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'gi')
        const reSingle = new RegExp(`\\{\\s*${k}\\s*\\}`, 'gi')
        output = output.replace(reDouble, String(val)).replace(reSingle, String(val))
      })
      return output
    }

    let resolvedTo = replaceAllVars(rawTo)
    let resolvedCc = replaceAllVars(rawCc)
    let resolvedBcc = replaceAllVars(rawBcc)
    let resolvedSubject = replaceAllVars(rawSubject)
    let resolvedBody = replaceAllVars(rawBody)

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

                {/* Role Selector Dropdown from connectDB */}
                <select
                  id="email-to-role-dropdown"
                  name="email_to_role_select"
                  aria-label="Add role to recipient"
                  className="wf-token-dropdown"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      appendRecipient('to', e.target.value)
                      e.target.value = ''
                    }
                  }}
                  title="Select role from connected database"
                  style={{ maxWidth: '110px' }}
                >
                  <option value="" disabled>+ Role (DB)...</option>
                  {dbRoles.length > 0 ? (
                    dbRoles.map(r => (
                      <option key={`to-role-${r}`} value={`role:${r}`}>Role: {r}</option>
                    ))
                  ) : (
                    <option value="" disabled>No DB roles found</option>
                  )}
                </select>

                {!showCc && (
                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => setShowCc(true)}
                    style={{ fontSize: '11px', color: '#818cf8' }}
                  >
                    + CC
                  </button>
                )}
                {!showBcc && (
                  <button
                    type="button"
                    className="wf-link-btn"
                    onClick={() => setShowBcc(true)}
                    style={{ fontSize: '11px', color: '#818cf8' }}
                  >
                    + BCC
                  </button>
                )}
              </div>
            </div>
            <input
              id="email-to-input"
              name="email_to"
              aria-label="Email Recipients (To)"
              type="text"
              className="wf-input text-xs"
              value={data.to || ''}
              onChange={(e) => handleFieldChange('to', e.target.value)}
              placeholder={dbUsers.length > 0 ? `e.g. ${dbUsers[0].email}, role:${dbRoles[0] || 'EMPLOYEE'}` : 'e.g. jasminbabariya22@gmail.com, role:EMPLOYEE, {{email}}'}
            />
            {/* Dynamic Quick Helper Chips from Connected Database */}
            {(dbUsers.length > 0 || dbRoles.length > 0) && (
              <div className="wf-token-bar" style={{ marginTop: '5px' }}>
                <span className="wf-token-bar-label">Quick Add:</span>
                {dbUsers.slice(0, 3).map(u => (
                  <button
                    key={`quick-user-${u.id || u.email}`}
                    type="button"
                    className="wf-token-chip"
                    onClick={() => appendRecipient('to', u.email)}
                    title={`Add ${u.email}`}
                  >
                    + {u.name ? u.name.split(' ')[0] : u.email}
                  </button>
                ))}
                {dbRoles.slice(0, 3).map(r => (
                  <button
                    key={`quick-role-${r}`}
                    type="button"
                    className="wf-token-chip"
                    onClick={() => appendRecipient('to', `role:${r}`)}
                    title={`Add role:${r}`}
                  >
                    + Role: {r}
                  </button>
                ))}
                <button
                  type="button"
                  className="wf-token-chip"
                  onClick={() => appendRecipient('to', '{{email}}')}
                  title="Add dynamic context {{email}}"
                >
                  + &#123;&#123;email&#125;&#125;
                </button>
              </div>
            )}
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
              Choose user email or role from the connected database, or type directly. Separate multiple recipients with commas.
            </div>
          </div>

          {/* CC Field (Optional) */}
          {showCc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '6px' }}>
                <label className="wf-field-label" htmlFor="email-cc-input" style={{ margin: 0 }}>CC (Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  {/* User Email Dropdown from connectDB */}
                  <select
                    id="email-cc-user-dropdown"
                    name="email_cc_user_select"
                    aria-label="Add user email to CC"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('cc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    title="Select user email from connected database"
                    style={{ maxWidth: '140px' }}
                  >
                    <option value="" disabled>+ User Email (DB)...</option>
                    {dbUsers.length > 0 ? (
                      dbUsers.map(u => (
                        <option key={`cc-user-${u.id || u.email}`} value={u.email}>
                          {u.name ? `${u.name} (${u.email})` : u.email}
                        </option>
                      ))
                    ) : (
                      <option value="" disabled>No DB users with email</option>
                    )}
                  </select>

                  {/* Role Selector Dropdown from connectDB */}
                  <select
                    id="email-cc-role-dropdown"
                    name="email_cc_role_select"
                    aria-label="Add role to CC"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('cc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    title="Select role from connected database"
                    style={{ maxWidth: '110px' }}
                  >
                    <option value="" disabled>+ Role (DB)...</option>
                    {dbRoles.length > 0 ? (
                      dbRoles.map(r => (
                        <option key={`cc-role-${r}`} value={`role:${r}`}>Role: {r}</option>
                      ))
                    ) : (
                      <option value="" disabled>No DB roles found</option>
                    )}
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
                placeholder={dbUsers.length > 1 ? `e.g. ${dbUsers[1].email}, role:${dbRoles[0] || 'MANAGER'}` : 'e.g. manager@example.com, role:MANAGER'}
              />
            </div>
          )}

          {/* BCC Field (Optional) */}
          {showBcc && (
            <div className="wf-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '6px' }}>
                <label className="wf-field-label" htmlFor="email-bcc-input" style={{ margin: 0 }}>BCC (Blind Carbon Copy)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  {/* User Email Dropdown from connectDB */}
                  <select
                    id="email-bcc-user-dropdown"
                    name="email_bcc_user_select"
                    aria-label="Add user email to BCC"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('bcc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    title="Select user email from connected database"
                    style={{ maxWidth: '140px' }}
                  >
                    <option value="" disabled>+ User Email (DB)...</option>
                    {dbUsers.length > 0 ? (
                      dbUsers.map(u => (
                        <option key={`bcc-user-${u.id || u.email}`} value={u.email}>
                          {u.name ? `${u.name} (${u.email})` : u.email}
                        </option>
                      ))
                    ) : (
                      <option value="" disabled>No DB users with email</option>
                    )}
                  </select>

                  {/* Role Selector Dropdown from connectDB */}
                  <select
                    id="email-bcc-role-dropdown"
                    name="email_bcc_role_select"
                    aria-label="Add role to BCC"
                    className="wf-token-dropdown"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        appendRecipient('bcc', e.target.value)
                        e.target.value = ''
                      }
                    }}
                    title="Select role from connected database"
                    style={{ maxWidth: '110px' }}
                  >
                    <option value="" disabled>+ Role (DB)...</option>
                    {dbRoles.length > 0 ? (
                      dbRoles.map(r => (
                        <option key={`bcc-role-${r}`} value={`role:${r}`}>Role: {r}</option>
                      ))
                    ) : (
                      <option value="" disabled>No DB roles found</option>
                    )}
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap', gap: '4px' }}>
              <label className="wf-field-label" htmlFor="email-subject-input" style={{ margin: 0 }}>Subject <span style={{ color: '#f43f5e' }}>*</span></label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '10px', color: '#94a3b8' }}>Insert:</span>
                {activeVars.slice(0, 4).map(v => (
                  <button
                    key={`subj-var-${v.token}`}
                    type="button"
                    className="wf-token-chip"
                    onClick={() => insertToken('subject', v.token)}
                    title={`Insert ${v.token} into Subject`}
                    style={{ fontSize: '10px', padding: '1px 6px', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                  >
                    +{v.token}
                  </button>
                ))}
              </div>
            </div>
            <input
              id="email-subject-input"
              name="email_subject"
              aria-label="Email Subject"
              type="text"
              className="wf-input text-xs"
              value={data.subject || ''}
              onChange={(e) => handleFieldChange('subject', e.target.value)}
              placeholder="e.g. New Incident created for {Name} - {Incident_Id}"
            />
          </div>

          {/* Body Field */}
          <div className="wf-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="wf-field-label" htmlFor="email-body-input" style={{ margin: 0 }}>Message Body</label>
              <span style={{ fontSize: '10px', color: '#64748b' }}>Supports plain text & variables ({`{Name}`}, {`{Incident_Id}`})</span>
            </div>
            <textarea
              id="email-body-input"
              name="email_body"
              aria-label="Email Message Body"
              className="wf-textarea font-sans text-xs"
              rows={6}
              value={data.body || ''}
              onChange={(e) => handleFieldChange('body', e.target.value)}
              placeholder="e.g. Hello {Name}, your incident has been created with ID = {Incident_Id} at {Address}. Status: {status}"
              style={{ lineHeight: '1.5' }}
            />
          </div>

          {/* Generic Available Variables & Parameters Bar */}
          <div className="wf-var-palette">
            <div className="wf-var-palette-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
              <span>Insert Variable / Parameter into Body:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <input
                  type="text"
                  placeholder="Custom param (e.g. Name)"
                  value={customVarInput}
                  onChange={(e) => setCustomVarInput(e.target.value)}
                  style={{ fontSize: '10px', padding: '2px 6px', height: '22px', borderRadius: '4px', border: '1px solid #cbd5e1', width: '130px', background: 'var(--wf-surface-card, #fff)', color: 'inherit' }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && customVarInput.trim()) {
                      e.preventDefault()
                      insertToken('body', `{${customVarInput.trim()}}`)
                      setCustomVarInput('')
                    }
                  }}
                />
                <button
                  type="button"
                  className="wf-token-chip"
                  onClick={() => {
                    if (customVarInput.trim()) {
                      insertToken('body', `{${customVarInput.trim()}}`)
                      setCustomVarInput('')
                    }
                  }}
                  style={{ fontSize: '10px', padding: '2px 6px', height: '22px' }}
                >
                  +Insert
                </button>
              </div>
            </div>
            <div className="wf-var-chips-wrap">
              {activeVars.map(v => (
                <button
                  key={v.token}
                  type="button"
                  className="wf-var-pill wf-var-pill-db"
                  onClick={() => insertToken('body', v.token)}
                  title={`Click to insert ${v.token} into message body`}
                >
                  +{v.token}
                </button>
              ))}
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
