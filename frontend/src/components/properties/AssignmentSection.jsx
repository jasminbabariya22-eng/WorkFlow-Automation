import React from 'react'

const VISIBILITY_OPTIONS = [
  { id: 'OWNER', label: 'Owner' },
  { id: 'DEPARTMENT', label: 'Department' },
  { id: 'APPROVER', label: 'Approver' }
]

export default function AssignmentSection({
  assignmentType,
  handleAssignmentTypeChange,
  assignment,
  backendRoles,
  backendUsers,
  backendDepartments,
  handleRoleSelect,
  handleUserSelect,
  handleDepartmentSelect,
  onUpdateNodeData,
  selectedNode,
  data,
  activeVisibility,
  handleToggleVisibility
}) {
  return (
    <>
      <div className="wf-section-divider">ASSIGNMENT</div>

      <div className="wf-field-group">
        <label className="wf-field-label">Assignment Type</label>
        <div className="wf-type-toggle-buttons">
          {['user', 'role', 'department'].map(t => (
            <button
              key={t}
              type="button"
              className={`wf-preset-btn ${assignmentType === t ? 'active' : ''}`}
              onClick={() => handleAssignmentTypeChange(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {assignmentType === 'role' && (
        <div className="wf-field-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <label className="wf-field-label" style={{ margin: 0 }}>Role</label>
            {backendRoles.length === 0 && (
              <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: '500' }}>⚠️ No role table in DB</span>
            )}
          </div>
          {backendRoles.length > 0 ? (
            <select
              className="wf-select"
              value={assignment.roleId || ''}
              onChange={(e) => handleRoleSelect(e.target.value)}
            >
              <option value="">-- Select Role --</option>
              {backendRoles.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className="wf-input font-mono uppercase"
              value={assignment.roleName || data.role || ''}
              onChange={(e) => {
                const val = e.target.value.toUpperCase()
                onUpdateNodeData(selectedNode.id, {
                  ...data,
                  role: val,
                  roleId: val,
                  assignment: { ...assignment, type: 'role', roleId: val, roleName: val }
                })
              }}
              placeholder="e.g. INITIATOR, REVIEWER, APPROVER"
            />
          )}
        </div>
      )}

      {assignmentType === 'user' && (
        <div className="wf-field-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <label className="wf-field-label" style={{ margin: 0 }}>User</label>
            {backendUsers.length === 0 && (
              <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: '500' }}>⚠️ No users table in DB</span>
            )}
          </div>
          {backendUsers.length > 0 ? (
            <select
              className="wf-select"
              value={assignment.userId || ''}
              onChange={(e) => handleUserSelect(e.target.value)}
            >
              <option value="">-- Select User --</option>
              {backendUsers.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className="wf-input font-mono"
              value={assignment.userName || data.user || ''}
              onChange={(e) => {
                const val = e.target.value
                onUpdateNodeData(selectedNode.id, {
                  ...data,
                  user: val,
                  userId: val,
                  assignment: { ...assignment, type: 'user', userId: val, userName: val }
                })
              }}
              placeholder="e.g. 101 or initiator_id variable"
            />
          )}
        </div>
      )}

      {assignmentType === 'department' && (
        <div className="wf-field-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <label className="wf-field-label" style={{ margin: 0 }}>Department</label>
            {backendDepartments.length === 0 && (
              <span style={{ fontSize: '10px', color: '#f59e0b', fontWeight: '500' }}>⚠️ No department table in DB</span>
            )}
          </div>
          {backendDepartments.length > 0 ? (
            <select
              className="wf-select"
              value={assignment.departmentId || ''}
              onChange={(e) => handleDepartmentSelect(e.target.value)}
            >
              <option value="">-- Select Department --</option>
              {backendDepartments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className="wf-input"
              value={assignment.departmentName || data.department || ''}
              onChange={(e) => {
                const val = e.target.value
                onUpdateNodeData(selectedNode.id, {
                  ...data,
                  department: val,
                  departmentId: val,
                  assignment: { ...assignment, type: 'department', departmentId: val, departmentName: val }
                })
              }}
              placeholder="e.g. Engineering, Sales, Operations"
            />
          )}
        </div>
      )}

      <div className="wf-section-divider">VISIBILITY</div>
      <div className="wf-visibility-buttons-row">
        {VISIBILITY_OPTIONS.map(v => {
          const isSelected = activeVisibility.includes(v.id)
          return (
            <button
              key={v.id}
              type="button"
              className={`wf-vis-btn ${isSelected ? 'active' : ''}`}
              onClick={() => handleToggleVisibility(v.id)}
            >
              {v.label}
            </button>
          )
        })}
      </div>
    </>
  )
}
