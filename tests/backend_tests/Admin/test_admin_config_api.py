import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.admin.config_repository import ConfigRepository
from backend.services.io.file_manager import FileManager

client = TestClient(app)


def test_put_and_get_config(tmp_path):
    # You’ll likely want DI to inject tmp base dir cleanly later.
    # For MVP: at least ensure PUT works structurally.
    payload = {
        "version": "1.0.0",
        "city": "TestCity",
        "objective_weights": {"revenue": 1, "utilization": 1, "fairness": 1},
        "price_rules": [{"zone_id": "A", "max_price_eur_per_hour": 4, "min_price_eur_per_hour": 1}],
        "discounts": [{"user_group": "resident", "percent": 10}],
        "allow_real_data": False,
        "active_dataset_id": None
    }

    r = client.put("/admin/config", json=payload)
    assert r.status_code == 200

    r2 = client.get("/admin/config")
    assert r2.status_code == 200
    assert r2.json()["city"] == "TestCity"


def test_put_config_rejects_invalid_prices():
    payload = {
        "version": "1.0.0",
        "city": "TestCity",
        "objective_weights": {"revenue": 1, "utilization": 1, "fairness": 1},
        "price_rules": [{"zone_id": "A", "max_price_eur_per_hour": 1, "min_price_eur_per_hour": 3}],
        "discounts": []
    }

    r = client.put("/admin/config", json=payload)
    assert r.status_code == 400
