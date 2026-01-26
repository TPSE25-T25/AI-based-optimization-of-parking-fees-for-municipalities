import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

import ParkingMap from './components/ParkingMap';
import MenuPanel from './components/MenuPanel';
import InfoPanel from './components/InfoPanel';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI state
  const [menuOpen, setMenuOpen] = useState(false);
  const [weights, setWeights] = useState({ revenue: 50, occupancy: 30, drop: 10, fairness: 10 });
  const [selectedZoneId, setSelectedZoneId] = useState(null);

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

  const selectedZone = zones.find(z => z.id === selectedZoneId) || null;

  return (
    <div className="App">
      <div className="top-info">
        <div className="top-left">
          <h1>🅿️ Parking Fee Optimization</h1>
          <p className="muted">Real-time parking zone analysis with OpenStreetMap</p>
        </div>
        <div className="top-right-info">
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