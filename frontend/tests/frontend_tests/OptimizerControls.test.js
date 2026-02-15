/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import OptimizerControls from '../../src/components/App/OptimizerControls.js';

// This is kind of a duplicate of OptimizationSettings are we gonna use this?



describe('OptimizerControls', () => {
  const defaultProps = {
    optimizerType: 'elasticity',
    setOptimizerType: jest.fn(),
    dataSource: 'osmnx',
    setDataSource: jest.fn(),
    runOptimization: jest.fn(),
    loadCity: jest.fn(),
    optimizing: false,
    loading: false,
  };

  const renderComponent = (props = {}) => {
    render(<OptimizerControls {...defaultProps} {...props} />)
    };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('Renders both selects with correct default values', () => {
    renderComponent();

    expect(screen.getByDisplayValue('OpenStreetMap')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Elasticity-Based')).toBeInTheDocument();
  });

  test('Calls setDataSource when data source changes', () => {
    renderComponent();

    const select = screen.getByDisplayValue('OpenStreetMap');
    fireEvent.change(select, { target: { value: 'mobidata' } });

    expect(defaultProps.setDataSource).toHaveBeenCalledWith('mobidata');
  });

  test('Calls setOptimizerType when optimizer changes', () => {
    renderComponent();

    const select = screen.getByDisplayValue('Elasticity-Based');
    fireEvent.change(select, { target: { value: 'agent' } });

    expect(defaultProps.setOptimizerType).toHaveBeenCalledWith('agent');
  });

  test('Calls loadCity when reload button is clicked', () => {
    renderComponent();

    const reloadButton = screen.getAllByRole('button')[0];
    fireEvent.click(reloadButton);

    expect(defaultProps.loadCity).toHaveBeenCalledTimes(1);
  });

  test('Calls runOptimization when run button is clicked', () => {
    renderComponent();

    const runButton = screen.getAllByRole('button')[1];
    fireEvent.click(runButton);

    expect(defaultProps.runOptimization).toHaveBeenCalledTimes(1);
  });

  test('Disables load button when loading', () => {
    renderComponent({ loading: true });

    const reloadButton = screen.getAllByRole('button')[0];
    expect(reloadButton).toBeDisabled();
  });

  test('Disables run button when optimizing', () => {
    renderComponent({ optimizing: true });

    const runButton = screen.getAllByRole('button')[1];
    expect(runButton).toBeDisabled();
  });

  test('Disables run button when loading', () => {
    renderComponent({ loading: true });

    const runButton = screen.getAllByRole('button')[1];
    expect(runButton).toBeDisabled();
  });
});