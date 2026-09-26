import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';

export default function AuditLogTable() {
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  const [actionFilter, setActionFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      if (actionFilter.trim()) params.append('action', actionFilter.trim());
      if (actorFilter.trim()) params.append('actorUsername', actorFilter.trim());
      if (roleFilter.trim()) params.append('actorRole', roleFilter.trim());

      const res = await apiFetch(`/api/admin/audit-logs?${params.toString()}`);
      const data = await res.json();

      if (!res.ok) {
        setErrorMsg(data.error || 'Failed to fetch audit logs');
        setLogs([]);
      } else {
        setLogs(data.logs || []);
        setTotal(data.total || 0);
        setTotalPages(data.totalPages || 1);
      }
    } catch (err) {
      setErrorMsg('Network error connecting to audit log service');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, limit, actionFilter, actorFilter, roleFilter]);

  const renderDetails = (details) => {
    if (!details || Object.keys(details).length === 0) return '—';
    return Object.entries(details)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
      .join(' | ');
  };

  return (
    <section className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0, color: 'var(--primary-accent)' }}>System Audit Logs (Admin Only)</h2>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Total Audit Events: <strong>{total}</strong>
        </span>
      </div>

      {/* Filter Toolbar */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Filter by Action..."
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid var(--border-color)', fontSize: '0.85rem', flex: '1 1 180px' }}
        />
        <input
          type="text"
          placeholder="Filter by Actor Username..."
          value={actorFilter}
          onChange={(e) => { setActorFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid var(--border-color)', fontSize: '0.85rem', flex: '1 1 180px' }}
        />
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid var(--border-color)', fontSize: '0.85rem', flex: '1 1 140px' }}
        >
          <option value="">All Roles</option>
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="user">User</option>
        </select>
      </div>

      {loading ? (
        <div className="empty-state">
          <p>Loading audit logs...</p>
        </div>
      ) : errorMsg ? (
        <div className="empty-state" style={{ backgroundColor: '#fef2f2', borderColor: '#fca5a5' }}>
          <p style={{ color: '#991b1b', fontWeight: 600 }}>{errorMsg}</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <p>No audit events match the selected criteria.</p>
        </div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#f1f5f9', textAlign: 'left', borderBottom: '2px solid var(--border-color)' }}>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Timestamp (UTC)</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Actor</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Role</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Action</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Parcel ID</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log._id || log.timestamp} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.6rem 0.75rem', whiteSpace: 'nowrap' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600 }}>
                      {log.actorUsername}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      <span className="role-tag" style={{ fontSize: '0.7rem' }}>{log.actorRole}</span>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600, color: 'var(--primary-accent)' }}>
                      {log.action}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      {log.parcelId ? <code>{log.parcelId}</code> : '—'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', color: 'var(--text-muted)', maxWidth: '300px', wordBreak: 'break-word' }}>
                      {renderDetails(log.details)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Page <strong>{page}</strong> of <strong>{totalPages}</strong>
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
              >
                Previous
              </button>
              <button
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
