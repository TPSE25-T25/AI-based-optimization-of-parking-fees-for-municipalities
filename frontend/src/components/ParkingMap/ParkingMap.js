// PARKING MAP - Interactive Leaflet map with zone markers and occupancy visualization

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './ParkingMap.css';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// ===== COMPONENT =====
const ParkingMap = ({ zones, selectedZoneId, onZoneClick, isLoading, error }) => {
  // ===== STATE =====
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [mapCenter, setMapCenter] = useState([49.0069, 8.4037]);

  // ===== EFFECTS =====
  useEffect(() => {
    if (zones && zones.length > 0) {
      const hasCoordinates = zones.some((zone) => zone.lat && zone.lon);
      if (hasCoordinates) {
        const avgLat = zones.reduce((sum, zone) => sum + (zone.lat || 0), 0) / zones.length;
        const avgLon = zones.reduce((sum, zone) => sum + (zone.lon || 0), 0) / zones.length;
        setMapCenter([avgLat, avgLon]);
      }
    }
  }, [zones]);

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
  }, [mapCenter]);

  useEffect(() => {
    if (!mapInstanceRef.current || !zones) return;

    Object.values(markersRef.current).forEach((marker) => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = {};

    zones.forEach((zone) => {
      const lat = zone.lat || mapCenter[0];
      const lon = zone.lon || mapCenter[1];

      if (!lat || !lon) return;

      let color = '#3388ff';
      if (zone.occupancy_rate >= 0.85) {
        color = '#e74c3c';
      } else if (zone.occupancy_rate >= 0.65) {
        color = '#f39c12';
      } else if (zone.occupancy_rate >= 0.3) {
        color = '#27ae60';
      } else {
        color = '#9b59b6';
      }

      const marker = L.circleMarker([lat, lon], {
        radius: 8,
        fillColor: color,
        color: '#000',
        weight: 2,
        opacity: selectedZoneId === zone.id ? 1 : 0.7,
        fillOpacity: selectedZoneId === zone.id ? 0.9 : 0.7,
      });

      const popupContent = `
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h4 style="margin: 8px 0;">${zone.name || `Zone ${zone.id}`}</h4>
          <hr style="margin: 8px 0;" />
          <p><b>Current Fee:</b> $${(zone.current_fee || 0).toFixed(2)}/hr</p>
          <p><b>Occupancy:</b> ${((zone.occupancy_rate || 0) * 100).toFixed(1)}%</p>
          <p><b>Capacity:</b> ${zone.capacity || 'N/A'} spots</p>
          ${
            zone.suggested_fee
              ? `<p><b>Suggested Fee:</b> $${zone.suggested_fee.toFixed(2)}/hr</p>`
              : ''
          }
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

  // ===== RENDER =====
  if (error) {
    return (
      <div className="parking-map-error">
        <div className="parking-map-error-card">
          <p className="parking-map-error-title">Error loading map</p>
          <p className="parking-map-error-text">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={mapRef} className="parking-map">
      {isLoading && (
        <div className="parking-map-loading">
          <p>Loading parking zones...</p>
        </div>
      )}
    </div>
  );
};

// ===== EXPORT =====
export default ParkingMap;
