import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import DashboardMetrics from '../components/DashboardMetrics.jsx';
import ParcelTable from '../components/ParcelTable.jsx';
import ParcelDetailModal from '../components/ParcelDetailModal.jsx';

describe('Phase 4 Frontend Components', () => {
  it('1. Admin/Operator dashboard renders and displays metrics from API response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        period: 'all',
        totalParcels: 10,
        successfullyProcessed: 6,
        failed: 1,
        insurancePending: 2,
        insuranceRejected: 1,
        departmentDistribution: { mail: 4, regular: 4, heavy: 2 }
      })
    });

    render(<DashboardMetrics />);

    expect(await screen.findByText('Operational Dashboard Summary')).toBeInTheDocument();
    expect(await screen.findByText('10')).toBeInTheDocument();
    expect(screen.getByText('Successfully Processed')).toBeInTheDocument();
  });

  it('2. Time filter changes request/state', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        period: 'today',
        totalParcels: 2,
        successfullyProcessed: 1,
        failed: 0,
        insurancePending: 1,
        insuranceRejected: 0,
        departmentDistribution: { mail: 1, regular: 1, heavy: 0 }
      })
    });
    global.fetch = fetchSpy;

    render(<DashboardMetrics />);

    const todayBtn = await screen.findByRole('button', { name: 'Today' });
    fireEvent.click(todayBtn);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('period=today'), expect.anything());
    });
  });

  it('3. Renders loading state', () => {
    global.fetch = vi.fn().mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<DashboardMetrics />);
    expect(screen.getByText('Loading dashboard metrics...')).toBeInTheDocument();
  });

  it('4. Renders explicit error state on API failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ success: false, error: 'Database unavailable' })
    });

    render(<DashboardMetrics />);

    expect(await screen.findByText('Dashboard Error')).toBeInTheDocument();
    expect(screen.getByText('Database unavailable')).toBeInTheDocument();
  });

  it('5. Renders empty state when zero parcels exist', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        period: 'all',
        totalParcels: 0,
        successfullyProcessed: 0,
        failed: 0,
        insurancePending: 0,
        insuranceRejected: 0,
        departmentDistribution: { mail: 0, regular: 0, heavy: 0 }
      })
    });

    render(<DashboardMetrics />);

    expect(await screen.findByText('No parcels found for the selected time filter.')).toBeInTheDocument();
  });

  it('6. Parcel table renders and displays list items', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        items: [
          {
            parcelId: 'PCL-100',
            origin: 'Berlin',
            destination: 'Munich',
            department: 'REGULAR',
            status: 'RECEIVED',
            insuranceStatus: 'NOT_REQUIRED',
            submittedAt: '2026-09-26T10:00:00Z'
          }
        ],
        page: 1,
        limit: 10,
        total: 1,
        totalPages: 1
      })
    });

    render(<ParcelTable userRole="operator" onSelectParcel={() => {}} />);

    expect(await screen.findByText('PCL-100')).toBeInTheDocument();
    expect(screen.getByText('Berlin → Munich')).toBeInTheDocument();
  });

  it('7. Filters work in parcel table', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        items: [],
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 1
      })
    });
    global.fetch = fetchSpy;

    render(<ParcelTable userRole="operator" onSelectParcel={() => {}} />);

    const searchInput = await screen.findByPlaceholderText('Search by Parcel ID...');
    fireEvent.change(searchInput, { target: { value: 'PCL-SEARCH' } });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('parcelId=PCL-SEARCH'), expect.anything());
    });
  });

  it('8. Parcel detail modal renders parcel details correctly', () => {
    const sampleParcel = {
      parcelId: 'PCL-999',
      senderName: 'Alice',
      senderContact: '123',
      receiverName: 'Bob',
      receiverContact: '456',
      origin: 'Berlin',
      destination: 'Munich',
      weightKg: 2.5,
      valueEur: 500,
      department: 'REGULAR',
      insuranceRequired: false,
      insuranceStatus: 'NOT_REQUIRED',
      status: 'RECEIVED',
      submittedBy: 'user123',
      submittedAt: '2026-09-26T10:00:00Z'
    };

    render(<ParcelDetailModal parcel={sampleParcel} onClose={() => {}} />);

    expect(screen.getByText('PCL-999')).toBeInTheDocument();
    expect(screen.getByText('Alice (123)')).toBeInTheDocument();
    expect(screen.getByText('Bob (456)')).toBeInTheDocument();
  });

  it('9. Parcel detail modal triggers onClose when Close button is clicked', () => {
    const onCloseMock = vi.fn();
    const sampleParcel = { parcelId: 'PCL-999', senderName: 'Alice', senderContact: '123', receiverName: 'Bob', receiverContact: '456', origin: 'Berlin', destination: 'Munich', weightKg: 2.5, valueEur: 500, department: 'REGULAR', insuranceRequired: false, insuranceStatus: 'NOT_REQUIRED', status: 'RECEIVED', submittedBy: 'user123', submittedAt: '2026-09-26T10:00:00Z' };

    render(<ParcelDetailModal parcel={sampleParcel} onClose={onCloseMock} />);

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onCloseMock).toHaveBeenCalled();
  });
});
