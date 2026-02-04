// RESULTS ACTIONS - Download and load optimization results

import React from 'react';

// ===== COMPONENT =====
export default function ResultsActions({
  optimizationResponse,
  handleDownloadResults,
  handleLoadResults,
}) {
  // ===== RENDER =====
  return (
    <div className="results-actions">
      <button
        className="results-button"
        onClick={handleDownloadResults}
        disabled={!optimizationResponse}
        title="Download current optimization results as JSON"
      >
        ⬇️ Download
      </button>

      <label className="results-button load-button">
        <input
          type="file"
          accept=".json"
          onChange={handleLoadResults}
          style={{ display: 'none' }}
        />
        📁 Load Results
      </label>
    </div>
  );
}
