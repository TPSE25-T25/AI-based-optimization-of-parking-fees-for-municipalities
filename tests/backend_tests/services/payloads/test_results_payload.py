import pytest
from pydantic import ValidationError
from backend.services.payloads.results_payload import SaveResultRequest


def test_save_result_request_minimal():
    r = SaveResultRequest(parameters={"key": "value"})
    assert r.parameters == {"key": "value"}
    assert r.map_config is None
    assert r.map_snapshot is None
    assert r.map_path is None
    assert r.csv_path is None
    assert r.best_scenario is None


def test_save_result_request_full():
    r = SaveResultRequest(
        parameters={"a": 1},
        map_config={"zoom": 10},
        map_snapshot=[{"layer": "zones"}],
        map_path="/tmp/map.html",
        csv_path="/tmp/data.csv",
        best_scenario={"id": 1},
    )
    assert r.map_config["zoom"] == 10
    assert r.map_path == "/tmp/map.html"
    assert r.best_scenario["id"] == 1


# --- Edge cases ---

def test_save_result_request_missing_parameters():
    with pytest.raises(ValidationError):
        SaveResultRequest()


def test_save_result_request_empty_parameters():
    r = SaveResultRequest(parameters={})
    assert r.parameters == {}


def test_save_result_request_empty_snapshot_list():
    r = SaveResultRequest(parameters={"a": 1}, map_snapshot=[])
    assert r.map_snapshot == []


def test_save_result_request_empty_strings():
    r = SaveResultRequest(parameters={"a": 1}, map_path="", csv_path="")
    assert r.map_path == ""
    assert r.csv_path == ""
