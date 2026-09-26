import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import RuleManagement from '../components/RuleManagement.jsx';

describe('Phase 5 — Rule Management Frontend Components', () => {
  const mockActiveRules = {
    version: 1,
    isActive: true,
    activatedAt: '2026-09-26T10:00:00Z',
    activatedBy: 'system',
    departmentRules: [
      { department: 'MAIL', maxWeight: 1.0, maxOp: 'LTE' },
      { department: 'REGULAR', minWeight: 1.0, minOp: 'GT', maxWeight: 10.0, maxOp: 'LTE' },
      { department: 'HEAVY', minWeight: 10.0, minOp: 'GT', maxWeight: null }
    ],
    insuranceRule: { thresholdEur: 1000.0, operator: 'GT' }
  };

  const mockRequests = [
    {
      requestId: 'RCR-000001',
      action: 'MODIFY',
      category: 'INSURANCE',
      proposedChange: { thresholdEur: 800.0, operator: 'GT' },
      reason: 'Lower threshold for holiday season',
      requestedBy: 'operator1',
      status: 'PENDING',
      requestedAt: '2026-09-26T11:00:00Z'
    }
  ];

  const mockHistory = [
    {
      version: 1,
      isActive: true,
      activatedAt: '2026-09-26T10:00:00Z',
      activatedBy: 'system'
    }
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Admin rule management renders active rule configuration & version history', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      if (url.includes('/api/routing-rules/history')) {
        return Promise.resolve({ ok: true, json: async () => ({ history: mockHistory }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="admin" />);

    expect(await screen.findByText(/Routing Rule Management/i)).toBeInTheDocument();
    expect(await screen.findByText(/Active Rule Configuration \(Version 1\)/i)).toBeInTheDocument();
    expect(screen.getByText('MAIL')).toBeInTheDocument();
    expect(screen.getByText('Rule Version History')).toBeInTheDocument();
    expect(screen.getByText('Version 1')).toBeInTheDocument();
  });

  it('2. Operator rule management renders active rules & submission form', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="operator" />);

    expect(await screen.findByText(/Routing Rule Management \(Operator Read-Only & Requests\)/i)).toBeInTheDocument();
    expect(screen.getByText('Submit Rule Change Request')).toBeInTheDocument();
    expect(screen.queryByText('Rule Version History')).not.toBeInTheDocument();
  });

  it('3. Operator form submits rule change request successfully', async () => {
    const fetchSpy = vi.fn().mockImplementation((url, options) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests') && (!options || options.method === 'GET')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      if (url.includes('/api/rule-change-requests') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, request: { requestId: 'RCR-000002', status: 'PENDING' } })
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
    global.fetch = fetchSpy;

    render(<RuleManagement userRole="operator" />);

    const reasonInput = await screen.findByPlaceholderText('Explain why this rule change is requested...');
    fireEvent.change(reasonInput, { target: { value: 'High package volume demand' } });

    const submitBtn = screen.getByRole('button', { name: 'Submit Change Request' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/submitted successfully/i)).toBeInTheDocument();
    });
  });

  it('4. Operator form displays validation error when submitting with empty reason', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="operator" />);

    const submitBtn = await screen.findByRole('button', { name: 'Submit Change Request' });
    fireEvent.click(submitBtn);

    expect(await screen.findByText('Please enter a reason for the rule change request.')).toBeInTheDocument();
  });

  it('5. Operator pending requests table displays Withdraw action for operator', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="operator" />);

    expect(await screen.findByText('RCR-000001')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Withdraw' })).toBeInTheDocument();
  });

  it('6. Admin pending requests table displays Approve and Reject actions', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      if (url.includes('/api/routing-rules/history')) {
        return Promise.resolve({ ok: true, json: async () => ({ history: mockHistory }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="admin" />);

    expect(await screen.findByText('RCR-000001')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
  });

  it('7. Admin approve modal opens, confirms, and calls approval API with confirm: true', async () => {
    const fetchSpy = vi.fn().mockImplementation((url, options) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests/RCR-000001/approve') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true, activeRuleVersion: { version: 2 } })
        });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      if (url.includes('/api/routing-rules/history')) {
        return Promise.resolve({ ok: true, json: async () => ({ history: mockHistory }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
    global.fetch = fetchSpy;

    render(<RuleManagement userRole="admin" />);

    const approveBtn = await screen.findByRole('button', { name: 'Approve' });
    fireEvent.click(approveBtn);

    expect(screen.getByText('Confirm Rule Activation')).toBeInTheDocument();

    const input = screen.getByPlaceholderText('ACTIVATE');
    fireEvent.change(input, { target: { value: 'ACTIVATE' } });

    const confirmBtn = screen.getByRole('button', { name: 'Confirm & Activate' });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/rule-change-requests/RCR-000001/approve'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ confirmation: 'ACTIVATE' })
        })
      );
    });
  });

  it('8. Admin reject modal requires rejection reason and submits rejection API', async () => {
    const fetchSpy = vi.fn().mockImplementation((url, options) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests/RCR-000001/reject') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true })
        });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: mockRequests }) });
      }
      if (url.includes('/api/routing-rules/history')) {
        return Promise.resolve({ ok: true, json: async () => ({ history: mockHistory }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
    global.fetch = fetchSpy;

    render(<RuleManagement userRole="admin" />);

    const rejectBtn = await screen.findByRole('button', { name: 'Reject' });
    fireEvent.click(rejectBtn);

    expect(screen.getByText('Reject Rule Change Request')).toBeInTheDocument();

    const textInput = screen.getByPlaceholderText('Enter rejection reason...');
    fireEvent.change(textInput, { target: { value: 'Threshold too low' } });

    const submitReject = screen.getByRole('button', { name: 'Reject Request' });
    fireEvent.click(submitReject);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/rule-change-requests/RCR-000001/reject'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ reason: 'Threshold too low' })
        })
      );
    });
  });

  it('9. Handles API error gracefully when fetching active rules fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ success: false, error: 'Internal Server Error' })
    });

    render(<RuleManagement userRole="operator" />);

    expect(await screen.findByText('Routing Rule Management (Operator Read-Only & Requests)')).toBeInTheDocument();
  });

  it('10. Renders empty change requests state when list is empty', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/routing-rules/active')) {
        return Promise.resolve({ ok: true, json: async () => ({ activeRules: mockActiveRules }) });
      }
      if (url.includes('/api/rule-change-requests')) {
        return Promise.resolve({ ok: true, json: async () => ({ requests: [] }) });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(<RuleManagement userRole="operator" />);

    expect(await screen.findByText('No rule change requests found.')).toBeInTheDocument();
  });
});
