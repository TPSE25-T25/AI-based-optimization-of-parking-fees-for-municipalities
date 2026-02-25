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

  // When one slider moves, proportionally scale the remaining three so the total stays at 100.
  const update = (key, rawValue) => {
    const newValue = Math.max(0, Math.min(100, rawValue));
    setWeights((prev) => {
      const otherKeys = Object.keys(prev).filter(k => k !== key);
      const remaining  = 100 - newValue;
      const otherSum   = otherKeys.reduce((s, k) => s + prev[k], 0);

      let scaled;
      if (otherSum === 0) {
        // All others are 0 — distribute the remaining budget equally
        const base     = Math.floor(remaining / otherKeys.length);
        const leftover = remaining - base * otherKeys.length;
        scaled = Object.fromEntries(otherKeys.map((k, i) => [k, base + (i === 0 ? leftover : 0)]));
      } else {
        // Proportional scaling, then fix any rounding error on the largest other value
        scaled = Object.fromEntries(otherKeys.map(k => [k, Math.round(prev[k] * remaining / otherSum)]));
        const diff = remaining - otherKeys.reduce((s, k) => s + scaled[k], 0);
        if (diff !== 0) {
          const largestKey = otherKeys.reduce((a, b) => scaled[a] >= scaled[b] ? a : b);
          scaled[largestKey] += diff;
        }
      }

      return { ...prev, [key]: newValue, ...scaled };
    });
  };

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
            <span className="slider-value">{weights[key]}%</span>
          </div>
        ))}
        <div className="slider-total">
          Total: {Object.values(weights).reduce((s, v) => s + v, 0)}%
        </div>
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
