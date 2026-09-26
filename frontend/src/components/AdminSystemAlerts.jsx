import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';

export default function AdminSystemAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchAlerts = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await apiFetch('/api/admin/alerts');
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.error || 'Failed to fetch admin system alerts');
        setAlerts([]);
      } else {
        setAlerts(data.alerts || []);
      }
    } catch (err) {
      setErrorMsg('Network error connecting to alerts service');
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // refresh every 60s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <section className="card" style={{ marginBottom: '1.5rem' }}>
        <p>Evaluating system alerts...</p>
      </section>
    );
  }

  if (errorMsg) {
    return (
      <section className="card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', marginBottom: '1.5rem' }}>
        <h3 style={{ color: '#991b1b', margin: 0 }}>System Alerts Warning</h3>
        <p style={{ color: '#991b1b', fontWeight: 600, marginTop: '0.5rem' }}>{errorMsg}</p>
      </section>
    );
  }

  return (
    <section className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, color: 'var(--primary-accent)' }}>Admin System Alerts (Last 1 Hour)</h2>
        <button
          className="btn btn-secondary"
          onClick={fetchAlerts}
          style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
        >
          Refresh Alerts
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state" style={{ backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }}>
          <p style={{ color: '#15803d', fontWeight: 600 }}>
            ✓ All systems operating normally. No threshold spikes detected in the last hour window.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {alerts.map((alert, index) => {
            const isHigh = alert.severity === 'HIGH';
            const bgColor = isHigh ? '#fef2f2' : '#fffbeb';
            const borderColor = isHigh ? '#fca5a5' : '#fde68a';
            const textColor = isHigh ? '#991b1b' : '#92400e';
            const badgeBg = isHigh ? '#dc2626' : '#d97706';

            return (
              <div
                key={index}
                style={{
                  backgroundColor: bgColor,
                  border: `1px solid ${borderColor}`,
                  borderRadius: '6px',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.25rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span
                    style={{
                      backgroundColor: badgeBg,
                      color: '#ffffff',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px',
                      textTransform: 'uppercase'
                    }}
                  >
                    {alert.severity} SEVERITY — {alert.type}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: textColor }}>
                    Window: <strong>{alert.window}</strong>
                  </span>
                </div>
                <p style={{ color: textColor, fontWeight: 600, fontSize: '0.95rem', margin: '0.25rem 0' }}>
                  {alert.message}
                </p>
                <div style={{ fontSize: '0.8rem', color: textColor, opacity: 0.9 }}>
                  Current Observed Value: <strong>{alert.currentValue}</strong> | Threshold Limit: <strong>{alert.threshold}</strong>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
