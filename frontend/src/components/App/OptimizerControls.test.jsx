import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OptimizerControls from './OptimizerControls';

describe('OptimizerControls', () => {
  const baseProps = {
    optimizerType: 'elasticity',
    setOptimizerType: vi.fn(),
    dataSource: 'osmnx',
    setDataSource: vi.fn(),
    runOptimization: vi.fn(),
    loadCity: vi.fn(),
    optimizing: false,
    loading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables optimize button when no parking zones are loaded', async () => {
    const user = userEvent.setup();

    render(<OptimizerControls {...baseProps} hasParkingZones={false} />);

    const optimizeButton = screen.getByRole('button', { name: '▶️' });
    expect(optimizeButton).toBeDisabled();

    await user.click(optimizeButton);
    expect(baseProps.runOptimization).not.toHaveBeenCalled();
  });

  it('enables optimize button when parking zones are available', async () => {
    const user = userEvent.setup();

    render(<OptimizerControls {...baseProps} hasParkingZones={true} />);

    const optimizeButton = screen.getByRole('button', { name: '▶️' });
    expect(optimizeButton).toBeEnabled();

    await user.click(optimizeButton);
    expect(baseProps.runOptimization).toHaveBeenCalledTimes(1);
  });
});
