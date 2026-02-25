// PARKING MAP - Interactive Leaflet map with zone markers and occupancy visualization

import React, { useEffect, useRef, useState, useMemo, memo } from 'react';
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
  const rate = Math.max(0, Math.min(1, occupancyRate));

  const green  = { r: 39,  g: 174, b: 96 };
  const yellow = { r: 243, g: 156, b: 18 };
  const red    = { r: 231, g: 76,  b: 60 };

  let r, g, b;

  if (rate <= 0.5) {
    const t = rate * 2;
    r = Math.round(green.r + (yellow.r - green.r) * t);
    g = Math.round(green.g + (yellow.g - green.g) * t);
    b = Math.round(green.b + (yellow.b - green.b) * t);
  } else {
    const t = (rate - 0.5) * 2;
    r = Math.round(yellow.r + (red.r - yellow.r) * t);
    g = Math.round(yellow.g + (red.g - yellow.g) * t);
    b = Math.round(yellow.b + (red.b - yellow.b) * t);
  }

  return `rgb(${r}, ${g}, ${b})`;
};

// ===== CLUSTER CANVAS OVERLAY =====
// Replaces 500 individual HTML <div> markers with a single <canvas> element.
//
// Why this matters:
//   L.marker + divIcon = one real DOM node per cluster.
//   On every pan Leaflet calls style.setProperty / transform on each node → O(n) style mutations.
//   One canvas = zero per-element DOM mutations during pan.
//   The entire canvas moves as a single GPU-composited layer, then redraws once on moveend.
//
// Click detection is done with simple circle-hit math in handleMapClick(),
// which the parent calls from the map's 'click' event.
class ClusterCanvasLayer extends L.Layer {
  constructor() {
    super();
    this._clusters       = [];
    this._expandedSet    = new Set();
    this._onClusterClick = null;
    this._hitTargets     = [];   // [{id, pt, r}] rebuilt on every _draw()
  }

  onAdd(map) {
    this._map    = map;
    this._canvas = L.DomUtil.create('canvas', 'leaflet-cluster-canvas');
    Object.assign(this._canvas.style, {
      position:      'absolute',
      top:           '0',
      left:          '0',
      pointerEvents: 'none', // clicks fall through to the map; we handle them manually
    });
    map.getPanes().overlayPane.appendChild(this._canvas);

    // After pan/zoom finishes: reposition + redraw at correct pixel coordinates.
    map.on('moveend zoomend viewreset', this._draw, this);

    // During zoom animation: Leaflet CSS-scales the overlay pane, but our canvas
    // content was drawn at the old zoom level and looks wrong at the new scale.
    // We mirror what Leaflet's own L.Canvas renderer does: apply a matching
    // CSS transform to the canvas element so it visually tracks the animation,
    // then let _draw() correct it precisely once zoomend fires.
    map.on('zoomanim', this._onZoomAnim, this);

    this._draw();
  }

  onRemove(map) {
    this._canvas.remove();
    this._canvas = null;
    map.off('moveend zoomend viewreset', this._draw, this);
    map.off('zoomanim', this._onZoomAnim, this);
  }

  // Mirrors L.Canvas._onZoomAnim: scale+translate the canvas to match the animation
  // frame so cluster bubbles move fluidly during pinch/scroll zoom.
  _onZoomAnim(ev) {
    if (!this._map || !this._canvas) return;
    const scale  = ev.scale;
    const offset = this._map._latLngBoundsToNewLayerBounds(
      this._map.getBounds(),
      ev.zoom,
      ev.center,
    ).min;
    L.DomUtil.setTransform(this._canvas, offset, scale);
  }

  // Called by the React effect whenever cluster data or expandedClusters changes.
  update(clusters, expandedSet, onClusterClick) {
    this._clusters       = clusters;
    this._expandedSet    = expandedSet;
    this._onClusterClick = onClusterClick;
    this._hitTargets     = [];
    this._draw();
  }

  _draw() {
    if (!this._map || !this._canvas) return;

    const map  = this._map;
    const size = map.getSize();
    const c    = this._canvas;
    const dpr  = window.devicePixelRatio || 1;

    // Physical pixel buffer = logical size × DPR → crisp on retina / HiDPI screens.
    // CSS size stays at logical pixels so the canvas covers the map exactly.
    c.width        = size.x * dpr;
    c.height       = size.y * dpr;
    c.style.width  = `${size.x}px`;
    c.style.height = `${size.y}px`;

    // Counter-act the overlay pane's CSS transform so canvas pixel-coords match container-coords.
    // Also resets any transform that _onZoomAnim applied during animation.
    const topLeft = map.containerPointToLayerPoint([0, 0]);
    L.DomUtil.setPosition(c, topLeft);

    const ctx = c.getContext('2d');
    // All drawing coordinates are in logical px; ctx.scale makes them map to physical px.
    ctx.scale(dpr, dpr);

    this._hitTargets = [];

    this._clusters.forEach(cluster => {
      if (this._expandedSet.has(cluster.id)) return;

      const pt = map.latLngToContainerPoint([cluster.centerLat, cluster.centerLon]);

      // Viewport cull — skip anything well outside the visible area
      if (pt.x < -64 || pt.y < -64 || pt.x > size.x + 64 || pt.y > size.y + 64) return;

      const r     = Math.max(16, Math.min(24, 9 + cluster.zones.length));
      const occ   = cluster.totalOccupied / (cluster.totalCapacity || 1);
      const color = getColorFromOccupancy(occ);

      // ── Filled circle ────────────────────────────────────────────────────
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = 'rgba(0,0,0,0.35)';
      ctx.lineWidth   = 2;
      ctx.stroke();

      // ── Zone count (upper label) ─────────────────────────────────────────
      ctx.fillStyle    = '#fff';
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'middle';
      ctx.font         = `bold ${Math.round(r * 0.58)}px sans-serif`;
      ctx.fillText(String(cluster.zones.length), pt.x, pt.y - r * 0.20);

      // ── Total capacity (lower label, smaller) ────────────────────────────
      ctx.font = `${Math.round(r * 0.38)}px sans-serif`;
      ctx.fillText(String(cluster.totalCapacity), pt.x, pt.y + r * 0.42);

      this._hitTargets.push({ id: cluster.id, pt, r });
    });
  }

  // Called by the map 'click' handler in ParkingMap.
  // Returns true if the click landed on a cluster bubble (and handles it), false otherwise.
  handleMapClick(containerPt) {
    for (let i = this._hitTargets.length - 1; i >= 0; i--) {
      const { id, pt, r } = this._hitTargets[i];
      const dx = containerPt.x - pt.x;
      const dy = containerPt.y - pt.y;
      if (dx * dx + dy * dy <= r * r) {
        if (this._onClusterClick) this._onClusterClick(id);
        return true;
      }
    }
    return false;
  }
}

// ===== COMPONENT =====
// React.memo: ParkingMap skips re-render when unrelated App state changes
// (menuOpen, weights slider, modalMessage, loading flags, etc.)
const ParkingMap = memo(({ zones, selectedZoneId, onZoneClick, isLoading, loadingMessage = 'Loading parking zones...', error, isPickingLocation, onLocationPicked }) => {
  // ===== REFS =====
  const mapRef            = useRef(null);
  const mapInstanceRef    = useRef(null);
  const canvasRendererRef = useRef(null); // Shared L.canvas renderer for all zone circleMarkers
  const zoneLayerRef      = useRef(null); // L.layerGroup — clearLayers() beats 500× removeLayer()
  const clusterOverlayRef = useRef(null); // ClusterCanvasLayer instance
  const markersRef        = useRef({});   // zone.id → L.circleMarker  (for selectedZone setStyle)

  const [currentZoom, setCurrentZoom]           = useState(13);
  const [expandedClusters, setExpandedClusters] = useState(new Set());

  // Stable refs for callbacks — never cause a marker rebuild when identity changes
  const onZoneClickRef       = useRef(onZoneClick);
  const isPickingLocationRef = useRef(isPickingLocation);
  useEffect(() => { onZoneClickRef.current       = onZoneClick;       }, [onZoneClick]);
  useEffect(() => { isPickingLocationRef.current = isPickingLocation; }, [isPickingLocation]);

  // ===== MEMOIZED DERIVED DATA =====
  const clusters = useMemo(
    () => (zones && zones.length > 0) ? computeClusters(zones) : [],
    [zones]
  );

  // O(1) zone→cluster lookup — replaces O(n×m) .find().some() per zone
  const zoneToClusterMap = useMemo(() => {
    const m = new Map();
    clusters.forEach(c => c.zones.forEach(z => m.set(z.id, c)));
    return m;
  }, [clusters]);

  // ===== MAP INITIALISATION (runs exactly once) =====
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, { preferCanvas: true }).setView([49.0069, 8.4037], 13);
    mapInstanceRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    // One shared canvas renderer for ALL zone circleMarkers.
    // 500 markers → 1 <canvas> element → 1 repaint per frame instead of 500 SVG node moves.
    canvasRendererRef.current = L.canvas({ padding: 0.5 });
    zoneLayerRef.current      = L.layerGroup().addTo(map);

    // The cluster canvas overlay: replaces 500 L.marker+divIcon HTML elements
    clusterOverlayRef.current = new ClusterCanvasLayer();
    clusterOverlayRef.current.addTo(map);

    map.on('zoomend', () => {
      const z = map.getZoom();
      setCurrentZoom(z);
      if (z >= CLUSTER_ZOOM_THRESHOLD) setExpandedClusters(new Set());
    });

    // Cluster click detection: the canvas overlay has pointer-events:none so clicks
    // fall through to the map. The overlay's handleMapClick() does circle-hit math.
    map.on('click', (e) => {
      if (!isPickingLocationRef.current) {
        clusterOverlayRef.current.handleMapClick(e.containerPoint);
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Centre the map when zones first arrive (panTo preserves the user's zoom level)
  useEffect(() => {
    if (!mapInstanceRef.current || !zones || zones.length === 0) return;
    const withPos = zones.filter(z => z.position);
    if (withPos.length === 0) return;
    const avgLat = withPos.reduce((s, z) => s + z.position[0], 0) / withPos.length;
    const avgLon = withPos.reduce((s, z) => s + z.position[1], 0) / withPos.length;
    mapInstanceRef.current.panTo([avgLat, avgLon]);
  }, [zones]);

  // Location picking mode
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (isPickingLocation) {
      mapInstanceRef.current.getContainer().style.cursor = 'crosshair';

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

  // ===== MARKER REBUILD =====
  // Triggered by: zone data change, zoom crossing threshold, cluster expansion.
  // NOT triggered by: selectedZoneId changes, callback identity changes.
  useEffect(() => {
    if (!mapInstanceRef.current || !zoneLayerRef.current || !clusterOverlayRef.current) return;

    // Clear zone markers (single clearLayers() call, not 500× removeLayer())
    zoneLayerRef.current.clearLayers();
    markersRef.current = {};

    if (!zones || zones.length === 0) {
      clusterOverlayRef.current.update([], new Set(), null);
      return;
    }

    const expandAtLowZoom = currentZoom < CLUSTER_ZOOM_THRESHOLD;

    // ── Cluster canvas overlay (one draw call, zero DOM elements) ────────────
    if (expandAtLowZoom) {
      clusterOverlayRef.current.update(clusters, expandedClusters, (clusterId) => {
        setExpandedClusters(prev => new Set([...prev, clusterId]));
      });
    } else {
      clusterOverlayRef.current.update([], new Set(), null);
    }

    // ── Individual zone markers (canvas renderer) ────────────────────────────
    zones.forEach((zone) => {
      // O(1) lookup — was O(n×m) find+some previously
      const zoneCluster = zoneToClusterMap.get(zone.id);
      if (zoneCluster && expandAtLowZoom && !expandedClusters.has(zoneCluster.id)) return;

      const lat = zone.position?.[0];
      const lon = zone.position?.[1];
      if (!lat || !lon) return;

      const occupancyRate = (zone.current_capacity / zone.maximum_capacity) || 0;
      const color         = getColorFromOccupancy(occupancyRate);

      const marker = L.circleMarker([lat, lon], {
        renderer:    canvasRendererRef.current, // shared canvas — 1 <canvas> for all 500
        radius:      8,
        fillColor:   color,
        color:       '#000',
        weight:      2,
        opacity:     0.7,
        fillOpacity: 0.7,
      });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e); // prevent map-level click from also running
        if (!isPickingLocationRef.current) {
          onZoneClickRef.current(zone.id);
        }
      });

      zoneLayerRef.current.addLayer(marker);
      markersRef.current[zone.id] = marker;
    });

    // Restore selection highlight on freshly-built markers
    if (selectedZoneId && markersRef.current[selectedZoneId]) {
      markersRef.current[selectedZoneId].setStyle({ opacity: 1, fillOpacity: 0.9 });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zones, clusters, zoneToClusterMap, currentZoom, expandedClusters]);
  // NOTE: selectedZoneId intentionally excluded — handled by the cheap effect below

  // ===== SELECTED ZONE HIGHLIGHT =====
  // Touches exactly 2 markers with setStyle() instead of rebuilding all 500+
  const prevSelectedZoneIdRef = useRef(selectedZoneId);
  useEffect(() => {
    const prevId = prevSelectedZoneIdRef.current;
    prevSelectedZoneIdRef.current = selectedZoneId;

    if (prevId === selectedZoneId) return;
    if (prevId    && markersRef.current[prevId])        markersRef.current[prevId].setStyle({ opacity: 0.7, fillOpacity: 0.7 });
    if (selectedZoneId && markersRef.current[selectedZoneId]) markersRef.current[selectedZoneId].setStyle({ opacity: 1, fillOpacity: 0.9 });
  }, [selectedZoneId]);

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
});

// ===== EXPORT =====
export default ParkingMap;
