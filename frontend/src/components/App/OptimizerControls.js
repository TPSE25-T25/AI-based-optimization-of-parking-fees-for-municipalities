// OPTIMIZER CONTROLS - Select optimizer type, data source, and run optimization

import React from 'react';

// ===== COMPONENT =====
export default function OptimizerControls({
  optimizerType,
  setOptimizerType,
  dataSource,
  setDataSource,
  runOptimization,
  loadCity,
  optimizing,
  loading,
}) {
  // ===== RENDER =====
  return (
    <div className="top-right-info">
      <div className="optimizer-row">
        <label className="optimizer-label">Karlsruhe Data Source:</label>
        <div className="optimizer-controls-row">
          <select
            className="optimizer-select"
            value={dataSource}
            onChange={(e) => setDataSource(e.target.value)}
          >
            <option value="osmnx">OpenStreetMap</option>
            <option value="mobidata">MobiData BW</option>
            <option value="generated">Generated</option>
          </select>
          <button
            className="optimizer-button"
            onClick={loadCity}
            disabled={loading}
          >
            {loading ? '⏳' : '🔄'}
          </button>
        </div>
      </div>
      <div className="optimizer-row">
        <label className="optimizer-label">Optimizer:</label>
        <div className="optimizer-controls-row">
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
            {optimizing ? '⏳' : '▶️'}
          </button>
        </div>
      </div>
    </div>
  );
}
