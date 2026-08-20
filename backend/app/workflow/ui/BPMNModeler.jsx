import React, { useEffect, useRef, useState } from 'react';
import BpmnModeler from 'bpmn-js/lib/Modeler';

// Import bpmn-js default styles (ensure these are imported in your build configuration)
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';

/**
 * BPMNModeler represents the visual canvas component integrating BPMN.io Modeler
 * with the FastAPI version control and verification backend.
 */
export default function BPMNModeler({ specId = 'RiskApprovalWorkflow', apiBaseUrl = '/api' }) {
  const containerRef = useRef(null);
  const modelerRef = useRef(null);
  const [xml, setXml] = useState('');
  const [versionInfo, setVersionInfo] = useState({ version: 0, is_active: false });
  const [versionsList, setVersionsList] = useState([]);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  // 1. Fetch latest active definition and version history from backend
  useEffect(() => {
    fetchLatestDefinition();
    fetchVersionHistory();
  }, [specId]);

  // 2. Initialize BPMN.io Modeler Canvas
  useEffect(() => {
    if (!containerRef.current) return;

    // Create the Modeler instance
    const modeler = new BpmnModeler({
      container: containerRef.current,
      keyboard: { bindTo: window }
    });

    modelerRef.current = modeler;

    // Cleanup on unmount
    return () => {
      modeler.destroy();
    };
  }, []);

  // 3. Load XML content onto the Modeler canvas when fetched
  useEffect(() => {
    if (xml && modelerRef.current) {
      modelerRef.current.importXML(xml, (err) => {
        if (err) {
          setErrorMessage(`Error rendering BPMN Diagram: ${err.message}`);
        } else {
          setErrorMessage(null);
          // Zoom to fit canvas bounds
          const canvas = modelerRef.current.get('canvas');
          canvas.zoom('fit-viewport');
        }
      });
    }
  }, [xml]);

  const fetchLatestDefinition = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/workflow/definitions/${specId}/latest`);
      const resData = await response.json();
      if (response.ok) {
        setXml(resData.data.xml_content);
        setVersionInfo({
          id: resData.data.id,
          version: resData.data.version,
          is_active: resData.data.is_active
        });
      } else {
        setErrorMessage(resData.message || 'Failed to retrieve latest definition.');
      }
    } catch (err) {
      setErrorMessage(`Connection Error: ${err.message}`);
    }
  };

  const fetchVersionHistory = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/workflow/definitions/${specId}/versions`);
      const resData = await response.json();
      if (response.ok) {
        setVersionsList(resData.data);
      }
    } catch (err) {
      console.error('Failed to load version history:', err);
    }
  };

  // 4. Save draft XML (POST /save)
  const handleSaveDraft = async () => {
    if (!modelerRef.current) return;
    setIsSaving(true);
    setStatusMessage('Saving draft...');
    setErrorMessage(null);

    modelerRef.current.saveXML({ format: true }, async (err, updatedXml) => {
      if (err) {
        setErrorMessage(`Failed to export XML from Modeler: ${err.message}`);
        setIsSaving(false);
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/workflow/definitions/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            spec_id: specId,
            xml_content: updatedXml,
            description: 'Draft saved from BPMN.io designer'
          })
        });
        const resData = await response.json();
        
        if (response.ok) {
          setStatusMessage('Draft saved successfully!');
          setTimeout(() => setStatusMessage(null), 3000);
          fetchVersionHistory();
        } else {
          setErrorMessage(resData.message || 'Error occurred while saving.');
        }
      } catch (e) {
        setErrorMessage(`Server Connection Error: ${e.message}`);
      } finally {
        setIsSaving(false);
      }
    });
  };

  // 5. Publish process as new version (POST /publish)
  const handlePublish = async () => {
    if (!modelerRef.current) return;
    setIsPublishing(true);
    setStatusMessage('Validating and publishing BPMN...');
    setErrorMessage(null);

    modelerRef.current.saveXML({ format: true }, async (err, updatedXml) => {
      if (err) {
        setErrorMessage(`Export error: ${err.message}`);
        setIsPublishing(false);
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/workflow/definitions/publish`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            spec_id: specId,
            xml_content: updatedXml,
            description: `Published release`
          })
        });
        const resData = await response.json();
        
        if (response.ok) {
          setStatusMessage(`Version ${resData.data.version} published successfully!`);
          setTimeout(() => setStatusMessage(null), 3000);
          fetchLatestDefinition();
          fetchVersionHistory();
        } else {
          // Display BPMN compilation validation error directly in the UI
          setErrorMessage(resData.message || 'BPMN Validation failed.');
        }
      } catch (e) {
        setErrorMessage(`Network error: ${e.message}`);
      } finally {
        setIsPublishing(false);
      }
    });
  };

  // 6. Activate/Deactivate specific version
  const handleToggleVersion = async (versionId, isActive) => {
    setStatusMessage('Updating version status...');
    const action = isActive ? 'deactivate' : 'activate';
    try {
      const response = await fetch(`${apiBaseUrl}/workflow/definitions/${versionId}/${action}`, {
        method: 'POST'
      });
      if (response.ok) {
        fetchLatestDefinition();
        fetchVersionHistory();
        setStatusMessage('Status updated successfully.');
        setTimeout(() => setStatusMessage(null), 3000);
      } else {
        const resData = await response.json();
        setErrorMessage(resData.message || 'Failed to update version status.');
      }
    } catch (e) {
      setErrorMessage(`Network error: ${e.message}`);
    }
  };

  return (
    <div style={styles.container}>
      {/* Modeler Header Toolbar */}
      <header style={styles.header}>
        <div>
          <h2 style={styles.title}>BPMN Workflow Designer ({specId})</h2>
          <p style={styles.subtitle}>
            Active Version: {versionInfo.version > 0 ? `v${versionInfo.version}` : 'None (Draft)'} 
            <span style={versionInfo.is_active ? styles.activeBadge : styles.draftBadge}>
              {versionInfo.is_active ? 'Active' : 'Inactive Draft'}
            </span>
          </p>
        </div>
        <div style={styles.actions}>
          <button onClick={handleSaveDraft} disabled={isSaving || isPublishing} style={styles.buttonSecondary}>
            {isSaving ? 'Saving...' : 'Save Draft'}
          </button>
          <button onClick={handlePublish} disabled={isSaving || isPublishing} style={styles.buttonPrimary}>
            {isPublishing ? 'Publishing...' : 'Publish Version'}
          </button>
        </div>
      </header>

      {/* Notifications Banners */}
      {statusMessage && <div style={styles.successAlert}>{statusMessage}</div>}
      {errorMessage && <div style={styles.errorAlert}>{errorMessage}</div>}

      <div style={styles.workspace}>
        {/* BPMN Canvas Container */}
        <div ref={containerRef} style={styles.canvas} />

        {/* Versions Sidebar */}
        <aside style={styles.sidebar}>
          <h3 style={styles.sidebarTitle}>Versions Index</h3>
          <div style={styles.versionsList}>
            {versionsList.map((ver) => (
              <div key={ver.id} style={styles.versionCard}>
                <div style={styles.versionHeader}>
                  <span style={styles.versionLabel}>Version {ver.version}</span>
                  <span style={ver.is_active ? styles.activeText : styles.inactiveText}>
                    {ver.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p style={styles.versionDesc}>{ver.description}</p>
                <div style={styles.versionActions}>
                  <button 
                    onClick={() => handleToggleVersion(ver.id, ver.is_active)}
                    style={ver.is_active ? styles.buttonDeactivate : styles.buttonActivate}
                  >
                    {ver.is_active ? 'Deactivate' : 'Set Active'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

// Premium Aesthetics CSS-in-JS style configurations
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    backgroundColor: '#1E1E2F',
    color: '#E5E5E5'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#11111F',
    borderBottom: '1px solid #2A2A3F'
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: '#FFFFFF'
  },
  subtitle: {
    margin: '4px 0 0 0',
    fontSize: '13px',
    color: '#8A8A9F',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  activeBadge: {
    fontSize: '11px',
    backgroundColor: '#28A745',
    color: '#FFFFFF',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: 500
  },
  draftBadge: {
    fontSize: '11px',
    backgroundColor: '#FFC107',
    color: '#11111F',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: 500
  },
  actions: {
    display: 'flex',
    gap: '12px'
  },
  buttonPrimary: {
    backgroundColor: '#6C5CE7',
    color: '#FFFFFF',
    border: 'none',
    padding: '10px 18px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'background 0.2s'
  },
  buttonSecondary: {
    backgroundColor: '#2A2A3F',
    color: '#E5E5E5',
    border: '1px solid #3F3F5F',
    padding: '10px 18px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer'
  },
  workspace: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden'
  },
  canvas: {
    flex: 1,
    height: '100%',
    backgroundColor: '#FAFAFA', // Standard light grey canvas for clear BPMN drawing visibility
  },
  sidebar: {
    width: '320px',
    backgroundColor: '#11111F',
    borderLeft: '1px solid #2A2A3F',
    display: 'flex',
    flexDirection: 'column',
    padding: '20px'
  },
  sidebarTitle: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    fontWeight: 600,
    color: '#FFFFFF'
  },
  versionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    overflowY: 'auto',
    flex: 1
  },
  versionCard: {
    backgroundColor: '#1E1E2F',
    border: '1px solid #2A2A3F',
    borderRadius: '8px',
    padding: '12px'
  },
  versionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px'
  },
  versionLabel: {
    fontWeight: 600,
    fontSize: '14px'
  },
  activeText: {
    color: '#28A745',
    fontSize: '12px',
    fontWeight: 500
  },
  inactiveText: {
    color: '#8A8A9F',
    fontSize: '12px'
  },
  versionDesc: {
    margin: '0 0 10px 0',
    fontSize: '12px',
    color: '#8A8A9F',
    lineHeight: '1.4'
  },
  versionActions: {
    display: 'flex',
    justifyContent: 'flex-end'
  },
  buttonActivate: {
    backgroundColor: 'transparent',
    color: '#6C5CE7',
    border: '1px solid #6C5CE7',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  buttonDeactivate: {
    backgroundColor: 'transparent',
    color: '#DC3545',
    border: '1px solid #DC3545',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  successAlert: {
    padding: '12px 24px',
    backgroundColor: '#28A74522',
    color: '#28A745',
    borderBottom: '1px solid #28A74533',
    fontSize: '14px'
  },
  errorAlert: {
    padding: '12px 24px',
    backgroundColor: '#DC354522',
    color: '#DC3545',
    borderBottom: '1px solid #DC354533',
    fontSize: '14px'
  }
};
