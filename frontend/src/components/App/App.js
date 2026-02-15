// APP - Main application container and state management

import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import './App.css';

import OptimizationSettings, { INITIAL_SETTINGS } from './Settings/OptimizationSettings';
import InfoPanel from '../InfoPanel/InfoPanel';
import MenuPanel from '../MenuPanel/MenuPanel';
import ParkingMap from '../ParkingMap/ParkingMap';
import OptimizerControls from './OptimizerControls';
import ResultsActions from './ResultsActions';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [city, setCity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(true);
  const [weights, setWeights] = useState({revenue: 50, occupancy: 30, drop: 10, fairness: 10});
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [optimizationResponse, setOptimizationResponse] = useState(null);
  const [optimizerType, setOptimizerType] = useState('elasticity');
  const [dataSource, setDataSource] = useState('osmnx');
  const [optimizing, setOptimizing] = useState(false);
  const [applyingWeights, setApplyingWeights] = useState(false);
  const [settings, setSettings] = useState(INITIAL_SETTINGS);
  const [modalMessage, setModalMessage] = useState(null);
  const [isPickingLocation, setIsPickingLocation] = useState(false);
  const [dbResults, setDbResults] = useState([]);
  const [selectedDbResultId, setSelectedDbResultId] = useState('');
  const [loadingDbResults, setLoadingDbResults] = useState(false);

  const handleSettingsChange = useCallback((newSettings) => {
    setSettings(newSettings);
  }, []);

  const handleLocationPicked = useCallback(async (center_lat, center_lon) => {
    setIsPickingLocation(false);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/reverse-geocode`, {
        center_lat: center_lat, 
        center_lon: center_lon 
      });
      const cityName = response.data.geo_info.city_name || 'Unknown Location';
      // Update settings with new location
      setSettings(prev => ({
        ...prev,
        common: {
          ...prev.common,
          cityName: cityName,
          centerLat: center_lat,
          centerLon: center_lon
        }
      }));
    } catch (error) {
      console.error('Error reverse geocoding:', error);
      // Still update coordinates even if geocoding fails
      setSettings(prev => ({
        ...prev,
        common: {
          ...prev.common,
          centerLat: center_lat,
          centerLon: center_lon
        }
      }));
    }
  }, []);

  const handlePickLocationRequest = useCallback(() => {
    setIsPickingLocation(true);
  }, []);

  const fetchCity = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const { common } = settings;
      const requestBody = { 
        data_source: dataSource,
        limit: common.limit,
        city_name: common.cityName,
        center_lat: common.centerLat,
        center_lon: common.centerLon,
        seed: common.seed,
        poi_limit: common.poiLimit,
        default_elasticity: common.defaultElasticity,
        search_radius: common.searchRadius,
        default_current_fee: common.defaultCurrentFee,
        tariffs: common.tariffs
      };
      
      const response = await axios.post(`${API_BASE_URL}/load_city`, requestBody);
      const cityData = response.data.city || response.data; // Handle both wrapped and unwrapped responses
      setCity(cityData);
      console.log('Loaded city:', cityData.name, 'with', cityData.parking_zones?.length || 0, 'zones and', cityData.point_of_interests?.length || 0, 'POIs');
    } catch (err) {
      console.error('Error fetching city:', err);
      setError('Unable to connect to backend. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  }, [dataSource, settings]);

  const fetchDbResults = async () => {
    try {
      setLoadingDbResults(true);
      const response = await axios.get(`${API_BASE_URL}/results`);
      setDbResults(response.data || []);
    } catch (err) {
      console.error('Error fetching DB results:', err);
    } finally {
      setLoadingDbResults(false);
    }
  };

  const buildMapCenter = (zones) => {
    if (!zones || zones.length === 0) return [49.0069, 8.4037];
    const avgLat = zones.reduce((sum, zone) => sum + (zone.position?.[0] || 0), 0) / zones.length;
    const avgLon = zones.reduce((sum, zone) => sum + (zone.position?.[1] || 0), 0) / zones.length;
    return [avgLat, avgLon];
  };

  const buildMapConfig = (zones) => ({
    center: buildMapCenter(zones),
    zoom: 13,
    tiles: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  });

  const buildMapSnapshotFromZones = (zones) =>
    zones.map((zone) => ({
      id: zone.id,
      name: zone.name || `Zone ${zone.id}`,
      position: zone.position,
      current_fee: zone.current_fee,
      maximum_capacity: zone.maximum_capacity || zone.capacity,
      current_capacity: zone.current_capacity || zone.occupancy,
      new_fee: zone.new_fee,
      predicted_occupancy: zone.predicted_occupancy,
      predicted_revenue: zone.predicted_revenue,
    }));

  const saveResultToDb = async ({ mapSnapshot, bestScenario, optimizationResponseData = null }) => {
    const parameters = {
      optimizer_type: optimizerType,
      weights,
      settings: settings,
      zone_count: city?.parking_zones?.length || 0,
      timestamp: new Date().toISOString(),
    };

    try {
      await axios.post(
        `${API_BASE_URL}/results`,
        {
          parameters,
          map_config: buildMapConfig(city?.parking_zones || []),
          map_snapshot: mapSnapshot,
          best_scenario: bestScenario || null,
          optimization_response: optimizationResponseData || null,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );
      fetchDbResults();
    } catch (err) {
      console.error('Error saving result to DB:', err);
    }
  };

  useEffect(() => {
    fetchCity();
    fetchDbResults();
  }, [dataSource]);

  const runOptimization = async () => {
    if (!city || !city.parking_zones || city.parking_zones.length === 0) {
      setError('No zones loaded. Please wait for zones to load first.');
      return;
    }

    try {
      setOptimizing(true);
      setError(null);

      const { common, optimizer, agent } = settings;

      const datasourceSettings = {
        data_source: dataSource,
        limit: common.limit,
        city_name: common.cityName,
        center_coords: [common.centerLat, common.centerLon],
        seed: common.seed,
        poi_limit: common.poiLimit,
        tariffs: common.tariffs,
        default_elasticity: common.defaultElasticity,
        search_radius: common.searchRadius,
        default_current_fee: common.defaultCurrentFee,
      };
      
      const request = {
        city: city,
        optimizer_settings: {
          optimizer_type: optimizerType,
          population_size: optimizer.populationSize,
          generations: optimizer.generations,
          target_occupancy: optimizer.targetOccupancy,
          random_seed: common.seed,
          min_fee: optimizer.minFee,
          max_fee: optimizer.maxFee,
          fee_increment: optimizer.feeIncrement,
          ...(optimizerType === 'agent' && {
            drivers_per_zone_capacity: agent.driversPerZoneCapacity,
            simulation_runs: agent.simulationRuns,
            driver_fee_weight: agent.driverFeeWeight,
            driver_distance_to_lot_weight: agent.driverDistanceToLotWeight,
            driver_walking_distance_weight: agent.driverWalkingDistanceWeight,
            driver_availability_weight: agent.driverAvailabilityWeight,
          }),
        },
        datasource_settings: datasourceSettings
      };

      const endpoint = `${API_BASE_URL}/optimize`

      const response = await axios.post(endpoint, request);
      setOptimizationResponse(response.data);

      console.log('Optimization completed:', response.data);
      setModalMessage(
        `Optimization completed! Found ${
          response.data.scenarios?.length || 0
        } solutions.`
      );
    } catch (err) {
      console.error('Error running optimization:', err);
      setError(`Optimization failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setOptimizing(false);
    }
  };

  const applyOptimizationWeights = async () => {
    if (!optimizationResponse) {
      setError('No optimization results available. Please run optimization first.');
      return;
    }

    try {
      setApplyingWeights(true);
      setError(null);

      const weightsDict = {
        revenue: weights.revenue,
        occupancy: weights.occupancy,
        drop: weights.drop,
        fairness: weights.fairness,
      };

      const endpoint =`${API_BASE_URL}/select_best_solution_by_weight`;
      const response = await axios.post(endpoint,
        {
          scenarios: optimizationResponse.scenarios,
          weights: weightsDict,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );

      const selectedSolution = response.data.scenario;
      setCity(prevCity => {
        if (!prevCity || !prevCity.parking_zones) return prevCity;
        return {
          ...prevCity,
          parking_zones: prevCity.parking_zones.map(zone => {
            const updatedZone = selectedSolution.zones.find(z => z.id === zone.id);
            return updatedZone ? { ...zone, new_fee: updatedZone.new_fee, predicted_occupancy: updatedZone.predicted_occupancy } : zone;
          })
        };
      });

      // Save result to DB
      const zoneById = new Map(city.parking_zones.map((zone) => [zone.id, zone]));
      const mapSnapshot = selectedSolution.zones.map((zoneResult) => {
        const original = zoneById.get(zoneResult.id);
        return {
          id: zoneResult.id,
          name: original?.name || `Zone ${zoneResult.id}`,
          position: original?.position,
          current_fee: original?.current_fee,
          maximum_capacity: original?.maximum_capacity || original?.capacity,
          current_capacity: original?.current_capacity || original?.occupancy,
          new_fee: zoneResult.new_fee,
          predicted_occupancy: zoneResult.predicted_occupancy,
          predicted_revenue: zoneResult.predicted_revenue,
        };
      });

      await saveResultToDb({
        mapSnapshot,
        bestScenario: {
          scenario_id: selectedSolution.scenario_id,
          score_revenue: selectedSolution.score_revenue,
          score_occupancy_gap: selectedSolution.score_occupancy_gap,
          score_demand_drop: selectedSolution.score_demand_drop,
          score_user_balance: selectedSolution.score_user_balance,
        },
        optimizationResponseData: optimizationResponse,
      });

      console.log('Applied optimization with weights:', weights);
    } catch (err) {
      console.error('Error applying optimization weights:', err);
      setError('Failed to apply optimization weights.');
    } finally {
      setApplyingWeights(false);
    }
  };

  const handleDownloadResults = () => {
    if (!optimizationResponse) {
      setError('No optimization results to download. Please run optimization first.');
      return;
    }

    try {
      const timestamp = new Date().toISOString().slice(0, 10);
      const filename = `parking-optimization-results-${timestamp}.json`;
      const dataStr = JSON.stringify(optimizationResponse, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      console.log(`Downloaded results: ${filename}`);

      // Save snapshot to DB
      if (city?.parking_zones && city.parking_zones.length > 0) {
        const mapSnapshot = buildMapSnapshotFromZones(city.parking_zones);
        saveResultToDb({ mapSnapshot, bestScenario: null, optimizationResponseData: optimizationResponse });
      }
    } catch (err) {
      console.error('Error downloading results:', err);
      setError('Failed to download optimization results.');
    }
  };

  const handleLoadResults = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result;
        if (typeof content === 'string') {
          const results = JSON.parse(content);
          setOptimizationResponse(results);
          
          console.log('Loaded optimization results with', results.scenarios?.length || 0, 'scenarios');
          setModalMessage(`Loaded optimization results with ${results.scenarios?.length || 0} scenarios!`);
        }
      };
      reader.readAsText(file);
    } catch (err) {
      console.error('Error loading results:', err);
      setError('Failed to load optimization results. Make sure the file is valid JSON.');
    }

    event.target.value = '';
  };

  const loadDbResult = async () => {
    if (!selectedDbResultId) return;
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(`${API_BASE_URL}/results/${selectedDbResultId}`);
      const result = response.data;

      if (!result?.map_snapshot || result.map_snapshot.length === 0) {
        setError('No map snapshot found in the selected result.');
        return;
      }

      // Restore optimization response with all scenarios if available
      // This allows applying different weights after loading from DB
      if (result.optimization_response && result.optimization_response.scenarios) {
        setOptimizationResponse(result.optimization_response);
        console.log('Restored optimization response with', result.optimization_response.scenarios.length, 'scenarios');
        
        // Build city object from map_snapshot using current_fee (pre-optimization state)
        // Remove new_fee and predicted values so user can apply weights fresh
        const loadedZones = result.map_snapshot.map((zone) => ({
          id: zone.id,
          name: zone.name,
          position: zone.position,
          current_fee: zone.current_fee ?? 0,
          maximum_capacity: zone.maximum_capacity ?? 0,
          capacity: zone.maximum_capacity ?? 0,
          current_capacity: zone.current_capacity ?? 0,
          occupancy: zone.current_capacity ?? 0,
          // Don't restore new_fee, predicted_occupancy, predicted_revenue
          // User will apply weights to generate these
          elasticity: zone.elasticity ?? -0.4,
          short_term_share: zone.short_term_share ?? 0.5,
          min_fee: zone.min_fee ?? 0.5,
          max_fee: zone.max_fee ?? 5.0,
        }));

        setCity({
          name: result.parameters?.settings?.common?.cityName || result.parameters?.city_name || 'Loaded from DB',
          parking_zones: loadedZones,
          point_of_interests: [],
        });

        setModalMessage(`Loaded ${result.optimization_response.scenarios.length} scenarios. Adjust weights and click "Apply Weights" to select a solution.`);
      } else {
        // No optimization response - just show the final solution
        setOptimizationResponse(null);
        console.log('No optimization response in DB result - loading final solution only');
        
        const loadedZones = result.map_snapshot.map((zone) => ({
          id: zone.id,
          name: zone.name,
          position: zone.position,
          current_fee: zone.current_fee ?? 0,
          maximum_capacity: zone.maximum_capacity ?? 0,
          capacity: zone.maximum_capacity ?? 0,
          current_capacity: zone.current_capacity ?? 0,
          occupancy: zone.current_capacity ?? 0,
          new_fee: zone.new_fee,
          predicted_occupancy: zone.predicted_occupancy,
          predicted_revenue: zone.predicted_revenue,
          elasticity: zone.elasticity ?? -0.4,
          short_term_share: zone.short_term_share ?? 0.5,
          min_fee: zone.min_fee ?? 0.5,
          max_fee: zone.max_fee ?? 5.0,
        }));

        setCity({
          name: result.parameters?.settings?.common?.cityName || result.parameters?.city_name || 'Loaded from DB',
          parking_zones: loadedZones,
          point_of_interests: [],
        });

        setModalMessage(`Loaded result with ${loadedZones.length} zones (final solution only - no scenarios available)`);
      }

      // Restore weights from saved parameters
      const savedWeights = result.parameters?.weights;
      if (savedWeights) {
        setWeights((prev) => ({ ...prev, ...savedWeights }));
      }

      // Restore optimizer type
      const savedOptimizer = result.parameters?.optimizer_type;
      if (savedOptimizer) {
        setOptimizerType(savedOptimizer);
      }

      // Restore settings if available
      const savedSettings = result.parameters?.settings;
      if (savedSettings) {
        setSettings((prev) => ({ ...prev, ...savedSettings }));
      }

      setSelectedZoneId(null);
    } catch (err) {
      console.error('Error loading DB result:', err);
      setError('Failed to load result from database.');
    } finally {
      setLoading(false);
    }
  };

  const selectedZone = city?.parking_zones?.find((zone) => zone.id === selectedZoneId) || null;

  return (
    <div className="app">
      {modalMessage && (
        <div className="modal-overlay" onClick={() => setModalMessage(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <p>{modalMessage}</p>
            <button onClick={() => setModalMessage(null)}>OK</button>
          </div>
        </div>
      )}
      <div className="top-info">
        <div className="top-left">
          <h1>🅿️ Parking Fee Optimization</h1>
          <p className="muted">Real-time parking zone analysis</p>
        </div>
        <OptimizerControls
          optimizerType={optimizerType}
          setOptimizerType={setOptimizerType}
          dataSource={dataSource}
          setDataSource={setDataSource}
          runOptimization={runOptimization}
          loadCity={fetchCity}
          optimizing={optimizing}
          loading={loading}
        />
        <OptimizationSettings
          dataSource={dataSource}
          optimizerType={optimizerType}
          settings={settings}
          onSettingsChange={handleSettingsChange}
          onPickLocationRequest={handlePickLocationRequest}
          isPickingLocation={isPickingLocation}
        />

        <ResultsActions
          optimizationResponse={optimizationResponse}
          handleDownloadResults={handleDownloadResults}
          handleLoadResults={handleLoadResults}
          dbResults={dbResults}
          selectedDbResultId={selectedDbResultId}
          setSelectedDbResultId={setSelectedDbResultId}
          loadDbResult={loadDbResult}
          refreshDbResults={fetchDbResults}
          loadingDbResults={loadingDbResults}
        />
      </div>

      <div className="map-wrapper">
        <div className="map-area">
          <button className="menu-toggle" onClick={() => setMenuOpen(true)}>
            ☰
          </button>

          <MenuPanel
            open={menuOpen}
            onClose={() => setMenuOpen(false)}
            weights={weights}
            setWeights={setWeights}
            onApply={applyOptimizationWeights}
            hasOptimizationResults={!!optimizationResponse}
          />

          <ParkingMap
            zones={city?.parking_zones || []}
            selectedZoneId={selectedZoneId}
            onZoneClick={setSelectedZoneId}
            isLoading={loading || optimizing || applyingWeights}
            loadingMessage={
              optimizing ? 'Optimizing parking zones...' :
              applyingWeights ? 'Applying weights to zones...' :
              'Loading parking zones...'
            }
            error={error}
            isPickingLocation={isPickingLocation}
            onLocationPicked={handleLocationPicked}
          />

          {selectedZone && (
            <InfoPanel zone={selectedZone} onClose={() => setSelectedZoneId(null)} />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
