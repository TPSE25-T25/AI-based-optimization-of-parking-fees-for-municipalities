import React from 'react';

export default function MenuPanel({ open, onClose, weights, setWeights, onApply, hasOptimizationResults }) {
  if (!open) return null;

  const update = (key, value) => setWeights(prev => ({ ...prev, [key]: value }));

  const handleApply = async () => {
    if (onApply) {
      await onApply();
    }
    onClose();
  };

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

      {!hasOptimizationResults && (
        <div style={{ padding: '10px', backgroundColor: '#fff3cd', borderRadius: '5px', marginBottom: '10px' }}>
          <small>⚠️ Run optimization first to apply weights</small>
        </div>
      )}

      <div style={{ textAlign: 'right' }}>
        <button 
          className="btn" 
          onClick={handleApply}
          disabled={!hasOptimizationResults}
          style={{ opacity: hasOptimizationResults ? 1 : 0.5, cursor: hasOptimizationResults ? 'pointer' : 'not-allowed' }}
        >
          Apply Weights
        </button>
      </div>
    </div>
  );
}
