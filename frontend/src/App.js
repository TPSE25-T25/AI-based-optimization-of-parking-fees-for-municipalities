import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedZone, setSelectedZone] = useState('');
  const [targetOccupancy, setTargetOccupancy] = useState(0.75);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [optimizing, setOptimizing] = useState(false);

  // Fetch parking zones on component mount
  useEffect(() => {
    fetchZones();
  }, []);

  const fetchZones = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/zones`);
      setZones(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch parking zones. Make sure the backend server is running.');
      console.error('Error fetching zones:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimization = async (e) => {
    e.preventDefault();
    
    if (!selectedZone) {
      setError('Please select a parking zone');
      return;
    }

    try {
      setOptimizing(true);
      setOptimizationResult(null);
      setError(null);

      const response = await axios.post(`${API_BASE_URL}/optimize`, {
        zone_id: parseInt(selectedZone),
        target_occupancy: targetOccupancy
      });

      setOptimizationResult(response.data);
      
      // Refresh zones to see updated suggested fees
      await fetchZones();
    } catch (err) {
      setError('Failed to optimize parking fee. Please try again.');
      console.error('Error optimizing fee:', err);
    } finally {
      setOptimizing(false);
    }
  };

  const ZoneCard = ({ zone }) => (
    <div className="zone-card">
      <h3>{zone.name}</h3>
      
      <div className="zone-stats">
        <div className="stat-item">
          <span className="stat-label">Current Fee</span>
          <span className="stat-value">${zone.current_fee}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Occupancy</span>
          <span className="stat-value">{(zone.occupancy_rate * 100).toFixed(1)}%</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Suggested Fee</span>
          <span className="stat-value">${zone.suggested_fee}</span>
        </div>
      </div>
      
      <div className="occupancy-bar">
        <div 
          className="occupancy-fill" 
          style={{ 
            width: `${zone.occupancy_rate * 100}%`,
            backgroundColor: zone.occupancy_rate > 0.8 ? '#e74c3c' : zone.occupancy_rate > 0.6 ? '#f39c12' : '#27ae60'
          }}
        ></div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="App">
        <div className="container">
          <div className="loading">Loading parking zones...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="header">
        <h1>🅿️ Parking Fee Optimization System</h1>
        <p>AI-based optimization of parking fees for municipalities</p>
      </header>
      
      <div className="container">
        {error && (
          <div className="error">
            {error}
          </div>
        )}
        
        <h2>Current Parking Zones</h2>
        <div className="zones-grid">
          {zones.map(zone => (
            <ZoneCard key={zone.id} zone={zone} />
          ))}
        </div>
        
        <div className="optimization-section">
          <h2>Fee Optimization</h2>
          <form onSubmit={handleOptimization}>
            <div className="form-group">
              <label htmlFor="zone-select">Select Parking Zone:</label>
              <select
                id="zone-select"
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
              >
                <option value="">-- Select a zone --</option>
                {zones.map(zone => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name} (Current: ${zone.current_fee})
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="target-occupancy">Target Occupancy Rate:</label>
              <input
                id="target-occupancy"
                type="number"
                min="0.1"
                max="1.0"
                step="0.05"
                value={targetOccupancy}
                onChange={(e) => setTargetOccupancy(parseFloat(e.target.value))}
              />
              <small>({(targetOccupancy * 100).toFixed(0)}%)</small>
            </div>
            
            <button 
              type="submit" 
              className="btn"
              disabled={optimizing || !selectedZone}
            >
              {optimizing ? 'Optimizing...' : 'Optimize Fee'}
            </button>
          </form>
          
          {optimizationResult && (
            <div className="result">
              <h3>Optimization Result</h3>
              <p><strong>Zone:</strong> {optimizationResult.message}</p>
              <p><strong>Current Fee:</strong> ${optimizationResult.current_fee}</p>
              <p><strong>Suggested Fee:</strong> ${optimizationResult.suggested_fee}</p>
              <p><strong>Current Occupancy:</strong> {(optimizationResult.current_occupancy * 100).toFixed(1)}%</p>
              <p><strong>Target Occupancy:</strong> {(optimizationResult.target_occupancy * 100).toFixed(1)}%</p>
            </div>
          )}
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '30px', color: '#666' }}>
          <p>
            <button className="btn" onClick={fetchZones}>
              🔄 Refresh Data
            </button>
          </p>
          <small>Backend API: {API_BASE_URL}</small>
        </div>
      </div>
    </div>
  );
}

export default App;