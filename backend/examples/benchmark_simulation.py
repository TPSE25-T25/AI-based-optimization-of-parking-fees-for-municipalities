"""
Benchmark for ParallelEngine backends (CPU serial, CPU parallel, CUDA).
Run directly:  python -m backend.services.simulation.benchmark_parallel_engine
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import numpy as np
from backend.services.simulation.parallel_engine import (
    ParallelEngine,
    ComputeBackend,
    CUDA_AVAILABLE,
    JOBLIB_AVAILABLE,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def make_inputs(n_drivers: int, n_lots: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    return {
        "driver_positions":    rng.uniform(0, 1000, (n_drivers, 2)).astype(np.float32),
        "driver_destinations": rng.uniform(0, 1000, (n_drivers, 2)).astype(np.float32),
        "driver_max_fees":     rng.uniform(1,   10, (n_drivers,)).astype(np.float32),
        "lot_positions":       rng.uniform(0, 1000, (n_lots,   2)).astype(np.float32),
        "lot_fees":            rng.uniform(0.5,  8, (n_lots,)).astype(np.float32),
        "lot_occupancy":       rng.uniform(0,  0.9, (n_lots,)).astype(np.float32),
    }

SCORE_KWARGS = dict(
    fee_weight=1.5,
    distance_to_lot_weight=0.8,
    walking_distance_weight=2.0,
    availability_weight=0.5,
)

def run_timed(engine: ParallelEngine, inputs: dict, n_warmup: int, n_runs: int) -> tuple[float, float]:
    """Returns (mean_ms, std_ms)."""
    # warmup
    for _ in range(n_warmup):
        engine.compute_driver_lot_scores(**inputs, **SCORE_KWARGS)

    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        engine.compute_driver_lot_scores(**inputs, **SCORE_KWARGS)
        times.append((time.perf_counter() - t0) * 1000)
    return float(np.mean(times)), float(np.std(times))


# ── benchmark matrix ─────────────────────────────────────────────────────────

SIZES = [
    (500,   20,  "small  (500  drivers × 20  lots)"),
    (2_000, 50,  "medium (2k   drivers × 50  lots)"),
    (10_000, 100, "large  (10k  drivers × 100 lots)"),
]

BACKENDS = [
    (ComputeBackend.CPU_SERIAL,   "CPU serial  (vectorised NumPy)",  True),
    (ComputeBackend.CPU_PARALLEL, "CPU parallel (joblib threads)",   JOBLIB_AVAILABLE),
    (ComputeBackend.CUDA,         "GPU  (CUDA / numba)",             CUDA_AVAILABLE),
]

N_WARMUP = 2
N_RUNS   = 8


def main():
    print("=" * 72)
    print("ParallelEngine backend benchmark")
    print("=" * 72)

    results: dict[str, list] = {}

    for backend_enum, backend_label, available in BACKENDS:
        if not available:
            print(f"\n{backend_label}  →  SKIPPED (not available)")
            continue

        engine = ParallelEngine(backend=backend_enum, n_jobs=-1)
        print(f"\n{backend_label}")
        print("-" * 60)
        row = []
        for n_drivers, n_lots, size_label in SIZES:
            inputs = make_inputs(n_drivers, n_lots)
            mean_ms, std_ms = run_timed(engine, inputs, N_WARMUP, N_RUNS)
            print(f"  {size_label}  →  {mean_ms:7.2f} ms  ± {std_ms:.2f} ms")
            row.append(mean_ms)
        results[backend_label] = row

    # ── relative speed-up table ───────────────────────────────────────────────
    baseline_label = "CPU serial  (vectorised NumPy)"
    if baseline_label in results and len(results) > 1:
        print("\n" + "=" * 72)
        print("Speed-up vs CPU serial")
        print("-" * 60)
        baseline = results[baseline_label]
        for label, times in results.items():
            if label == baseline_label:
                continue
            speedups = [b / t if t > 0 else float("inf") for b, t in zip(baseline, times)]
            formatted = "  ".join(f"{s:5.2f}×" for s in speedups)
            print(f"  {label:<40} [ {formatted} ]")
        print("  Column order:", "  /  ".join(s for _, _, s in SIZES))

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
