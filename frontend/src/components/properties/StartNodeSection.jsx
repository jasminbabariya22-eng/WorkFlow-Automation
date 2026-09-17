import React from 'react'
import { Database, Zap, Filter, Table, ArrowRight, Layers, CheckCircle2 } from 'lucide-react'

export default function StartNodeSection({
  data,
  backendEntities = [],
  availableFields = [],
  handleFieldChange,
  handleFieldsChange
}) {
  const triggerType = data.triggerType || 'Manual'
  const currentTable = data.table || data.entity || ''
  const eventType = data.eventType || data.triggerEvent || 'UPDATE'
  const filterField = data.filterField || data.triggerColumn || ''
  const filterOperator = data.filterOperator || '=='
  const filterValue = data.filterValue !== undefined ? data.filterValue : ''

  const handleTableChange = (tableName) => {
    handleFieldsChange({
      table: tableName,
      entity: tableName,
      target_entity: tableName
    })
  }

  return (
    <div className="wf-start-trigger-section">
      <div className="wf-section-divider" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Zap size={13} color="#818cf8" />
        <span>TRIGGER CONFIGURATION</span>
      </div>

      {/* 1. Trigger Type Selector */}
      <div className="wf-field-group">
        <label className="wf-field-label" htmlFor="start-trigger-source">Trigger Source</label>
        <select
          id="start-trigger-source"
          name="trigger_source"
          aria-label="Workflow Trigger Source"
          className="wf-select"
          value={triggerType}
          onChange={(e) => handleFieldChange('triggerType', e.target.value)}
        >
          <option value="Manual">Manual / API Trigger (Button / Submit)</option>
          <option value="Database">Database Event (Insert / Update on Table)</option>
        </select>
        <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
          {triggerType === 'Manual'
            ? 'Workflow starts when triggered via API or Test Run button.'
            : 'Workflow starts automatically based on database record changes.'}
        </div>
      </div>

      {/* 2. Database Event Configuration */}
      {triggerType === 'Database' && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.4)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          borderRadius: '8px',
          padding: '12px',
          marginTop: '8px'
        }}>
          {/* A. Target Database Table */}
          <div className="wf-field-group" style={{ marginBottom: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="wf-field-label" htmlFor="start-db-table" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Table size={12} color="#38bdf8" />
                <span>Target Database Table</span>
                <span style={{ color: '#f43f5e' }}>*</span>
              </label>
              {currentTable && (
                <span style={{ fontSize: '10px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.12)', padding: '1px 6px', borderRadius: '4px' }}>
                  {availableFields.length} columns
                </span>
              )}
            </div>
            <select
              id="start-db-table"
              name="db_table"
              aria-label="Target Database Table"
              className="wf-select"
              value={currentTable}
              onChange={(e) => handleTableChange(e.target.value)}
            >
              <option value="">-- Choose Database Table --</option>
              {backendEntities.map(t => (
                <option key={t.name} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
              Select which database table event triggers this workflow.
            </div>
          </div>

          {/* B. Event Action Type (Insert / Update) */}
          <div className="wf-field-group" style={{ marginBottom: '10px' }}>
            <label className="wf-field-label" id="start-event-type-label">Trigger On Event</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }} role="group" aria-labelledby="start-event-type-label">
              {[
                { id: 'UPDATE', label: 'On Update', desc: 'When record is updated' },
                { id: 'INSERT', label: 'On Insert', desc: 'When new record created' },
                { id: 'INSERT_OR_UPDATE', label: 'Insert & Update', desc: 'Any record change' }
              ].map(evt => (
                <button
                  key={evt.id}
                  type="button"
                  onClick={() => handleFieldChange('eventType', evt.id)}
                  aria-label={`Trigger on ${evt.label}`}
                  style={{
                    padding: '8px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontWeight: '600',
                    textAlign: 'left',
                    cursor: 'pointer',
                    gridColumn: evt.id === 'INSERT_OR_UPDATE' ? 'span 2' : 'span 1',
                    border: eventType === evt.id ? '1px solid #818cf8' : '1px solid rgba(255, 255, 255, 0.08)',
                    background: eventType === evt.id ? 'rgba(99, 102, 241, 0.18)' : 'rgba(0, 0, 0, 0.25)',
                    color: eventType === evt.id ? '#e0e7ff' : '#94a3b8',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div>{evt.label}</div>
                  <div style={{ fontSize: '9.5px', color: '#64748b', fontWeight: '400', marginTop: '2px' }}>{evt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* C. Trigger Condition Filter (e.g. status == 1) */}
          <div className="wf-field-group" style={{ marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '4px' }}>
              <Filter size={12} color="#a855f7" />
              <label className="wf-field-label" htmlFor="start-filter-field" style={{ margin: 0 }}>Trigger Filter Condition (Optional)</label>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr 1.2fr', gap: '6px' }}>
              {/* Field */}
              <select
                id="start-filter-field"
                name="filter_field"
                aria-label="Filter Field Column"
                className="wf-select"
                style={{ fontSize: '11px', padding: '6px' }}
                value={filterField}
                onChange={(e) => handleFieldChange('filterField', e.target.value)}
              >
                <option value="">Any Column</option>
                {availableFields.map(f => (
                  <option key={f.name} value={f.name}>{f.name}</option>
                ))}
              </select>

              {/* Operator */}
              <select
                id="start-filter-operator"
                name="filter_operator"
                aria-label="Filter Operator"
                className="wf-select"
                style={{ fontSize: '11px', padding: '6px' }}
                value={filterOperator}
                onChange={(e) => handleFieldChange('filterOperator', e.target.value)}
                disabled={!filterField}
              >
                <option value="==">== (equals)</option>
                <option value="!=">!= (not equals)</option>
                <option value=">">&gt; (greater)</option>
                <option value="<">&lt; (less)</option>
                <option value="is_not_null">is not null</option>
                <option value="changes_to">changes to</option>
              </select>

              {/* Value */}
              <input
                id="start-filter-value"
                name="filter_value"
                aria-label="Filter Match Value"
                type="text"
                className="wf-input"
                style={{ fontSize: '11px', padding: '6px' }}
                value={filterValue}
                onChange={(e) => handleFieldChange('filterValue', e.target.value)}
                placeholder="e.g. 1 or PENDING"
                disabled={!filterField || filterOperator === 'is_not_null'}
              />
            </div>
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '3px' }}>
              e.g. Only trigger when <code>status</code> is updated to <code>1</code>.
            </div>
          </div>

          {/* D. Live Trigger Summary Box */}
          <div style={{
            marginTop: '10px',
            padding: '8px 10px',
            background: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
            borderRadius: '6px',
            fontSize: '11px',
            color: '#c7d2fe',
            lineHeight: 1.4
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontWeight: '600', marginBottom: '2px', color: '#818cf8' }}>
              <CheckCircle2 size={12} />
              <span>Trigger Summary:</span>
            </div>
            <span>
              On <strong>{eventType}</strong> in table <strong>{currentTable || '&lt;select table&gt;'}</strong>
              {filterField && filterValue !== '' ? (
                <> where <code>{filterField} {filterOperator} '{filterValue}'</code></>
              ) : ''}
              , execute this workflow.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
