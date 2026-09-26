import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import SingleParcelUpload from '../components/SingleParcelUpload.jsx';

describe('Single Parcel Upload Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders single parcel form correctly', () => {
    render(<SingleParcelUpload />);

    expect(screen.getByText('Add Single Parcel')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. Alice Corp')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. Bob Logistics')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit Single Parcel' })).toBeInTheDocument();
  });

  it('displays validation error when missing required fields', async () => {
    render(<SingleParcelUpload />);

    const submitBtn = screen.getByRole('button', { name: 'Submit Single Parcel' });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Missing required fields/i)).toBeInTheDocument();
  });

  it('submits parcel and routes it successfully', async () => {
    const onParcelCreatedMock = vi.fn();
    const fetchSpy = vi.fn((url, options) => {
      if (url.includes('/api/parcels') && options?.method === 'POST' && !url.includes('/route')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            parcel: { parcelId: 'PCL-12345', status: 'RECEIVED', senderName: 'Alice' },
          }),
        });
      }
      if (url.includes('/route') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            parcel: { parcelId: 'PCL-12345', status: 'ROUTING_EVALUATED', department: 'REGULAR' },
          }),
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
    global.fetch = fetchSpy;

    render(<SingleParcelUpload onParcelCreated={onParcelCreatedMock} />);

    fireEvent.change(screen.getByPlaceholderText('e.g. Alice Corp'), { target: { value: 'Alice Corp' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. +91 9876543210'), { target: { value: '9876543210' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. Bob Logistics'), { target: { value: 'Bob Inc' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. +91 9123456789'), { target: { value: '9123456789' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. Mumbai Hub'), { target: { value: 'Mumbai' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. Delhi Depot'), { target: { value: 'Delhi' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. 2.5'), { target: { value: '2.5' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. 450.00'), { target: { value: '500' } });

    fireEvent.click(screen.getByRole('button', { name: 'Submit Single Parcel' }));

    await waitFor(() => {
      expect(screen.getByText(/submitted successfully!/i)).toBeInTheDocument();
      expect(onParcelCreatedMock).toHaveBeenCalled();
    });
  });
});
