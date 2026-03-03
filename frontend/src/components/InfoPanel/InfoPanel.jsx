// INFO PANEL - Displays selected parking zone details and metrics

import React from 'react';
import './InfoPanel.css';

// ===== COMPONENT =====
export default function InfoPanel({ zone, city, onClose, hasResults, bestScenario}) {
  // ===== LOGIC =====
  if (!city) return null;

  const percentColor = (percent) => {
    const color =
      percent >= 85
        ? '#e74c3c'
        : percent >= 65
          ? '#f39c12'
          : percent >= 30
            ? '#27ae60'
            : '#9b59b6';
    return color;
  }

  if (zone) {
    const occupancyPercent = (zone.current_capacity / zone.maximum_capacity * 100).toFixed(1);
    const occupancyColor = percentColor(occupancyPercent);

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

          {zone.new_fee != null && (
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

          {zone.predicted_occupancy != null && (
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

          {zone.predicted_revenue != null && (
            <div className="info-item">
              <span className="info-label">Predicted Daily Revenue:</span>
              <span
                className="info-value"
                style={{ color: '#27ae60', fontWeight: 'bold' }}
              >
                ${zone.predicted_revenue.toFixed(2)}/day
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  else {
    const occupancyPercent = city.city_occupancy_rate * 100;
    const barColor = percentColor(occupancyPercent);

    return (
      <div className="info-panel">
      <div className="info-header">
        <h3>{city.name}</h3>
      </div>

      <div className="info-body">
        {city.min_latitude != null && city.max_latitude != null && city.min_longitude != null && city.max_longitude != null && (
          <div className="info-item">
            <span className="info-label">Bounds:</span>
            <span className="info-value">({city.min_latitude.toFixed(2)}, {city.max_latitude.toFixed(2)}) to ({city.min_longitude.toFixed(2)}, {city.max_longitude.toFixed(2)})</span>
          </div>
        )}

        <div className="info-item">
          <span className="info-label">Total Parking Zones:</span>
          <span className="info-value">{city.parking_zones.length}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Points of Interest:</span>
          <span className="info-value">{city.point_of_interests.length}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Total Capacity:</span>
          <span className="info-value">{city.total_parking_capacity}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Available Spots:</span>
          <span className="info-value">{city.total_available_spots}</span>
        </div>

        <div className="info-item">
          <span className="info-label">Occupancy:</span>
          <div className="occupancy-display">
            <span style={{ color: barColor, fontWeight: 'bold' }}>
              {occupancyPercent.toFixed(1)}%
            </span>
            <div className="occupancy-bar-small">
              <div
                className="occupancy-fill-small"
                style={{
                  width: `${Math.min(100, occupancyPercent)}%`,
                  backgroundColor: barColor,
                }}
              />
            </div>
          </div>
        </div>

        {hasResults&& (
          <div className="info-item">
            <span className="info-label">Scenario:</span>
            <span className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              #{bestScenario.scenario_id} 
            </span>
          </div>
        )}

        {hasResults && (
          <div className="info-item">
            <span className="info-label">Weight Match Score:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {bestScenario.matching_score.toFixed(2)}%
            </span>
          </div>
        )}

        {hasResults && (
          <div className="info-item">
            <span className="info-label">Total Daily Revenue:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {bestScenario.score_revenue.toFixed(2)} €/day
            </span>
          </div>
        )}

        {hasResults&& (
          <div className="info-item">
            <span className="info-label">User Balance:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {(bestScenario.score_user_balance * 100).toFixed(2)}%
            </span>
          </div>
        )}

        {hasResults&& (
          <div className="info-item">
            <span className="info-label">Demand Drop:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {(bestScenario.score_demand_drop * 100).toFixed(2)}%
            </span>
          </div>
        )}

        {hasResults&& (
          <div className="info-item">
            <span className="info-label">Occupancy Gap:</span>
            <span
              className="info-value"
              style={{ color: '#27ae60', fontWeight: 'bold' }}
            >
              {(bestScenario.score_occupancy_gap * 100).toFixed(2)}%
            </span>
          </div>
        )}

      </div>
    </div>
    );
  }
}
