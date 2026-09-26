import React, { useState } from 'react';
import { apiFetch } from '../services/api.js';
import { getCsrfToken } from '../services/auth.js';

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
      const response = await apiFetch('/api/parcels/batch', {
        method: 'POST',
        headers: {
          ...(getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken() } : {}),
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
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <input
            type="file"
            accept=".json,.xml,application/json,application/xml,text/xml"
            onChange={handleFileChange}
            disabled={loading}
            style={{ padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px', flex: '1 1 250px', minWidth: '200px' }}
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

          {/* Container Metadata & Metric Cards */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1rem',
            padding: '1rem',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            marginBottom: '1.5rem'
          }}>
            {batchResult.containerId && (
              <div style={{ minWidth: '120px', flex: '1 1 auto' }}>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', display: 'block', fontWeight: 600 }}>Container ID</span>
                <strong style={{ fontSize: '0.95rem', color: '#0f172a', fontFamily: 'monospace' }}>{batchResult.containerId}</strong>
              </div>
            )}
            {batchResult.shippingDate && (
              <div style={{ minWidth: '120px', flex: '1 1 auto' }}>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', display: 'block', fontWeight: 600 }}>Shipping Date</span>
                <strong style={{ fontSize: '0.95rem', color: '#0f172a' }}>{batchResult.shippingDate}</strong>
              </div>
            )}
            <div style={{ minWidth: '90px', flex: '1 1 auto' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', display: 'block', fontWeight: 600 }}>Total Parcels</span>
              <strong style={{ fontSize: '1.1rem', color: '#0f172a' }}>{batchResult.total}</strong>
            </div>
            <div style={{ minWidth: '90px', flex: '1 1 auto' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#166534', display: 'block', fontWeight: 600 }}>Successful</span>
              <strong style={{ fontSize: '1.1rem', color: '#166534' }}>{batchResult.successful}</strong>
            </div>
            <div style={{ minWidth: '90px', flex: '1 1 auto' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#991b1b', display: 'block', fontWeight: 600 }}>Failed</span>
              <strong style={{ fontSize: '1.1rem', color: '#991b1b' }}>{batchResult.failed}</strong>
            </div>
          </div>

          {batchResult.results && batchResult.results.length > 0 && (
            <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '650px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>#</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Parcel ID</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Recipient Name</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Address (Street, No, Zip, City)</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Weight</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Value</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Status</th>
                    <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#475569' }}>Routing / Details</th>
                  </tr>
                </thead>
                <tbody>
                  {batchResult.results.map((res, idx) => {
                    const addressStr = [
                      res.street,
                      res.houseNumber,
                      res.postalCode,
                      res.city
                    ].filter(Boolean).join(' ') || res.destination || 'N/A';

                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0', backgroundColor: idx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#64748b' }}>{res.index || idx + 1}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', fontWeight: 600, fontSize: '0.85rem' }}>{res.parcelId}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem' }}>{res.recipientName || res.receiverName || 'N/A'}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', maxWidth: '200px', wordBreak: 'break-word' }}>{addressStr}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem' }}>{res.weightKg !== undefined && res.weightKg !== null ? `${res.weightKg} kg` : 'N/A'}</td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem' }}>{res.valueEur !== undefined && res.valueEur !== null ? `€${res.valueEur}` : 'N/A'}</td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            backgroundColor: res.status === 'SUCCESS' ? '#dcfce7' : '#fee2e2',
                            color: res.status === 'SUCCESS' ? '#166534' : '#991b1b'
                          }}>
                            {res.status}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem' }}>
                          {res.status === 'SUCCESS' ? (
                            <span style={{ color: '#166534' }}>
                              {res.department ? `Routed to: ${res.department}` : 'Parcel created (RECEIVED)'}
                            </span>
                          ) : (
                            <ul style={{ margin: 0, paddingLeft: '1rem', color: '#991b1b', fontSize: '0.8rem' }}>
                              {res.errors && res.errors.map((err, eIdx) => (
                                <li key={eIdx}>{err}</li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
