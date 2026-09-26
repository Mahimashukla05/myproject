import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import App from '../App.jsx';

describe('Frontend Auth Flow and UI Validation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders login form by default for unauthenticated users', async () => {
    global.fetch = vi.fn((url) => {
      if (url === '/api/health') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'healthy', database: 'connected' }),
        });
      }
      if (url === '/api/auth/me') {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);

    expect(await screen.findByText('Account Login')).toBeInTheDocument();
    expect(screen.getByLabelText(/Username, Email, or Mobile/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
  });

  it('navigates to register form and shows validation errors on missing input', async () => {
    global.fetch = vi.fn((url) => {
      if (url === '/api/health') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'healthy', database: 'connected' }),
        });
      }
      return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
    });

    render(<App />);

    const registerLink = await screen.findByText(/Need an account\? Register/i);
    fireEvent.click(registerLink);

    expect(await screen.findByText('Create Account')).toBeInTheDocument();

    const registerBtn = screen.getByRole('button', { name: /^Register$/i });
    fireEvent.click(registerBtn);

    expect(await screen.findByText(/Please fix highlighted form errors/i)).toBeInTheDocument();
  });

  it('displays authenticated UI with user name and role badge when user is logged in', async () => {
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
            user: { id: '123', fullName: 'Alice Admin', username: 'alice', role: 'admin' },
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);

    expect(await screen.findByText(/Logged in as/i)).toBeInTheDocument();
    expect(screen.getByText('Alice Admin')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('Total Parcels')).toBeInTheDocument();
  });
});
