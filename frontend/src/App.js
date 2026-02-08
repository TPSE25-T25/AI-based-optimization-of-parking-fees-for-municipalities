import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

import ParkingSpot from './components/ParkingSpot';
import MenuPanel from './components/MenuPanel';
import InfoPanel from './components/InfoPanel';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // Keep existing data hooks for the rest of the UI
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Map-specific UI state
  const [menuOpen, setMenuOpen] = useState(false);
  const [weights, setWeights] = useState({ Safety: 50, Accessibility: 20, Revenue: 30 });
  const [selectedSpotId, setSelectedSpotId] = useState(null);

  // Parking spots positions (percentages)
  const parkingSpots = [
    { id: 1, label: 'P1', left: 20, top: 30 },
    { id: 2, label: 'P2', left: 40, top: 60 },
    { id: 3, label: 'P3', left: 60, top: 25 },
    { id: 4, label: 'P4', left: 75, top: 55 },
    { id: 5, label: 'P5', left: 50, top: 75 }
  ];

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
      // It's OK if the backend isn't available for the map — keep UI usable
      setError(null);
    } finally {
      setLoading(false);
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
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  const selectedSpot = parkingSpots.find(s => s.id === selectedSpotId) || null;

  return (
    <div className="App">
      <div className="top-info">
        <div className="top-left">
          <h1>🅿️ Parking Fee Optimization</h1>
          <p className="muted">Prototype UI — Map view and controls</p>
        </div>
        <div className="top-right-info">
          <small>Backend: {API_BASE_URL}</small>
        </div>
      </div>

      <div className="map-wrapper">
        <div className="map-area">
          {/* Menu button in top-right */}
          <button className="menu-toggle" onClick={() => setMenuOpen(true)}>☰</button>

          {/* Menu panel / sliders */}
          <MenuPanel open={menuOpen} onClose={() => setMenuOpen(false)} weights={weights} setWeights={setWeights} />

          {/* Parking spots */}
          {parkingSpots.map(spot => (
            <ParkingSpot
              key={spot.id}
              id={spot.id}
              label={spot.label}
              left={spot.left}
              top={spot.top}
              onClick={(id) => setSelectedSpotId(id)}
              isSelected={selectedSpotId === spot.id}
            />
          ))}

          {/* Info panel */}
          <InfoPanel spot={selectedSpot} onClose={() => setSelectedSpotId(null)} />
        </div>
      </div>

      <footer className="footer-note">
        <small>Click a parking spot (P1–P5) to view details. Sliders are placeholders for weights.</small>
      </footer>
    </div>
  );
}

export default App;