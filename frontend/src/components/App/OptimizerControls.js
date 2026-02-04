// OPTIMIZER CONTROLS - Select optimizer type and run optimization

import React from 'react';

// ===== COMPONENT =====
export default function OptimizerControls({
  optimizerType,
  setOptimizerType,
  runOptimization,
  optimizing,
  loading,
}) {
  // ===== RENDER =====
  return (
    <div className="top-right-info">
      <div className="optimizer-row">
        <label className="optimizer-label">Optimizer:</label>
        <select
          className="optimizer-select"
          value={optimizerType}
          onChange={(e) => setOptimizerType(e.target.value)}
        >
          <option value="elasticity">Elasticity-Based</option>
          <option value="agent">Agent-Based</option>
        </select>
        <button
          className="optimizer-button"
          onClick={runOptimization}
          disabled={optimizing || loading}
        >
          {optimizing ? '⏳ Optimizing...' : '▶️ Run Optimization'}
        </button>
      </div>
    </div>
  );
}
