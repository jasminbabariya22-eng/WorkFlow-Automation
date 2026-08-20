import BaseRenderer from 'diagram-js/lib/draw/BaseRenderer'

const HIGH_PRIORITY = 1500
const SVG_NS = 'http://www.w3.org/2000/svg'

function svgCreate(type, attrs = {}) {
  const el = document.createElementNS(SVG_NS, type)
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, String(v))
  }
  return el
}

function svgAppend(parent, child) {
  parent.appendChild(child)
  return child
}

function svgText(parent, x, y, text, opts = {}) {
  const t = svgCreate('text', {
    x, y,
    fill: opts.fill || '#1e293b',
    'font-family': "'Inter','Segoe UI',system-ui,sans-serif",
    'font-size': opts.size || '12px',
    'font-weight': opts.weight || '400',
    'text-anchor': opts.anchor || 'start',
    'dominant-baseline': opts.baseline || 'auto'
  })
  t.textContent = text
  svgAppend(parent, t)
  return t
}

function svgRoundRect(parent, x, y, w, h, r, fill, stroke, sw = 1.5) {
  return svgAppend(parent, svgCreate('rect', {
    x, y, width: w, height: h, rx: r, ry: r,
    fill, stroke, 'stroke-width': sw
  }))
}

function svgCircle(parent, cx, cy, r, fill) {
  return svgAppend(parent, svgCreate('circle', { cx, cy, r, fill }))
}

function svgIcon(parent, cx, cy, iconKey, color = '#fff') {
  const g = svgCreate('g', { transform: `translate(${cx},${cy})` })
  if (iconKey === 'user') {
    svgAppend(g, svgCreate('circle', { cx: 0, cy: -3, r: 3.8, fill: color }))
    svgAppend(g, svgCreate('path', {
      d: 'M-6,6 Q-6,1 0,1 Q6,1 6,6',
      fill: color, stroke: 'none'
    }))
  } else if (iconKey === 'file') {
    svgAppend(g, svgCreate('path', {
      d: 'M-4,-7 L2,-7 L6,-3 L6,7 L-4,7 Z',
      fill: color, stroke: 'none'
    }))
  } else if (iconKey === 'check') {
    svgAppend(g, svgCreate('path', {
      d: 'M-4.5,0 L-1,3.5 L5.5,-4',
      fill: 'none', stroke: color, 'stroke-width': 2.5,
      'stroke-linecap': 'round', 'stroke-linejoin': 'round'
    }))
  }
  svgAppend(parent, g)
  return g
}

// ==========================================================================
// RENDERER — Only overrides SHAPES, NOT connections
// ==========================================================================
export default class CustomWorkflowRenderer extends BaseRenderer {
  constructor(eventBus, bpmnRenderer) {
    super(eventBus, HIGH_PRIORITY)
    this.bpmnRenderer = bpmnRenderer
    console.log('✅ CustomWorkflowRenderer LOADED and registered with bpmn-js')
  }

  canRender(element) {
    // ONLY render shapes, NOT connections (SequenceFlow)
    const t = element.type
    const shouldRender = t === 'bpmn:StartEvent' || t === 'bpmn:EndEvent' || t === 'bpmn:UserTask'
    if (shouldRender) {
      console.log('🎨 CustomRenderer canRender:', t, element.businessObject?.name)
    }
    return shouldRender
  }

  drawShape(parentGfx, element) {
    const bo = element.businessObject
    const name = (bo.name || bo.id || '').toLowerCase()
    const type = element.type
    const role = getCandidateGroups(bo)

    // START → Risk Owner card
    if (type === 'bpmn:StartEvent') {
      return this._drawRiskOwner(parentGfx, element)
    }
    // END → Approved card
    if (type === 'bpmn:EndEvent') {
      return this._drawApprovedEnd(parentGfx, element)
    }
    // Draft / Resubmission
    if (name.includes('draft') || name.includes('rework') || name.includes('resubmission')) {
      return this._drawDraft(parentGfx, element)
    }
    // Approval tasks (FH, RM, RH)
    if (type === 'bpmn:UserTask') {
      return this._drawApproval(parentGfx, element, role)
    }

    return this.bpmnRenderer.drawShape(parentGfx, element)
  }

  // ========================================================================
  // RISK OWNER (Start)
  // ========================================================================
  _drawRiskOwner(parentGfx, element) {
    const W = element.width, H = element.height

    // Main card rect — this is returned for hit-testing
    const mainRect = svgRoundRect(parentGfx, 0, 0, W, H, 12, '#f0fdf4', '#22c55e', 2)

    // Green circle icon
    svgCircle(parentGfx, 28, 24, 15, '#16a34a')
    svgIcon(parentGfx, 28, 24, 'user', '#ffffff')

    // Title
    svgText(parentGfx, 50, 20, 'RISK OWNER', { fill: '#15803d', size: '13px', weight: '700' })
    svgText(parentGfx, 50, 35, 'Create Risk', { fill: '#475569', size: '11px', weight: '500' })

    // Action pills
    const pillW = (W - 50) / 2
    const pillY = H - 30
    svgRoundRect(parentGfx, 15, pillY, pillW, 22, 6, '#ffffff', '#86efac', 1)
    svgText(parentGfx, 15 + pillW / 2, pillY + 15, 'DRAFT', { fill: '#16a34a', size: '10px', weight: '700', anchor: 'middle' })

    svgRoundRect(parentGfx, 25 + pillW, pillY, pillW, 22, 6, '#ffffff', '#86efac', 1)
    svgText(parentGfx, 25 + pillW + pillW / 2, pillY + 15, 'SAVE', { fill: '#16a34a', size: '10px', weight: '700', anchor: 'middle' })

    return mainRect
  }

  // ========================================================================
  // APPROVAL NODE (FH / RM / RH)
  // ========================================================================
  _drawApproval(parentGfx, element, role) {
    const W = element.width, H = element.height
    const bo = element.businessObject
    const name = bo.name || bo.id || ''

    const upperName = name.toUpperCase()
    const isRM = upperName.includes('RM') || role.includes('RISK_MANAGER')
    const isRH = upperName.includes('RH') || role.includes('RISK_HEAD')
    const hasForce = isRM || isRH

    let roleLabel = role.replace(/_/g, ' ') || 'FUNCTION HEAD'

    // Main card rect — returned for hit-testing
    const mainRect = svgRoundRect(parentGfx, 0, 0, W, H, 12, '#faf5ff', '#a855f7', 2)

    // Top accent bar
    svgAppend(parentGfx, svgCreate('rect', {
      x: 0, y: 0, width: W, height: 4, rx: 12,
      fill: '#a855f7'
    }))

    // Purple circle icon
    svgCircle(parentGfx, 28, 26, 15, '#7c3aed')
    svgIcon(parentGfx, 28, 26, 'user', '#ffffff')

    // Title
    svgText(parentGfx, 50, 22, upperName, { fill: '#1e293b', size: '13px', weight: '700' })
    svgText(parentGfx, 50, 37, `Role: ${roleLabel}`, { fill: '#6b7280', size: '10px', weight: '600' })

    // Actions header
    svgText(parentGfx, 14, 55, 'Actions:', { fill: '#6b7280', size: '9.5px', weight: '600' })

    // Action chips
    let chipX = 14
    const chipY = 62

    // ✓ Approve chip
    svgRoundRect(parentGfx, chipX, chipY, 62, 18, 4, '#dcfce7', '#86efac', 1)
    svgText(parentGfx, chipX + 31, chipY + 13, '✓ Approve', { fill: '#16a34a', size: '9px', weight: '700', anchor: 'middle' })
    chipX += 66

    // ✕ Reject chip
    svgRoundRect(parentGfx, chipX, chipY, 54, 18, 4, '#fef2f2', '#fca5a5', 1)
    svgText(parentGfx, chipX + 27, chipY + 13, '✕ Reject', { fill: '#dc2626', size: '9px', weight: '700', anchor: 'middle' })
    chipX += 58

    // ⚡ Force Approve chip (RM / RH only)
    if (hasForce) {
      svgRoundRect(parentGfx, chipX, chipY, 74, 18, 4, '#fef3c7', '#fcd34d', 1)
      svgText(parentGfx, chipX + 37, chipY + 13, '⚡ Force', { fill: '#b45309', size: '8.5px', weight: '700', anchor: 'middle' })
    }

    return mainRect
  }

  // ========================================================================
  // DRAFT / RESUBMISSION
  // ========================================================================
  _drawDraft(parentGfx, element) {
    const W = element.width, H = element.height

    // Main card rect
    const mainRect = svgRoundRect(parentGfx, 0, 0, W, H, 12, '#fffbeb', '#f59e0b', 2)

    // Orange circle icon
    svgCircle(parentGfx, 28, 26, 15, '#f59e0b')
    svgIcon(parentGfx, 28, 26, 'file', '#ffffff')

    // Title & subtitle
    svgText(parentGfx, 50, 22, 'DRAFT (EDIT)', { fill: '#b45309', size: '13px', weight: '700' })
    svgText(parentGfx, 50, 36, 'Risk Owner', { fill: '#475569', size: '11px', weight: '600' })
    svgText(parentGfx, 50, 49, 'edits risk', { fill: '#94a3b8', size: '10px', weight: '400' })

    // Resubmit pill
    const pillW = W - 40
    const pillY = H - 30
    svgRoundRect(parentGfx, 20, pillY, pillW, 22, 6, '#ffffff', '#e2e8f0', 1)
    svgText(parentGfx, 20 + pillW / 2, pillY + 15, 'RESUBMIT', { fill: '#16a34a', size: '10px', weight: '700', anchor: 'middle' })

    return mainRect
  }

  // ========================================================================
  // APPROVED END
  // ========================================================================
  _drawApprovedEnd(parentGfx, element) {
    const W = element.width, H = element.height

    // Main card rect
    const mainRect = svgRoundRect(parentGfx, 0, 0, W, H, 12, '#ecfdf5', '#10b981', 2)

    // Green circle with checkmark
    svgCircle(parentGfx, 28, H / 2, 15, '#059669')
    svgIcon(parentGfx, 28, H / 2, 'check', '#ffffff')

    // Title
    svgText(parentGfx, 50, H / 2 - 5, 'APPROVED (END)', { fill: '#047857', size: '13px', weight: '700' })
    svgText(parentGfx, 50, H / 2 + 11, 'Workflow Completed', { fill: '#6b7280', size: '10px', weight: '500' })

    return mainRect
  }
}

CustomWorkflowRenderer.$inject = ['eventBus', 'bpmnRenderer']

function getCandidateGroups(bo) {
  try {
    if (typeof bo.get === 'function') return bo.get('camunda:candidateGroups') || ''
    return bo['camunda:candidateGroups'] || ''
  } catch { return '' }
}
