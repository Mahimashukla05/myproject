import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';
import { getCsrfToken } from '../services/auth.js';

export default function ParcelDetailModal({ parcel, userRole, onClose, onParcelUpdated }) {
  const [modalParcel, setModalParcel] = useState(parcel);
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  useEffect(() => {
    setModalParcel(parcel);
    setActionError('');
    setActionSuccess('');
  }, [parcel]);

  if (!modalParcel) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'COMPLETED': return '#166534';
      case 'FAILED': return '#991b1b';
      case 'INSURANCE_REJECTED': return '#b91c1c';
      case 'AWAITING_INSURANCE': return '#d97706';
      case 'INSURANCE_APPROVED': return '#2563eb';
      case 'IN_PROCESSING': return '#7c3aed';
      case 'ASSIGNED': return '#0284c7';
      default: return '#4b5563';
    }
  };

  const isAdmin = userRole === 'admin';
  const isEligibleForApproval = 
    modalParcel.insuranceStatus !== 'APPROVED' &&
    modalParcel.insuranceStatus !== 'REJECTED' &&
    (modalParcel.insuranceRequired === true ||
     modalParcel.status === 'AWAITING_INSURANCE' ||
     ['PENDING', 'REQUIRED', 'AWAITING_INSURANCE'].includes(modalParcel.insuranceStatus));

  const handleApproveInsurance = async () => {
    setLoading(true);
    setActionError('');
    setActionSuccess('');

    try {
      const csrfToken = getCsrfToken();
      const response = await apiFetch(`/api/parcels/${modalParcel.parcelId}/insurance/approve`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setActionError(data.error || 'Failed to approve insurance.');
      } else {
        const updated = data.parcel || {
          ...modalParcel,
          status: 'INSURANCE_APPROVED',
          insuranceStatus: 'APPROVED',
        };
        setModalParcel(updated);
        setActionSuccess(`Insurance for parcel ${updated.parcelId} has been successfully APPROVED!`);
        if (onParcelUpdated) {
          onParcelUpdated(updated);
        }
      }
    } catch (err) {
      setActionError('Network error while approving insurance.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
    }}>
      <div className="card" style={{ width: '90%', maxWidth: '650px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e5e7eb', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>Parcel Details: <span style={{ fontFamily: 'monospace' }}>{modalParcel.parcelId}</span></h2>
          <button className="btn btn-secondary" style={{ width: 'auto', padding: '0.25rem 0.65rem' }} onClick={onClose}>Close</button>
        </div>

        {actionError && (
          <div style={{ padding: '0.75rem 1rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px', color: '#991b1b', marginBottom: '1rem' }}>
            {actionError}
          </div>
        )}

        {actionSuccess && (
          <div style={{ padding: '0.75rem 1rem', backgroundColor: '#f0fdf4', border: '1px solid #86efac', borderRadius: '6px', color: '#166534', marginBottom: '1rem' }}>
            {actionSuccess}
          </div>
        )}

        {modalParcel.failureReason && (
          <div style={{ padding: '0.75rem 1rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px', color: '#991b1b', marginBottom: '1.5rem' }}>
            <strong style={{ display: 'block', marginBottom: '0.2rem', fontSize: '0.9rem' }}>⚠️ Reason of Failure:</strong>
            <span style={{ fontSize: '0.85rem' }}>{modalParcel.failureReason}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <strong>Status:</strong>{' '}
            <span style={{
              padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 700,
              backgroundColor: modalParcel.status === 'FAILED' ? '#fee2e2' : '#f3f4f6',
              color: getStatusColor(modalParcel.status)
            }}>
              {modalParcel.status}
            </span>
          </div>
          <div><strong>Department:</strong> {modalParcel.department || 'Unassigned'}</div>
          <div><strong>Sender:</strong> {modalParcel.senderName} ({modalParcel.senderContact})</div>
          <div><strong>Receiver:</strong> {modalParcel.receiverName} ({modalParcel.receiverContact})</div>
          <div><strong>Origin:</strong> {modalParcel.origin}</div>
          <div><strong>Destination:</strong> {modalParcel.destination}</div>
          <div><strong>Weight:</strong> {modalParcel.weightKg} kg</div>
          <div><strong>Value:</strong> €{modalParcel.valueEur}</div>
          <div><strong>Insurance Required:</strong> {modalParcel.insuranceRequired ? 'Yes' : 'No'}</div>
          <div>
            <strong>Insurance Status:</strong>{' '}
            <span style={{
              fontWeight: 'bold',
              color: modalParcel.insuranceStatus === 'APPROVED' ? '#166534' : modalParcel.insuranceStatus === 'REJECTED' ? '#991b1b' : '#d97706'
            }}>
              {modalParcel.insuranceStatus}
            </span>
          </div>
          <div><strong>Submitted By:</strong> {modalParcel.submittedBy}</div>
          <div><strong>Submitted At:</strong> {new Date(modalParcel.submittedAt).toLocaleString()}</div>
        </div>

        {/* Admin Insurance Action Controls */}
        {isAdmin && isEligibleForApproval && (
          <div style={{
            marginBottom: '1.5rem',
            padding: '1rem',
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justify: 'space-between',
            gap: '1rem'
          }}>
            <div>
              <strong style={{ color: '#1e40af', display: 'block' }}>Admin Action Required</strong>
              <span style={{ fontSize: '0.85rem', color: '#1e3a8a' }}>This parcel requires insurance approval before it can be assigned to processing.</span>
            </div>
            <button
              className="btn btn-primary"
              style={{
                width: 'auto',
                padding: '0.5rem 1.25rem',
                backgroundColor: '#16a34a',
                borderColor: '#16a34a',
                whiteSpace: 'nowrap'
              }}
              disabled={loading}
              onClick={handleApproveInsurance}
            >
              {loading ? 'Approving...' : 'Approve Insurance'}
            </button>
          </div>
        )}

        <div style={{ backgroundColor: '#f9fafb', padding: '1rem', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>Lifecycle Progress Overview</h4>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
            {['RECEIVED', 'ROUTING_EVALUATED', 'AWAITING_INSURANCE', 'INSURANCE_APPROVED', 'ASSIGNED', 'IN_PROCESSING', 'COMPLETED', 'FAILED'].map((step, idx) => {
              const isCurrent = modalParcel.status === step;
              return (
                <div key={idx} style={{
                  padding: '0.3rem 0.6rem',
                  borderRadius: '4px',
                  backgroundColor: isCurrent ? getStatusColor(step) : '#e5e7eb',
                  color: isCurrent ? '#fff' : '#6b7280',
                  fontWeight: isCurrent ? 'bold' : 'normal'
                }}>
                  {step}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
