import React, { useState, useEffect } from 'react';

export default function DashboardMetrics() {
  const [period, setPeriod] = useState('all');
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchMetrics = async (selectedPeriod) => {
    setLoading(true);
    setErrorMsg('');
    try {
      const response = await fetch(`/api/dashboard/summary?period=${selectedPeriod}`);
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 503) {
          setErrorMsg(data.error || 'Database unavailable');
        } else {
          setErrorMsg(data.error || 'Failed to fetch dashboard metrics');
        }
        setMetrics(null);
      } else {
        setMetrics(data);
      }
    } catch (err) {
      setErrorMsg('Network error connecting to dashboard API');
      setMetrics(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics(period);
  }, [period]);

  if (loading) {
    return (
      <section className="card" style={{ marginBottom: '1.5rem' }}>
        <p>Loading dashboard metrics...</p>
      </section>
    );
  }

  if (errorMsg) {
    return (
      <section className="card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', marginBottom: '1.5rem' }}>
        <h2 style={{ color: '#991b1b' }}>Dashboard Error</h2>
        <p style={{ color: '#991b1b', fontWeight: 600 }}>{errorMsg}</p>
      </section>
    );
  }

  const totalParcels = metrics?.totalParcels ?? 0;
  const dept = metrics?.departmentDistribution || { mail: 0, regular: 0, heavy: 0 };

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Operational Dashboard Summary</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['today', 'week', 'all'].map((p) => (
            <button
              key={p}
              className={`btn ${period === p ? 'btn-primary' : 'btn-secondary'}`}
              style={{ width: 'auto', padding: '0.35rem 0.85rem', fontSize: '0.85rem' }}
              onClick={() => setPeriod(p)}
            >
              {p === 'today' ? 'Today' : p === 'week' ? 'This Week' : 'All Time'}
            </button>
          ))}
        </div>
      </div>

      <section className="metrics-grid">
        <div className="metric-card">
          <div className="value">{totalParcels}</div>
          <div className="label">Total Parcels</div>
        </div>
        <div className="metric-card">
          <div className="value" style={{ color: '#166534' }}>{metrics?.successfullyProcessed ?? 0}</div>
          <div className="label">Successfully Processed</div>
        </div>
        <div className="metric-card">
          <div className="value" style={{ color: '#991b1b' }}>{metrics?.failed ?? 0}</div>
          <div className="label">Failed</div>
        </div>
        <div className="metric-card">
          <div className="value" style={{ color: '#d97706' }}>{metrics?.insurancePending ?? 0}</div>
          <div className="label">Insurance Pending</div>
        </div>
        <div className="metric-card">
          <div className="value" style={{ color: '#b91c1c' }}>{metrics?.insuranceRejected ?? 0}</div>
          <div className="label">Insurance Rejected</div>
        </div>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h3>Department Distribution ({period === 'today' ? 'Today' : period === 'week' ? 'This Week' : 'All Time'})</h3>
        {totalParcels === 0 ? (
          <div className="empty-state">
            <p>No parcels found for the selected time filter.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '2rem', marginTop: '0.75rem' }}>
            <div style={{ flex: 1, padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{dept.mail}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>MAIL (&le; 1 kg)</div>
            </div>
            <div style={{ flex: 1, padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{dept.regular}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>REGULAR (1 - 10 kg)</div>
            </div>
            <div style={{ flex: 1, padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{dept.heavy}</div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>HEAVY (&gt; 10 kg)</div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
