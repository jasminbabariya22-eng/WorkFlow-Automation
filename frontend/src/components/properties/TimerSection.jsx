import React from 'react'
import { Clock, Hourglass, Calendar, Zap, AlertCircle } from 'lucide-react'

export default function TimerSection({
  data,
  handleFieldChange,
  handleFieldsChange
}) {
  const timerType = data.timerType || 'duration' // 'duration', 'dateTime', 'expression'
  const durationValue = data.durationValue !== undefined ? data.durationValue : (data.duration || 15)
  const durationUnit = data.durationUnit || 'minutes'
  const targetDate = data.targetDate || ''
  const timerExpression = data.timerExpression || ''
  const interruptible = data.interruptible || false

  return (
    <>
      <div className="wf-section-divider">TIMER CONFIGURATION</div>

      {/* Timer Type Selector */}
      <div className="wf-field-group">
        <label className="wf-field-label">Timer Mode</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginTop: '4px' }}>
          <button
            type="button"
            className={`wf-btn wf-btn-sm ${timerType === 'duration' ? 'wf-btn-primary' : 'wf-btn-outline'}`}
            style={{ fontSize: '11px', padding: '6px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
            onClick={() => handleFieldChange('timerType', 'duration')}
          >
            <Clock size={12} />
            <span>Duration</span>
          </button>
          <button
            type="button"
            className={`wf-btn wf-btn-sm ${timerType === 'dateTime' ? 'wf-btn-primary' : 'wf-btn-outline'}`}
            style={{ fontSize: '11px', padding: '6px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
            onClick={() => handleFieldChange('timerType', 'dateTime')}
          >
            <Calendar size={12} />
            <span>Fixed Date</span>
          </button>
          <button
            type="button"
            className={`wf-btn wf-btn-sm ${timerType === 'expression' ? 'wf-btn-primary' : 'wf-btn-outline'}`}
            style={{ fontSize: '11px', padding: '6px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
            onClick={() => handleFieldChange('timerType', 'expression')}
          >
            <Zap size={12} />
            <span>Dynamic</span>
          </button>
        </div>
      </div>

      {/* 1. DURATION MODE */}
      {timerType === 'duration' && (
        <div className="wf-field-group">
          <label className="wf-field-label">Delay Duration</label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '8px' }}>
            <input
              type="number"
              min="1"
              max="9999"
              className="wf-input"
              value={durationValue}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10) || 1
                handleFieldsChange({
                  durationValue: val,
                  duration: val
                })
              }}
              placeholder="15"
            />
            <select
              className="wf-select"
              value={durationUnit}
              onChange={(e) => handleFieldChange('durationUnit', e.target.value)}
            >
              <option value="seconds">Seconds (s)</option>
              <option value="minutes">Minutes (m)</option>
              <option value="hours">Hours (h)</option>
              <option value="days">Days (d)</option>
            </select>
          </div>
          <p className="wf-hint-text" style={{ marginTop: '6px' }}>
            Workflow execution will pause for <strong>{durationValue} {durationUnit}</strong> before proceeding to the next node.
          </p>
        </div>
      )}

      {/* 2. FIXED DATE / TIME MODE */}
      {timerType === 'dateTime' && (
        <div className="wf-field-group">
          <label className="wf-field-label">Target Date & Time</label>
          <input
            type="datetime-local"
            className="wf-input font-mono"
            value={targetDate}
            onChange={(e) => handleFieldChange('targetDate', e.target.value)}
          />
          <p className="wf-hint-text" style={{ marginTop: '6px' }}>
            Workflow pauses until the exact timestamp specified is reached.
          </p>
        </div>
      )}

      {/* 3. DYNAMIC EXPRESSION MODE */}
      {timerType === 'expression' && (
        <div className="wf-field-group">
          <label className="wf-field-label">Dynamic Duration / Date Variable</label>
          <input
            type="text"
            className="wf-input font-mono"
            value={timerExpression}
            onChange={(e) => handleFieldChange('timerExpression', e.target.value)}
            placeholder="{{record.sla_deadline}} or {{workflow.delay_hours}}"
          />
          <p className="wf-hint-text" style={{ marginTop: '6px' }}>
            Supports JSON variables from previous nodes or record fields.
          </p>
        </div>
      )}

      {/* Advanced Settings */}
      <div className="wf-section-divider">ADVANCED SETTINGS</div>

      <div className="wf-field-group">
        <label className="wf-checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={Boolean(interruptible)}
            onChange={(e) => handleFieldChange('interruptible', e.target.checked)}
          />
          <span style={{ fontSize: '12px', color: '#e2e8f0' }}>Allow External Cancellation / Override</span>
        </label>
        <p className="wf-hint-text">
          If enabled, an incoming webhook or admin action can cancel the timer early.
        </p>
      </div>

      <div className="wf-section-divider">OUTGOING PORTS</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <span style={{ fontSize: '11px', color: '#fbbf24', fontWeight: 600 }}>TIMEOUT / ELAPSED</span>
          <span style={{ fontSize: '10px', color: '#94a3b8' }}>Fires when duration ends</span>
        </div>
      </div>
    </>
  )
}
