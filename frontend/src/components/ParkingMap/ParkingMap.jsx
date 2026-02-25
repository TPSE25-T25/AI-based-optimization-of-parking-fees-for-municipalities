// PARKING MAP - Interactive Leaflet map with zone markers and occupancy visualization

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import './ParkingMap.css';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;

// ===== CONSTANTS =====
const CLUSTER_ZOOM_THRESHOLD = 16;

// ===== CLUSTER HELPER =====
const computeClusters = (zones) => {
  const map = new Map();
  zones.forEach(zone => {
    const cid = (zone.cluster_id !== null && zone.cluster_id !== undefined && zone.cluster_id >= 0)
      ? zone.cluster_id : null;
    if (cid === null) return;
    if (!map.has(cid)) map.set(cid, []);
    map.get(cid).push(zone);
  });
  return [...map.entries()]
    .filter(([, zs]) => zs.length > 1)
    .map(([id, zs]) => ({
      id,
      zones: zs,
      totalCapacity: zs.reduce((s, z) => s + (z.maximum_capacity || 0), 0),
      totalOccupied:  zs.reduce((s, z) => s + (z.current_capacity  || 0), 0),
      centerLat: zs.reduce((s, z) => s + z.position[0], 0) / zs.length,
      centerLon: zs.reduce((s, z) => s + z.position[1], 0) / zs.length,
    }));
};
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
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
  const clusterMarkersRef = useRef({});
  const [mapCenter, setMapCenter] = useState([49.0069, 8.4037]);
  const [currentZoom, setCurrentZoom] = useState(13);
  const [expandedClusters, setExpandedClusters] = useState(new Set());

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

      mapInstanceRef.current.on('zoomend', () => {
        const z = mapInstanceRef.current.getZoom();
        setCurrentZoom(z);
        if (z >= CLUSTER_ZOOM_THRESHOLD) setExpandedClusters(new Set());
      });
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

    // Clear all existing markers
    Object.values(markersRef.current).forEach((m) => mapInstanceRef.current.removeLayer(m));
    Object.values(clusterMarkersRef.current).forEach((m) => mapInstanceRef.current.removeLayer(m));
    markersRef.current = {};
    clusterMarkersRef.current = {};

    const clusters = computeClusters(zones);
    const expandAtLowZoom = currentZoom < CLUSTER_ZOOM_THRESHOLD;
    const clusteredZoneIds = new Set(clusters.flatMap((c) => c.zones.map((z) => z.id)));

    // ── Cluster bubbles ──────────────────────────────────────────────────────
    if (expandAtLowZoom) {
      clusters.forEach((cluster) => {
        if (expandedClusters.has(cluster.id)) return; // already expanded

        const occupancyRate = cluster.totalOccupied / (cluster.totalCapacity || 1);
        const color = getColorFromOccupancy(occupancyRate);
        const size = Math.max(32, Math.min(48, 18 + cluster.zones.length * 2));

        const icon = L.divIcon({
          html: `<div class="cluster-bubble" style="width:${size}px;height:${size}px;background-color:${color};">
                   <span class="cluster-bubble_count">${cluster.zones.length}</span>
                   <span class="cluster-bubble_spaces">${cluster.totalCapacity}</span>
                 </div>`,
          className: '',
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });

        const marker = L.marker([cluster.centerLat, cluster.centerLon], { icon });
        marker.on('click', () =>
          setExpandedClusters((prev) => new Set([...prev, cluster.id]))
        );
        marker.addTo(mapInstanceRef.current);
        clusterMarkersRef.current[cluster.id] = marker;
      });
    }

    // ── Individual zone markers ──────────────────────────────────────────────
    zones.forEach((zone) => {
      // Skip zones hidden inside a collapsed cluster bubble
      const inCluster = clusteredZoneIds.has(zone.id);
      if (inCluster && expandAtLowZoom) {
        const clusterForZone = clusters.find((c) => c.zones.some((z) => z.id === zone.id));
        if (clusterForZone && !expandedClusters.has(clusterForZone.id)) return;
      }

      const lat = zone.position[0] || mapCenter[0];
      const lon = zone.position[1] || mapCenter[1];
      if (!lat || !lon) return;

      const occupancyRate = (zone.current_capacity / zone.maximum_capacity) || 0;
      const color = getColorFromOccupancy(occupancyRate);

      const marker = L.circleMarker([lat, lon], {
        radius: 8,
        fillColor: color,
        color: '#000',
        weight: 2,
        opacity: selectedZoneId === zone.id ? 1 : 0.7,
        fillOpacity: selectedZoneId === zone.id ? 0.9 : 0.7,
      });

      marker.on('click', (e) => {
        if (!isPickingLocation) {
          onZoneClick(zone.id);
          marker.openPopup();
        } else {
          L.DomEvent.stopPropagation(e);
        }
      });

      marker.addTo(mapInstanceRef.current);
      markersRef.current[zone.id] = marker;
    });
  }, [zones, selectedZoneId, mapCenter, onZoneClick, currentZoom, expandedClusters]);

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
