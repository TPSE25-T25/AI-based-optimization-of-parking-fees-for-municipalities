// APP - Main application container and state management

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

import ConfigurationPanel from '../ConfigurationPanel/ConfigurationPanel';
import InfoPanel from '../InfoPanel/InfoPanel';
import MenuPanel from '../MenuPanel/MenuPanel';
import ParkingMap from '../ParkingMap/ParkingMap';
import OptimizerControls from './OptimizerControls';
import ResultsActions from './ResultsActions';

// ===== CONSTANTS =====
const API_BASE_URL = 'http://localhost:8000';
const DEFAULT_MAP_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const DEFAULT_MAP_ZOOM = 13;
const optimizationSettings = {
  population_size: 200,
  generations: 50,
  target_occupancy: 0.85,
};

function App() {
  // ===== STATE =====
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [weights, setWeights] = useState({
    revenue: 50,
    occupancy: 30,
    drop: 10,
    fairness: 10,
  });
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [optimizationResponse, setOptimizationResponse] = useState(null);
  const [optimizerType, setOptimizerType] = useState('elasticity');
  const [optimizing, setOptimizing] = useState(false);
  const [dbResults, setDbResults] = useState([]);
  const [selectedDbResultId, setSelectedDbResultId] = useState('');
  const [loadingDbResults, setLoadingDbResults] = useState(false);

  // ===== EFFECTS =====
  useEffect(() => {
    fetchZones();
    fetchDbResults();
  }, []);

  // ===== EVENT HANDLERS =====
  const fetchZones = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/zones`);
      setZones(response.data);
    } catch (err) {
      console.error('Error fetching zones:', err);
      setError('Unable to connect to backend. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

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

  const buildMapCenter = (sourceZones) => {
    if (!sourceZones.length) return [49.0069, 8.4037];
    const avgLat = sourceZones.reduce((sum, zone) => sum + (zone.position?.[0] || 0), 0) / sourceZones.length;
    const avgLon = sourceZones.reduce((sum, zone) => sum + (zone.position?.[1] || 0), 0) / sourceZones.length;
    return [avgLat, avgLon];
  };

  const buildMapConfig = (sourceZones) => ({
    center: buildMapCenter(sourceZones),
    zoom: DEFAULT_MAP_ZOOM,
    tiles: DEFAULT_MAP_TILES,
  });

  const buildMapSnapshotFromZones = (sourceZones) =>
    sourceZones.map((zone) => ({
      id: zone.id,
      name: zone.name || `Zone ${zone.id}`,
      position: zone.position,
      current_fee: zone.current_fee,
      maximum_capacity: zone.maximum_capacity,
      current_capacity: zone.current_capacity,
      new_fee: zone.new_fee,
      predicted_occupancy: zone.predicted_occupancy,
      predicted_revenue: zone.predicted_revenue,
    }));

  const saveResultToDb = async ({ mapSnapshot, bestScenario }) => {
    const parameters = {
      optimizer_type: optimizerType,
      weights,
      settings: optimizationSettings,
      zone_count: zones.length,
      timestamp: new Date().toISOString(),
    };

    await axios.post(
      `${API_BASE_URL}/results`,
      {
        parameters,
        map_config: buildMapConfig(zones),
        map_snapshot: mapSnapshot,
        best_scenario: bestScenario || null,
      },
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
    fetchDbResults();
  };

  const runOptimization = async () => {
    if (zones.length === 0) {
      setError('No zones loaded. Please wait for zones to load first.');
      return;
    }

    try {
      setOptimizing(true);
      setError(null);

      // Prepare optimization request
      const request = {
        zones: zones.map((zone) => ({
          id: zone.id,
          name: zone.name || `Zone ${zone.id}`,
          current_fee: zone.current_fee || 2.0,
          position: zone.position,
          maximum_capacity: zone.maximum_capacity || 100,
          current_capacity: zone.current_capacity || 0,
          min_fee: 0.5,
          max_fee: 5.0,
          elasticity: -0.4,
          short_term_share: 0.5,
        })),
        settings: optimizationSettings,
      };

      const endpoint =
        optimizerType === 'elasticity'
          ? `${API_BASE_URL}/optimize_elasticity`
          : `${API_BASE_URL}/optimize_agent`;

      const response = await axios.post(endpoint, request);
      setOptimizationResponse(response.data);

      console.log('Optimization completed:', response.data);
      alert(
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
      setLoading(true);
      setError(null);

      // Convert weights object to dict with normalized values (0-1)
      const weightsDict = {
        revenue: weights.revenue,
        occupancy: weights.occupancy,
        drop: weights.drop,
        fairness: weights.fairness,
      };

      const endpoint =
        optimizerType === 'elasticity'
          ? `${API_BASE_URL}/select_best_solution_elasticity`
          : `${API_BASE_URL}/select_best_solution_agent`;

      const response = await axios.post(
        endpoint,
        {
          optimization_response: optimizationResponse,
          weights: weightsDict,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );

      // Update zones with new fees from the selected solution
      const selectedSolution = response.data;
      setZones((prevZones) =>
        prevZones.map((zone) => {
          const zoneResult = selectedSolution.zones.find(
            (zoneItem) => zoneItem.id === zone.id
          );
          return zoneResult
            ? { ...zone, 
                new_fee: zoneResult.new_fee, 
                predicted_occupancy: zoneResult.predicted_occupancy, 
                //predicted_revenue: zoneResult.predicted_revenue #TODO: Revenue prediction can be very small???
              }
            : zone;
        })
      );

      const zoneById = new Map(zones.map((zone) => [zone.id, zone]));
      const mapSnapshot = selectedSolution.zones.map((zoneResult) => {
        const original = zoneById.get(zoneResult.id);
        return {
          id: zoneResult.id,
          name: original?.name || `Zone ${zoneResult.id}`,
          position: original?.position,
          current_fee: original?.current_fee,
          maximum_capacity: original?.maximum_capacity,
          current_capacity: original?.current_capacity,
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
      });

      console.log('Applied optimization with weights:', weights);
    } catch (err) {
      console.error('Error applying optimization weights:', err);
      setError('Failed to apply optimization weights.');
    } finally {
      setLoading(false);
    }
  };

  // Download optimization results as JSON file
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

      if (zones.length > 0) {
        const mapSnapshot = buildMapSnapshotFromZones(zones);
        saveResultToDb({ mapSnapshot, bestScenario: null });
      }
    } catch (err) {
      console.error('Error downloading results:', err);
      setError('Failed to download optimization results.');
    }
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

      setZones(
        result.map_snapshot.map((zone) => ({
          id: zone.id,
          name: zone.name,
          position: zone.position,
          current_fee: zone.current_fee ?? 0,
          maximum_capacity: zone.maximum_capacity ?? 0,
          current_capacity: zone.current_capacity ?? 0,
          new_fee: zone.new_fee,
          predicted_occupancy: zone.predicted_occupancy,
          predicted_revenue: zone.predicted_revenue,
        }))
      );

      const savedWeights = result.parameters?.weights;
      if (savedWeights) {
        setWeights((prev) => ({ ...prev, ...savedWeights }));
      }

      const savedOptimizer = result.parameters?.optimizer_type;
      if (savedOptimizer) {
        setOptimizerType(savedOptimizer);
      }

      setSelectedZoneId(null);
      setOptimizationResponse(null);
    } catch (err) {
      console.error('Error loading DB result:', err);
      setError('Failed to load result from database.');
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER =====
  const selectedZone = zones.find((zone) => zone.id === selectedZoneId) || null;

  return (
    <div className="app">
      <div className="top-info">
        <div className="top-left">
          <h1>🅿️ Parking Fee Optimization</h1>
          <p className="muted">Real-time parking zone analysis with OpenStreetMap</p>
        </div>
        <OptimizerControls
          optimizerType={optimizerType}
          setOptimizerType={setOptimizerType}
          runOptimization={runOptimization}
          optimizing={optimizing}
          loading={loading}
        />
        <ConfigurationPanel />

        <ResultsActions
          optimizationResponse={optimizationResponse}
          handleDownloadResults={handleDownloadResults}
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
            zones={zones}
            selectedZoneId={selectedZoneId}
            onZoneClick={setSelectedZoneId}
            isLoading={loading}
            error={error}
          />

          {selectedZone && (
            <InfoPanel zone={selectedZone} onClose={() => setSelectedZoneId(null)} />
          )}
        </div>
      </div>
    </div>
  );
}

// ===== EXPORT =====
export default App;
