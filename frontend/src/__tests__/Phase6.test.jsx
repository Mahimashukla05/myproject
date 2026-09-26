import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import AuditLogTable from '../components/AuditLogTable.jsx';
import AdminSystemAlerts from '../components/AdminSystemAlerts.jsx';
import OperatorWorkAlerts from '../components/OperatorWorkAlerts.jsx';

describe('Phase 6 Frontend Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. AuditLogTable renders audit logs and handles empty/loading states', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        logs: [
          {
            _id: '1',
            timestamp: '2026-09-26T12:00:00Z',
            actorUsername: 'operator1',
            actorRole: 'operator',
            action: 'BATCH_UPLOAD',
            parcelId: null,
            details: { outcome: 'SUCCESS', total: 10 }
          }
        ],
        page: 1,
        limit: 20,
        total: 1,
        totalPages: 1
      })
    });

    render(<AuditLogTable />);

    expect(await screen.findByText('System Audit Logs (Admin Only)')).toBeInTheDocument();
    expect(await screen.findByText('operator1')).toBeInTheDocument();
    expect(screen.getByText('BATCH_UPLOAD')).toBeInTheDocument();
  });

  it('2. AdminSystemAlerts renders active alerts correctly', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        alerts: [
          {
            type: 'FAILURE_RATE_SPIKE',
            severity: 'HIGH',
            message: 'Technical failure rate in the last hour is 20.0% (threshold: 15.0%).',
            currentValue: 20.0,
            threshold: 15.0,
            window: 'last_hour'
          }
        ]
      })
    });

    render(<AdminSystemAlerts />);

    expect(await screen.findByText('Admin System Alerts (Last 1 Hour)')).toBeInTheDocument();
    expect(await screen.findByText(/FAILURE_RATE_SPIKE/)).toBeInTheDocument();
    expect(screen.getByText(/Technical failure rate in the last hour/)).toBeInTheDocument();
  });

  it('3. AdminSystemAlerts renders empty normal state when no alerts exist', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        alerts: []
      })
    });

    render(<AdminSystemAlerts />);

    expect(await screen.findByText(/All systems operating normally/)).toBeInTheDocument();
  });

  it('4. OperatorWorkAlerts renders operator-scoped alerts', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        operatorId: 'op1',
        failedParcelsCount: 1,
        failedParcels: [
          { parcelId: 'P-FAIL-99', failureReason: 'Label damaged' }
        ],
        insuranceRejectionsCount: 0,
        batchAlertsCount: 1,
        batchAlertsSummary: { partialFailures: 1, completeFailures: 0, formatErrors: 0 },
        recentBatchFailures: []
      })
    });

    render(<OperatorWorkAlerts />);

    expect(await screen.findByText('Operator Work Alerts')).toBeInTheDocument();
    expect(await screen.findByText(/Technical Parcel Failures/)).toBeInTheDocument();
    expect(screen.getByText(/P-FAIL-99/)).toBeInTheDocument();
  });
});
