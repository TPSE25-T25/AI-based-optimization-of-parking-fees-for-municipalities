/**
 * CONFIGURATION PANEL COMPONENT
 * Displays a form for adjusting genetic algorithm parameters.
 * Fetches min/max constraints and descriptions from the backend.
 */

// ===== IMPORTS =====
import { useEffect, useState } from 'react';
import './ConfigurationPanel.css';

// ===== CONSTANTS =====
const API_BASE_URL = 'http://localhost:8000';

// ===== COMPONENT =====
const ConfigurationPanel = () => {
  // ===== STATE =====
  const [settingsMeta, setSettingsMeta] = useState(null);
  const [hasUserEdited, setHasUserEdited] = useState(false);
  const [populationSize, setPopulationSize] = useState(200);
  const [generations, setGenerations] = useState(50);
  const [targetOccupancy, setTargetOccupancy] = useState(0.85);

  // ===== EFFECTS =====
  // Fetch backend metadata on mount and whenever user edits
  useEffect(() => {
    const fetchSettingsMeta = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/optimization-settings`);
        if (!response.ok) {
          throw new Error('Failed to fetch optimization settings metadata');
        }
        const data = await response.json();
        setSettingsMeta(data);

        if (!hasUserEdited) {
          setPopulationSize(data.population_size?.default ?? 200);
          setGenerations(data.generations?.default ?? 50);
          setTargetOccupancy(data.target_occupancy?.default ?? 0.85);
        }
      } catch (error) {
        console.error('Failed to load optimization settings metadata', error);
      }
    };

    fetchSettingsMeta();
  }, [hasUserEdited]);

  // ===== EVENT HANDLERS =====
  const handleExport = (event) => {
    event.preventDefault();
    // TODO: Export configuration to JSON file
    console.log('Export configuration:', {
      populationSize,
      generations,
      targetOccupancy,
    });
  };

  const handleImport = (event) => {
    event.preventDefault();
    // TODO: Import configuration from JSON file
    console.log('Import configuration');
  };

  // ===== RENDER =====
  return (
    <div className="configuration-panel">
      <form className="configuration-form">
        <div className="configuration-inputs">
          {/* Population Size */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.population_size?.description || 'Number of solutions per generation'}
            </div>
            <label>Population Size</label>
            <input
              type="number"
              min={settingsMeta?.population_size?.min ?? 10}
              max={settingsMeta?.population_size?.max ?? undefined}
              value={populationSize}
              onChange={(event) => {
                setHasUserEdited(true);
                setPopulationSize(Number(event.target.value));
              }}
            />
          </div>

          {/* Generations */}
          <div className="configuration-input-group">
            <label>Generations</label>
            <div className="configuration-input-description">
              {settingsMeta?.generations?.description || 'Number of generations (iterations)'}
            </div>
            <input
              type="number"
              min={settingsMeta?.generations?.min ?? 1}
              max={settingsMeta?.generations?.max ?? undefined}
              value={generations}
              onChange={(event) => {
                setHasUserEdited(true);
                setGenerations(Number(event.target.value));
              }}
            />
          </div>

          {/* Target Occupancy */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.target_occupancy?.description || 'Desired target occupancy'}
            </div>
            <label>Target Occupancy</label>
            <input
              type="number"
              min={settingsMeta?.target_occupancy?.min ?? 0}
              max={settingsMeta?.target_occupancy?.max ?? 1}
              step="0.05"
              value={targetOccupancy}
              onChange={(event) => {
                setHasUserEdited(true);
                setTargetOccupancy(Number(event.target.value));
              }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="configuration-actions">
          <button type="button" onClick={handleImport}>
            Import Configuration
          </button>
          <button type="button" onClick={handleExport}>
            Export Configuration
          </button>
        </div>
      </form>
    </div>
  );
};

// ===== EXPORT =====
export default ConfigurationPanel;