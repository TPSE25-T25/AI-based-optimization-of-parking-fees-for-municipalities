
import React from 'react';

export default function ResultsActions({
  optimizationResponse,
  handleDownloadResults,
  dbResults,
  selectedDbResultId,
  setSelectedDbResultId,
  loadDbResult,
  refreshDbResults,
  loadingDbResults,
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

      <button
        className="results-button"
        onClick={refreshDbResults}
        disabled={loadingDbResults}
        title="Refresh saved results from database"
      >
        🔄 Refresh DB
      </button>

      <select
        className="results-button"
        value={selectedDbResultId || ''}
        onChange={(e) => setSelectedDbResultId(e.target.value)}
        title="Select a saved result"
      >
        <option value="">Select result</option>
        {(dbResults || []).map((item) => (
          <option key={item.id} value={item.id}>
            #{item.id} — {new Date(item.created_at).toLocaleString()}
          </option>
        ))}
      </select>

      <button
        className="results-button"
        onClick={loadDbResult}
        disabled={!selectedDbResultId || loadingDbResults}
        title="Load selected result from database"
      >
        🗄️ Load DB
      </button>
    </div>
  );
}
