import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';

export default function RuleManagement({ userRole }) {
  const [activeRules, setActiveRules] = useState(null);
  const [history, setHistory] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Operator Form State
  const [action, setAction] = useState('MODIFY');
  const [category, setCategory] = useState('INSURANCE');
  const [targetDept, setTargetDept] = useState('MAIL');
  const [proposedThreshold, setProposedThreshold] = useState('');
  const [proposedMaxWeight, setProposedMaxWeight] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Admin Modal State
  const [selectedReqForApprove, setSelectedReqForApprove] = useState(null);
  const [activateConfirmation, setActivateConfirmation] = useState('');
  const [selectedReqForReject, setSelectedReqForReject] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');

  const getCsrfToken = () => {
    const name = 'csrf_access_token=';
    const decodedCookies = decodeURIComponent(document.cookie);
    const ca = decodedCookies.split(';');
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i].trim();
      if (c.indexOf(name) === 0) {
        return c.substring(name.length, c.length);
      }
    }
    return '';
  };

  const fetchData = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      // 1. Fetch Active Rules
      const rulesRes = await apiFetch('/api/routing-rules/active');
      const rulesData = await rulesRes.json();
      if (rulesRes.ok) setActiveRules(rulesData.activeRules);

      // 2. Fetch Change Requests
      const reqRes = await apiFetch('/api/rule-change-requests');
      const reqData = await reqRes.json();
      if (reqRes.ok) setRequests(reqData.requests || []);

      // 3. Fetch History for Admin
      if (userRole === 'admin') {
        const histRes = await apiFetch('/api/routing-rules/history');
        const histData = await histRes.json();
        if (histRes.ok) setHistory(histData.history || []);
      }
    } catch (err) {
      setErrorMsg('Failed to load routing rules data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [userRole]);

  const handleCreateRequest = async (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      setErrorMsg('Please enter a reason for the rule change request.');
      return;
    }

    setSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    let proposedChange = {};
    if (category === 'INSURANCE') {
      proposedChange = { thresholdEur: parseFloat(proposedThreshold) || 1000.0, operator: 'GT' };
    } else {
      proposedChange = { department: targetDept, maxWeight: parseFloat(proposedMaxWeight) || 1.0, maxOp: 'LTE' };
    }

    try {
      const response = await apiFetch('/api/rule-change-requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({
          action,
          category,
          targetDepartment: category === 'DEPARTMENT' ? targetDept : null,
          proposedChange,
          reason
        })
      });

      const data = await response.json();
      if (!response.ok) {
        setErrorMsg(data.error || 'Failed to submit change request');
      } else {
        setSuccessMsg(`Rule change request '${data.request.requestId}' submitted successfully!`);
        setReason('');
        setProposedThreshold('');
        setProposedMaxWeight('');
        fetchData();
      }
    } catch (err) {
      setErrorMsg('Error submitting change request.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedReqForApprove) return;
    if (activateConfirmation !== 'ACTIVATE') {
      setErrorMsg('Explicit confirmation "ACTIVATE" is required.');
      return;
    }
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const response = await apiFetch(`/api/rule-change-requests/${selectedReqForApprove.requestId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ confirmation: activateConfirmation })
      });

      const data = await response.json();
      if (!response.ok) {
        setErrorMsg(data.error || 'Approval failed');
      } else {
        setSuccessMsg(`Request '${selectedReqForApprove.requestId}' approved and activated Rule Version ${data.activeRuleVersion.version}!`);
        setSelectedReqForApprove(null);
        setActivateConfirmation('');
        fetchData();
      }
    } catch (err) {
      setErrorMsg('Error approving rule change request.');
    }
  };

  const handleReject = async () => {
    if (!selectedReqForReject) return;
    if (!rejectionReason.trim()) {
      setErrorMsg('Rejection reason is required.');
      return;
    }
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const response = await apiFetch(`/api/rule-change-requests/${selectedReqForReject.requestId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken()
        },
        body: JSON.stringify({ reason: rejectionReason })
      });

      const data = await response.json();
      if (!response.ok) {
        setErrorMsg(data.error || 'Rejection failed');
      } else {
        setSuccessMsg(`Request '${selectedReqForReject.requestId}' rejected.`);
        setSelectedReqForReject(null);
        setRejectionReason('');
        fetchData();
      }
    } catch (err) {
      setErrorMsg('Error rejecting rule change request.');
    }
  };

  const handleWithdraw = async (requestId) => {
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const response = await apiFetch(`/api/rule-change-requests/${requestId}/withdraw`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': getCsrfToken()
        }
      });

      const data = await response.json();
      if (!response.ok) {
        setErrorMsg(data.error || 'Withdrawal failed');
      } else {
        setSuccessMsg(`Request '${requestId}' withdrawn.`);
        fetchData();
      }
    } catch (err) {
      setErrorMsg('Error withdrawing request.');
    }
  };

  if (loading) return <section className="card"><p>Loading routing rules...</p></section>;

  return (
    <section className="card" style={{ marginTop: '1.5rem' }}>
      <h2>Routing Rule Management {userRole === 'operator' ? '(Operator Read-Only & Requests)' : '(Admin Versioning & Governance)'}</h2>

      {errorMsg && (
        <div style={{ padding: '0.75rem', backgroundColor: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '4px', marginBottom: '1rem' }}>
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', border: '1px solid #86efac', color: '#166534', borderRadius: '4px', marginBottom: '1rem' }}>
          {successMsg}
        </div>
      )}

      {/* Active Rules Card */}
      <div style={{ backgroundColor: '#f9fafb', padding: '1rem', borderRadius: '6px', border: '1px solid #e5e7eb', marginBottom: '1.5rem' }}>
        <h3>Active Rule Configuration (Version {activeRules?.version ?? 1})</h3>
        <p style={{ fontSize: '0.85rem', color: '#6b7280', margin: '0 0 1rem 0' }}>
          Activated At: {new Date(activeRules?.activatedAt || Date.now()).toLocaleString()} | Activated By: {activeRules?.activatedBy || 'system'}
        </p>

        <h4 style={{ margin: '0.5rem 0' }}>Department Rules</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: '#e5e7eb' }}>
              <th style={{ padding: '0.4rem' }}>Department</th>
              <th style={{ padding: '0.4rem' }}>Weight Range (kg)</th>
            </tr>
          </thead>
          <tbody>
            {activeRules?.departmentRules?.map((r, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '0.4rem', fontWeight: 600 }}>{r.department}</td>
                <td style={{ padding: '0.4rem' }}>
                  {r.minWeight !== null && r.minWeight !== undefined ? `${r.minWeight} ${r.minOp || 'GT'}` : ''} weight &le; {r.maxWeight !== null ? `${r.maxWeight} kg` : '&infin;'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <h4 style={{ margin: '0.5rem 0' }}>Insurance Rule</h4>
        <p style={{ margin: 0 }}>
          Insurance Required when parcel <strong>valueEur &gt; €{activeRules?.insuranceRule?.thresholdEur ?? 1000}</strong>
        </p>
      </div>

      {/* Operator Submission Form */}
      {userRole === 'operator' && (
        <div style={{ marginBottom: '1.5rem', padding: '1rem', border: '1px solid #d1d5db', borderRadius: '6px' }}>
          <h3>Submit Rule Change Request</h3>
          <form onSubmit={handleCreateRequest} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <label style={{ flex: 1 }}>
                Action:
                <select value={action} onChange={(e) => setAction(e.target.value)} style={{ width: '100%', padding: '0.4rem' }}>
                  <option value="MODIFY">MODIFY</option>
                  <option value="ADD">ADD</option>
                  <option value="DEACTIVATE">DEACTIVATE</option>
                </select>
              </label>
              <label style={{ flex: 1 }}>
                Category:
                <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ width: '100%', padding: '0.4rem' }}>
                  <option value="INSURANCE">INSURANCE</option>
                  <option value="DEPARTMENT">DEPARTMENT</option>
                </select>
              </label>
            </div>

            {category === 'INSURANCE' ? (
              <label>
                Proposed Insurance Threshold (€):
                <input
                  type="number"
                  step="0.01"
                  placeholder="e.g. 800.00"
                  value={proposedThreshold}
                  onChange={(e) => setProposedThreshold(e.target.value)}
                  style={{ width: '100%', padding: '0.4rem', marginTop: '0.2rem' }}
                />
              </label>
            ) : (
              <div style={{ display: 'flex', gap: '1rem' }}>
                <label style={{ flex: 1 }}>
                  Target Department:
                  <select value={targetDept} onChange={(e) => setTargetDept(e.target.value)} style={{ width: '100%', padding: '0.4rem' }}>
                    <option value="MAIL">MAIL</option>
                    <option value="REGULAR">REGULAR</option>
                    <option value="HEAVY">HEAVY</option>
                  </select>
                </label>
                <label style={{ flex: 1 }}>
                  Proposed Max Weight (kg):
                  <input
                    type="number"
                    step="0.01"
                    placeholder="e.g. 1.5"
                    value={proposedMaxWeight}
                    onChange={(e) => setProposedMaxWeight(e.target.value)}
                    style={{ width: '100%', padding: '0.4rem' }}
                  />
                </label>
              </div>
            )}

            <label>
              Reason / Justification:
              <textarea
                rows="2"
                placeholder="Explain why this rule change is requested..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', marginTop: '0.2rem' }}
              />
            </label>

            <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: 'auto', alignSelf: 'flex-start' }}>
              {submitting ? 'Submitting...' : 'Submit Change Request'}
            </button>
          </form>
        </div>
      )}

      {/* Change Requests List */}
      <div>
        <h3>{userRole === 'admin' ? 'Rule Change Requests Governance' : 'My Rule Change Requests'}</h3>
        {requests.length === 0 ? (
          <div className="empty-state"><p>No rule change requests found.</p></div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: '#f3f4f6' }}>
                <th style={{ padding: '0.5rem' }}>Request ID</th>
                <th style={{ padding: '0.5rem' }}>Action / Category</th>
                <th style={{ padding: '0.5rem' }}>Reason</th>
                <th style={{ padding: '0.5rem' }}>Status</th>
                <th style={{ padding: '0.5rem' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.requestId} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '0.5rem', fontFamily: 'monospace' }}>{r.requestId}</td>
                  <td style={{ padding: '0.5rem' }}>{r.action} {r.category}</td>
                  <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{r.reason}</td>
                  <td style={{ padding: '0.5rem' }}>
                    <span style={{
                      padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 600,
                      backgroundColor: r.status === 'APPROVED' ? '#dcfce7' : r.status === 'REJECTED' ? '#fee2e2' : '#fef3c7',
                      color: r.status === 'APPROVED' ? '#166534' : r.status === 'REJECTED' ? '#991b1b' : '#92400e'
                    }}>
                      {r.status}
                    </span>
                  </td>
                  <td style={{ padding: '0.5rem' }}>
                    {userRole === 'admin' && r.status === 'PENDING' && (
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn btn-primary" style={{ width: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => { setSelectedReqForApprove(r); setActivateConfirmation(''); }}>Approve</button>
                        <button className="btn btn-secondary" style={{ width: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.8rem', color: '#991b1b' }} onClick={() => setSelectedReqForReject(r)}>Reject</button>
                      </div>
                    )}
                    {userRole === 'operator' && r.status === 'PENDING' && (
                      <button className="btn btn-secondary" style={{ width: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => handleWithdraw(r.requestId)}>Withdraw</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Admin Version History */}
      {userRole === 'admin' && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Rule Version History</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: '#f3f4f6' }}>
                <th style={{ padding: '0.5rem' }}>Version</th>
                <th style={{ padding: '0.5rem' }}>Status</th>
                <th style={{ padding: '0.5rem' }}>Activated By</th>
                <th style={{ padding: '0.5rem' }}>Activated At</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.version} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '0.5rem', fontWeight: 'bold' }}>Version {h.version}</td>
                  <td style={{ padding: '0.5rem' }}>{h.isActive ? 'ACTIVE' : 'HISTORICAL'}</td>
                  <td style={{ padding: '0.5rem' }}>{h.activatedBy || 'system'}</td>
                  <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>{new Date(h.activatedAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Admin Approve Modal */}
      {selectedReqForApprove && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '90%', maxWidth: '500px', backgroundColor: '#fff', padding: '1.5rem', borderRadius: '8px' }}>
            <h3>Confirm Rule Activation</h3>
            <p>To approve request <strong>{selectedReqForApprove.requestId}</strong> and activate a new rule version, type <strong>ACTIVATE</strong> below:</p>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>Type ACTIVATE to confirm rule activation:</label>
              <input
                type="text"
                value={activateConfirmation}
                onChange={(e) => setActivateConfirmation(e.target.value)}
                placeholder="ACTIVATE"
                style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => { setSelectedReqForApprove(null); setActivateConfirmation(''); }}>Cancel</button>
              <button className="btn btn-primary" style={{ width: 'auto' }} disabled={activateConfirmation !== 'ACTIVATE'} onClick={handleApprove}>Confirm & Activate</button>
            </div>
          </div>
        </div>
      )}

      {/* Admin Reject Modal */}
      {selectedReqForReject && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '90%', maxWidth: '500px', backgroundColor: '#fff', padding: '1.5rem', borderRadius: '8px' }}>
            <h3>Reject Rule Change Request</h3>
            <p>Specify rejection reason for request <strong>{selectedReqForReject.requestId}</strong>:</p>
            <textarea
              rows="3"
              placeholder="Enter rejection reason..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem' }}
            />
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => setSelectedReqForReject(null)}>Cancel</button>
              <button className="btn btn-primary" style={{ width: 'auto', backgroundColor: '#991b1b' }} onClick={handleReject}>Reject Request</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
