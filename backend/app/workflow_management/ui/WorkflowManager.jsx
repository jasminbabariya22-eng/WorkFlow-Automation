import React, { useEffect, useRef, useState } from 'react';
import BpmnModeler from 'bpmn-js/lib/Modeler';

// Import bpmn-js styles
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';

export default function WorkflowManager({ apiBaseUrl = '/workflow/definitions' }) {
  const containerRef = useRef(null);
  const modelerRef = useRef(null);

  // Core state variables
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modeler specific state
  const [xmlContent, setXmlContent] = useState('');
  const [validationErrors, setValidationErrors] = useState([]);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  
  // Selection states
  const [selectedElement, setSelectedElement] = useState(null);
  const [nodeName, setNodeName] = useState('');
  const [nodeProperties, setNodeProperties] = useState([]);

  // Loading flags
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  // Form states for creating a new workflow spec
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSpecId, setNewSpecId] = useState('');
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newTags, setNewTags] = useState('');

  // 1. Fetch all workflow definitions on load
  useEffect(() => {
    fetchWorkflows();
  }, []);

  // 2. Initialize BPMN.io Modeler
  useEffect(() => {
    if (!containerRef.current) return;

    const modeler = new BpmnModeler({
      container: containerRef.current,
      keyboard: { bindTo: window }
    });

    modelerRef.current = modeler;

    // Listen to node selection events on canvas
    modeler.on('selection.changed', (event) => {
      const selection = event.newSelection;
      if (selection && selection.length > 0) {
        setSelectedElement(selection[0]);
      } else {
        setSelectedElement(null);
      }
    });

    return () => {
      modeler.destroy();
    };
  }, []);

  // 3. Render XML onto canvas when loaded
  useEffect(() => {
    if (xmlContent && modelerRef.current) {
      modelerRef.current.importXML(xmlContent, (err) => {
        if (err) {
          setErrorMessage(`Rendering Error: ${err.message}`);
        } else {
          setErrorMessage(null);
          zoomFit();
        }
      });
    }
  }, [xmlContent]);

  // Fetch extension elements from bpmn-js element
  const getExtensionProperties = (element) => {
    if (!element || !element.businessObject) return [];
    const extensionElements = element.businessObject.extensionElements;
    if (!extensionElements || !extensionElements.values) return [];
    const camundaProperties = extensionElements.values.find(v => v.$type === 'camunda:Properties');
    if (!camundaProperties || !camundaProperties.values) return [];
    return camundaProperties.values.map(p => ({ name: p.name, value: p.value }));
  };

  // Sync selection state to sidebar fields
  useEffect(() => {
    if (selectedElement) {
      setNodeName(selectedElement.businessObject.name || '');
      setNodeProperties(getExtensionProperties(selectedElement));
    } else {
      setNodeName('');
      setNodeProperties([]);
    }
  }, [selectedElement]);

  const updateElementPropertiesInModeler = (name, properties) => {
    if (!modelerRef.current || !selectedElement) return;
    const modeling = modelerRef.current.get('modeling');
    const elementRegistry = modelerRef.current.get('elementRegistry');
    const bpmnFactory = modelerRef.current.get('bpmnFactory');
    
    const bpmnElement = elementRegistry.get(selectedElement.id);
    if (!bpmnElement) return;
    
    // 1. Update standard name label
    modeling.updateProperties(bpmnElement, { name: name });
    
    // 2. Build Extension Elements
    const bo = bpmnElement.businessObject;
    let extensionElements = bo.extensionElements;
    if (!extensionElements) {
      extensionElements = bpmnFactory.create('bpmn:ExtensionElements', { values: [] });
    }
    
    // Remove existing camunda:Properties and create a clean one
    extensionElements.values = (extensionElements.values || []).filter(v => v.$type !== 'camunda:Properties');
    
    if (properties.length > 0) {
      const camundaProperties = bpmnFactory.create('camunda:Properties', { values: [] });
      properties.forEach(p => {
        if (p.name) {
          const prop = bpmnFactory.create('camunda:Property', { name: p.name, value: p.value || '' });
          camundaProperties.values.push(prop);
        }
      });
      extensionElements.values.push(camundaProperties);
    }
    
    modeling.updateProperties(bpmnElement, { extensionElements });
  };

  const handlePropertyChange = (index, field, value) => {
    const updated = [...nodeProperties];
    updated[index][field] = value;
    setNodeProperties(updated);
    updateElementPropertiesInModeler(nodeName, updated);
  };

  const handleAddProperty = () => {
    const updated = [...nodeProperties, { name: '', value: '' }];
    setNodeProperties(updated);
    updateElementPropertiesInModeler(nodeName, updated);
  };

  const handleRemoveProperty = (index) => {
    const updated = nodeProperties.filter((_, i) => i !== index);
    setNodeProperties(updated);
    updateElementPropertiesInModeler(nodeName, updated);
  };

  const handleNodeNameChange = (name) => {
    setNodeName(name);
    updateElementPropertiesInModeler(name, nodeProperties);
  };

  const fetchWorkflows = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(apiBaseUrl);
      const data = await res.json();
      if (res.ok) {
        setWorkflows(data.data || []);
        if (data.data && data.data.length > 0 && !selectedWorkflow) {
          handleSelectWorkflow(data.data[0]);
        }
      } else {
        setErrorMessage(data.message || 'Failed to retrieve workflow list');
      }
    } catch (err) {
      setErrorMessage(`Network error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectWorkflow = async (workflow) => {
    setSelectedWorkflow(workflow);
    setXmlContent(workflow.xml_content);
    setValidationErrors([]);
    setErrorMessage(null);
    setSelectedElement(null);
  };

  const handleSaveDraft = async () => {
    if (!modelerRef.current || !selectedWorkflow) return;
    setIsSaving(true);
    setStatusMessage('Saving draft...');
    setErrorMessage(null);

    modelerRef.current.saveXML({ format: true }, async (err, xml) => {
      if (err) {
        setErrorMessage(`Modeler export error: ${err.message}`);
        setIsSaving(false);
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: selectedWorkflow.name,
            description: selectedWorkflow.description,
            xml_content: xml,
            tags: selectedWorkflow.tags
          })
        });
        const resData = await response.json();
        if (response.ok) {
          setStatusMessage('Draft successfully saved in-place!');
          setTimeout(() => setStatusMessage(null), 3000);
          fetchWorkflows();
        } else {
          setErrorMessage(resData.message || 'Error saving draft');
        }
      } catch (e) {
        setErrorMessage(`Server Error: ${e.message}`);
      } finally {
        setIsSaving(false);
      }
    });
  };

  const handleValidate = async () => {
    if (!selectedWorkflow) return;
    setIsValidating(true);
    setStatusMessage('Validating structure...');
    setErrorMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}/validate`, {
        method: 'POST'
      });
      const resData = await response.json();
      if (response.ok) {
        setValidationErrors(resData.data.errors || []);
        if (resData.data.is_valid) {
          setStatusMessage('BPMN Diagram structure is valid!');
        } else {
          setErrorMessage('BPMN Validation warnings or errors discovered.');
        }
        setTimeout(() => setStatusMessage(null), 3000);
      } else {
        setErrorMessage(resData.message || 'Failed to complete validation analysis');
      }
    } catch (e) {
      setErrorMessage(`Network error: ${e.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedWorkflow) return;
    setIsPublishing(true);
    setStatusMessage('Publishing a new locked version...');
    setErrorMessage(null);

    modelerRef.current.saveXML({ format: true }, async (err, xml) => {
      if (err) {
        setErrorMessage(`Modeler export error: ${err.message}`);
        setIsPublishing(false);
        return;
      }

      try {
        await fetch(`${apiBaseUrl}/${selectedWorkflow.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ xml_content: xml })
        });
      } catch (e) {
        console.error('Failed to update draft before publishing:', e);
      }

      try {
        const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}/publish`, {
          method: 'POST'
        });
        const resData = await response.json();
        if (response.ok) {
          setStatusMessage(`Workflow published as Version ${resData.data.version}!`);
          setTimeout(() => setStatusMessage(null), 3000);
          fetchWorkflows();
        } else {
          setErrorMessage(resData.message || 'BPMN Schema failed publishing rules.');
        }
      } catch (e) {
        setErrorMessage(`Network error: ${e.message}`);
      } finally {
        setIsPublishing(false);
      }
    });
  };

  const handleActivate = async () => {
    if (!selectedWorkflow) return;
    setStatusMessage('Activating workflow version...');
    try {
      const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}/activate`, {
        method: 'POST'
      });
      if (response.ok) {
        setStatusMessage('Workflow activated successfully!');
        setTimeout(() => setStatusMessage(null), 3000);
        fetchWorkflows();
      } else {
        const data = await response.json();
        setErrorMessage(data.message || 'Failed to activate version');
      }
    } catch (e) {
      setErrorMessage(`Network error: ${e.message}`);
    }
  };

  const handleCreateWorkflow = async (e) => {
    e.preventDefault();
    if (!newSpecId || !newName) return;
    
    try {
      const response = await fetch(apiBaseUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spec_id: newSpecId,
          name: newName,
          description: newDescription,
          tags: newTags
        })
      });
      const data = await response.json();
      if (response.ok) {
        setShowCreateModal(false);
        setNewSpecId('');
        setNewName('');
        setNewDescription('');
        setNewTags('');
        setStatusMessage('New Workflow draft initialized!');
        setTimeout(() => setStatusMessage(null), 3000);
        fetchWorkflows();
      } else {
        setErrorMessage(data.message || 'Failed to instantiate draft');
      }
    } catch (err) {
      setErrorMessage(`Connection error: ${err.message}`);
    }
  };

  const handleDuplicate = async () => {
    if (!selectedWorkflow) return;
    setStatusMessage('Duplicating specification...');
    try {
      const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}/duplicate`, {
        method: 'POST'
      });
      const resData = await response.json();
      if (response.ok) {
        setStatusMessage('Duplicated draft created!');
        setTimeout(() => setStatusMessage(null), 3000);
        fetchWorkflows();
      } else {
        setErrorMessage(resData.message || 'Cloning failed.');
      }
    } catch (e) {
      setErrorMessage(`Network error: ${e.message}`);
    }
  };

  const handleDeleteDraft = async () => {
    if (!selectedWorkflow) return;
    if (!window.confirm('Are you sure you want to delete this workflow version?')) return;
    
    try {
      const response = await fetch(`${apiBaseUrl}/${selectedWorkflow.id}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setStatusMessage('Workflow deleted successfully.');
        setTimeout(() => setStatusMessage(null), 3000);
        setSelectedWorkflow(null);
        setXmlContent('');
        fetchWorkflows();
      } else {
        const data = await response.json();
        setErrorMessage(data.message || 'Deletion failed.');
      }
    } catch (e) {
      setErrorMessage(`Network error: ${e.message}`);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !selectedWorkflow) return;

    const formData = new FormData();
    formData.append('spec_id', `${selectedWorkflow.spec_id}_imported`);
    formData.append('name', `${selectedWorkflow.name} (Imported)`);
    formData.append('file', file);

    setStatusMessage('Uploading BPMN file...');
    try {
      const response = await fetch(`${apiBaseUrl}/import`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (response.ok) {
        setStatusMessage('BPMN File uploaded successfully as Draft Version 1!');
        setTimeout(() => setStatusMessage(null), 3000);
        fetchWorkflows();
      } else {
        setErrorMessage(data.message || 'Import failed.');
      }
    } catch (e) {
      setErrorMessage(`Upload error: ${e.message}`);
    }
  };

  const handleExport = () => {
    if (!selectedWorkflow) return;
    window.open(`${apiBaseUrl}/${selectedWorkflow.id}/export`);
  };

  const zoomIn = () => {
    if (modelerRef.current) modelerRef.current.get('zoomScroll').stepZoom(1);
  };
  const zoomOut = () => {
    if (modelerRef.current) modelerRef.current.get('zoomScroll').stepZoom(-1);
  };
  const zoomFit = () => {
    if (modelerRef.current) modelerRef.current.get('canvas').zoom('fit-viewport');
  };

  const handleUndo = () => {
    if (modelerRef.current) modelerRef.current.get('commandStack').undo();
  };
  const handleRedo = () => {
    if (modelerRef.current) modelerRef.current.get('commandStack').redo();
  };

  const filteredWorkflows = workflows.filter(w =>
    w.spec_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (w.name && w.name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div style={styles.container}>
      {/* 1. TOP TOOLBAR */}
      <header style={styles.toolbar}>
        <div style={styles.toolbarLeft}>
          <span style={styles.logo}>Elsa Studio</span>
          <div style={styles.divider} />
          <button onClick={() => setShowCreateModal(true)} style={styles.toolbarBtn} title="New Workflow">New</button>
          <button onClick={handleSaveDraft} disabled={isSaving} style={styles.toolbarBtn} title="Save Draft">Save</button>
          <button onClick={handleValidate} disabled={isValidating} style={styles.toolbarBtn} title="Validate structure">Validate</button>
          <button onClick={handlePublish} disabled={isPublishing} style={styles.toolbarBtn} title="Lock and publish version">Publish</button>
          <button onClick={handleActivate} style={styles.toolbarBtn} title="Activate for runtime">Activate</button>
          <button onClick={handleDuplicate} style={styles.toolbarBtn} title="Duplicate spec">Duplicate</button>
          <button onClick={handleDeleteDraft} style={styles.toolbarBtnDanger} title="Delete draft">Delete</button>
        </div>

        <div style={styles.toolbarRight}>
          <button onClick={handleUndo} style={styles.toolbarBtnSmall}>Undo</button>
          <button onClick={handleRedo} style={styles.toolbarBtnSmall}>Redo</button>
          <div style={styles.divider} />
          <button onClick={zoomIn} style={styles.toolbarBtnSmall}>Zoom +</button>
          <button onClick={zoomOut} style={styles.toolbarBtnSmall}>Zoom -</button>
          <button onClick={zoomFit} style={styles.toolbarBtnSmall}>Fit</button>
          <div style={styles.divider} />
          <button onClick={handleExport} style={styles.toolbarBtnSecondary}>Export</button>
          <label style={styles.fileInputLabel}>
            Import
            <input type="file" onChange={handleFileUpload} accept=".bpmn,.xml" style={{ display: 'none' }} />
          </label>
        </div>
      </header>

      {/* 2. MAIN WORKSPACE */}
      <div style={styles.workspace}>
        {/* LEFT SIDEBAR */}
        <aside style={styles.sidebarLeft}>
          <div style={styles.sidebarSection}>
            <h3 style={styles.sidebarTitle}>Workflow Explorer</h3>
            <input
              type="text"
              placeholder="Search workflows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={styles.searchInput}
            />
            <div style={styles.explorerList}>
              {isLoading ? (
                <div style={styles.infoText}>Loading definitions...</div>
              ) : filteredWorkflows.length === 0 ? (
                <div style={styles.infoText}>No processes found</div>
              ) : (
                filteredWorkflows.map(w => (
                  <div
                    key={w.id}
                    onClick={() => handleSelectWorkflow(w)}
                    style={{
                      ...styles.explorerCard,
                      borderLeftColor: selectedWorkflow && selectedWorkflow.spec_id === w.spec_id ? '#6C5CE7' : 'transparent',
                      backgroundColor: selectedWorkflow && selectedWorkflow.id === w.id ? '#1E1E2F' : 'transparent'
                    }}
                  >
                    <div style={styles.cardHeader}>
                      <span style={styles.cardTitle}>{w.name || w.spec_id}</span>
                      <span style={w.status === 'Active' ? styles.badgeActive : styles.badgeInactive}>{w.status}</span>
                    </div>
                    <span style={styles.cardMeta}>v{w.version} | {w.spec_id}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>

        {/* CENTER VISUAL BPMN CANVAS */}
        <main style={styles.canvasContainer}>
          {statusMessage && <div style={styles.alertSuccess}>{statusMessage}</div>}
          {errorMessage && <div style={styles.alertError}>{errorMessage}</div>}
          <div ref={containerRef} style={styles.canvas} />
        </main>

        {/* RIGHT SIDEBAR */}
        <aside style={styles.sidebarRight}>
          {selectedElement ? (
            <div>
              <h3 style={styles.sidebarTitle}>Element Config</h3>
              <div style={styles.formGroup}>
                <label style={styles.label}>Node ID</label>
                <input type="text" value={selectedElement.id} disabled style={styles.inputDisabled} />
              </div>
              <div style={{ ...styles.formGroup, marginTop: '12px' }}>
                <label style={styles.label}>Label Name</label>
                <input
                  type="text"
                  value={nodeName}
                  onChange={(e) => handleNodeNameChange(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={{ marginTop: '16px' }}>
                <label style={styles.label}>Camunda Properties</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                  {nodeProperties.map((p, index) => (
                    <div key={index} style={{ display: 'flex', gap: '6px' }}>
                      <input
                        type="text"
                        placeholder="Key"
                        value={p.name}
                        onChange={(e) => handlePropertyChange(index, 'name', e.target.value)}
                        style={{ ...styles.input, flex: 1, padding: '4px 8px' }}
                      />
                      <input
                        type="text"
                        placeholder="Value"
                        value={p.value}
                        onChange={(e) => handlePropertyChange(index, 'value', e.target.value)}
                        style={{ ...styles.input, flex: 1.5, padding: '4px 8px' }}
                      />
                      <button
                        onClick={() => handleRemoveProperty(index)}
                        style={{ ...styles.toolbarBtnSmall, backgroundColor: '#DC3545', color: '#FFF', border: 'none', cursor: 'pointer' }}
                      >
                        x
                      </button>
                    </div>
                  ))}
                  <button onClick={handleAddProperty} style={{ ...styles.toolbarBtnSmall, marginTop: '4px', cursor: 'pointer' }}>
                    + Add Property
                  </button>
                </div>
              </div>
            </div>
          ) : selectedWorkflow ? (
            <div style={styles.propertiesForm}>
              <h3 style={styles.sidebarTitle}>Properties</h3>
              <div style={styles.formGroup}>
                <label style={styles.label}>Workflow Name</label>
                <input
                  type="text"
                  value={selectedWorkflow.name || ''}
                  onChange={(e) => setSelectedWorkflow({ ...selectedWorkflow, name: e.target.value })}
                  style={styles.input}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Specification ID</label>
                <input
                  type="text"
                  value={selectedWorkflow.spec_id || ''}
                  disabled
                  style={styles.inputDisabled}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Description</label>
                <textarea
                  value={selectedWorkflow.description || ''}
                  onChange={(e) => setSelectedWorkflow({ ...selectedWorkflow, description: e.target.value })}
                  rows={4}
                  style={styles.textarea}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Tags (Comma separated)</label>
                <input
                  type="text"
                  value={selectedWorkflow.tags || ''}
                  onChange={(e) => setSelectedWorkflow({ ...selectedWorkflow, tags: e.target.value })}
                  style={styles.input}
                />
              </div>

              <div style={styles.divider} />
              
              <div style={styles.metaInfo}>
                <div><strong>Status:</strong> {selectedWorkflow.status}</div>
                <div><strong>Version:</strong> v{selectedWorkflow.version}</div>
                <div><strong>Created On:</strong> {new Date(selectedWorkflow.created_on).toLocaleDateString()}</div>
                {selectedWorkflow.published_on && (
                  <div><strong>Published:</strong> {new Date(selectedWorkflow.published_on).toLocaleDateString()}</div>
                )}
              </div>
            </div>
          ) : (
            <div style={styles.infoText}>Select a workflow to edit properties</div>
          )}
        </aside>
      </div>

      {/* 3. BOTTOM PANEL */}
      <footer style={styles.bottomPanel}>
        <div style={styles.bottomHeader}>
          <span>Validation Diagnostics</span>
          <span style={validationErrors.length > 0 ? styles.alertTextRed : styles.alertTextGreen}>
            {validationErrors.length === 0 ? 'No issues detected' : `${validationErrors.length} Diagnostic Reports`}
          </span>
        </div>
        <div style={styles.diagnosticsList}>
          {validationErrors.length === 0 ? (
            <div style={styles.diagPlaceholder}>Diagram structural health is clean. Trigger validate to refresh.</div>
          ) : (
            validationErrors.map((err, index) => (
              <div key={index} style={styles.diagRow}>
                <span style={err.severity === 'Error' ? styles.diagSeverityError : styles.diagSeverityWarn}>
                  [{err.severity.toUpperCase()}]
                </span>
                <span style={styles.diagText}>
                  {err.node_name ? `Node '${err.node_name}' (${err.node_id}): ` : ''} {err.message}
                </span>
              </div>
            ))
          )}
        </div>
      </footer>

      {/* CREATE WORKFLOW MODAL */}
      {showCreateModal && (
        <div style={styles.modalBackdrop}>
          <div style={styles.modalContainer}>
            <h3 style={styles.modalTitle}>Initialize New BPMN Workflow</h3>
            <form onSubmit={handleCreateWorkflow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Specification ID (Must be camelCase, unique)</label>
                <input
                  type="text"
                  value={newSpecId}
                  onChange={(e) => setNewSpecId(e.target.value)}
                  placeholder="e.g. LeaveRequestWorkflow"
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Human-Readable Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Leave Request Process"
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Description</label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Summarize the lifecycle of this workflow..."
                  rows={3}
                  style={styles.textarea}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Tags</label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="hr, approvals, forms"
                  style={styles.input}
                />
              </div>
              <div style={styles.modalActions}>
                <button type="button" onClick={() => setShowCreateModal(false)} style={styles.modalBtnCancel}>Cancel</button>
                <button type="submit" style={styles.modalBtnSubmit}>Create Draft</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// Elsa Studio Dark Glassmorphism Styling Config
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    backgroundColor: '#161624',
    color: '#D1D1E0'
  },
  toolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 20px',
    backgroundColor: '#0F0F1A',
    borderBottom: '1px solid #232338',
    zIndex: 10
  },
  toolbarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  toolbarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  logo: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#8C7AE6',
    letterSpacing: '0.5px'
  },
  divider: {
    width: '1px',
    height: '16px',
    backgroundColor: '#2A2A3F',
    margin: '0 8px'
  },
  toolbarBtn: {
    backgroundColor: '#202035',
    color: '#D1D1E0',
    border: '1px solid #32324D',
    borderRadius: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#6C5CE7',
      color: '#FFF'
    }
  },
  toolbarBtnDanger: {
    backgroundColor: '#351C24',
    color: '#FF6B81',
    border: '1px solid #5F2B39',
    borderRadius: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer'
  },
  toolbarBtnSecondary: {
    backgroundColor: '#6C5CE7',
    color: '#FFF',
    border: 'none',
    borderRadius: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer'
  },
  fileInputLabel: {
    backgroundColor: '#202035',
    color: '#D1D1E0',
    border: '1px solid #32324D',
    borderRadius: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer'
  },
  toolbarBtnSmall: {
    backgroundColor: '#1E1E2F',
    color: '#8A8A9F',
    border: 'none',
    borderRadius: '4px',
    padding: '4px 8px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  workspace: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden'
  },
  sidebarLeft: {
    width: '280px',
    backgroundColor: '#0F0F1A',
    borderRight: '1px solid #232338',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px'
  },
  sidebarRight: {
    width: '300px',
    backgroundColor: '#0F0F1A',
    borderLeft: '1px solid #232338',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px',
    overflowY: 'auto'
  },
  sidebarSection: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%'
  },
  sidebarTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#FFF',
    margin: '0 0 12px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  searchInput: {
    backgroundColor: '#1C1C2D',
    border: '1px solid #2F2F4D',
    borderRadius: '4px',
    padding: '8px 12px',
    color: '#FFF',
    fontSize: '13px',
    marginBottom: '16px',
    outline: 'none'
  },
  explorerList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    overflowY: 'auto',
    flex: 1
  },
  explorerCard: {
    borderLeft: '3px solid transparent',
    padding: '10px',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: '#1A1A2F'
    }
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px'
  },
  cardTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#FFF'
  },
  cardMeta: {
    fontSize: '11px',
    color: '#6E6E85'
  },
  badgeActive: {
    fontSize: '10px',
    backgroundColor: '#1E4620',
    color: '#66BB6A',
    padding: '1px 5px',
    borderRadius: '3px'
  },
  badgeInactive: {
    fontSize: '10px',
    backgroundColor: '#3C2F1E',
    color: '#FFA726',
    padding: '1px 5px',
    borderRadius: '3px'
  },
  canvasContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative'
  },
  canvas: {
    flex: 1,
    backgroundColor: '#FAFAFA'
  },
  propertiesForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  label: {
    fontSize: '12px',
    color: '#8E8EAF',
    fontWeight: 500
  },
  input: {
    backgroundColor: '#1C1C2D',
    border: '1px solid #2F2F4D',
    borderRadius: '4px',
    padding: '8px 12px',
    color: '#FFF',
    fontSize: '13px',
    outline: 'none'
  },
  inputDisabled: {
    backgroundColor: '#0F0F1A',
    border: '1px solid #232338',
    borderRadius: '4px',
    padding: '8px 12px',
    color: '#6E6E85',
    fontSize: '13px'
  },
  textarea: {
    backgroundColor: '#1C1C2D',
    border: '1px solid #2F2F4D',
    borderRadius: '4px',
    padding: '8px 12px',
    color: '#FFF',
    fontSize: '13px',
    resize: 'none',
    outline: 'none'
  },
  metaInfo: {
    fontSize: '12px',
    color: '#8E8EAF',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  bottomPanel: {
    height: '180px',
    backgroundColor: '#0F0F1A',
    borderTop: '1px solid #232338',
    display: 'flex',
    flexDirection: 'column',
    padding: '12px 20px',
    zIndex: 5
  },
  bottomHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    fontWeight: 600,
    color: '#FFF',
    textTransform: 'uppercase',
    borderBottom: '1px solid #1F1F35',
    paddingBottom: '8px',
    marginBottom: '8px'
  },
  diagnosticsList: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  diagPlaceholder: {
    color: '#6E6E85',
    fontSize: '12px',
    textAlign: 'center',
    padding: '20px'
  },
  diagRow: {
    display: 'flex',
    gap: '8px',
    fontSize: '12px'
  },
  diagSeverityError: {
    color: '#FF6B81',
    fontWeight: 600
  },
  diagSeverityWarn: {
    color: '#FFA726',
    fontWeight: 600
  },
  diagText: {
    color: '#B0B0C5'
  },
  alertTextRed: {
    color: '#FF6B81'
  },
  alertTextGreen: {
    color: '#66BB6A'
  },
  alertSuccess: {
    position: 'absolute',
    top: '12px',
    left: '12px',
    right: '12px',
    padding: '10px 16px',
    backgroundColor: '#1E4620EE',
    color: '#81C784',
    borderRadius: '4px',
    fontSize: '13px',
    zIndex: 100
  },
  alertError: {
    position: 'absolute',
    top: '12px',
    left: '12px',
    right: '12px',
    padding: '10px 16px',
    backgroundColor: '#4A1D24EE',
    color: '#E57373',
    borderRadius: '4px',
    fontSize: '13px',
    zIndex: 100
  },
  infoText: {
    color: '#6E6E85',
    fontSize: '13px',
    textAlign: 'center',
    padding: '12px'
  },
  modalBackdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#00000088',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000
  },
  modalContainer: {
    width: '460px',
    backgroundColor: '#161624',
    border: '1px solid #2E2E4A',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
  },
  modalTitle: {
    color: '#FFF',
    fontSize: '16px',
    fontWeight: 600,
    margin: '0 0 20px 0'
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '20px'
  },
  modalBtnCancel: {
    backgroundColor: 'transparent',
    color: '#8E8EAF',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px'
  },
  modalBtnSubmit: {
    backgroundColor: '#6C5CE7',
    color: '#FFF',
    border: 'none',
    borderRadius: '4px',
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer'
  }
};
