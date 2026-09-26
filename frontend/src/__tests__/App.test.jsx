import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import App from '../App.jsx';

describe('App Component Empty State and Database Availability', () => {
  it('renders metrics and default empty states when user is logged in and database is connected', async () => {
    global.fetch = vi.fn((url) => {
      if (url === '/api/health') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'healthy', database: 'connected' }),
        });
      }
      if (url === '/api/auth/me') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            user: { id: '123', fullName: 'Operator Jane', username: 'jane', role: 'operator' },
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);

    expect(await screen.findByText('Parcel Routing System')).toBeInTheDocument();
    expect(await screen.findByText('No parcels found matching the criteria.')).toBeInTheDocument();
    expect(screen.getByText('No parcels found for the selected time filter.')).toBeInTheDocument();
  });

  it('renders explicit database error banner when database is unavailable for logged in user', async () => {
    global.fetch = vi.fn((url) => {
      if (url === '/api/health') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'degraded', database: 'unavailable' }),
        });
      }
      if (url === '/api/auth/me') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            user: { id: '123', fullName: 'Operator Jane', username: 'jane', role: 'operator' },
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);

    expect(await screen.findByText('Parcel Routing System')).toBeInTheDocument();
    expect(await screen.findByText(/Database unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText('No parcels found matching the criteria.')).not.toBeInTheDocument();
  });
});
