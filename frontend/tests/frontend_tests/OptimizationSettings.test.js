/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import OptimizationSettings from '../../src/components/App/Settings/OptimizationSettings.js'
import { INITIAL_SETTINGS } from '../../src/components/App/Settings/OptimizationSettings.js';

global.fetch = jest.fn();
global.URL.createObjectURL = jest.fn(() => 'blob:test');
global.URL.revokeObjectURL = jest.fn();

describe('OptimizationSettings', () => {
  const defaultProps = {
    dataSource: 'osmnx', // change to mobidata?
    optimizerType: 'elasticity',
    settings: INITIAL_SETTINGS,
    onSettingsChange: jest.fn(),
    onPickLocationRequest: jest.fn(),
    isPickingLocation: false,
  };

  const mockFetchResponse = {
    population_size: { default: 200 },
    generations: { default: 50 },
    target_occupancy: { default: 0.85},
    min_fee: { default: 0 },
    max_fee: { default: 10},
    fee_increment: { default: 0.25},
    optimizerType: { default: 'elasticity'},
    random_seed: { default: 1}
  }


  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockFetchResponse),
      })
    )
  })

  afterEach(() => {
    jest.clearAllMocks()
  })


  const renderComponent = (props = {}) => {
    return render(<OptimizationSettings {...defaultProps} {...props} />);
  };

  test('Renders configuration inputs with default values', async () => { // hmmmmmmm
    renderComponent();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/optimization-settings'
      )
    });

    expect(screen.getByLabelText('Zone Limit')).toBeInTheDocument();
    expect(screen.getByLabelText('Zone Limit').value).toBe('3000');

    expect(screen.getByLabelText('City Name')).toBeInTheDocument();
    expect(screen.getByLabelText('City Name').value).toBe('Karlsruhe, Germany');

    expect(screen.getByLabelText('Center Latitude')).toBeInTheDocument();
    expect(screen.getByLabelText('Center Latitude').value).toBe('49.0069');

    expect(screen.getByLabelText('Center Longitude')).toBeInTheDocument();
    expect(screen.getByLabelText('Center Longitude').value).toBe('8.4037');

    expect(screen.getByLabelText('Seed')).toBeInTheDocument();
    expect(screen.getByLabelText('Seed').value).toBe('42');

    expect(screen.getByLabelText('Points of Interest Limit')).toBeInTheDocument();
    expect(screen.getByLabelText('Points of Interest Limit').value).toBe('50');

    expect(screen.getByLabelText('Default Elasticity')).toBeInTheDocument();
    expect(screen.getByLabelText('Default Elasticity').value).toBe('-0.4');

    expect(screen.getByLabelText('Search Radius (m)')).toBeInTheDocument();
    expect(screen.getByLabelText('Search Radius (m)').value).toBe('10000');

    expect(screen.getByLabelText('Default Current Fee')).toBeInTheDocument();
    expect(screen.getByLabelText('Default Current Fee').value).toBe('1');

    expect(screen.getByLabelText('Population Size')).toBeInTheDocument();
    expect(screen.getByLabelText('Population Size').value).toBe('200');

    expect(screen.getByLabelText('Generations')).toBeInTheDocument();
    expect(screen.getByLabelText('Generations').value).toBe('50');

    expect(screen.getByLabelText('Target Occupancy')).toBeInTheDocument();
    expect(screen.getByLabelText('Target Occupancy').value).toBe('0.85');

    expect(screen.getByLabelText('Min Fee')).toBeInTheDocument();
    expect(screen.getByLabelText('Min Fee').value).toBe('0');

    expect(screen.getByLabelText('Max Fee')).toBeInTheDocument();
    expect(screen.getByLabelText('Max Fee').value).toBe('10');

    expect(screen.getByLabelText('Fee Increment')).toBeInTheDocument();
    expect(screen.getByLabelText('Fee Increment').value).toBe('0.1');
    
  });

  test('Call onSettingsChange upon updated input field', async () => {
    const onSettingsChange = jest.fn()

    renderComponent({ onSettingsChange })

    await waitFor(() => {
      expect(onSettingsChange).toHaveBeenCalled()
    });
  });

  test('Calls onPickLocationRequest when pin button is clicked', () => {
    renderComponent();

    const button = screen.getByTitle('Pick location from map');
    fireEvent.click(button);

    expect(defaultProps.onPickLocationRequest).toHaveBeenCalledTimes(1);
  });

  test('Agent settings rendered when optimizerType is agent', () => {
    renderComponent({ optimizerType: 'agent' });

    expect(screen.getByLabelText('Drivers per Zone Capacity')).toBeInTheDocument();
    expect(screen.getByLabelText('Simulation Runs')).toBeInTheDocument();
    expect(screen.getByLabelText('Driver Fee Weight')).toBeInTheDocument();
    expect(screen.getByLabelText('Driver Distance to Lot Weight')).toBeInTheDocument();
    expect(screen.getByLabelText('Driver Walking Distance Weight')).toBeInTheDocument();
    expect(screen.getByLabelText('Driver Availability Weight')).toBeInTheDocument();
  });

  test('Agent settings hidden when optimizerType is elasticity', () => {
    renderComponent({ optimizerType: 'elasticity' });

    expect(screen.queryByLabelText('Drivers per Zone Capacity')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Simulation Runs')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Driver Fee Weight')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Driver Distance to Lot Weight')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Driver Walking Distance Weight')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Driver Availability Weight')).not.toBeInTheDocument();
    
  });

  test('Imports configuration from .json file', async () => {
    renderComponent();

    const file = new File(
      [
        JSON.stringify({
          settings: {
            ...INITIAL_SETTINGS,
            common: { ...INITIAL_SETTINGS.common, limit: 2000 },
          },
        }),
      ],

      'testconfig.json',
      { type: 'application/json' }
    );

    const fileInput = screen.getByLabelText('import-config');

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(defaultProps.onSettingsChange).toHaveBeenCalled();
    });
  });


  test('Exports configuration to .json file', () => {
    const createObjectURLSpy = jest
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:test');

    const revokeSpy = jest.spyOn(URL, 'revokeObjectURL').mockImplementation();

    renderComponent();

    const exportButton = screen.getByText('Export Config');
    fireEvent.click(exportButton);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalled();

    createObjectURLSpy.mockRestore();
    revokeSpy.mockRestore();
  });

  test('Syncs with externalSettings when prop changes', () => {
    const {rerender} = renderComponent();

    const newSettings = {
      ...INITIAL_SETTINGS,
      common: { ...INITIAL_SETTINGS.common, limit: 540 },
    };

    rerender(
      <OptimizationSettings
        {...defaultProps}
        settings={newSettings}
      />
    );

    expect(screen.getByLabelText('Zone Limit').value).toBe('540');
  });
});