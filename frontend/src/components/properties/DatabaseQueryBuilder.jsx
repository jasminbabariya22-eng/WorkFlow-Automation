import React, { useState, useEffect, useMemo } from 'react'
import {
  Database,
  Code2,
  Plus,
  Trash2,
  SlidersHorizontal,
  ArrowRight,
  Eye,
  Check,
  FilePlus,
  FileSearch,
  RefreshCw,
  Zap,
  Play,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Link2,
  ShieldAlert,
  Braces
} from 'lucide-react'

export default function DatabaseQueryBuilder({
  nodeType = 'record',
  nodeName = '',
  connectionId,
  data = {},
  availableTables = [],
  availableFields = [],
  onFieldChange,
  onFieldsChange
}) {
  const labelLower = String(data.label || nodeName || '').toLowerCase()
  const subTypeUpper = String(data.subType || data.actionType || data.queryOperation || '').toUpperCase()

  // Detect specific record node types by subType first, fallback to label only if unassigned
  const isCreate = subTypeUpper.includes('CREATE') || subTypeUpper === 'INSERT' || (!subTypeUpper && labelLower.includes('create'))
  const isRead = subTypeUpper.includes('READ') || subTypeUpper.includes('GET') || subTypeUpper === 'SELECT' || (!subTypeUpper && (labelLower.includes('read') || labelLower.includes('fetch') || labelLower.includes('get')))
  const isUpdate = subTypeUpper.includes('UPDATE') || (!subTypeUpper && labelLower.includes('update'))
  const isDelete = subTypeUpper.includes('DELETE') || (!subTypeUpper && labelLower.includes('delete'))

  // Specific Record node vs Generic Database Action
  const isSpecificNode = nodeType === 'record' && (isCreate || isRead || isUpdate || isDelete)
  const lockedOp = isCreate ? 'INSERT' : isRead ? 'SELECT' : isUpdate ? 'UPDATE' : isDelete ? 'DELETE' : null

  // Operation is locked if it's a dedicated record node; otherwise user can toggle
  const operation = isSpecificNode ? lockedOp : (data.queryOperation || data.subType || data.actionType || 'SELECT').toUpperCase().replace('_RECORD', '')
  const mode = data.queryMode || 'visual'
  const currentTable = data.table || data.entity || ''

  // Sync operation into data on mount or change if locked
  useEffect(() => {
    if (lockedOp && data.queryOperation !== lockedOp) {
      onFieldsChange({
        queryOperation: lockedOp,
        subType: `${lockedOp}_RECORD`,
        actionType: `${lockedOp}_RECORD`
      })
    }
  }, [lockedOp, data.queryOperation])

  // Selected Columns for SELECT
  const selectedColumns = useMemo(() => {
    if (Array.isArray(data.selectedColumns)) return data.selectedColumns
    if (Array.isArray(data.retrieveFields)) return data.retrieveFields
    return []
  }, [data.selectedColumns, data.retrieveFields])

  // Field Mappings for UPDATE / INSERT
  const fieldMappings = useMemo(() => {
    if (Array.isArray(data.fieldMappings)) return data.fieldMappings
    if (Array.isArray(data.fieldsToUpdate)) return data.fieldsToUpdate
    return []
  }, [data.fieldMappings, data.fieldsToUpdate])

  // Filters for WHERE clause
  const filters = useMemo(() => {
    if (Array.isArray(data.filters)) return data.filters
    return []
  }, [data.filters])

  // Local state for adding a new field mapping
  const [newMapKey, setNewMapKey] = useState('')
  const [newMapVal, setNewMapVal] = useState('')

  // Local state for adding a new WHERE condition
  const [newFilterCol, setNewFilterCol] = useState('')
  const [newFilterOp, setNewFilterOp] = useState('=')
  const [newFilterVal, setNewFilterVal] = useState('')

  // State for Test SQL execution
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testParamId, setTestParamId] = useState('1')

  const handleTestSql = async () => {
    if (!generatedSql || !generatedSql.trim()) return
    setIsTesting(true)
    setTestResult(null)

    try {
      const res = await fetch('/workflow-studio/test/execute-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: generatedSql,
          connection_id: connectionId,
          params: {
            ...(testParamId ? { entity_id: Number(testParamId), id: Number(testParamId), record_id: Number(testParamId), user_id: Number(testParamId) } : {})
          }
        })
      })
      const json = await res.json()
      setTestResult(json)
    } catch (err) {
      setTestResult({
        status: 'ERROR',
        error: err.message || 'Failed to connect to backend server'
      })
    } finally {
      setIsTesting(false)
    }
  }

  // Helper to safely format values into SQL literals, numbers, functions, or parameters
  const formatSqlValue = (val, colName) => {
    if (val === undefined || val === null || val === '') {
      return `:${colName}`
    }
    const str = String(val).trim()
    if (!str) return `:${colName}`

    // 1. Template variable or parameter marker: {{var}} or :param
    if (str.startsWith(':') || (str.startsWith('{{') && str.endsWith('}}'))) {
      return str
    }

    // 2. Numeric values: 3, 1, 42.5, -1
    if (!isNaN(Number(str)) && !isNaN(parseFloat(str))) {
      return str
    }

    // 3. Already quoted strings: 'value' or "value"
    if ((str.startsWith("'") && str.endsWith("'")) || (str.startsWith('"') && str.endsWith('"'))) {
      return str
    }

    // 4. SQL keywords, boolean constants, and functions
    const upper = str.toUpperCase()
    const sqlKeywords = [
      'NOW()', 'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'CURRENT_TIME',
      'NULL', 'TRUE', 'FALSE', 'DEFAULT', 'LOCALTIMESTAMP', 'LOCALTIME', 'GEN_RANDOM_UUID()'
    ]
    if (sqlKeywords.includes(upper)) {
      return upper
    }

    // 5. String literal: wrap in single quotes and escape single quotes
    const escaped = str.replace(/'/g, "''")
    return `'${escaped}'`
  }

  // Generate Live SQL Preview dynamically
  const generatedSql = useMemo(() => {
    if (data.sql && mode === 'raw') {
      return data.sql
    }

    const tbl = currentTable || 'target_table'
    const whereClauses = filters.map(f => {
      const col = f.field || f.column
      const op = f.operator || '='
      const val = formatSqlValue(f.value, col)
      return `${col} ${op} ${val}`
    })
    const whereStr = whereClauses.length > 0 ? ` WHERE ${whereClauses.join(' AND ')}` : ''

    if (operation === 'SELECT') {
      const cols = selectedColumns.length > 0 ? selectedColumns.join(', ') : '*'
      const orderStr = data.orderBy ? ` ORDER BY ${data.orderBy} ${data.orderDirection || 'ASC'}` : ''
      const limitStr = data.limit ? ` LIMIT ${data.limit}` : ''
      return `SELECT ${cols} FROM ${tbl}${whereStr}${orderStr}${limitStr};`
    }

    if (operation === 'UPDATE') {
      const pkCol = availableFields.find(f => f.is_primary_key || f.primary_key)?.name || 'id'
      if (fieldMappings.length === 0) {
        const nonPkFields = availableFields.filter(f => !f.is_primary_key && !f.primary_key)
        const fallbackCol = nonPkFields.length > 0 ? nonPkFields[0].name : 'status'
        return `UPDATE ${tbl} SET ${fallbackCol} = :${fallbackCol}${whereStr || ` WHERE ${pkCol} = :entity_id`};`
      }
      const setClauses = fieldMappings.map(m => {
        const col = m.field || m.column
        return `${col} = ${formatSqlValue(m.value, col)}`
      })
      return `UPDATE ${tbl} SET ${setClauses.join(', ')}${whereStr || ` WHERE ${pkCol} = :entity_id`};`
    }

    if (operation === 'INSERT') {
      const pkCol = availableFields.find(f => f.is_primary_key || f.primary_key)?.name || ''
      const returningClause = pkCol ? ` RETURNING ${pkCol}` : ' RETURNING *'

      if (fieldMappings.length === 0) {
        const nonPkFields = availableFields.filter(f => !f.is_primary_key && !f.primary_key)
        if (nonPkFields.length > 0) {
          const fallbackCol = nonPkFields[0].name
          return `INSERT INTO ${tbl} (${fallbackCol}) VALUES (:${fallbackCol})${returningClause};`
        }
        // If table has no other columns besides PK or no columns mapped yet, standard SQL DEFAULT VALUES auto-generates PK safely
        return `INSERT INTO ${tbl} DEFAULT VALUES${returningClause};`
      }
      const cols = fieldMappings.map(m => m.field || m.column)
      const vals = fieldMappings.map(m => formatSqlValue(m.value, m.field || m.column))

      let conflictClause = ''
      if (data.conflictResolution === 'DO_NOTHING') {
        conflictClause = ' ON CONFLICT DO NOTHING'
      } else if (data.conflictResolution === 'DO_UPDATE') {
        const targetPk = pkCol || 'id'
        const updateCols = cols.filter(c => c !== targetPk).map(c => `${c} = EXCLUDED.${c}`)
        if (updateCols.length > 0) {
          conflictClause = ` ON CONFLICT (${targetPk}) DO UPDATE SET ${updateCols.join(', ')}`
        } else {
          conflictClause = ` ON CONFLICT (${targetPk}) DO NOTHING`
        }
      }

      return `INSERT INTO ${tbl} (${cols.join(', ')}) VALUES (${vals.join(', ')})${conflictClause}${returningClause};`
    }

    if (operation === 'DELETE') {
      const pkCol = availableFields.find(f => f.is_primary_key || f.primary_key)?.name || 'id'
      return `DELETE FROM ${tbl}${whereStr || ` WHERE ${pkCol} = :entity_id`};`
    }

    return `SELECT * FROM ${tbl}${whereStr};`
  }, [mode, operation, currentTable, selectedColumns, fieldMappings, filters, availableFields, data.orderBy, data.orderDirection, data.limit, data.sql, data.conflictResolution])

  // Sync generated SQL into data.sql if in visual mode
  useEffect(() => {
    if (mode === 'visual' && generatedSql && generatedSql !== data.sql) {
      onFieldChange('sql', generatedSql)
    }
  }, [generatedSql, mode])

  // Helper: toggle column selection (SELECT)
  const handleToggleColumn = (colName) => {
    let next
    if (selectedColumns.includes(colName)) {
      next = selectedColumns.filter(c => c !== colName)
    } else {
      next = [...selectedColumns, colName]
    }
    onFieldsChange({
      selectedColumns: next,
      retrieveFields: next
    })
  }

  const handleSelectAllColumns = () => {
    const all = availableFields.map(f => f.name)
    onFieldsChange({
      selectedColumns: all,
      retrieveFields: all
    })
  }

  const handleClearColumns = () => {
    onFieldsChange({
      selectedColumns: [],
      retrieveFields: []
    })
  }

  // Helper: auto-fill sensible default values for all table fields
  const handleAutoFillDefaults = () => {
    const mappings = []
    availableFields.forEach(f => {
      const isPk = f.is_primary_key || f.primary_key
      if (isPk) return // omit PK to let sequence auto-increment

      const name = f.name.toLowerCase()
      const type = String(f.data_type || f.type || '').toLowerCase()

      let val = ''
      if (type.includes('bool')) {
        val = 'TRUE'
      } else if (name.includes('start_date') || name.includes('from_date')) {
        val = 'CURRENT_DATE'
      } else if (name.includes('end_date') || name.includes('to_date')) {
        val = 'CURRENT_DATE'
      } else if (type.includes('time') || name.includes('_at')) {
        val = 'NOW()'
      } else if (name === 'status') {
        val = operation === 'UPDATE' ? '2' : 'PENDING'
      } else if (name.includes('user') || name.includes('employee')) {
        val = '{{user_id}}'
      } else if (name.includes('reason') || name.includes('description') || name.includes('title') || name.includes('note')) {
        val = 'Annual Vacation'
      } else if (name === 'days' || name === 'quantity' || name === 'count') {
        val = '3'
      } else if (name.includes('type_id')) {
        val = '1'
      } else if (name.includes('_id')) {
        val = '1'
      } else if (f.nullable === false) {
        val = `:${f.name}`
      }

      if (val) {
        mappings.push({ field: f.name, value: val })
      }
    })

    onFieldsChange({
      fieldMappings: mappings,
      fieldsToUpdate: mappings
    })
  }

  const handleClearAllMappings = () => {
    onFieldsChange({
      fieldMappings: [],
      fieldsToUpdate: []
    })
  }

  // Helper: direct field value update by column name
  const handleUpdateFieldValue = (fieldName, val) => {
    let next
    if (val === '' || val === undefined) {
      next = fieldMappings.filter(item => (item.field || item.column) !== fieldName)
    } else {
      const exists = fieldMappings.some(item => (item.field || item.column) === fieldName)
      if (exists) {
        next = fieldMappings.map(item => (item.field || item.column) === fieldName ? { ...item, field: fieldName, value: val } : item)
      } else {
        next = [...fieldMappings, { field: fieldName, value: val }]
      }
    }
    onFieldsChange({
      fieldMappings: next,
      fieldsToUpdate: next
    })
  }

  // Helper: add field mapping (UPDATE / INSERT)
  const handleAddMapping = (key = newMapKey, val = newMapVal) => {
    if (!key) return
    handleUpdateFieldValue(key, val || `:${key}`)
    setNewMapKey('')
    setNewMapVal('')
  }

  const handleRemoveMapping = (index) => {
    const next = fieldMappings.filter((_, idx) => idx !== index)
    onFieldsChange({
      fieldMappings: next,
      fieldsToUpdate: next
    })
  }

  // Helper: add WHERE filter
  const handleAddFilter = (col = newFilterCol, op = newFilterOp, val = newFilterVal) => {
    if (!col) return
    const next = [...filters, {
      field: col,
      operator: op,
      value: val || `:${col}`
    }]
    onFieldChange('filters', next)
    setNewFilterCol('')
    setNewFilterVal('')
  }

  const handleRemoveFilter = (index) => {
    const next = filters.filter((_, idx) => idx !== index)
    onFieldChange('filters', next)
  }

  return (
    <div className="wf-query-builder">
      {/* 1. DEDICATED HEADER PER NODE TYPE WITH VISUAL / RAW SQL TOGGLE */}
      <div className="wf-qb-header-row mb-3 flex items-center justify-between">
        {isCreate && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <FilePlus size={15} />
            <span>CREATE RECORD</span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 ml-1">
              INSERT
            </span>
          </div>
        )}

        {isRead && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-400">
            <FileSearch size={15} />
            <span>READ RECORD</span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/40 ml-1">
              SELECT
            </span>
          </div>
        )}

        {isUpdate && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
            <RefreshCw size={15} />
            <span>UPDATE RECORD</span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 ml-1">
              UPDATE
            </span>
          </div>
        )}

        {isDelete && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-400">
            <Trash2 size={15} />
            <span>DELETE RECORD</span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 ml-1">
              DELETE
            </span>
          </div>
        )}

        {!isSpecificNode && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400">
            <Database size={14} />
            <span>DATABASE ACTION</span>
          </div>
        )}

        <div className="wf-mode-toggle-group">
          <button
            type="button"
            className={`wf-mode-toggle-btn ${mode === 'visual' ? 'active' : ''}`}
            onClick={() => onFieldChange('queryMode', 'visual')}
            title="Visual Query Designer"
          >
            <SlidersHorizontal size={11} />
            <span>Visual</span>
          </button>
          <button
            type="button"
            className={`wf-mode-toggle-btn ${mode === 'raw' ? 'active' : ''}`}
            onClick={() => onFieldChange('queryMode', 'raw')}
            title="Raw SQL Editor"
          >
            <Code2 size={11} />
            <span>Raw SQL</span>
          </button>
        </div>
      </div>

      {mode === 'visual' ? (
        <>
          {/* 2. SQL OPERATION SELECTOR PILLS (SHOWN ONLY ON GENERAL DATABASE ACTION) */}
          {!isSpecificNode && (
            <div className="wf-field-group mb-3">
              <label className="wf-field-label">SQL Operation</label>
              <div className="wf-op-pills">
                {['SELECT', 'UPDATE', 'INSERT', 'DELETE'].map(op => {
                  const isSelected = operation === op
                  return (
                    <button
                      key={op}
                      type="button"
                      className={`wf-op-pill ${isSelected ? 'active ' + op.toLowerCase() : ''}`}
                      onClick={() => {
                        onFieldsChange({
                          queryOperation: op,
                          subType: `${op}_RECORD`,
                          actionType: `${op}_RECORD`
                        })
                      }}
                    >
                      {op}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* 3. TARGET TABLE SELECTOR */}
          <div className="wf-field-group">
            <label className="wf-field-label">Database Table</label>
            <select
              className="wf-select"
              value={currentTable}
              onChange={(e) => {
                const val = e.target.value
                onFieldsChange({
                  table: val,
                  entity: val,
                  selectedColumns: [],
                  fieldMappings: [],
                  filters: []
                })
              }}
            >
              <option value="">-- Choose Database Table --</option>
              {availableTables.map(t => (
                <option key={t.name} value={t.name}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* ============================================================ */}
          {/* SECTION A: READ RECORD (SELECT) -> COLUMNS PICKER            */}
          {/* ============================================================ */}
          {operation === 'SELECT' && (
            <div className="wf-field-group">
              <div className="flex items-center justify-between mb-1">
                <label className="wf-field-label mb-0">Columns to Retrieve</label>
                {availableFields.length > 0 && (
                  <div className="flex gap-2 text-[10px]">
                    <button
                      type="button"
                      className="text-cyan-400 hover:underline"
                      onClick={handleSelectAllColumns}
                    >
                      All ({availableFields.length})
                    </button>
                    <span className="text-slate-600">|</span>
                    <button
                      type="button"
                      className="text-slate-400 hover:underline"
                      onClick={handleClearColumns}
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>

              {availableFields.length > 0 ? (
                <div className="wf-qb-column-chips">
                  {availableFields.map(f => {
                    const isChecked = selectedColumns.includes(f.name)
                    return (
                      <button
                        key={f.name}
                        type="button"
                        className={`wf-col-chip ${isChecked ? 'selected' : ''}`}
                        onClick={() => handleToggleColumn(f.name)}
                      >
                        {isChecked && <Check size={10} className="stroke-[3]" />}
                        <span>{f.name}</span>
                        {f.is_primary_key && <span className="wf-chip-pk">PK</span>}
                      </button>
                    )
                  })}
                </div>
              ) : (
                <div className="text-[11px] text-slate-500 italic p-2 bg-slate-900/50 rounded border border-slate-800">
                  {currentTable ? 'Select columns above or leave empty for * (all columns)' : 'Select a database table first to load columns.'}
                </div>
              )}
            </div>
          )}

          {/* ============================================================ */}
          {/* SECTION B: UPDATE RECORD (UPDATE) -> WHERE FILTER FIRST      */}
          {/* ============================================================ */}
          {operation === 'UPDATE' && (
            <div className="wf-field-group">
              <div className="flex items-center justify-between mb-1">
                <label className="wf-field-label mb-0">Target Record Filter (WHERE)</label>
                <span className="text-[10px] text-slate-400">Specifies which record to update</span>
              </div>

              {/* Quick helper button to target entity_id */}
              <div className="mb-2">
                <button
                  type="button"
                  className="wf-token-chip"
                  onClick={() => {
                    const idCol = availableFields.find(f => f.is_primary_key)?.name || 'id'
                    handleAddFilter(idCol, '=', '{{entity_id}}')
                  }}
                  title="Add filter WHERE id = {{entity_id}}"
                >
                  + Target Current Record (id = &#123;&#123;entity_id&#125;&#125;)
                </button>
              </div>

              {filters.length > 0 && (
                <div className="wf-qb-filter-list mb-2">
                  {filters.map((f, idx) => (
                    <div key={idx} className="wf-qb-filter-row">
                      <span className="wf-filter-col">{f.field || f.column}</span>
                      <span className="wf-filter-op">{f.operator || '='}</span>
                      <span className="wf-filter-val">{f.value}</span>
                      <button
                        type="button"
                        className="wf-mapping-del"
                        onClick={() => handleRemoveFilter(idx)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="wf-qb-add-filter-grid">
                {availableFields.length > 0 ? (
                  <select
                    className="wf-select text-xs font-mono"
                    value={newFilterCol}
                    onChange={(e) => setNewFilterCol(e.target.value)}
                  >
                    <option value="">-- Column --</option>
                    {availableFields.map(f => (
                      <option key={f.name} value={f.name}>{f.name}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    className="wf-input text-xs"
                    placeholder="Column"
                    value={newFilterCol}
                    onChange={(e) => setNewFilterCol(e.target.value)}
                  />
                )}

                <select
                  className="wf-select text-xs font-mono"
                  value={newFilterOp}
                  onChange={(e) => setNewFilterOp(e.target.value)}
                >
                  <option value="=">=</option>
                  <option value="!=">!=</option>
                  <option value=">">&gt;</option>
                  <option value="<">&lt;</option>
                  <option value=">=">&gt;=</option>
                  <option value="<=">&lt;=</option>
                  <option value="LIKE">LIKE</option>
                  <option value="IN">IN</option>
                </select>

                <input
                  type="text"
                  className="wf-input text-xs"
                  placeholder="Value e.g. {{entity_id}}"
                  value={newFilterVal}
                  onChange={(e) => setNewFilterVal(e.target.value)}
                />

                <button
                  type="button"
                  className="wf-add-action-btn"
                  onClick={() => handleAddFilter()}
                >
                  <Plus size={11} />
                  <span>Filter</span>
                </button>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* SECTION C: OPTION B - FULL SCHEMA GRID (INSERT & UPDATE)     */}
          {/* ============================================================ */}
          {(operation === 'UPDATE' || operation === 'INSERT') && (
            <div className="wf-field-group">
              {/* Header toolbar with schema stats and actions */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div>
                  <label className="wf-field-label" style={{ marginBottom: '2px', color: '#e2e8f0', fontWeight: '600', fontSize: '11px' }}>
                    {operation === 'UPDATE' ? 'Fields to Modify (SET)' : 'Fields to Insert (Schema Grid)'}
                  </label>
                  {availableFields.length > 0 && (
                    <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'monospace' }}>
                      {availableFields.length} columns &bull; {availableFields.filter(f => f.nullable === false && !f.is_primary_key && !f.primary_key && !f.has_default).length} required &bull; {availableFields.filter(f => f.has_default).length} defaults
                    </div>
                  )}
                </div>

                {availableFields.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <button
                      type="button"
                      className="wf-autofill-btn"
                      onClick={handleAutoFillDefaults}
                      title="Pre-fill sensible default values for required columns"
                    >
                      <Zap size={11} fill="currentColor" />
                      <span>Auto-Fill Defaults</span>
                    </button>
                    <button
                      type="button"
                      className="wf-clear-btn"
                      onClick={handleClearAllMappings}
                      title="Clear all fields"
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>

              {availableFields.length > 0 ? (
                <div className="wf-schema-grid-container">
                  {/* Grid Table Header */}
                  <div className="wf-schema-grid-header">
                    <span style={{ width: '44%' }}>Column & Type</span>
                    <span style={{ width: '54%' }}>Value / Expression</span>
                  </div>

                  {/* Grid Table Rows */}
                  <div className="wf-schema-list">
                    {availableFields.map(f => {
                      const isPk = f.is_primary_key || f.primary_key
                      const isFk = Boolean(f.foreign_key)
                      const fkTarget = typeof f.foreign_key === 'object' && f.foreign_key
                        ? `${f.foreign_key.referred_table || ''}.${f.foreign_key.referred_column || ''}`
                        : String(f.foreign_key || '')

                      const currentVal = fieldMappings.find(m => (m.field || m.column) === f.name)?.value || ''
                      const typeLower = String(f.data_type || f.type || '').toLowerCase()
                      const isBool = typeLower.includes('bool')
                      const isDateOrTime = typeLower.includes('date') || typeLower.includes('time') || f.name.includes('_at')
                      const isStatus = f.name.toLowerCase().includes('status')
                      const hasDefault = f.has_default
                      const isRequired = f.nullable === false && !isPk && !hasDefault

                      return (
                        <div
                          key={f.name}
                          className={`wf-schema-row ${currentVal ? 'has-value' : ''}`}
                        >
                          {/* Column details (Left) */}
                          <div className="wf-schema-col-info">
                            <div className="wf-schema-col-top">
                              <span className={`wf-schema-col-name ${
                                isRequired ? 'is-req' : isPk ? 'is-pk' : isFk ? 'is-fk' : ''
                              }`}>
                                {f.name}
                              </span>
                              {isPk && <span className="wf-badge-pk">PK</span>}
                              {isFk && (
                                <span className="wf-badge-fk" title={`FK referencing ${fkTarget}`}>
                                  <Link2 size={8} />
                                  <span>FK</span>
                                </span>
                              )}
                              {isRequired && <span className="wf-badge-req">Required</span>}
                              {hasDefault && !isPk && <span className="wf-badge-def">Default</span>}
                            </div>
                            <div className="wf-schema-col-type" title={`${f.data_type || f.type || 'any'}${isFk && fkTarget ? ` → ${fkTarget}` : ''}`}>
                              {f.data_type || f.type || 'any'}
                              {isFk && fkTarget ? ` → ${fkTarget}` : ''}
                            </div>
                          </div>

                          {/* Value Input and Presets (Right) */}
                          <div className="wf-schema-input-cell">
                            <div className="wf-schema-input-wrapper">
                              <input
                                type="text"
                                className={`wf-schema-input ${currentVal ? 'has-value' : isRequired ? 'is-required-empty' : ''}`}
                                placeholder={
                                  isPk && isCreate
                                    ? '(Auto-generated sequence)'
                                    : isDateOrTime
                                    ? 'NOW() or CURRENT_DATE'
                                    : isStatus
                                    ? '1 or "PENDING"'
                                    : 'Value or {{var}}'
                                }
                                value={currentVal}
                                onChange={(e) => handleUpdateFieldValue(f.name, e.target.value)}
                              />

                              {currentVal && (
                                <button
                                  type="button"
                                  className="wf-schema-input-clear"
                                  onClick={() => handleUpdateFieldValue(f.name, '')}
                                  title="Clear value"
                                >
                                  ×
                                </button>
                              )}
                            </div>

                            {/* Preset Buttons for specific column types */}
                            <div className="wf-schema-presets">
                              {isBool && (
                                <>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn emerald ${currentVal === 'TRUE' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, 'TRUE')}
                                  >
                                    True
                                  </button>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn ${currentVal === 'FALSE' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, 'FALSE')}
                                  >
                                    False
                                  </button>
                                </>
                              )}

                              {isStatus && (
                                <>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn ${currentVal === '1' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, '1')}
                                  >
                                    1 (Pending)
                                  </button>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn ${currentVal === '2' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, '2')}
                                  >
                                    2 (Approved)
                                  </button>
                                </>
                              )}

                              {isDateOrTime && (
                                <>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn amber ${currentVal === 'NOW()' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, 'NOW()')}
                                  >
                                    NOW()
                                  </button>
                                  <button
                                    type="button"
                                    className={`wf-preset-btn amber ${currentVal === 'CURRENT_DATE' ? 'active' : ''}`}
                                    onClick={() => handleUpdateFieldValue(f.name, 'CURRENT_DATE')}
                                  >
                                    TODAY
                                  </button>
                                </>
                              )}

                              {isPk && isCreate && !currentVal && (
                                <span style={{ fontSize: '9px', color: '#64748b', fontStyle: 'italic' }}>
                                  (Auto sequence if blank)
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                /* Fallback if no schema columns are loaded */
                <div>
                  {fieldMappings.length > 0 && (
                    <div className="wf-field-mapping-list mb-2">
                      {fieldMappings.map((m, idx) => (
                        <div key={idx} className="wf-mapping-row">
                          <span className="wf-map-key">{m.field || m.column}</span>
                          <span className="wf-map-arrow">=</span>
                          <span className="wf-map-val">{m.value}</span>
                          <button
                            type="button"
                            className="wf-mapping-del"
                            onClick={() => handleRemoveMapping(idx)}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="wf-add-mapping-box">
                    <input
                      type="text"
                      className="wf-input text-xs"
                      placeholder="Column name (e.g. status)"
                      value={newMapKey}
                      onChange={(e) => setNewMapKey(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddMapping()
                      }}
                    />
                    <input
                      type="text"
                      className="wf-input text-xs"
                      placeholder="Value e.g. 1, 'ACTIVE', {{user_id}}"
                      value={newMapVal}
                      onChange={(e) => setNewMapVal(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddMapping()
                      }}
                    />
                    <button
                      type="button"
                      className="wf-add-action-btn"
                      onClick={() => handleAddMapping()}
                      title="Add field mapping"
                    >
                      <Plus size={11} />
                      <span>Set</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 4. Conflict Resolution (ON CONFLICT) for Create Record (INSERT) */}
              {isCreate && (
                <div style={{ marginTop: '10px', padding: '8px 10px', background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <label style={{ margin: 0, fontSize: '11px', fontWeight: '600', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <ShieldAlert size={13} style={{ color: '#fbbf24' }} />
                      <span>Duplicate Conflict Rule</span>
                    </label>
                    <span style={{ fontSize: '9px', color: '#64748b', fontFamily: 'monospace' }}>ON CONFLICT</span>
                  </div>
                  <select
                    className="wf-select"
                    style={{ width: '100%', fontSize: '11px', fontFamily: 'monospace', marginTop: '4px' }}
                    value={data.conflictResolution || 'FAIL'}
                    onChange={(e) => onFieldChange('conflictResolution', e.target.value)}
                  >
                    <option value="FAIL">Default (Fail on duplicate)</option>
                    <option value="DO_NOTHING">DO NOTHING (Skip insert if exists)</option>
                    <option value="DO_UPDATE">DO UPDATE (Upsert / Overwrite)</option>
                  </select>
                </div>
              )}
            </div>
          )}

          {/* ============================================================ */}
          {/* SECTION D: READ RECORD / DELETE RECORD -> WHERE FILTERS     */}
          {/* ============================================================ */}
          {(operation === 'SELECT' || operation === 'DELETE') && (
            <div className="wf-field-group">
              <label className="wf-field-label">WHERE Filter Conditions</label>

              {/* Quick helper for ID filter */}
              <div className="mb-2">
                <button
                  type="button"
                  className="wf-token-chip"
                  onClick={() => {
                    const idCol = availableFields.find(f => f.is_primary_key)?.name || 'id'
                    handleAddFilter(idCol, '=', '{{entity_id}}')
                  }}
                  title="Add filter WHERE id = {{entity_id}}"
                >
                  + Match Record ID (id = &#123;&#123;entity_id&#125;&#125;)
                </button>
              </div>

              {filters.length > 0 && (
                <div className="wf-qb-filter-list mb-2">
                  {filters.map((f, idx) => (
                    <div key={idx} className="wf-qb-filter-row">
                      <span className="wf-filter-col">{f.field || f.column}</span>
                      <span className="wf-filter-op">{f.operator || '='}</span>
                      <span className="wf-filter-val">{f.value}</span>
                      <button
                        type="button"
                        className="wf-mapping-del"
                        onClick={() => handleRemoveFilter(idx)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="wf-qb-add-filter-grid">
                {availableFields.length > 0 ? (
                  <select
                    className="wf-select text-xs font-mono"
                    value={newFilterCol}
                    onChange={(e) => setNewFilterCol(e.target.value)}
                  >
                    <option value="">-- Column --</option>
                    {availableFields.map(f => (
                      <option key={f.name} value={f.name}>{f.name}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    className="wf-input text-xs"
                    placeholder="Column"
                    value={newFilterCol}
                    onChange={(e) => setNewFilterCol(e.target.value)}
                  />
                )}

                <select
                  className="wf-select text-xs font-mono"
                  value={newFilterOp}
                  onChange={(e) => setNewFilterOp(e.target.value)}
                >
                  <option value="=">=</option>
                  <option value="!=">!=</option>
                  <option value=">">&gt;</option>
                  <option value="<">&lt;</option>
                  <option value=">=">&gt;=</option>
                  <option value="<=">&lt;=</option>
                  <option value="LIKE">LIKE</option>
                  <option value="IN">IN</option>
                </select>

                <input
                  type="text"
                  className="wf-input text-xs"
                  placeholder="Value e.g. {{entity_id}}"
                  value={newFilterVal}
                  onChange={(e) => setNewFilterVal(e.target.value)}
                />

                <button
                  type="button"
                  className="wf-add-action-btn"
                  onClick={() => handleAddFilter()}
                >
                  <Plus size={11} />
                  <span>Filter</span>
                </button>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* SECTION E: ORDER & LIMIT (FOR SELECT ONLY)                   */}
          {/* ============================================================ */}
          {operation === 'SELECT' && (
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div className="wf-field-group mb-0">
                <label className="wf-field-label">Order By</label>
                <select
                  className="wf-select text-xs"
                  value={data.orderBy || ''}
                  onChange={(e) => onFieldChange('orderBy', e.target.value)}
                >
                  <option value="">-- Default Order --</option>
                  {availableFields.map(f => (
                    <option key={f.name} value={f.name}>{f.name}</option>
                  ))}
                </select>
              </div>

              <div className="wf-field-group mb-0">
                <label className="wf-field-label">Limit Rows</label>
                <input
                  type="number"
                  className="wf-input text-xs"
                  placeholder="e.g. 50"
                  value={data.limit || ''}
                  onChange={(e) => onFieldChange('limit', e.target.value ? parseInt(e.target.value) : '')}
                />
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* SECTION F: OUTPUT VARIABLE NAME                             */}
          {/* ============================================================ */}
          <div className="wf-field-group mt-3">
            <div className="flex items-center justify-between">
              <label className="wf-field-label mb-0">
                {isCreate
                  ? 'New Record ID Variable'
                  : isRead
                  ? 'Output Variable for Fetched Record'
                  : 'Execution Result Variable'}
              </label>
              <span className="text-[10px] text-slate-400">
                {isCreate ? 'Stores generated primary key' : 'Available in downstream nodes'}
              </span>
            </div>
            <input
              type="text"
              className="wf-input font-mono text-xs mt-1"
              placeholder={isCreate ? 'created_id' : isRead ? 'record_data' : 'result'}
              value={data.outputVariable || (isCreate ? 'created_id' : isRead ? 'record_data' : 'query_result')}
              onChange={(e) => onFieldChange('outputVariable', e.target.value)}
            />
            <div className="text-[10px] text-slate-500 mt-0.5">
              {isCreate && <>Reference the new ID in subsequent nodes via <code>&#123;&#123;{data.outputVariable || 'created_id'}&#125;&#125;</code></>}
              {isRead && <>Access fetched columns via <code>&#123;&#123;{data.outputVariable || 'record_data'}.column_name&#125;&#125;</code></>}
            </div>
          </div>
        </>
      ) : (
        /* RAW SQL MODE (FOR DATABASE ACTION & SPECIFIC NODES) */
        <div className="wf-field-group mt-2">
          <div className="flex items-center justify-between mb-1">
            <label className="wf-field-label mb-0">Raw SQL Statement</label>
            <span className="text-[10px] font-mono text-cyan-400">
              {isCreate ? 'INSERT' : isRead ? 'SELECT' : isUpdate ? 'UPDATE' : isDelete ? 'DELETE' : 'SQL'}
            </span>
          </div>
          <textarea
            className="wf-textarea font-mono text-xs"
            rows={6}
            value={data.sql || ''}
            onChange={(e) => onFieldChange('sql', e.target.value)}
            placeholder={
              isCreate
                ? `INSERT INTO ${currentTable || 'test'} (status) VALUES ('PENDING') RETURNING id;`
                : isRead
                ? `SELECT * FROM ${currentTable || 'test'} WHERE id = :entity_id;`
                : isUpdate
                ? `UPDATE ${currentTable || 'test'} SET status = 'APPROVED' WHERE id = :entity_id;`
                : isDelete
                ? `DELETE FROM ${currentTable || 'test'} WHERE id = :entity_id;`
                : "UPDATE leave_balances SET balance = balance - :days WHERE employee_id = :user_id;"
            }
          />
          <div className="text-[10px] text-slate-500 mt-1">
            Tip: Bind parameters with <code className="text-cyan-400 font-mono">:variable_name</code> (e.g. <code>:entity_id</code>, <code>:user_id</code>, <code>:id</code>)
          </div>

          {/* Output Variable Configuration in Raw SQL Mode */}
          <div className="wf-field-group mt-3">
            <div className="flex items-center justify-between">
              <label className="wf-field-label mb-0">
                {isCreate
                  ? 'New Record ID Variable'
                  : isRead
                  ? 'Output Variable for Fetched Record'
                  : 'Execution Result Variable'}
              </label>
              <span className="text-[10px] text-slate-400">
                {isCreate ? 'Stores generated primary key' : 'Available in downstream nodes'}
              </span>
            </div>
            <input
              type="text"
              className="wf-input font-mono text-xs mt-1"
              placeholder={isCreate ? 'created_id' : isRead ? 'record_data' : 'query_result'}
              value={data.outputVariable || (isCreate ? 'created_id' : isRead ? 'record_data' : 'query_result')}
              onChange={(e) => onFieldChange('outputVariable', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* 9. LIVE GENERATED SQL PREVIEW & TEST QUERY RUNNER */}
      <div className="wf-qb-preview-box mt-3">
        <div className="wf-qb-preview-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="flex items-center gap-1.5">
            <Eye size={12} className="text-emerald-400" />
            <span className="font-semibold text-[11px]">LIVE SQL PREVIEW</span>
            <span className="text-[9px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded ml-1">
              {mode === 'visual' ? 'Auto-generated' : 'Custom SQL'}
            </span>
          </div>

          {/* Test Query Button */}
          <button
            type="button"
            className="wf-btn wf-btn-sm"
            style={{
              background: isTesting ? '#334155' : 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
              color: '#ffffff',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: '600',
              borderRadius: '4px',
              cursor: isTesting ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
            onClick={handleTestSql}
            disabled={isTesting || !generatedSql}
            title="Execute test query against connected database"
          >
            {isTesting ? <Loader2 size={12} className="animate-spin" /> : <Play size={11} fill="currentColor" />}
            <span>{isTesting ? 'Testing...' : 'Test Query'}</span>
          </button>
        </div>

        <pre className="wf-qb-sql-text">
          <code>{generatedSql}</code>
        </pre>

        {/* Optional Test Parameter Config (Shown only for SELECT/UPDATE/DELETE where record ID is required) */}
        {operation !== 'INSERT' && (
          <div style={{ padding: '4px 8px', background: 'rgba(15, 23, 42, 0.6)', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10px' }}>
            <span style={{ color: '#94a3b8' }}>Test parameter <code>:entity_id</code> (Target Record ID):</span>
            <input
              type="number"
              className="wf-input font-mono"
              style={{ width: '60px', padding: '1px 4px', fontSize: '10px', height: '20px' }}
              value={testParamId}
              onChange={(e) => setTestParamId(e.target.value)}
              placeholder="1"
              title="Existing Record ID used for :entity_id filter during test"
            />
          </div>
        )}

        {/* Live Test Execution Result Display */}
        {testResult && (
          <div style={{
            marginTop: '8px',
            background: testResult.status === 'SUCCESS' ? 'rgba(6, 78, 59, 0.25)' : 'rgba(127, 29, 29, 0.25)',
            border: `1px solid ${testResult.status === 'SUCCESS' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
            borderRadius: '6px',
            padding: '8px 10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600' }}>
                {testResult.status === 'SUCCESS' ? (
                  <CheckCircle2 size={13} className="text-emerald-400" />
                ) : (
                  <AlertCircle size={13} className="text-rose-400" />
                )}
                <span style={{ color: testResult.status === 'SUCCESS' ? '#34d399' : '#f87171' }}>
                  {testResult.status === 'SUCCESS' ? 'Query Executed Successfully' : 'Execution Failed'}
                </span>
              </div>
              {testResult.execution_time_ms && (
                <span style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'monospace' }}>
                  {testResult.execution_time_ms} ms
                </span>
              )}
            </div>

            {testResult.status === 'SUCCESS' ? (
              <div>
                {/* SELECT RESULTS */}
                {testResult.operation === 'SELECT' && (
                  <>
                    <div style={{ fontSize: '10px', color: '#a7f3d0', marginBottom: '4px' }}>
                      Returned {testResult.row_count} {testResult.row_count === 1 ? 'row' : 'rows'}:
                    </div>
                    {testResult.rows && testResult.rows.length > 0 ? (
                      <div style={{ overflowX: 'auto', maxHeight: '160px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.08)' }}>
                        <table style={{ width: '100%', fontSize: '10px', borderCollapse: 'collapse', textAlign: 'left', fontFamily: 'monospace' }}>
                          <thead>
                            <tr style={{ background: 'rgba(15, 23, 42, 0.9)', color: '#cbd5e1' }}>
                              {testResult.columns.map(c => (
                                <th key={c} style={{ padding: '3px 6px', borderBottom: '1px solid rgba(255,255,255,0.1)', whiteSpace: 'nowrap' }}>
                                  {c}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {testResult.rows.map((row, rIdx) => (
                              <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent', color: '#e2e8f0' }}>
                                {testResult.columns.map(c => (
                                  <td key={c} style={{ padding: '3px 6px', borderBottom: '1px solid rgba(255,255,255,0.04)', whiteSpace: 'nowrap' }}>
                                    {row[c] !== null && row[c] !== undefined ? String(row[c]) : <span style={{ color: '#64748b' }}>NULL</span>}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div style={{ fontSize: '11px', color: '#94a3b8', fontStyle: 'italic', padding: '4px 0' }}>
                        No records matched your filter criteria.
                      </div>
                    )}
                  </>
                )}

                {/* INSERT / UPDATE / DELETE RESULTS */}
                {testResult.operation !== 'SELECT' && (
                  <div style={{ fontSize: '11px', color: '#e2e8f0' }}>
                    <span>Rows affected: <strong style={{ color: '#34d399' }}>{testResult.rows_affected ?? 1}</strong></span>
                    {testResult.rows && testResult.rows.length > 0 && (
                      <div style={{ marginTop: '4px', fontSize: '10px', color: '#94a3b8' }}>
                        Returned: <code>{JSON.stringify(testResult.rows[0])}</code>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              /* ERROR DISPLAY */
              <div style={{ fontSize: '11px', color: '#fca5a5', whiteSpace: 'pre-wrap', fontFamily: 'monospace', maxHeight: '120px', overflowY: 'auto' }}>
                {testResult.error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
