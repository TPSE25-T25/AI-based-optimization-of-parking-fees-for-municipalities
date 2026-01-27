import React from 'react';

export default function InfoPanel({ zone, onClose }) {
  if (!zone) return null;

  const occupancyPercent = ((zone.occupancy_rate || 0) * 100).toFixed(1);
  const occupancyColor = 
    zone.occupancy_rate >= 0.85 ? '#e74c3c' :
    zone.occupancy_rate >= 0.65 ? '#f39c12' :
    zone.occupancy_rate >= 0.3 ? '#27ae60' :
    '#9b59b6';

  return (
    <div className="info-panel">
      <div className="info-header">
        <h3>{zone.name || `Zone ${zone.id}`}</h3>
        <button className="close-btn" onClick={onClose}>✖</button>
      </div>

      <div className="info-body">
        <div className="info-item">
          <span className="info-label">Zone ID:</span>
          <span className="info-value">{zone.id}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Current Fee:</span>
          <span className="info-value">${(zone.current_fee || 0).toFixed(2)}/hr</span>
        </div>

        <div className="info-item">
          <span className="info-label">Capacity:</span>
          <span className="info-value">{zone.capacity || 'N/A'} spaces</span>
        </div>

        <div className="info-item">
          <span className="info-label">Occupancy:</span>
          <div className="occupancy-display">
            <span style={{ color: occupancyColor, fontWeight: 'bold' }}>
              {occupancyPercent}%
            </span>
            <div className="occupancy-bar-small">
              <div 
                className="occupancy-fill-small" 
                style={{ 
                  width: `${Math.min(100, zone.occupancy_rate * 100)}%`,
                  backgroundColor: occupancyColor
                }}
              />
            </div>
          </div>
        </div>

        {zone.suggested_fee && (
          <div className="info-item">
            <span className="info-label">Suggested Fee:</span>
            <span className="info-value" style={{ color: '#27ae60', fontWeight: 'bold' }}>
              ${zone.suggested_fee.toFixed(2)}/hr
            </span>
          </div>
        )}

        {zone.lat && zone.lon && (
          <div className="info-item">
            <span className="info-label">Coordinates:</span>
            <span className="info-value">{zone.lat.toFixed(4)}, {zone.lon.toFixed(4)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
