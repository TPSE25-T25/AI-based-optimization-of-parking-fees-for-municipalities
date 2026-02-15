/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import InfoPanel from '../../src/components/InfoPanel/InfoPanel.js';

// Is this deprecated?

describe('InfoPanel', () => {
  const baseZone = {
    id: 101,
    name: 'Downtown Core',
    current_fee: 2.5,
    current_capacity: 85,
    maximum_capacity: 100,
    position: [40.7128, -74.006],
  };

  test('does not render if zone is null', () => {
    const { container } = render(
      <InfoPanel zone={null} onClose={jest.fn()} />
    );

    expect(container.firstChild).toBeNull();
  });

  test('renders basic zone information', () => {
    render(<InfoPanel zone={baseZone} onClose={jest.fn()} />);

    expect(screen.getByText('Downtown Core')).toBeInTheDocument();
    expect(screen.getByText('101')).toBeInTheDocument();
    expect(screen.getByText('$2.50/hr')).toBeInTheDocument();
    expect(screen.getByText('100 spaces')).toBeInTheDocument();
  });

  test('falls back to Zone {id} if name is missing', () => {
    const zoneWithoutName = { ...baseZone, name: undefined };

    render(<InfoPanel zone={zoneWithoutName} onClose={jest.fn()} />);

    expect(screen.getByText('Zone 101')).toBeInTheDocument();
  });

  test('calculates and displays occupancy percentage correctly', () => {
    render(<InfoPanel zone={baseZone} onClose={jest.fn()} />);

    // 85 / 100 = 85.0%
    expect(screen.getByText('85.0%')).toBeInTheDocument();
  });

  test('applies correct color for high occupancy (>=85%)', () => {
    render(<InfoPanel zone={baseZone} onClose={jest.fn()} />);

    const occupancyText = screen.getByText('85.0%');
    expect(occupancyText).toHaveStyle('color: #e74c3c');
  });

  test('shows coordinates formatted to 4 decimals', () => {
    render(<InfoPanel zone={baseZone} onClose={jest.fn()} />);

    expect(
      screen.getByText('40.7128, -74.0060')
    ).toBeInTheDocument();
  });

  test('renders new fee when present', () => {
    const zone = { ...baseZone, new_fee: 3.75 };

    render(<InfoPanel zone={zone} onClose={jest.fn()} />);

    expect(screen.getByText('$3.75/hr')).toBeInTheDocument();
  });

  test('renders predicted occupancy correctly formatted', () => {
    const zone = { ...baseZone, predicted_occupancy: 0.9234 };

    render(<InfoPanel zone={zone} onClose={jest.fn()} />);

    expect(screen.getByText('92.34%')).toBeInTheDocument();
  });

  test('renders predicted revenue correctly formatted', () => {
    const zone = { ...baseZone, predicted_revenue: 1234.567 };

    render(<InfoPanel zone={zone} onClose={jest.fn()} />);

    expect(screen.getByText('$1234.57')).toBeInTheDocument();
  });

  test('close button triggers onClose', () => {
    const onClose = jest.fn();

    render(<InfoPanel zone={baseZone} onClose={onClose} />);

    const closeBtn = screen.getByText('✖');
    fireEvent.click(closeBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('occupancy bar width is capped at 100%', () => {
    const zone = {
      ...baseZone,
      current_capacity: 150,
      maximum_capacity: 100,
    };

    render(<InfoPanel zone={zone} onClose={jest.fn()} />);

    const fill = document.querySelector('.occupancy-fill-small');
    expect(fill).toHaveStyle('width: 100%');
  });

  test('shows N/A when maximum_capacity is missing', () => {
    const zone = { ...baseZone, maximum_capacity: null };

    render(<InfoPanel zone={zone} onClose={jest.fn()} />);

    expect(screen.getByText('N/A spaces')).toBeInTheDocument();
  });
});
