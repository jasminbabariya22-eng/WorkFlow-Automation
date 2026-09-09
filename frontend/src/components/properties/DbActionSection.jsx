import React from 'react'
import { Globe } from 'lucide-react'
import DatabaseQueryBuilder from './DatabaseQueryBuilder'

export default function DbActionSection({
  nodeType,
  data,
  name,
  connectionId,
  backendEntities,
  availableFields,
  handleFieldChange,
  handleFieldsChange
}) {
  // 1. RECORD NODE (Create, Read, Update, Delete Record)
  if (nodeType === 'record') {
    return (
      <DatabaseQueryBuilder
        nodeType={nodeType}
        nodeName={name}
        connectionId={connectionId}
        data={data}
        availableTables={backendEntities}
        availableFields={availableFields}
        onFieldChange={handleFieldChange}
        onFieldsChange={handleFieldsChange}
      />
    )
  }

  // 2. ACTION NODE (REST API vs Database Action)
  if (nodeType === 'action') {
    const subTypeUpper = String(data.subType || '').toUpperCase()
    const isExplicitDb = subTypeUpper === 'DATABASE' || Boolean(data.table || data.entity || data.queryOperation)
    const isApi = !isExplicitDb && (
      subTypeUpper === 'API' || 
      subTypeUpper === 'REST_API' || 
      data.type === 'apiCall' || 
      data.type === 'api' ||
      Boolean(data.endpoint || data.url) ||
      String(data.label || name || '').toLowerCase().includes('api')
    )

    if (isApi) {
      // Auto-assign subType='API' if missing so it is permanently stored
      if (data.subType !== 'API') {
        setTimeout(() => handleFieldChange('subType', 'API'), 0)
      }

      return (
        <div className="wf-api-config">
          <div className="wf-qb-header-row mb-3 flex items-center justify-between" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: '600', color: '#2dd4bf' }}>
              <Globe size={15} />
              <span>REST API CALL</span>
              <span style={{ fontSize: '9px', fontFamily: 'monospace', fontWeight: 'bold', padding: '2px 6px', borderRadius: '4px', background: 'rgba(45, 212, 191, 0.15)', color: '#5eead4', border: '1px solid rgba(45, 212, 191, 0.3)' }}>
                HTTP
              </span>
            </div>
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">HTTP Method</label>
            <select
              className="wf-select"
              value={data.method || 'POST'}
              onChange={(e) => handleFieldChange('method', e.target.value)}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="PATCH">PATCH</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Endpoint URL</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.endpoint || data.url || 'https://api.internal/v1/webhook'}
              onChange={(e) => handleFieldChange('endpoint', e.target.value)}
              placeholder="https://api.internal/v1/notify"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Headers (Optional)</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.headers || ''}
              onChange={(e) => handleFieldChange('headers', e.target.value)}
              placeholder="Authorization: Bearer {{token}}"
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Payload Body (JSON)</label>
            <textarea
              className="wf-textarea font-mono text-xs"
              rows={4}
              value={data.body || ''}
              onChange={(e) => handleFieldChange('body', e.target.value)}
              placeholder={'{\n  "entity_id": "{{entity_id}}",\n  "status": "APPROVED"\n}'}
            />
          </div>

          <div className="wf-field-group">
            <label className="wf-field-label">Response Variable</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.outputVariable || data.responseVariable || 'api_response'}
              onChange={(e) => handleFieldChange('outputVariable', e.target.value)}
              placeholder="api_response"
            />
          </div>
        </div>
      )
    }

    // Direct Database Action
    return (
      <DatabaseQueryBuilder
        nodeType={nodeType}
        nodeName={name}
        connectionId={connectionId}
        data={data}
        availableTables={backendEntities}
        availableFields={availableFields}
        onFieldChange={handleFieldChange}
        onFieldsChange={handleFieldsChange}
      />
    )
  }

  return null
}
