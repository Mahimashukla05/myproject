import React from 'react';

export default function ParcelDetailModal({ parcel, onClose }) {
  if (!parcel) return null;

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

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
    }}>
      <div className="card" style={{ width: '90%', maxWidth: '650px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: '#fff', borderRadius: '8px', padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e5e7eb', pb: '0.75rem', mb: '1rem' }}>
          <h2 style={{ margin: 0 }}>Parcel Details: <span style={{ fontFamily: 'monospace' }}>{parcel.parcelId}</span></h2>
          <button className="btn btn-secondary" style={{ width: 'auto', padding: '0.25rem 0.65rem' }} onClick={onClose}>Close</button>
        </div>

        {parcel.failureReason && (
          <div style={{ padding: '0.75rem 1rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px', color: '#991b1b', marginBottom: '1.5rem' }}>
            <strong style={{ display: 'block', marginBottom: '0.2rem', fontSize: '0.9rem' }}>⚠️ Reason of Failure:</strong>
            <span style={{ fontSize: '0.85rem' }}>{parcel.failureReason}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <strong>Status:</strong>{' '}
            <span style={{
              padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 700,
              backgroundColor: parcel.status === 'FAILED' ? '#fee2e2' : '#f3f4f6',
              color: getStatusColor(parcel.status)
            }}>
              {parcel.status}
            </span>
          </div>
          <div><strong>Department:</strong> {parcel.department || 'Unassigned'}</div>
          <div><strong>Sender:</strong> {parcel.senderName} ({parcel.senderContact})</div>
          <div><strong>Receiver:</strong> {parcel.receiverName} ({parcel.receiverContact})</div>
          <div><strong>Origin:</strong> {parcel.origin}</div>
          <div><strong>Destination:</strong> {parcel.destination}</div>
          <div><strong>Weight:</strong> {parcel.weightKg} kg</div>
          <div><strong>Value:</strong> €{parcel.valueEur}</div>
          <div><strong>Insurance Required:</strong> {parcel.insuranceRequired ? 'Yes' : 'No'}</div>
          <div><strong>Insurance Status:</strong> {parcel.insuranceStatus}</div>
          <div><strong>Submitted By:</strong> {parcel.submittedBy}</div>
          <div><strong>Submitted At:</strong> {new Date(parcel.submittedAt).toLocaleString()}</div>
        </div>

        <div style={{ backgroundColor: '#f9fafb', padding: '1rem', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>Lifecycle Progress Overview</h4>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
            {['RECEIVED', 'ROUTING_EVALUATED', 'AWAITING_INSURANCE', 'INSURANCE_APPROVED', 'ASSIGNED', 'IN_PROCESSING', 'COMPLETED', 'FAILED'].map((step, idx) => {
              const isCurrent = parcel.status === step;
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
