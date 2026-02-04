// MENU PANEL - Overlay for adjusting optimization objective weights

import React from 'react';
import './MenuPanel.css';

// ===== COMPONENT =====
export default function MenuPanel({
  open,
  onClose,
  weights,
  setWeights,
  onApply,
  hasOptimizationResults,
}) {
  // ===== LOGIC =====
  if (!open) return null;

  const update = (key, value) => setWeights((prev) => ({ ...prev, [key]: value }));
  const handleApply = async () => {
    if (onApply) {
      await onApply();
    }
    onClose();
  };

  // ===== RENDER =====
  return (
    <div className="menu-panel">
      <div className="menu-header">
        <h3>Optimization Weights</h3>
        <button className="close-btn" onClick={onClose}>
          ✖
        </button>
      </div>

      <div className="sliders">
        {Object.keys(weights).map((key) => (
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

      {!hasOptimizationResults && (
        <div className="warning-box">
          <small>⚠️ Run optimization first to apply weights</small>
        </div>
      )}

      <div className="actions">
        <button
          className="btn"
          onClick={handleApply}
          disabled={!hasOptimizationResults}
        >
          Apply Weights
        </button>
      </div>
    </div>
  );
}
