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

  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successResult, setSuccessResult] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
    setErrorMsg('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessResult(null);

    const newFieldErrors = {};
    const missing = [];
    const nameRegex = /^[A-Za-z ]+$/;
    const phoneRegex = /^\d{10}$/;

    // Validate Sender Name
    if (!formData.senderName.trim()) {
      missing.push('Sender Name');
      newFieldErrors.senderName = 'Sender Name is required.';
    } else if (!nameRegex.test(formData.senderName.trim())) {
      newFieldErrors.senderName = 'Must contain only English alphabets (A-Z, a-z) and spaces. No numbers or special characters allowed.';
    }

    // Validate Sender Contact (Exactly 10 digits)
    if (!formData.senderContact.trim()) {
      missing.push('Sender Contact');
      newFieldErrors.senderContact = 'Sender Contact is required.';
    } else if (!phoneRegex.test(formData.senderContact.trim())) {
      newFieldErrors.senderContact = 'Phone number must be exactly 10 digits.';
    }

    // Validate Receiver Name
    if (!formData.receiverName.trim()) {
      missing.push('Receiver Name');
      newFieldErrors.receiverName = 'Receiver Name is required.';
    } else if (!nameRegex.test(formData.receiverName.trim())) {
      newFieldErrors.receiverName = 'Must contain only English alphabets (A-Z, a-z) and spaces. No numbers or special characters allowed.';
    }

    // Validate Receiver Contact (Exactly 10 digits)
    if (!formData.receiverContact.trim()) {
      missing.push('Receiver Contact');
      newFieldErrors.receiverContact = 'Receiver Contact is required.';
    } else if (!phoneRegex.test(formData.receiverContact.trim())) {
      newFieldErrors.receiverContact = 'Phone number must be exactly 10 digits.';
    }

    // Validate Origin
    if (!formData.origin.trim()) {
      missing.push('Origin');
      newFieldErrors.origin = 'Origin is required.';
    } else if (!nameRegex.test(formData.origin.trim())) {
      newFieldErrors.origin = 'Must contain only English alphabets (A-Z, a-z) and spaces. No numbers or special characters allowed.';
    }

    // Validate Destination
    if (!formData.destination.trim()) {
      missing.push('Destination');
      newFieldErrors.destination = 'Destination is required.';
    } else if (!nameRegex.test(formData.destination.trim())) {
      newFieldErrors.destination = 'Must contain only English alphabets (A-Z, a-z) and spaces. No numbers or special characters allowed.';
    }

    // Origin and Destination Same Rule Check
    if (formData.origin.trim() && formData.destination.trim() && !newFieldErrors.origin && !newFieldErrors.destination) {
      if (formData.origin.trim().toLowerCase() === formData.destination.trim().toLowerCase()) {
        newFieldErrors.destination = 'Origin and Destination cannot be the same.';
      }
    }

    // Validate Weight
    if (formData.weightKg === '' || formData.weightKg === undefined || formData.weightKg === null) {
      missing.push('Weight');
      newFieldErrors.weightKg = 'Weight is required.';
    } else {
      const weightNum = parseFloat(formData.weightKg);
      if (isNaN(weightNum) || weightNum <= 0) {
        newFieldErrors.weightKg = 'Weight must be greater than 0 kg.';
      }
    }

    // Validate Value
    if (formData.valueEur === '' || formData.valueEur === undefined || formData.valueEur === null) {
      missing.push('Value');
      newFieldErrors.valueEur = 'Value is required.';
    } else {
      const valueNum = parseFloat(formData.valueEur);
      if (isNaN(valueNum) || valueNum < 0) {
        newFieldErrors.valueEur = 'Value must be non-negative (>= 0).';
      }
    }

    setFieldErrors(newFieldErrors);

    if (Object.keys(newFieldErrors).length > 0) {
      if (missing.length > 0) {
        setErrorMsg(`Missing required fields: ${missing.join(', ')}`);
      } else {
        setErrorMsg('Please fix the rule validation errors highlighted below before submitting.');
      }
      return;
    }

    const weightNum = parseFloat(formData.weightKg);
    const valueNum = parseFloat(formData.valueEur);

    setLoading(true);

    try {
      const csrfToken = getCsrfToken();
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

      const routeRes = await apiFetch(`/api/parcels/${createdParcel.parcelId}/route`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken,
        },
      });

      const routeData = await routeRes.json();
      const finalParcel = routeRes.ok ? routeData.parcel : createdParcel;

      setSuccessResult(finalParcel);
      setFieldErrors({});
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
            className={fieldErrors.senderName ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.senderName ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.senderName ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.senderName && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.senderName}</span>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Sender Contact * (10 Digits)</label>
          <input
            type="text"
            name="senderContact"
            value={formData.senderContact}
            onChange={handleChange}
            placeholder="e.g. 9876543210"
            className={fieldErrors.senderContact ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.senderContact ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.senderContact ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.senderContact && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.senderContact}</span>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Receiver Name *</label>
          <input
            type="text"
            name="receiverName"
            value={formData.receiverName}
            onChange={handleChange}
            placeholder="e.g. Bob Logistics"
            className={fieldErrors.receiverName ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.receiverName ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.receiverName ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.receiverName && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.receiverName}</span>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Receiver Contact * (10 Digits)</label>
          <input
            type="text"
            name="receiverContact"
            value={formData.receiverContact}
            onChange={handleChange}
            placeholder="e.g. 9123456789"
            className={fieldErrors.receiverContact ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.receiverContact ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.receiverContact ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.receiverContact && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.receiverContact}</span>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Origin *</label>
          <input
            type="text"
            name="origin"
            value={formData.origin}
            onChange={handleChange}
            placeholder="e.g. Mumbai Hub"
            className={fieldErrors.origin ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.origin ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.origin ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.origin && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.origin}</span>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Destination *</label>
          <input
            type="text"
            name="destination"
            value={formData.destination}
            onChange={handleChange}
            placeholder="e.g. Delhi Depot"
            className={fieldErrors.destination ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.destination ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.destination ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.destination && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.destination}</span>
            </div>
          )}
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
            className={fieldErrors.weightKg ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.weightKg ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.weightKg ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.weightKg && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.weightKg}</span>
            </div>
          )}
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
            className={fieldErrors.valueEur ? 'input-error' : ''}
            style={{
              width: '100%',
              padding: '0.45rem',
              border: fieldErrors.valueEur ? '2px solid #dc2626' : '1px solid #ccc',
              backgroundColor: fieldErrors.valueEur ? '#fef2f2' : '#fff',
              borderRadius: '4px',
            }}
          />
          {fieldErrors.valueEur && (
            <div className="field-error-popup" style={{ color: '#dc2626', fontSize: '0.78rem', marginTop: '0.25rem', padding: '0.25rem 0.5rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span>⚠️</span> <span>{fieldErrors.valueEur}</span>
            </div>
          )}
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
