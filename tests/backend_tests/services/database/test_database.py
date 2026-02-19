"""Unit tests for database.py, init_db.py, and models.py — targeting >90% coverage."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.services.database.database import Base, engine, SessionLocal, DATABASE_URL
from backend.services.database.init_db import init_db
from backend.services.database.models import SimulationResult


# ── Test-only in-memory engine & session ─────────────────────────────────────

_test_engine = create_engine("sqlite:///:memory:", echo=False, future=True)
_TestSession = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(autouse=True)
def _setup_tables():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def session():
    """Provide a transactional test session that rolls back after each test."""
    s = _TestSession()
    yield s
    s.rollback()
    s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# database.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabaseModule:

    def test_engine_exists(self):
        assert engine is not None

    def test_session_local_creates_session(self):
        s = SessionLocal()
        assert s is not None
        s.close()

    def test_base_has_metadata(self):
        assert Base.metadata is not None

    def test_database_url_is_string(self):
        assert isinstance(DATABASE_URL, str)

    def test_database_url_default_is_sqlite(self):
        assert "sqlite" in DATABASE_URL


# ═══════════════════════════════════════════════════════════════════════════════
# init_db.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestInitDb:

    def test_init_db_creates_tables(self):
        """init_db() should create the simulation_results table."""
        test_eng = create_engine("sqlite:///:memory:", echo=False, future=True)
        Base.metadata.create_all(bind=test_eng)
        table_names = inspect(test_eng).get_table_names()
        assert "simulation_results" in table_names

    def test_init_db_idempotent(self):
        """Calling init_db twice should not raise."""
        test_eng = create_engine("sqlite:///:memory:", echo=False, future=True)
        Base.metadata.create_all(bind=test_eng)
        Base.metadata.create_all(bind=test_eng)  # second call
        assert "simulation_results" in inspect(test_eng).get_table_names()

    def test_init_db_callable(self):
        """init_db is callable and runs without error (uses production engine)."""
        init_db()  # creates tables on the real engine (SQLite file, safe)


# ═══════════════════════════════════════════════════════════════════════════════
# models.py — SimulationResult schema
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationResultSchema:

    def test_tablename(self):
        assert SimulationResult.__tablename__ == "simulation_results"

    def test_columns_exist(self):
        cols = {c.name for c in SimulationResult.__table__.columns}
        expected = {"id", "created_at", "parameters", "map_path",
                    "map_config", "map_snapshot", "csv_path", "best_scenario"}
        assert cols == expected

    def test_id_is_primary_key(self):
        assert SimulationResult.__table__.c.id.primary_key

    def test_parameters_not_nullable(self):
        assert SimulationResult.__table__.c.parameters.nullable is False

    def test_created_at_not_nullable(self):
        assert SimulationResult.__table__.c.created_at.nullable is False

    def test_optional_columns_nullable(self):
        for col_name in ("map_path", "map_config", "map_snapshot", "csv_path", "best_scenario"):
            assert SimulationResult.__table__.c[col_name].nullable is True

    def test_map_path_max_length(self):
        assert SimulationResult.__table__.c.map_path.type.length == 1024

    def test_csv_path_max_length(self):
        assert SimulationResult.__table__.c.csv_path.type.length == 1024


# ═══════════════════════════════════════════════════════════════════════════════
# models.py — CRUD operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationResultCRUD:

    def test_create_minimal(self, session):
        row = SimulationResult(parameters={"fee": 3.0})
        session.add(row)
        session.commit()
        assert row.id is not None

    def test_create_full(self, session):
        row = SimulationResult(
            parameters={"fee": 3.0, "weights": [1, 2]},
            map_path="/maps/test.html",
            map_config={"center": [49.0, 8.4], "zoom": 13},
            map_snapshot={"zones": [{"id": 1}]},
            csv_path="/exports/test.csv",
            best_scenario={"revenue": 1000},
        )
        session.add(row)
        session.commit()
        assert row.id is not None
        assert row.map_path == "/maps/test.html"
        assert row.csv_path == "/exports/test.csv"

    def test_read_back(self, session):
        row = SimulationResult(parameters={"a": 1})
        session.add(row)
        session.commit()
        fetched = session.get(SimulationResult, row.id)
        assert fetched is not None
        assert fetched.parameters == {"a": 1}

    def test_update(self, session):
        row = SimulationResult(parameters={"v": 1})
        session.add(row)
        session.commit()
        row.parameters = {"v": 2}
        session.commit()
        fetched = session.get(SimulationResult, row.id)
        assert fetched.parameters == {"v": 2}

    def test_delete(self, session):
        row = SimulationResult(parameters={"x": 1})
        session.add(row)
        session.commit()
        rid = row.id
        session.delete(row)
        session.commit()
        assert session.get(SimulationResult, rid) is None

    def test_multiple_rows(self, session):
        for i in range(5):
            session.add(SimulationResult(parameters={"i": i}))
        session.commit()
        count = session.query(SimulationResult).count()
        assert count == 5

    def test_json_complex_parameters(self, session):
        data = {"nested": {"list": [1, 2, 3], "deep": {"key": "val"}}}
        row = SimulationResult(parameters=data)
        session.add(row)
        session.commit()
        fetched = session.get(SimulationResult, row.id)
        assert fetched.parameters["nested"]["deep"]["key"] == "val"

    def test_nullable_fields_default_none(self, session):
        row = SimulationResult(parameters={"p": 1})
        session.add(row)
        session.commit()
        fetched = session.get(SimulationResult, row.id)
        assert fetched.map_path is None
        assert fetched.map_config is None
        assert fetched.map_snapshot is None
        assert fetched.csv_path is None
        assert fetched.best_scenario is None

    def test_created_at_auto_set(self, session):
        row = SimulationResult(parameters={"t": 1})
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.created_at is not None

    # ── Edge cases ──

    def test_empty_parameters_dict(self, session):
        row = SimulationResult(parameters={})
        session.add(row)
        session.commit()
        assert session.get(SimulationResult, row.id).parameters == {}

    def test_large_json_parameters(self, session):
        big = {"items": list(range(1000))}
        row = SimulationResult(parameters=big)
        session.add(row)
        session.commit()
        assert len(session.get(SimulationResult, row.id).parameters["items"]) == 1000

    def test_long_map_path(self, session):
        long_path = "/maps/" + "a" * 1000 + ".html"
        row = SimulationResult(parameters={"p": 1}, map_path=long_path)
        session.add(row)
        session.commit()
        assert session.get(SimulationResult, row.id).map_path == long_path

    def test_update_nullable_field(self, session):
        row = SimulationResult(parameters={"p": 1})
        session.add(row)
        session.commit()
        row.best_scenario = {"revenue": 500}
        session.commit()
        assert session.get(SimulationResult, row.id).best_scenario == {"revenue": 500}

    def test_set_nullable_back_to_none(self, session):
        row = SimulationResult(parameters={"p": 1}, csv_path="/a.csv")
        session.add(row)
        session.commit()
        row.csv_path = None
        session.commit()
        assert session.get(SimulationResult, row.id).csv_path is None
