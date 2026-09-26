import React, { useState, useEffect } from 'react';

export default function OperatorWorkAlerts() {
  const [alertsData, setAlertsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchOperatorAlerts = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/operator/alerts');
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.error || 'Failed to fetch operator work alerts');
        setAlertsData(null);
      } else {
        setAlertsData(data);
      }
    } catch (err) {
      setErrorMsg('Network error connecting to operator alerts service');
      setAlertsData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOperatorAlerts();
  }, []);

  if (loading) {
    return (
      <section className="card" style={{ marginBottom: '1.5rem' }}>
        <p>Loading operator workspace alerts...</p>
      </section>
    );
  }

  if (errorMsg) {
    return (
      <section className="card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', marginBottom: '1.5rem' }}>
        <h3 style={{ color: '#991b1b', margin: 0 }}>Operator Alerts Warning</h3>
        <p style={{ color: '#991b1b', fontWeight: 600, marginTop: '0.5rem' }}>{errorMsg}</p>
      </section>
    );
  }

  const failedParcelsCount = alertsData?.failedParcelsCount ?? 0;
  const failedParcels = alertsData?.failedParcels || [];
  const batchSummary = alertsData?.batchAlertsSummary || { partialFailures: 0, completeFailures: 0, formatErrors: 0 };
  const recentBatchFailures = alertsData?.recentBatchFailures || [];
  const hasAlerts = failedParcelsCount > 0 || alertsData?.batchAlertsCount > 0;

  return (
    <section className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, color: 'var(--primary-accent)' }}>Operator Work Alerts</h2>
        <button
          className="btn btn-secondary"
          onClick={fetchOperatorAlerts}
          style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
        >
          Refresh
        </button>
      </div>

      {!hasAlerts ? (
        <div className="empty-state" style={{ backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }}>
          <p style={{ color: '#15803d', fontWeight: 600 }}>
            ✓ No operational work alerts. All your submitted parcels and batch uploads are clear.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Failed Parcels Alert Block */}
          {failedParcelsCount > 0 && (
            <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px', padding: '1rem' }}>
              <h3 style={{ color: '#991b1b', fontSize: '1rem', marginTop: 0, marginBottom: '0.5rem' }}>
                Technical Parcel Failures ({failedParcelsCount})
              </h3>
              <ul style={{ paddingLeft: '1.25rem', color: '#991b1b', fontSize: '0.85rem' }}>
                {failedParcels.map((p) => (
                  <li key={p.parcelId} style={{ marginBottom: '0.25rem' }}>
                    Parcel <code>{p.parcelId}</code> — Reason: {p.failureReason || 'Technical failure during processing'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Batch Upload Alerts Block */}
          {alertsData?.batchAlertsCount > 0 && (
            <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', padding: '1rem' }}>
              <h3 style={{ color: '#92400e', fontSize: '1rem', marginTop: 0, marginBottom: '0.5rem' }}>
                Batch Upload Issues ({alertsData.batchAlertsCount})
              </h3>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: '#92400e', marginBottom: '0.75rem' }}>
                <span>Partial Failures: <strong>{batchSummary.partialFailures}</strong></span>
                <span>Complete Failures: <strong>{batchSummary.completeFailures}</strong></span>
                <span>Format Errors: <strong>{batchSummary.formatErrors}</strong></span>
              </div>

              {recentBatchFailures.length > 0 && (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', color: '#92400e' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #fde68a', textAlign: 'left' }}>
                        <th style={{ padding: '0.4rem' }}>Timestamp</th>
                        <th style={{ padding: '0.4rem' }}>Type</th>
                        <th style={{ padding: '0.4rem' }}>Outcome</th>
                        <th style={{ padding: '0.4rem' }}>Successful / Failed / Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentBatchFailures.map((b, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #fef3c7' }}>
                          <td style={{ padding: '0.4rem' }}>{b.timestamp ? new Date(b.timestamp).toLocaleString() : '—'}</td>
                          <td style={{ padding: '0.4rem' }}>{b.fileType}</td>
                          <td style={{ padding: '0.4rem', fontWeight: 600 }}>{b.outcome}</td>
                          <td style={{ padding: '0.4rem' }}>{b.successful} / {b.failed} / {b.total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
