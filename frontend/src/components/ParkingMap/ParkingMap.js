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

// ===== HELPER FUNCTIONS =====
const getColorFromOccupancy = (occupancyRate) => {
  // Clamp occupancy rate between 0 and 1
  const rate = Math.max(0, Math.min(1, occupancyRate));
  
  // Define colors: Green (0%), Yellow (50%), Red (100%)
  const green = { r: 39, g: 174, b: 96 };
  const yellow = { r: 243, g: 156, b: 18 };
  const red = { r: 231, g: 76, b: 60 };
  
  let r, g, b;
  
  if (rate <= 0.5) {
    // Interpolate between green and yellow (0% to 50%)
    const t = rate * 2; // Scale to 0-1 for this range
    r = Math.round(green.r + (yellow.r - green.r) * t);
    g = Math.round(green.g + (yellow.g - green.g) * t);
    b = Math.round(green.b + (yellow.b - green.b) * t);
  } else {
    // Interpolate between yellow and red (50% to 100%)
    const t = (rate - 0.5) * 2; // Scale to 0-1 for this range
    r = Math.round(yellow.r + (red.r - yellow.r) * t);
    g = Math.round(yellow.g + (red.g - yellow.g) * t);
    b = Math.round(yellow.b + (red.b - yellow.b) * t);
  }
  
  return `rgb(${r}, ${g}, ${b})`;
};

// ===== COMPONENT =====
const ParkingMap = ({ zones, selectedZoneId, onZoneClick, isLoading, loadingMessage = 'Loading parking zones...', error, isPickingLocation, onLocationPicked }) => {
  // ===== STATE =====
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [mapCenter, setMapCenter] = useState([49.0069, 8.4037]);

  // ===== EFFECTS =====
  useEffect(() => {
    if (zones && zones.length > 0) {
      const hasCoordinates = zones.some((zone) => zone.position);
      if (hasCoordinates) {
        const avgLat = zones.reduce((sum, zone) => sum + (zone.position[0] || 0), 0) / zones.length;
        const avgLon = zones.reduce((sum, zone) => sum + (zone.position[1] || 0), 0) / zones.length;
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

  // Handle location picking mode
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (isPickingLocation) {
      // Change cursor to crosshair
      mapInstanceRef.current.getContainer().style.cursor = 'crosshair';
      
      // Add click handler for picking location
      const handleMapClick = (e) => {
        const { lat, lng } = e.latlng;
        onLocationPicked(lat, lng);
      };
      
      mapInstanceRef.current.on('click', handleMapClick);
      
      return () => {
        mapInstanceRef.current.off('click', handleMapClick);
        mapInstanceRef.current.getContainer().style.cursor = '';
      };
    } else {
      mapInstanceRef.current.getContainer().style.cursor = '';
    }
  }, [isPickingLocation, onLocationPicked]);

  useEffect(() => {
    if (!mapInstanceRef.current || !zones) return;

    Object.values(markersRef.current).forEach((marker) => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current = {};

    zones.forEach((zone) => {
      const lat = zone.position[0] || mapCenter[0];
      const lon = zone.position[1] || mapCenter[1];

      if (!lat || !lon) return;

      const occupancyRate = (zone.current_capacity / zone.maximum_capacity) ?? 0;
      const color = getColorFromOccupancy(occupancyRate);

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
          <p><b>Current Fee:</b> $${zone.current_fee.toFixed(2)}/hr</p>
          <p><b>Occupancy:</b> ${((zone.current_capacity / zone.maximum_capacity) * 100).toFixed(1)}%</p>
          <p><b>Capacity:</b> ${zone.maximum_capacity || 'N/A'} spots</p>
          ${
            zone.new_fee
              ? `<p><b>New Fee:</b> $${zone.new_fee.toFixed(2)}/hr</p>`
              : ''
          }
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', (e) => {
        if (!isPickingLocation) {
          onZoneClick(zone.id);
          marker.openPopup();
        } else {
          // Prevent zone selection when picking location
          L.DomEvent.stopPropagation(e);
        }
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
          <p>{loadingMessage}</p>
        </div>
      )}
      {isPickingLocation && (
        <div className="parking-map-picking-overlay">
          <div className="parking-map-picking-message">
            📍 Click on the map to select a location
          </div>
        </div>
      )}
    </div>
  );
};

// ===== EXPORT =====
export default ParkingMap;
