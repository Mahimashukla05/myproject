import React, { useState } from 'react';
import { apiFetch } from '../services/api.js';
import { getCsrfToken } from '../services/auth.js';

export default function SingleParcelUpload({ onParcelCreated }) {
  const [formData, setFormData] = useState({
    senderName: '',
    senderContact: '',
    receiverName: '',
    receiverContact: '',
    origin: '',
    destination: '',
    weightKg: '',
    valueEur: '',
  });

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successResult, setSuccessResult] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setErrorMsg('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessResult(null);

    const missing = [];
    if (!formData.senderName.trim()) missing.push('Sender Name');
    if (!formData.senderContact.trim()) missing.push('Sender Contact');
    if (!formData.receiverName.trim()) missing.push('Receiver Name');
    if (!formData.receiverContact.trim()) missing.push('Receiver Contact');
    if (!formData.origin.trim()) missing.push('Origin');
    if (!formData.destination.trim()) missing.push('Destination');
    if (!formData.weightKg) missing.push('Weight');
    if (formData.valueEur === '') missing.push('Value');

    if (missing.length > 0) {
      setErrorMsg(`Missing required fields: ${missing.join(', ')}`);
      return;
    }

    const weightNum = parseFloat(formData.weightKg);
    const valueNum = parseFloat(formData.valueEur);

    if (isNaN(weightNum) || weightNum <= 0) {
      setErrorMsg("Field 'weightKg' must be greater than 0.");
      return;
    }
    if (isNaN(valueNum) || valueNum < 0) {
      setErrorMsg("Field 'valueEur' must be non-negative (>= 0).");
      return;
    }

    setLoading(true);

    try {
      const csrfToken = getCsrfToken();
      // 1. Submit parcel to existing backend creation endpoint
      const createRes = await apiFetch('/api/parcels', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({
          senderName: formData.senderName.trim(),
          senderContact: formData.senderContact.trim(),
          receiverName: formData.receiverName.trim(),
          receiverContact: formData.receiverContact.trim(),
          origin: formData.origin.trim(),
          destination: formData.destination.trim(),
          weightKg: weightNum,
          valueEur: valueNum,
        }),
      });

      const createData = await createRes.json();
      if (!createRes.ok) {
        setErrorMsg(createData.error || 'Failed to create parcel.');
        return;
      }

      const createdParcel = createData.parcel;

      // 2. Trigger routing using existing backend routing endpoint
      const routeRes = await apiFetch(`/api/parcels/${createdParcel.parcelId}/route`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken,
        },
      });

      const routeData = await routeRes.json();
      const finalParcel = routeRes.ok ? routeData.parcel : createdParcel;

      setSuccessResult(finalParcel);
      setFormData({
        senderName: '',
        senderContact: '',
        receiverName: '',
        receiverContact: '',
        origin: '',
        destination: '',
        weightKg: '',
        valueEur: '',
      });

      if (onParcelCreated) {
        onParcelCreated(finalParcel);
      }
    } catch (err) {
      setErrorMsg('Network or server error submitting parcel.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" style={{ marginTop: '1.5rem' }}>
      <h2>Add Single Parcel</h2>
      {errorMsg && (
        <div style={{ padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '4px', marginBottom: '1rem' }}>
          {errorMsg}
        </div>
      )}

      {successResult && (
        <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', border: '1px solid #86efac', color: '#166534', borderRadius: '4px', marginBottom: '1rem' }}>
          Parcel <strong>{successResult.parcelId}</strong> submitted successfully! Status: <strong>{successResult.status}</strong> | Department: <strong>{successResult.department || 'N/A'}</strong>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Sender Name *</label>
          <input
            type="text"
            name="senderName"
            value={formData.senderName}
            onChange={handleChange}
            placeholder="e.g. Alice Corp"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Sender Contact *</label>
          <input
            type="text"
            name="senderContact"
            value={formData.senderContact}
            onChange={handleChange}
            placeholder="e.g. +91 9876543210"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Receiver Name *</label>
          <input
            type="text"
            name="receiverName"
            value={formData.receiverName}
            onChange={handleChange}
            placeholder="e.g. Bob Logistics"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Receiver Contact *</label>
          <input
            type="text"
            name="receiverContact"
            value={formData.receiverContact}
            onChange={handleChange}
            placeholder="e.g. +91 9123456789"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Origin *</label>
          <input
            type="text"
            name="origin"
            value={formData.origin}
            onChange={handleChange}
            placeholder="e.g. Mumbai Hub"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Destination *</label>
          <input
            type="text"
            name="destination"
            value={formData.destination}
            onChange={handleChange}
            placeholder="e.g. Delhi Depot"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Weight (kg) *</label>
          <input
            type="number"
            step="0.01"
            name="weightKg"
            value={formData.weightKg}
            onChange={handleChange}
            placeholder="e.g. 2.5"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Value (€) *</label>
          <input
            type="number"
            step="0.01"
            name="valueEur"
            value={formData.valueEur}
            onChange={handleChange}
            placeholder="e.g. 450.00"
            style={{ width: '100%', padding: '0.45rem', border: '1px solid #ccc', borderRadius: '4px' }}
          />
        </div>

        <div style={{ gridColumn: '1 / -1', marginTop: '0.5rem' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: 'auto', padding: '0.5rem 1.5rem' }}
          >
            {loading ? 'Submitting Parcel...' : 'Submit Single Parcel'}
          </button>
        </div>
      </form>
    </section>
  );
}
