import React, { useState } from 'react';

export default function BatchUpload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [batchResult, setBatchResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMsg('');
      setBatchResult(null);
    }
  };

  const getCsrfToken = () => {
    const name = 'csrf_access_token=';
    const decodedCookies = decodeURIComponent(document.cookie);
    const ca = decodedCookies.split(';');
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i].trim();
      if (c.indexOf(name) === 0) {
        return c.substring(name.length, c.length);
      }
    }
    return '';
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg('Please select a JSON or XML file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    setLoading(true);
    setErrorMsg('');
    setBatchResult(null);

    try {
      const response = await fetch('/api/parcels/batch', {
        method: 'POST',
        headers: {
          'X-CSRF-Token': getCsrfToken(),
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setErrorMsg(data.error || 'Batch upload failed');
      } else {
        setBatchResult(data);
      }
    } catch (err) {
      setErrorMsg('Network or server error during batch upload.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" style={{ marginTop: '1.5rem' }}>
      <h2>Batch Parcel Upload (JSON / XML)</h2>
      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            type="file"
            accept=".json,.xml,application/json,application/xml,text/xml"
            onChange={handleFileChange}
            disabled={loading}
            style={{ padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px', flex: 1 }}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !selectedFile}
            style={{ width: 'auto', padding: '0.5rem 1.25rem' }}
          >
            {loading ? 'Uploading...' : 'Upload Batch'}
          </button>
        </div>
      </form>

      {errorMsg && (
        <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '4px' }}>
          {errorMsg}
        </div>
      )}

      {batchResult && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3>Batch Results Summary</h3>
          <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem' }}>
            <div><strong>Total:</strong> {batchResult.total}</div>
            <div style={{ color: '#166534' }}><strong>Successful:</strong> {batchResult.successful}</div>
            <div style={{ color: '#991b1b' }}><strong>Failed:</strong> {batchResult.failed}</div>
          </div>

          {batchResult.results && batchResult.results.length > 0 && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '0.5rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f3f4f6', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ padding: '0.5rem' }}>Parcel ID</th>
                    <th style={{ padding: '0.5rem' }}>Status</th>
                    <th style={{ padding: '0.5rem' }}>Details / Validation Errors</th>
                  </tr>
                </thead>
                <tbody>
                  {batchResult.results.map((res, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <td style={{ padding: '0.5rem', fontFamily: 'monospace' }}>{res.parcelId}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          backgroundColor: res.status === 'SUCCESS' ? '#dcfce7' : '#fee2e2',
                          color: res.status === 'SUCCESS' ? '#166534' : '#991b1b'
                        }}>
                          {res.status}
                        </span>
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {res.status === 'SUCCESS' ? (
                          <span style={{ color: '#166534' }}>Parcel created & routed successfully</span>
                        ) : (
                          <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#991b1b' }}>
                            {res.errors && res.errors.map((err, eIdx) => (
                              <li key={eIdx}>{err}</li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
