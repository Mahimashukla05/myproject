import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import BatchUpload from '../components/BatchUpload.jsx';

describe('BatchUpload Component', () => {
  it('renders upload input and button', () => {
    render(<BatchUpload />);
    expect(screen.getByText('Batch Parcel Upload (JSON / XML)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload batch/i })).toBeInTheDocument();
  });

  it('renders success response after batch upload', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        total: 2,
        successful: 2,
        failed: 0,
        results: [
          { parcelId: 'P001', status: 'SUCCESS' },
          { parcelId: 'P002', status: 'SUCCESS' },
        ],
      }),
    });

    render(<BatchUpload />);

    const fileInput = screen.getByLabelText ? screen.getByRole('button', { name: /upload batch/i }).previousElementSibling : null;
    const file = new File(['{"parcels":[]}'], 'batch.json', { type: 'application/json' });

    if (fileInput) {
      fireEvent.change(fileInput, { target: { files: [file] } });
      fireEvent.click(screen.getByRole('button', { name: /upload batch/i }));

      await waitFor(() => {
        expect(screen.getByText('Batch Results Summary')).toBeInTheDocument();
        expect(screen.getByText('P001')).toBeInTheDocument();
      });
    }
  });
});
