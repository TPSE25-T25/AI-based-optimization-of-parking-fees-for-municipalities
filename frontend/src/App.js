import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

import ParkingMap from './components/ParkingMap';
import MenuPanel from './components/MenuPanel';
import InfoPanel from './components/InfoPanel';
import OptimizationSettings from './components/OptimizationSettings';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI state
  const [menuOpen, setMenuOpen] = useState(false);
  const [weights, setWeights] = useState({ revenue: 50, occupancy: 30, drop: 10, fairness: 10 });
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [optimizationResponse, setOptimizationResponse] = useState(null);
  const [optimizerType, setOptimizerType] = useState('elasticity');
  const [optimizing, setOptimizing] = useState(false);

  // Optimization Settings state

  const [populationSize, setPopulationSize] = useState(100);
  const [generations, setGenerations] = useState(40);
  const [targetOccupancy, setTargetOccupancy] = useState(0.85);

  useEffect(() => {
    fetchZones();
  }, []);

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
        zones: zones.map(zone => ({
          id: zone.id,
          pseudonym: zone.name,
          price: zone.current_fee || 2.0,
          position: [zone.lat, zone.lon],
          maximum_capacity: zone.capacity || 100,
          current_capacity: Math.floor((zone.occupancy_rate || 0.5) * (zone.capacity || 100)),
          min_fee: 0.5,
          max_fee: 5.0,
          elasticity: -0.4,
          short_term_share: 0.5
        })),
        settings: {
          population_size: populationSize,
          generations: generations,
          target_occupancy: targetOccupancy
        }
      };

      console.log(request);

      const endpoint = optimizerType === 'elasticity' 
        ? `${API_BASE_URL}/optimize_elasticity`
        : `${API_BASE_URL}/optimize_agent`;

      const response = await axios.post(endpoint, request);
      setOptimizationResponse(response.data);
      
      console.log('Optimization completed:', response.data);
      alert(`Optimization completed! Found ${response.data.scenarios?.length || 0} solutions.`);
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
        fairness: weights.fairness
      };

      const endpoint = optimizerType === 'elasticity'
        ? `${API_BASE_URL}/select_best_solution_elasticity`
        : `${API_BASE_URL}/select_best_solution_agent`;

      const response = await axios.post(
        endpoint,
        {
          optimization_response: optimizationResponse,
          weights: weightsDict
        },
        { 
          headers: { 'Content-Type': 'application/json' }
        }
      );

      // Update zones with suggested fees from the selected solution
      const selectedSolution = response.data;
      setZones(prevZones => 
        prevZones.map(zone => {
          const zoneResult = selectedSolution.zones.find(
            z => z.zone_id === zone.id
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

  const selectedZone = zones.find(z => z.id === selectedZoneId) || null;

  return (
    <div className="App">
      <div className="top-info">
        <div className="top-left">
          <h1>🅿️ Parking Fee Optimization</h1>
          <p className="muted">Real-time parking zone analysis with OpenStreetMap</p>
        </div>
        <div className="top-right-info">
          <div style={{ marginBottom: '10px' }}>
            <label style={{ marginRight: '10px' }}>Optimizer:</label>
            <select 
              value={optimizerType} 
              onChange={(e) => setOptimizerType(e.target.value)}
              style={{ padding: '5px', marginRight: '10px' }}
            >
              <option value="elasticity">Elasticity-Based</option>
              <option value="agent">Agent-Based</option>
            </select>
            <button 
              onClick={runOptimization} 
              disabled={optimizing || loading}
              style={{ padding: '5px 15px', cursor: optimizing ? 'not-allowed' : 'pointer' }}
            >
              {optimizing ? '⏳ Optimizing...' : '▶️ Run Optimization'}
            </button>
          </div>
          <small>Backend: {API_BASE_URL} | Zones: {zones.length}</small>
        </div>
      </div>

      <div className="map-wrapper">
        <div className="map-area">
          {/* Menu button */}
          <button className="menu-toggle" onClick={() => setMenuOpen(true)}>☰</button>

          {/* Menu panel */}
          <MenuPanel 
            open={menuOpen} 
            onClose={() => setMenuOpen(false)} 
            weights={weights} 
            setWeights={setWeights}
            onApply={applyOptimizationWeights}
            hasOptimizationResults={!!optimizationResponse}
          />

          <OptimizationSettings 
            handleSubmit={runOptimization}
            generations={generations}
            populationSize={populationSize}
            targetOccupancy={targetOccupancy}
            setGenerations={setGenerations}
            setPopulationSize={setPopulationSize}
            setTargetOccupancy={setTargetOccupancy}
          />

          {/* Interactive map */}
          <ParkingMap 
            zones={zones}
            selectedZoneId={selectedZoneId}
            onZoneClick={setSelectedZoneId}
            isLoading={loading}
            error={error}
          />

          {/* Info panel */}
          {selectedZone && (
            <InfoPanel 
              zone={selectedZone} 
              onClose={() => setSelectedZoneId(null)} 
            />
          )}
        </div>
      </div>

      <footer className="footer-note">
        <small>Click on any parking zone marker to view details. Use the menu to adjust optimization weights.</small>
      </footer>
    </div>
  );
}

export default App;