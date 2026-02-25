"""Unit tests for ParallelEngine — thorough + edge cases, targeting >90% coverage"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from backend.services.simulation.parallel_engine import (
    ParallelEngine, ComputeBackend, CUDA_AVAILABLE, JOBLIB_AVAILABLE,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _arrays(n_drivers=3, n_lots=2):
    """Build minimal input arrays for compute_driver_lot_scores."""
    rng = np.random.default_rng(42)
    return dict(
        driver_positions=rng.random((n_drivers, 2)),
        driver_destinations=rng.random((n_drivers, 2)),
        driver_max_fees=np.array([5.0] * n_drivers),
        lot_positions=rng.random((n_lots, 2)),
        lot_fees=np.array([2.0] * n_lots),
        lot_occupancy=np.array([0.5] * n_lots),
        fee_weight=1.5,
        distance_to_lot_weight=0.8,
        walking_distance_weight=2.0,
        availability_weight=0.5,
    )


def _engine(backend=ComputeBackend.CPU_SERIAL, n_jobs=-1):
    return ParallelEngine(backend=backend, n_jobs=n_jobs)


# ═══════════════════════════════════════════════════════════════════════════════
# Init & backend selection
# ═══════════════════════════════════════════════════════════════════════════════

class TestInit:

    def test_auto_detect(self):
        e = ParallelEngine()
        assert e.backend in ComputeBackend

    def test_force_serial(self):
        assert _engine().backend == ComputeBackend.CPU_SERIAL

    def test_custom_n_jobs(self):
        e = _engine(n_jobs=4)
        assert e.n_jobs == 4

    def test_cuda_fallback_when_unavailable(self):
        if not CUDA_AVAILABLE:
            with pytest.warns(UserWarning, match="CUDA requested"):
                e = ParallelEngine(backend=ComputeBackend.CUDA)
            assert e.backend != ComputeBackend.CUDA

    def test_cuda_fallback_to_parallel(self):
        """When CUDA unavailable but joblib is, fallback to CPU_PARALLEL."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", False), \
             patch("backend.services.simulation.parallel_engine.JOBLIB_AVAILABLE", True):
            with pytest.warns(UserWarning):
                e = ParallelEngine(backend=ComputeBackend.CUDA)
            assert e.backend == ComputeBackend.CPU_PARALLEL

    def test_cuda_fallback_to_serial(self):
        """When both CUDA and joblib unavailable, fallback to CPU_SERIAL."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", False), \
             patch("backend.services.simulation.parallel_engine.JOBLIB_AVAILABLE", False):
            with pytest.warns(UserWarning):
                e = ParallelEngine(backend=ComputeBackend.CUDA)
            assert e.backend == ComputeBackend.CPU_SERIAL

    def test_parallel_fallback_to_serial(self):
        """When joblib unavailable, CPU_PARALLEL falls back to serial."""
        with patch("backend.services.simulation.parallel_engine.JOBLIB_AVAILABLE", False):
            with pytest.warns(UserWarning, match="joblib not available"):
                e = ParallelEngine(backend=ComputeBackend.CPU_PARALLEL)
            assert e.backend == ComputeBackend.CPU_SERIAL

    def test_auto_detect_serial_only(self):
        """When nothing available, auto-detect picks serial."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", False), \
             patch("backend.services.simulation.parallel_engine.JOBLIB_AVAILABLE", False):
            e = ParallelEngine()
            assert e.backend == ComputeBackend.CPU_SERIAL

    def test_auto_detect_joblib(self):
        """When joblib available but not CUDA, auto-detect picks parallel."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", False), \
             patch("backend.services.simulation.parallel_engine.JOBLIB_AVAILABLE", True):
            e = ParallelEngine()
            assert e.backend == ComputeBackend.CPU_PARALLEL

    def test_auto_detect_cuda(self):
        """When CUDA available, auto-detect picks CUDA."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", True):
            e = ParallelEngine()
            assert e.backend == ComputeBackend.CUDA

    def test_cuda_dispatch_routes_to_compute_cuda(self):
        """Compute with CUDA backend calls _compute_cuda."""
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", True):
            e = ParallelEngine(backend=ComputeBackend.CUDA)
        dummy = np.zeros((2, 2))
        with patch.object(e, "_compute_cuda", return_value=dummy) as mock:
            e.compute_driver_lot_scores(**_arrays(n_drivers=2, n_lots=2))
            mock.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# get_backend_info
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackendInfo:

    def test_serial_info(self):
        info = _engine().get_backend_info()
        assert info["backend"] == "cpu_serial"
        assert info["n_jobs"] == 1

    @pytest.mark.skipif(not JOBLIB_AVAILABLE, reason="joblib not installed")
    def test_parallel_info_n_jobs(self):
        info = _engine(backend=ComputeBackend.CPU_PARALLEL, n_jobs=4).get_backend_info()
        assert info["backend"] == "cpu_parallel"
        assert info["n_jobs"] == 4

    def test_info_flags(self):
        info = _engine().get_backend_info()
        assert info["cuda_available"] == CUDA_AVAILABLE
        assert info["joblib_available"] == JOBLIB_AVAILABLE


# ═══════════════════════════════════════════════════════════════════════════════
# Score computation (serial — always available)
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeScores:

    def test_output_shape(self):
        scores = _engine().compute_driver_lot_scores(**_arrays(4, 3))
        assert scores.shape == (4, 3)

    def test_scores_finite_and_non_negative(self):
        scores = _engine().compute_driver_lot_scores(**_arrays())
        assert np.all(np.isfinite(scores))
        assert np.all(scores >= 0)

    def test_unaffordable_lot_is_inf(self):
        a = _arrays(n_drivers=2, n_lots=2)
        a["driver_max_fees"] = np.array([1.0, 1.0])  # below lot fee 2.0
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.all(np.isinf(scores))

    def test_mixed_affordability(self):
        a = _arrays(n_drivers=1, n_lots=2)
        a["lot_fees"] = np.array([1.0, 100.0])
        a["driver_max_fees"] = np.array([5.0])
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.isfinite(scores[0, 0])
        assert np.isinf(scores[0, 1])

    def test_higher_fee_gives_higher_score(self):
        a = _arrays(n_drivers=1, n_lots=2)
        a["lot_fees"] = np.array([1.0, 5.0])
        a["lot_positions"] = np.array([[0.5, 0.5], [0.5, 0.5]])
        a["lot_occupancy"] = np.array([0.5, 0.5])
        scores = _engine().compute_driver_lot_scores(**a)
        assert scores[0, 0] < scores[0, 1]

    def test_single_driver_single_lot(self):
        scores = _engine().compute_driver_lot_scores(**_arrays(1, 1))
        assert scores.shape == (1, 1) and np.isfinite(scores[0, 0])

    def test_zero_weights_give_zero_scores(self):
        a = _arrays()
        for w in ("fee_weight", "distance_to_lot_weight",
                   "walking_distance_weight", "availability_weight"):
            a[w] = 0.0
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.allclose(scores[np.isfinite(scores)], 0.0)

    def test_zero_fees_zero_occupancy(self):
        a = _arrays()
        a["lot_fees"] = np.array([0.0, 0.0])
        a["lot_occupancy"] = np.array([0.0, 0.0])
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.all(np.isfinite(scores))

    def test_exact_score_computation(self):
        """Verify the math for a fully deterministic input."""
        a = dict(
            driver_positions=np.array([[0.0, 0.0]]),
            driver_destinations=np.array([[1.0, 0.0]]),
            driver_max_fees=np.array([10.0]),
            lot_positions=np.array([[0.0, 0.0]]),
            lot_fees=np.array([2.0]),
            lot_occupancy=np.array([0.5]),
            fee_weight=1.0,
            distance_to_lot_weight=1.0,
            walking_distance_weight=1.0,
            availability_weight=1.0,
            normalize_fee=10.0,
            normalize_distance=1.0,
        )
        scores = _engine().compute_driver_lot_scores(**a)
        # fee_score = 2/10 = 0.2, dist_to_lot = 0, walking = 1.0, avail = 0.5
        expected = 0.2 + 0.0 + 1.0 + 0.5
        assert scores[0, 0] == pytest.approx(expected)

    # ── Edge cases ──

    def test_exact_fee_boundary_is_affordable(self):
        """Driver max_fee == lot_fee should NOT be inf."""
        a = _arrays(n_drivers=1, n_lots=1)
        a["driver_max_fees"] = np.array([2.0])
        a["lot_fees"] = np.array([2.0])
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.isfinite(scores[0, 0])

    def test_driver_at_lot_position(self):
        """Distance=0 when driver starts at lot."""
        a = dict(
            driver_positions=np.array([[5.0, 5.0]]),
            driver_destinations=np.array([[5.0, 5.0]]),
            driver_max_fees=np.array([10.0]),
            lot_positions=np.array([[5.0, 5.0]]),
            lot_fees=np.array([1.0]),
            lot_occupancy=np.array([0.0]),
            fee_weight=0.0,
            distance_to_lot_weight=1.0,
            walking_distance_weight=1.0,
            availability_weight=0.0,
        )
        scores = _engine().compute_driver_lot_scores(**a)
        assert scores[0, 0] == pytest.approx(0.0)

    def test_custom_normalize_params(self):
        a = _arrays(n_drivers=1, n_lots=1)
        s1 = _engine().compute_driver_lot_scores(**a, normalize_fee=10.0, normalize_distance=100.0)
        s2 = _engine().compute_driver_lot_scores(**a, normalize_fee=1.0, normalize_distance=1.0)
        # Smaller normalizers → larger scores
        assert s2[0, 0] > s1[0, 0]

    def test_many_lots(self):
        scores = _engine().compute_driver_lot_scores(**_arrays(2, 50))
        assert scores.shape == (2, 50)
        assert np.all(np.isfinite(scores))

    def test_many_drivers(self):
        scores = _engine().compute_driver_lot_scores(**_arrays(100, 2))
        assert scores.shape == (100, 2)

    def test_full_occupancy(self):
        a = _arrays(n_drivers=1, n_lots=1)
        a["lot_occupancy"] = np.array([1.0])
        scores = _engine().compute_driver_lot_scores(**a)
        assert np.isfinite(scores[0, 0])

    def test_only_fee_weight_matters(self):
        a = _arrays(n_drivers=1, n_lots=2)
        a["lot_fees"] = np.array([1.0, 3.0])
        a["lot_positions"] = np.array([[0.5, 0.5], [0.5, 0.5]])
        a["lot_occupancy"] = np.array([0.0, 0.0])
        a["fee_weight"] = 10.0
        a["distance_to_lot_weight"] = 0.0
        a["walking_distance_weight"] = 0.0
        a["availability_weight"] = 0.0
        scores = _engine().compute_driver_lot_scores(**a)
        assert scores[0, 1] == pytest.approx(scores[0, 0] * 3.0)


# ═══════════════════════════════════════════════════════════════════════════════
# CPU parallel path (if joblib available)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not JOBLIB_AVAILABLE, reason="joblib not installed")
class TestCPUParallel:

    def test_parallel_matches_serial_small(self):
        """Small dataset (< 5000)—parallel falls back to vectorized internally."""
        a = _arrays(10, 5)
        serial = _engine().compute_driver_lot_scores(**a)
        parallel = _engine(backend=ComputeBackend.CPU_PARALLEL).compute_driver_lot_scores(**a)
        np.testing.assert_allclose(serial, parallel)

    def test_parallel_large_dataset_matches_serial(self):
        """Large dataset (≥ 5000) triggers actual joblib chunking."""
        a = _arrays(n_drivers=5500, n_lots=3)
        serial = _engine().compute_driver_lot_scores(**a)
        parallel = _engine(backend=ComputeBackend.CPU_PARALLEL, n_jobs=2).compute_driver_lot_scores(**a)
        np.testing.assert_allclose(serial, parallel)

    def test_parallel_large_negative_n_jobs(self):
        """n_jobs = -1 (all cores) with large dataset."""
        a = _arrays(n_drivers=5500, n_lots=2)
        serial = _engine().compute_driver_lot_scores(**a)
        parallel = _engine(backend=ComputeBackend.CPU_PARALLEL, n_jobs=-1).compute_driver_lot_scores(**a)
        np.testing.assert_allclose(serial, parallel)

    def test_parallel_backend_info(self):
        info = _engine(backend=ComputeBackend.CPU_PARALLEL, n_jobs=2).get_backend_info()
        assert info["backend"] == "cpu_parallel"
        assert info["n_jobs"] == 2

    def test_compute_dispatches_to_parallel(self):
        """Ensure compute_driver_lot_scores routes to _compute_cpu_parallel."""
        e = _engine(backend=ComputeBackend.CPU_PARALLEL)
        a = _arrays()
        # Should not raise, and result should match serial
        serial = _engine().compute_driver_lot_scores(**a)
        parallel = e.compute_driver_lot_scores(**a)
        np.testing.assert_allclose(serial, parallel)


# ═══════════════════════════════════════════════════════════════════════════════
# CUDA method (mocked — no GPU required)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCUDAMocked:
    """Cover _compute_cuda body by mocking the cuda runtime and kernel."""

    def _make_cuda_engine(self):
        with patch("backend.services.simulation.parallel_engine.CUDA_AVAILABLE", True):
            return ParallelEngine(backend=ComputeBackend.CUDA)

    def test_compute_cuda_shape(self):
        e = self._make_cuda_engine()
        a = _arrays(n_drivers=3, n_lots=2)

        mock_cuda = MagicMock()
        mock_device = MagicMock()
        mock_device.copy_to_host = MagicMock(side_effect=lambda out: None)
        mock_cuda.to_device.return_value = mock_device

        mock_kernel = MagicMock()

        with patch("backend.services.simulation.parallel_engine.cuda", mock_cuda), \
             patch("backend.services.simulation.parallel_engine._cuda_compute_scores", mock_kernel, create=True):
            scores = e._compute_cuda(
                a["driver_positions"], a["driver_destinations"], a["driver_max_fees"],
                a["lot_positions"], a["lot_fees"], a["lot_occupancy"],
                a["fee_weight"], a["distance_to_lot_weight"],
                a["walking_distance_weight"], a["availability_weight"], 10.0, 1.0,
            )
        assert scores.shape == (3, 2)
        assert mock_cuda.to_device.call_count == 7  # 6 inputs + 1 scores
        mock_kernel.__getitem__.return_value.assert_called_once()

    def test_compute_cuda_single_driver(self):
        e = self._make_cuda_engine()
        a = _arrays(n_drivers=1, n_lots=1)

        mock_cuda = MagicMock()
        mock_device = MagicMock()
        mock_device.copy_to_host = MagicMock(side_effect=lambda out: None)
        mock_cuda.to_device.return_value = mock_device

        with patch("backend.services.simulation.parallel_engine.cuda", mock_cuda), \
             patch("backend.services.simulation.parallel_engine._cuda_compute_scores", MagicMock(), create=True):
            scores = e._compute_cuda(
                a["driver_positions"], a["driver_destinations"], a["driver_max_fees"],
                a["lot_positions"], a["lot_fees"], a["lot_occupancy"],
                a["fee_weight"], a["distance_to_lot_weight"],
                a["walking_distance_weight"], a["availability_weight"], 10.0, 1.0,
            )
        assert scores.shape == (1, 1)
        assert scores.dtype == np.float32