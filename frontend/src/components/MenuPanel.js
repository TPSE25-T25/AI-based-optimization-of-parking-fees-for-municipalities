import React from 'react';

export default function MenuPanel({ open, onClose, weights, setWeights }) {
  if (!open) return null;

  const update = (key, value) => setWeights(prev => ({ ...prev, [key]: value }));

  return (
    <div className="menu-panel">
      <div className="menu-header">
        <h3>Optimization Weights</h3>
        <button className="close-btn" onClick={onClose}>✖</button>
      </div>

      <div className="sliders">
        {Object.keys(weights).map(key => (
          <div className="slider-row" key={key}>
            <label>{key}</label>
            <input
              type="range"
              min="0"
              max="100"
              value={weights[key]}
              onChange={(e) => update(key, Number(e.target.value))}
            />
            <span className="slider-value">{weights[key]}</span>
          </div>
        ))}
      </div>

      <div style={{ textAlign: 'right' }}>
        <button className="btn" onClick={onClose}>Done</button>
      </div>
    </div>
  );
}
