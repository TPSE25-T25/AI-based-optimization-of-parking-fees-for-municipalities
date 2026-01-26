import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const ParkingMap = ({ zones, selectedZoneId, onZoneClick, isLoading, error }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [mapCenter, setMapCenter] = useState([49.0069, 8.4037]); // Default: Karlsruhe

  // Calculate map center from zones
  useEffect(() => {
    if (zones && zones.length > 0) {
      const hasCoordinates = zones.some(z => z.lat && z.lon);
      if (hasCoordinates) {
        const avgLat = zones.reduce((sum, z) => sum + (z.lat || 0), 0) / zones.length;
        const avgLon = zones.reduce((sum, z) => sum + (z.lon || 0), 0) / zones.length;
        setMapCenter([avgLat, avgLon]);
      }
    }
  }, [zones]);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current) return;

    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView(mapCenter, 13);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapInstanceRef.current);
    } else {
      mapInstanceRef.current.setView(mapCenter, 13);
    }

    return () => {
      // Clean up is handled in the zones effect
    };
  }, [mapCenter]);

  // Update markers when zones change
  useEffect(() => {
    if (!mapInstanceRef.current || !zones) return;

    // Clear old markers
    Object.values(markersRef.current).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = {};

    // Add new markers
    zones.forEach(zone => {
      const lat = zone.lat || mapCenter[0];
      const lon = zone.lon || mapCenter[1];

      if (!lat || !lon) return;

      // Determine color based on occupancy
      let color = '#3388ff'; // default blue
      if (zone.occupancy_rate >= 0.85) {
        color = '#e74c3c'; // red - very full
      } else if (zone.occupancy_rate >= 0.65) {
        color = '#f39c12'; // orange - moderately full
      } else if (zone.occupancy_rate >= 0.3) {
        color = '#27ae60'; // green - good availability
      } else {
        color = '#9b59b6'; // purple - very available
      }

      const marker = L.circleMarker([lat, lon], {
        radius: 8,
        fillColor: color,
        color: '#000',
        weight: 2,
        opacity: selectedZoneId === zone.id ? 1 : 0.7,
        fillOpacity: selectedZoneId === zone.id ? 0.9 : 0.7,
      });

      // Create popup content
      const popupContent = `
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h4 style="margin: 8px 0;">${zone.name || `Zone ${zone.id}`}</h4>
          <hr style="margin: 8px 0;" />
          <p><b>Current Fee:</b> $${(zone.current_fee || 0).toFixed(2)}/hr</p>
          <p><b>Occupancy:</b> ${((zone.occupancy_rate || 0) * 100).toFixed(1)}%</p>
          <p><b>Capacity:</b> ${zone.capacity || 'N/A'} spots</p>
          ${zone.suggested_fee ? `<p><b>Suggested Fee:</b> $${zone.suggested_fee.toFixed(2)}/hr</p>` : ''}
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', () => {
        onZoneClick(zone.id);
        marker.openPopup();
      });

      marker.addTo(mapInstanceRef.current);
      markersRef.current[zone.id] = marker;
    });
  }, [zones, selectedZoneId, mapCenter, onZoneClick]);

  if (error) {
    return (
      <div style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
      }}>
        <div style={{
          textAlign: 'center',
          padding: '20px',
          backgroundColor: '#fff',
          borderRadius: '8px',
          border: '1px solid #ddd',
        }}>
          <p style={{ color: '#e74c3c', fontWeight: 'bold' }}>Error loading map</p>
          <p style={{ fontSize: '12px', color: '#666' }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={mapRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        backgroundColor: '#f0f0f0',
      }}
    >
      {isLoading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            padding: '16px 24px',
            borderRadius: '6px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            zIndex: 1000,
          }}
        >
          <p style={{ margin: '0', color: '#666' }}>Loading parking zones...</p>
        </div>
      )}
    </div>
  );
};

export default ParkingMap;
