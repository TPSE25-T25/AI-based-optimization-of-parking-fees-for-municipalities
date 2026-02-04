// INFO PANEL - Displays selected parking zone details and metrics

import React from 'react';
import './InfoPanel.css';

// ===== COMPONENT =====
export default function InfoPanel({ zone, onClose }) {
  // ===== LOGIC =====
  if (!zone) return null;

  const occupancyPercent = (zone.current_capacity / zone.maximum_capacity * 100).toFixed(1);
  const occupancyColor =
    occupancyPercent >= 85
      ? '#e74c3c'
      : occupancyPercent >= 65
        ? '#f39c12'
        : occupancyPercent >= 30
          ? '#27ae60'
          : '#9b59b6';

  // ===== RENDER =====
  return (
    <div className="info-panel">
      <div className="info-header">
        <h3>{zone.name || `Zone ${zone.id}`}</h3>
        <button className="close-btn" onClick={onClose}>
          ✖
        </button>
      </div>

      <div className="info-body">
        <div className="info-item">
          <span className="info-label">Zone ID:</span>
          <span className="info-value">{zone.id}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Current Fee:</span>
          <span className="info-value">
            ${zone.current_fee.toFixed(2)}/hr
          </span>
        </div>

        <div className="info-item">
          <span className="info-label">Capacity:</span>
          <span className="info-value">{zone.maximum_capacity || 'N/A'} spaces</span>
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
                  width: `${Math.min(100, occupancyPercent)}%`,
                  backgroundColor: occupancyColor,
                }}
              />
            </div>
          </div>
        </div>

      {zone.position && (
          <div className="info-item">
            <span className="info-label">Coordinates:</span>
            <span className="info-value">
              {zone.position[0].toFixed(4)}, {zone.position[1].toFixed(4)}
            </span>
          </div>
        )}

        {zone.new_fee && (
          <div className="info-item">
            <span className="info-label">New Fee:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              ${zone.new_fee.toFixed(2)}/hr
            </span>
          </div>
        )}

        {zone.predicted_occupancy && (
          <div className="info-item">
            <span className="info-label">Predicted Occupancy:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {(zone.predicted_occupancy * 100).toFixed(2)}%
            </span>
          </div>
        )}

        {zone.predicted_revenue && (
          <div className="info-item">
            <span className="info-label">Predicted Revenue:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              ${zone.predicted_revenue.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
