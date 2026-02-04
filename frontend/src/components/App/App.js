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

  // ===== EFFECTS =====
  useEffect(() => {
    fetchZones();
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
          pseudonym: zone.name,
          price: zone.current_fee || 2.0,
          position: [zone.lat, zone.lon],
          maximum_capacity: zone.capacity || 100,
          current_capacity: Math.floor(
            (zone.occupancy_rate || 0.5) * (zone.capacity || 100)
          ),
          min_fee: 0.5,
          max_fee: 5.0,
          elasticity: -0.4,
          short_term_share: 0.5,
        })),
        settings: {
          population_size: 200,
          generations: 50,
          target_occupancy: 0.85,
        },
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

      // Update zones with suggested fees from the selected solution
      const selectedSolution = response.data;
      setZones((prevZones) =>
        prevZones.map((zone) => {
          const zoneResult = selectedSolution.zones.find(
            (zoneItem) => zoneItem.zone_id === zone.id
          );
          return zoneResult
            ? { ...zone, suggested_fee: zoneResult.new_fee }
            : zone;
        })
      );

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
    } catch (err) {
      console.error('Error downloading results:', err);
      setError('Failed to download optimization results.');
    }
  };

  // Load optimization results from JSON file
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
          alert(`Loaded optimization results with ${results.scenarios?.length || 0} scenarios!`);
        }
      };
      reader.readAsText(file);
    } catch (err) {
      console.error('Error loading results:', err);
      setError('Failed to load optimization results. Make sure the file is valid JSON.');
    }

    // Reset file input
    event.target.value = '';
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
          handleLoadResults={handleLoadResults}
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
