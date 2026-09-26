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

  it('renders container metadata and parsed fields for XML batch upload', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        containerId: '68465468',
        shippingDate: '2016-07-22',
        total: 2,
        successful: 2,
        failed: 0,
        results: [
          {
            index: 1,
            parcelId: '68465468-P1',
            recipientName: 'Vinny Gankema',
            street: 'Marijkestraat',
            houseNumber: '28',
            postalCode: '4744AT',
            city: 'Bosschenhoofd',
            weightKg: 0.02,
            valueEur: 0,
            status: 'SUCCESS'
          },
          {
            index: 2,
            parcelId: '68465468-P2',
            recipientName: 'Soner Colen',
            street: 'Meester Willemstraat',
            houseNumber: '111',
            postalCode: '3036MN',
            city: 'Rotterdam',
            weightKg: 2.0,
            valueEur: 0,
            status: 'SUCCESS'
          }
        ]
      }),
    });

    render(<BatchUpload />);

    const fileInput = screen.getByRole('button', { name: /upload batch/i }).previousElementSibling;
    const xmlFile = new File(['<Container><Id>68465468</Id></Container>'], 'batch.xml', { type: 'application/xml' });

    if (fileInput) {
      fireEvent.change(fileInput, { target: { files: [xmlFile] } });
      fireEvent.click(screen.getByRole('button', { name: /upload batch/i }));

      await waitFor(() => {
        expect(screen.getByText('68465468')).toBeInTheDocument();
        expect(screen.getByText('2016-07-22')).toBeInTheDocument();
        expect(screen.getByText('Vinny Gankema')).toBeInTheDocument();
        expect(screen.getByText('Marijkestraat 28 4744AT Bosschenhoofd')).toBeInTheDocument();
        expect(screen.getByText('Soner Colen')).toBeInTheDocument();
        expect(screen.getByText('Meester Willemstraat 111 3036MN Rotterdam')).toBeInTheDocument();
        expect(screen.getByText('0.02 kg')).toBeInTheDocument();
      });
    }
  });
});
