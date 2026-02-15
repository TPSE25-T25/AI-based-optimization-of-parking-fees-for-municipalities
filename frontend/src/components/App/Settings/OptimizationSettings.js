import React, { useState, useEffect } from 'react';
import '../../ConfigurationPanel/ConfigurationPanel.css';

const API_BASE_URL = 'http://localhost:8000';

const INITIAL_SETTINGS = {
  common: {
    limit: 3000,
    cityName: 'Karlsruhe, Germany',
    centerLat: 49.0069,
    centerLon: 8.4037,
    seed: 42,
    poiLimit: 50,
    defaultElasticity: -0.4,
    searchRadius: 10000,
    defaultCurrentFee: 1.0,
    tariffs: { //Hidden from the users.
      "schloss": 2.50, "postgalerie": 2.50, "passagehof": 3.00,
      "karstadt": 2.50, "marktplatz": 2.50, "ece": 2.00,
      "ettlinger": 2.00, "kongress": 2.00, "messe": 1.50,
      "bahnhof": 2.50, "hbf": 2.50, "süd": 2.00, "zkm": 1.50,
      "filmpalast": 1.50, "ludwigsplatz": 2.50, "friedrichsplatz": 2.50,
      "mendelssohn": 2.00, "kronenplatz": 2.00, "fasanengarten": 1.00,
      "waldhorn": 1.50, "sophien": 2.00, "kreuzstraße": 2.00,
      "akademiestraße": 2.50, "stephanplatz": 2.50, "amalien": 2.00,
      "landratsamt": 1.50, "tivoli": 1.50, "zoo": 1.50
    },
  },
  optimizer: {
    populationSize: 200,
    generations: 50,
    targetOccupancy: 0.85,
    minFee: 0,
    maxFee: 10,
    feeIncrement: 0.1,
  },
  agent: {
    driversPerZoneCapacity: 2.0,
    simulationRuns: 3,
    driverFeeWeight: 1.5,
    driverDistanceToLotWeight: 0.8,
    driverWalkingDistanceWeight: 2.0,
    driverAvailabilityWeight: 0.5,
  },
};

export default function OptimizationSettings({ dataSource, optimizerType, settings: externalSettings, onSettingsChange, onPickLocationRequest, isPickingLocation }) {
  const [settings, setSettings] = useState(externalSettings || INITIAL_SETTINGS);
  const [settingsMeta, setSettingsMeta] = useState(null);

  useEffect(() => {
    fetchSettingsMeta();
  }, []);

  // Sync internal state with external settings when they change
  useEffect(() => {
    if (externalSettings) {
      setSettings(externalSettings);
    }
  }, [externalSettings]);

  useEffect(() => {
    if (onSettingsChange) {
      onSettingsChange(settings);
    }
  }, [settings, onSettingsChange]);

  const fetchSettingsMeta = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/optimization-settings`);
      if (response.ok) {
        const data = await response.json();
        setSettingsMeta(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings metadata', error);
    }
  };

  const updateSetting = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value,
      },
    }));
  };

  const exportConfig = () => {
    const config = {
      dataSource,
      optimizerType,
      settings,
      timestamp: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `parking-optimization-config-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const importConfig = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const config = JSON.parse(e.target.result);
        if (config.settings) {
          setSettings(config.settings);
        }
      } catch (error) {
        console.error('Failed to import configuration', error);
        alert('Invalid configuration file');
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const renderInputGroup = (label, description, value, onChange, props = {}) => (
    <div className="configuration-input-group">
      <div className="configuration-input-description">{description}</div>
      <label>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} {...props} />
    </div>
  );

  return (
    <div className="configuration-panel">
      <form className="configuration-form">
        <div className="configuration-inputs">
          
          <div className="configuration-section-title">Data Source Settings</div>
          {renderInputGroup(
            'Zone Limit',
            'Maximum number of parking zones to load',
            settings.common.limit,
            (v) => updateSetting('common', 'limit', Number(v)),
            { type: 'number', min: 1 }
          )}
          <div className="configuration-input-group">
            <div className="configuration-input-description">City Name for data loading</div>
            <label>City Name</label>
            <div className="optimizer-controls-row">
              <input 
                className="optimizer-select"
                value={settings.common.cityName} 
                onChange={(e) => updateSetting('common', 'cityName', e.target.value)} 
                type="text"
              />
              <button 
                type="button" 
                className="optimizer-button"
                onClick={onPickLocationRequest}
                disabled={isPickingLocation}
                title="Pick location from map"
              >
                {isPickingLocation ? '⏳' : '📍'}
              </button>
            </div>
          </div>
          {renderInputGroup(
            'Center Latitude',
            'Center latitude coordinate',
            settings.common.centerLat,
            (v) => updateSetting('common', 'centerLat', Number(v)),
            { type: 'number', step: '0.0001' }
          )}
          {renderInputGroup(
            'Center Longitude',
            'Center longitude coordinate',
            settings.common.centerLon,
            (v) => updateSetting('common', 'centerLon', Number(v)),
            { type: 'number', step: '0.0001' }
          )}
          {renderInputGroup(
            'Seed',
            'Random seed for K-Means clustering and data generation for some cases (affects reproducibility)',
            settings.common.seed,
            (v) => updateSetting('common', 'seed', Number(v)),
            { type: 'number', min: 0 }
          )}
          {renderInputGroup(
            'Points of Interest Limit',
            'Maximum number of Points of Interest to load for the city',
            settings.common.poiLimit,
            (v) => updateSetting('common', 'poiLimit', Number(v)),
            { type: 'number', min: 1, max: 500 }
          )}
          {renderInputGroup(
            'Default Elasticity',
            'Default price elasticity of demand (used by all datasources)',
            settings.common.defaultElasticity,
            (v) => updateSetting('common', 'defaultElasticity', Number(v)),
            { type: 'number', step: '0.1' }
          )}
          {renderInputGroup(
            'Search Radius (m)',
            'Search radius in meters for OSMnx/MobiData API',
            settings.common.searchRadius,
            (v) => updateSetting('common', 'searchRadius', Number(v)),
            { type: 'number', min: 1 }
          )}
          {renderInputGroup(
            'Default Current Fee',
            'Default current fee for zones without specific data',
            settings.common.defaultCurrentFee,
            (v) => updateSetting('common', 'defaultCurrentFee', Number(v)),
            { type: 'number', step: '0.1', min: 0 }
          )}

          <div className="configuration-section-title">Optimization Settings</div>
          {renderInputGroup(
            'Population Size',
            settingsMeta?.population_size?.description || 'Number of solutions per generation',
            settings.optimizer.populationSize,
            (v) => updateSetting('optimizer', 'populationSize', Number(v)),
            { type: 'number', min: settingsMeta?.population_size?.min ?? 10 }
          )}
          {renderInputGroup(
            'Generations',
            settingsMeta?.generations?.description || 'Number of generations (iterations)',
            settings.optimizer.generations,
            (v) => updateSetting('optimizer', 'generations', Number(v)),
            { type: 'number', min: settingsMeta?.generations?.min ?? 1 }
          )}
          {renderInputGroup(
            'Target Occupancy',
            settingsMeta?.target_occupancy?.description || 'Desired target occupancy',
            settings.optimizer.targetOccupancy,
            (v) => updateSetting('optimizer', 'targetOccupancy', Number(v)),
            { type: 'number', min: 0, max: 1, step: '0.05' }
          )}
          {renderInputGroup(
            'Min Fee',
            settingsMeta?.min_fee?.description || 'Minimum fee for parking',
            settings.optimizer.minFee,
            (v) => updateSetting('optimizer', 'minFee', Number(v)),
            { type: 'number', min: 0, step: '0.05' }
          )}
          {renderInputGroup(
            'Max Fee',
            settingsMeta?.max_fee?.description || 'Maximum fee for parking',
            settings.optimizer.maxFee,
            (v) => updateSetting('optimizer', 'maxFee', Number(v)),
            { type: 'number', min: 0, step: '0.05' }
          )}
          {renderInputGroup(
            'Fee Increment',
            settingsMeta?.fee_increment?.description || 'Increment step for fee adjustments',
            settings.optimizer.feeIncrement,
            (v) => updateSetting('optimizer', 'feeIncrement', Number(v)),
            { type: 'number', min: 0, step: '0.01' }
          )}

          {optimizerType === 'agent' && (
            <>
              {renderInputGroup(
                'Drivers per Zone Capacity',
                'Number of drivers per zone capacity in simulation',
                settings.agent.driversPerZoneCapacity,
                (v) => updateSetting('agent', 'driversPerZoneCapacity', Number(v)),
                { type: 'number', step: '0.1', min: 0 }
              )}
              {renderInputGroup(
                'Simulation Runs',
                'Number of simulation runs for agent-based optimization',
                settings.agent.simulationRuns,
                (v) => updateSetting('agent', 'simulationRuns', Number(v)),
                { type: 'number', min: 1 }
              )}
              {renderInputGroup(
                'Driver Fee Weight',
                'Weight of parking fee in driver decision making',
                settings.agent.driverFeeWeight,
                (v) => updateSetting('agent', 'driverFeeWeight', Number(v)),
                { type: 'number', step: '0.1', min: 0 }
              )}
              {renderInputGroup(
                'Driver Distance to Lot Weight',
                'Weight of distance to parking lot in driver decision making',
                settings.agent.driverDistanceToLotWeight,
                (v) => updateSetting('agent', 'driverDistanceToLotWeight', Number(v)),
                { type: 'number', step: '0.1', min: 0 }
              )}
              {renderInputGroup(
                'Driver Walking Distance Weight',
                'Weight of walking distance in driver decision making',
                settings.agent.driverWalkingDistanceWeight,
                (v) => updateSetting('agent', 'driverWalkingDistanceWeight', Number(v)),
                { type: 'number', step: '0.1', min: 0 }
              )}
              {renderInputGroup(
                'Driver Availability Weight',
                'Weight of spot availability in driver decision making',
                settings.agent.driverAvailabilityWeight,
                (v) => updateSetting('agent', 'driverAvailabilityWeight', Number(v)),
                { type: 'number', step: '0.1', min: 0 }
              )}
            </>
          )}
        </div>

        <div className="configuration-actions">
          <input
            type="file"
            accept=".json"
            onChange={importConfig}
            style={{ display: 'none' }}
            id="import-config"
          />
          <button type="button" onClick={() => document.getElementById('import-config').click()}>
            Import Config
          </button>
          <button type="button" onClick={exportConfig}>
            Export Config
          </button>
        </div>
      </form>
    </div>
  );
}

export { INITIAL_SETTINGS };
