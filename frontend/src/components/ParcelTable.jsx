import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../services/api.js';

export default function ParcelTable({ onSelectParcel, userRole }) {
  const [parcels, setParcels] = useState([]);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  // Filter state
  const [statusFilter, setStatusFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [insuranceFilter, setInsuranceFilter] = useState('');
  const [searchId, setSearchId] = useState('');

  const fetchParcels = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('limit', limit);
      params.append('sort', '-submittedAt');
      if (statusFilter) params.append('status', statusFilter);
      if (deptFilter) params.append('department', deptFilter);
      if (insuranceFilter) params.append('insuranceStatus', insuranceFilter);
      if (searchId.trim()) params.append('parcelId', searchId.trim());

      const response = await fetch(getApiUrl(`/api/parcels?${params.toString()}`));
      const data = await response.json();

      if (!response.ok) {
        setErrorMsg(data.error || 'Failed to fetch parcels');
        setParcels([]);
      } else {
        setParcels(data.items || []);
        setTotal(data.total || 0);
        setTotalPages(data.totalPages || 1);
      }
    } catch (err) {
      setErrorMsg('Network error fetching parcels');
      setParcels([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchParcels();
  }, [page, limit, statusFilter, deptFilter, insuranceFilter, searchId]);

  return (
    <section className="card" style={{ marginTop: '1.5rem' }}>
      <h2>{userRole === 'user' ? 'My Submitted Parcels' : 'Operational Parcel History & Listing'}</h2>

      {/* Filter Bar */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Search by Parcel ID..."
          value={searchId}
          onChange={(e) => { setSearchId(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.75rem', border: '1px solid #ccc', borderRadius: '4px', flex: 1, minWidth: '180px' }}
        />

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.75rem', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          <option value="">All Statuses</option>
          <option value="RECEIVED">RECEIVED</option>
          <option value="ROUTING_EVALUATED">ROUTING_EVALUATED</option>
          <option value="AWAITING_INSURANCE">AWAITING_INSURANCE</option>
          <option value="INSURANCE_APPROVED">INSURANCE_APPROVED</option>
          <option value="INSURANCE_REJECTED">INSURANCE_REJECTED</option>
          <option value="ASSIGNED">ASSIGNED</option>
          <option value="IN_PROCESSING">IN_PROCESSING</option>
          <option value="COMPLETED">COMPLETED</option>
          <option value="FAILED">FAILED</option>
        </select>

        <select
          value={deptFilter}
          onChange={(e) => { setDeptFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.75rem', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          <option value="">All Departments</option>
          <option value="MAIL">MAIL</option>
          <option value="REGULAR">REGULAR</option>
          <option value="HEAVY">HEAVY</option>
        </select>

        <select
          value={insuranceFilter}
          onChange={(e) => { setInsuranceFilter(e.target.value); setPage(1); }}
          style={{ padding: '0.4rem 0.75rem', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          <option value="">All Insurance States</option>
          <option value="NOT_REQUIRED">NOT_REQUIRED</option>
          <option value="PENDING">PENDING</option>
          <option value="APPROVED">APPROVED</option>
          <option value="REJECTED">REJECTED</option>
        </select>

        <button
          className="btn btn-secondary"
          style={{ width: 'auto', padding: '0.4rem 0.75rem' }}
          onClick={() => { setStatusFilter(''); setDeptFilter(''); setInsuranceFilter(''); setSearchId(''); setPage(1); }}
        >
          Reset Filters
        </button>
      </div>

      {loading ? (
        <p>Loading parcel list...</p>
      ) : errorMsg ? (
        <div style={{ padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '4px' }}>
          {errorMsg}
        </div>
      ) : parcels.length === 0 ? (
        <div className="empty-state">
          <p>No parcels found matching the criteria.</p>
        </div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '0.5rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#f3f4f6', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '0.6rem' }}>Parcel ID</th>
                  <th style={{ padding: '0.6rem' }}>Route</th>
                  <th style={{ padding: '0.6rem' }}>Dept</th>
                  <th style={{ padding: '0.6rem' }}>Status</th>
                  <th style={{ padding: '0.6rem' }}>Insurance</th>
                  <th style={{ padding: '0.6rem' }}>Submitted At</th>
                  <th style={{ padding: '0.6rem' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {parcels.map((p) => (
                  <tr key={p.parcelId || p.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '0.6rem', fontFamily: 'monospace', fontWeight: 600 }}>{p.parcelId}</td>
                    <td style={{ padding: '0.6rem' }}>{p.origin} &rarr; {p.destination}</td>
                    <td style={{ padding: '0.6rem' }}>{p.department || 'N/A'}</td>
                    <td style={{ padding: '0.6rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 600,
                        backgroundColor: '#f3f4f6', color: '#374151'
                      }}>
                        {p.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem' }}>{p.insuranceStatus}</td>
                    <td style={{ padding: '0.6rem', fontSize: '0.85rem' }}>{new Date(p.submittedAt).toLocaleDateString()}</td>
                    <td style={{ padding: '0.6rem' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ width: 'auto', padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
                        onClick={() => onSelectParcel(p)}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #e5e7eb' }}>
            <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
              Page <strong>{page}</strong> of <strong>{totalPages}</strong> (Total: {total} parcels)
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-secondary"
                disabled={page <= 1}
                style={{ width: 'auto', padding: '0.3rem 0.75rem', fontSize: '0.85rem' }}
                onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
              >
                &larr; Previous
              </button>
              <button
                className="btn btn-secondary"
                disabled={page >= totalPages}
                style={{ width: 'auto', padding: '0.3rem 0.75rem', fontSize: '0.85rem' }}
                onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
              >
                Next &rarr;
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
