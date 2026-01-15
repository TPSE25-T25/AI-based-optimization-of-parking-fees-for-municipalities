import React from 'react';

export default function InfoPanel({ spot, onClose }) {
  if (!spot) return null;

  return (
    <div className="info-panel">
      <div className="info-header">
        <h3>{spot.label} Details</h3>
        <button className="close-btn" onClick={onClose}>✖</button>
      </div>

      <div className="info-body">
        <p><strong>ID:</strong> {spot.id}</p>
        <p><strong>Name:</strong> {spot.label}</p>
        <p><strong>Occupancy:</strong> 65% (placeholder)</p>
        <p><strong>Suggested Fee:</strong> $2.50 (placeholder)</p>
        <p><em>No backend connection for map yet — these values are placeholders.</em></p>
      </div>
    </div>
  );
}
