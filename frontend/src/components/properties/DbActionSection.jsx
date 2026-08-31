import React from 'react'

export default function DbActionSection({
  nodeType,
  data,
  name,
  backendEntities,
  availableFields,
  fieldMappings,
  newFieldKey,
  setNewFieldKey,
  newFieldValue,
  setNewFieldValue,
  handleAddFieldMapping,
  handleRemoveFieldMapping,
  retrieveFields,
  newRetrieveField,
  setNewRetrieveField,
  handleAddRetrieveField,
  handleRemoveRetrieveField,
  handleFieldChange,
  handleFieldsChange
}) {
  if (nodeType === 'record') {
    const currentOp = (data.subType || 
      (String(data.label || name || '').toLowerCase().includes('create') ? 'CREATE_RECORD' : 
       String(data.label || name || '').toLowerCase().includes('read') ? 'READ_RECORD' : 
       data.actionType || 'UPDATE_RECORD')).toUpperCase()

    return (
      <>
        <div className="wf-section-divider">DATABASE OPERATION</div>
        <div className="wf-field-group">
          <label className="wf-field-label">Operation</label>
          <select
            className="wf-select"
            value={currentOp}
            onChange={(e) => {
              const val = e.target.value
              handleFieldsChange({
                subType: val,
                actionType: val,
                label: val === 'READ_RECORD' && name.includes('Record') ? 'Read Record' : 
                       val === 'CREATE_RECORD' && name.includes('Record') ? 'Create Record' : 
                       val === 'UPDATE_RECORD' && name.includes('Record') ? 'Update Record' : name
              })
            }}
          >
            <option value="UPDATE_RECORD">UPDATE (DB_UPDATE)</option>
            <option value="CREATE_RECORD">CREATE (DB_CREATE)</option>
            <option value="READ_RECORD">READ (DB_READ)</option>
          </select>
        </div>

        <div className="wf-section-divider">ENTITY TARGET</div>

        <div className="wf-field-group">
          <label className="wf-field-label">Target Entity (Client Table)</label>
          <select
            className="wf-select"
            value={data.entity || data.table || ''}
            onChange={(e) => {
              const val = e.target.value
              handleFieldsChange({
                entity: val,
                table: val
              })
            }}
          >
            <option value="">-- Select Client Table --</option>
            {backendEntities.map(ent => (
              <option key={ent.name} value={ent.name}>{ent.name}</option>
            ))}
          </select>
        </div>

        {(currentOp === 'UPDATE_RECORD' || currentOp === 'READ_RECORD') && (
          <div className="wf-field-group">
            <label className="wf-field-label">Record Identifier</label>
            <input
              type="text"
              className="wf-input font-mono text-xs"
              value={data.recordId || '{{workflow.entity_id}}'}
              onChange={(e) => handleFieldChange('recordId', e.target.value)}
              placeholder="e.g. {{workflow.entity_id}}"
            />
          </div>
        )}

        {currentOp !== 'READ_RECORD' ? (
          <>
            <div className="wf-section-divider">FIELD MAPPINGS</div>
            <div className="wf-field-mapping-list">
              {fieldMappings.map((m, idx) => (
                <div key={idx} className="wf-mapping-row">
                  <span className="wf-map-key">{m.field}</span>
                  <span className="wf-map-arrow">➔</span>
                  <span className="wf-map-val">{m.value}</span>
                  <button
                    className="wf-mapping-del"
                    onClick={() => handleRemoveFieldMapping(idx)}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="wf-add-mapping-box">
              {availableFields.length > 0 ? (
                <select
                  className="wf-select text-xs font-mono"
                  value={newFieldKey}
                  onChange={(e) => setNewFieldKey(e.target.value)}
                >
                  <option value="">-- Select Column --</option>
                  {availableFields.map(f => (
                    <option key={f.name} value={f.name}>{f.name}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="wf-input text-xs"
                  placeholder="Field name (e.g. status)"
                  value={newFieldKey}
                  onChange={(e) => setNewFieldKey(e.target.value)}
                />
              )}
              <input
                type="text"
                className="wf-input text-xs"
                placeholder="Value (e.g. APPROVED)"
                value={newFieldValue}
                onChange={(e) => setNewFieldValue(e.target.value)}
              />
              <button
                className="wf-add-action-btn"
                onClick={handleAddFieldMapping}
              >
                Add Mapping
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="wf-section-divider">RETRIEVE FIELDS</div>
            <div className="wf-tag-list">
              {retrieveFields.map((f) => (
                <span key={f} className="wf-tag-item">
                  <span>{f}</span>
                  <button
                    className="wf-tag-remove"
                    onClick={() => handleRemoveRetrieveField(f)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="wf-add-action-box">
              {availableFields.length > 0 ? (
                <select
                  className="wf-select text-xs font-mono"
                  value={newRetrieveField}
                  onChange={(e) => setNewRetrieveField(e.target.value)}
                >
                  <option value="">-- Select Column --</option>
                  {availableFields.map(f => (
                    <option key={f.name} value={f.name}>{f.name}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="wf-input text-xs"
                  placeholder="Field to read (e.g. status)"
                  value={newRetrieveField}
                  onChange={(e) => setNewRetrieveField(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddRetrieveField()}
                />
              )}
              <button
                className="wf-add-action-btn"
                onClick={handleAddRetrieveField}
              >
                Add Field
              </button>
            </div>

            <div className="wf-field-group mt-3">
              <label className="wf-field-label">Output Variable Name</label>
              <input
                type="text"
                className="wf-input font-mono"
                value={data.outputVariable || 'entity_data'}
                onChange={(e) => handleFieldChange('outputVariable', e.target.value)}
              />
            </div>
          </>
        )}
      </>
    )
  }

  if (nodeType === 'action') {
    const isApi = data.subType === 'API' || 
      data.type === 'apiCall' || 
      String(data.label || name || '').toLowerCase().includes('api')

    return (
      <>
        <div className="wf-field-group">
          <label className="wf-field-label">Action Type</label>
          <div className="wf-type-toggle-buttons">
            <button
              type="button"
              className={`wf-preset-btn ${isApi ? 'active' : ''}`}
              onClick={() => {
                handleFieldsChange({
                  subType: 'API',
                  label: (data.label || name || '').toLowerCase().includes('database') ? 'API Call' : (data.label || name)
                })
              }}
            >
              🌐 REST API Call
            </button>
            <button
              type="button"
              className={`wf-preset-btn ${!isApi ? 'active' : ''}`}
              onClick={() => {
                handleFieldsChange({
                  subType: 'DATABASE',
                  label: (data.label || name || '').toLowerCase().includes('api') ? 'Database Action' : (data.label || name)
                })
              }}
            >
              🗄️ Database Action
            </button>
          </div>
        </div>

        {isApi ? (
          <>
            <div className="wf-section-divider">REST REQUEST</div>

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
                value={data.endpoint || data.url || 'https://api.internal/webhook'}
                onChange={(e) => handleFieldChange('endpoint', e.target.value)}
                placeholder="https://api.internal/v1/notify"
              />
            </div>
          </>
        ) : (
          <>
            <div className="wf-section-divider">SQL QUERY / ADAPTER</div>

            <div className="wf-field-group">
              <label className="wf-field-label">Query / Statement</label>
              <textarea
                className="wf-textarea font-mono text-xs"
                rows={3}
                value={data.sql || 'UPDATE ers.risk_register SET status_id = 4 WHERE id = :entity_id'}
                onChange={(e) => handleFieldChange('sql', e.target.value)}
                placeholder="UPDATE ers.mst_entity SET is_active = 1 WHERE id = :id"
              />
            </div>
          </>
        )}
      </>
    )
  }

  return null
}
