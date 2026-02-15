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
const ConfigurationPanel = ({
  dataSource,
  limit,
  setLimit,
  cityName,
  setCityName,
  centerLat,
  setCenterLat,
  centerLon,
  setCenterLon,
  tariffDatabase,
  setTariffDatabase,
  osmnxElasticity,
  setOsmnxElasticity,
  searchRadius,
  setSearchRadius,
  defaultCurrentFee,
  setDefaultCurrentFee,
  mobidataElasticity,
  setMobidataElasticity,
  generatorSeed,
  setGeneratorSeed,
  populationSize,
  setPopulationSize,
  generations,
  setGenerations,
  targetOccupancy,
  setTargetOccupancy,
  randomSeed,
  setRandomSeed,
  minFee,
  setMinFee,
  maxFee,
  setMaxFee,
  feeIncrement,
  setFeeIncrement,
  optimizerType,
  elasticity,
  setElasticity,
  driversPerZoneCapacity,
  setDriversPerZoneCapacity,
  simulationRuns,
  setSimulationRuns,
  driverFeeWeight,
  setDriverFeeWeight,
  driverDistanceToLotWeight,
  setDriverDistanceToLotWeight,
  driverWalkingDistanceWeight,
  setDriverWalkingDistanceWeight,
  driverAvailabilityWeight,
  setDriverAvailabilityWeight
}) => {
  // ===== STATE =====
  const [settingsMeta, setSettingsMeta] = useState(null);
  const [hasUserEdited, setHasUserEdited] = useState(false);

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
  }, [hasUserEdited, setPopulationSize, setGenerations, setTargetOccupancy]);

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

          {/* Data Source Settings Section */}
          <div className="configuration-section-title">Data Source Settings</div>

          {/* Limit */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              Maximum number of parking zones to load
            </div>
            <label>Zone Limit</label>
            <input
              type="number"
              min={1}
              max={10000}
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
            />
          </div>

          {/* City Name */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              City Name for data loading
            </div>
            <label>City Name</label>
            <input
              type="text"
              value={cityName}
              onChange={(event) => setCityName(event.target.value)}
            />
          </div>

          {/* Center Latitude */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              Center latitude coordinate
            </div>
            <label>Center Latitude</label>
            <input
              type="number"
              step="0.0001"
              value={centerLat}
              onChange={(event) => setCenterLat(Number(event.target.value))}
            />
          </div>

          {/* Center Longitude */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              Center longitude coordinate
            </div>
            <label>Center Longitude</label>
            <input
              type="number"
              step="0.0001"
              value={centerLon}
              onChange={(event) => setCenterLon(Number(event.target.value))}
            />
          </div>

          {/* OSMnx-specific settings */}
          {dataSource === 'osmnx' && (
            <>
              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Path to tariff database for OSMnx loader
                </div>
                <label>Tariff Database</label>
                <input
                  type="text"
                  value={tariffDatabase}
                  onChange={(event) => setTariffDatabase(event.target.value)}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Default price elasticity of demand for zones without specific data
                </div>
                <label>Default Elasticity</label>
                <input
                  type="number"
                  step="0.1"
                  value={osmnxElasticity}
                  onChange={(event) => setOsmnxElasticity(Number(event.target.value))}
                />
              </div>
            </>
          )}

          {/* MobiData-specific settings */}
          {dataSource === 'mobidata' && (
            <>
              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Search radius in meters for MobiData API
                </div>
                <label>Search Radius (m)</label>
                <input
                  type="number"
                  min={1000}
                  value={searchRadius}
                  onChange={(event) => setSearchRadius(Number(event.target.value))}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Default current fee for zones without specific data
                </div>
                <label>Default Current Fee</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={defaultCurrentFee}
                  onChange={(event) => setDefaultCurrentFee(Number(event.target.value))}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Default price elasticity of demand for zones without specific data
                </div>
                <label>Default Elasticity</label>
                <input
                  type="number"
                  step="0.1"
                  value={mobidataElasticity}
                  onChange={(event) => setMobidataElasticity(Number(event.target.value))}
                />
              </div>
            </>
          )}

          {/* Generator-specific settings */}
          {dataSource === 'generated' && (
            <div className="configuration-input-group">
              <div className="configuration-input-description">
                Random seed for reproducibility of generated data
              </div>
              <label>Generator Seed</label>
              <input
                type="number"
                value={generatorSeed}
                onChange={(event) => setGeneratorSeed(Number(event.target.value))}
              />
            </div>
          )}

          {/* Optimization Settings Section */}
          <div className="configuration-section-title">Optimization Settings</div>

          {/* Random Seed */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.random_seed?.description || 'Random seed for optimization reproducibility'}
            </div>
            <label>Random Seed</label>
            <input
              type="number"
              min={settingsMeta?.random_seed?.min ?? 0}
              max={settingsMeta?.random_seed?.max ?? undefined}
              value={randomSeed}
              onChange={(event) => {
                setHasUserEdited(true);
                setRandomSeed(Number(event.target.value));
              }}
            />
          </div>

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
          
          
          {/* Min Fee */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.min_fee?.description || 'Minimum fee for parking'}
            </div>
            <label>Min Fee</label>
            <input
              type="number"
              min={settingsMeta?.min_fee?.min ?? 0}
              max={settingsMeta?.min_fee?.max ?? undefined}
              step="0.05"
              value={minFee}
              onChange={(event) => {
                setHasUserEdited(true);
                setMinFee(Number(event.target.value));
              }}
            />
          </div>

          
          {/* Max Fee */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.max_fee?.description || 'Maximum fee for parking'}
            </div>
            <label>Max Fee</label>
            <input
              type="number"
              min={settingsMeta?.max_fee?.min ?? 0}
              max={settingsMeta?.max_fee?.max ?? undefined}
              step="0.05"
              value={maxFee}
              onChange={(event) => {
                setHasUserEdited(true);
                setMaxFee(Number(event.target.value));
              }}
            />
          </div>

          
          {/* Fee Increment */}
          <div className="configuration-input-group">
            <div className="configuration-input-description">
              {settingsMeta?.fee_increment?.description || 'Increment step for fee adjustments'}
            </div>
            <label>Fee Increment</label>
            <input
              type="number"
              min={settingsMeta?.fee_increment?.min ?? 0}
              max={settingsMeta?.fee_increment?.max ?? undefined}
              step="0.25"
              value={feeIncrement}
              onChange={(event) => {
                setHasUserEdited(true);
                setFeeIncrement(Number(event.target.value));
              }}
            />
          </div>

          {/* Elasticity-based optimizer settings */}
          {optimizerType === 'elasticity' && (
            <div className="configuration-input-group">
              <div className="configuration-input-description">
                Price elasticity coefficient for demand simulation
              </div>
              <label>Elasticity</label>
              <input
                type="number"
                step="0.1"
                value={elasticity}
                onChange={(event) => {
                  setHasUserEdited(true);
                  setElasticity(Number(event.target.value));
                }}
              />
            </div>
          )}

          {/* Agent-based optimizer settings */}
          {optimizerType === 'agent' && (
            <>
              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Number of drivers per zone capacity in simulation
                </div>
                <label>Drivers per Zone Capacity</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={driversPerZoneCapacity}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setDriversPerZoneCapacity(Number(event.target.value));
                  }}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Number of simulation runs for agent-based optimization
                </div>
                <label>Simulation Runs</label>
                <input
                  type="number"
                  min={1}
                  value={simulationRuns}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setSimulationRuns(Number(event.target.value));
                  }}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Weight of parking fee in driver decision making
                </div>
                <label>Driver Fee Weight</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={driverFeeWeight}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setDriverFeeWeight(Number(event.target.value));
                  }}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Weight of distance to parking lot in driver decision making
                </div>
                <label>Driver Distance to Lot Weight</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={driverDistanceToLotWeight}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setDriverDistanceToLotWeight(Number(event.target.value));
                  }}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Weight of walking distance in driver decision making
                </div>
                <label>Driver Walking Distance Weight</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={driverWalkingDistanceWeight}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setDriverWalkingDistanceWeight(Number(event.target.value));
                  }}
                />
              </div>

              <div className="configuration-input-group">
                <div className="configuration-input-description">
                  Weight of spot availability in driver decision making
                </div>
                <label>Driver Availability Weight</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={driverAvailabilityWeight}
                  onChange={(event) => {
                    setHasUserEdited(true);
                    setDriverAvailabilityWeight(Number(event.target.value));
                  }}
                />
              </div>
            </>
          )}
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