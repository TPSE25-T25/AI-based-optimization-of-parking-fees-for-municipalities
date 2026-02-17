import os
import pytest

from backend.services.visualization.result_handler import OptimizationResultHandler


# -------------------------
# Small fakes for testing
# -------------------------

class FakeScenario:
    def __init__(self):
        self.scenario_id = 7
        self.score_revenue = 1234.56
        self.score_occupancy_gap = 0.12
        self.score_demand_drop = 0.05
        self.score_user_balance = 0.77
        self.zones = [{"id": 1}, {"id": 2}]


class FakeLoader:
    def __init__(self, gdf):
        self._gdf = gdf
        self.export_calls = []

    def get_gdf_with_results(self, zones):
        return self._gdf

    def export_results_for_superset(self, optimized_zones, csv_path):
        # emulate a CSV export by writing a file
        self.export_calls.append((optimized_zones, csv_path))
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,new_fee\n")


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeGeometry:
    # Mimic a geometry object with centroid.x / centroid.y
    def __init__(self, x, y):
        self.centroid = FakePoint(x, y)


class FakeGDF:
    """
    Minimal GeoDataFrame-like object supporting:
      - .empty
      - .iterrows() yielding (index, row)
    Row must support row['new_fee'], row['old_fee'], row['predicted_occupancy'], row['predicted_revenue'], row.get('name', ..)
    and row.geometry.centroid.x/y
    """
    def __init__(self, rows):
        self._rows = rows

    @property
    def empty(self):
        return len(self._rows) == 0

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row


class RowDict(dict):
    # Provide .geometry attribute like geopandas row
    def __init__(self, *args, geometry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry = geometry


# -------------------------
# Tests
# -------------------------

class TestOptimizationResultHandler:
    def test_present_winning_scenario_prints(self, capsys):
        handler = OptimizationResultHandler()
        scenario = FakeScenario()

        handler.present_winning_scenario(scenario, user_weights={"revenue": 100})

        out = capsys.readouterr().out
        assert "WINNING RESULT" in out
        assert "Scenario #7" in out
        assert "Applying User Weights" in out
        assert "Revenue Score" in out

    def test_default_popup_html_contains_expected_fields(self):
        handler = OptimizationResultHandler()
        row = RowDict(
            {
                "new_fee": 3.5,
                "old_fee": 2.0,
                "predicted_occupancy": 0.8,
                "predicted_revenue": 100.0,
                "name": "Zone A",
            },
            geometry=FakeGeometry(8.4, 49.0),
        )

        html = handler._default_popup_html(row, trend="📈 Higher", method_label="Elasticity")
        assert "Zone A" in html
        assert "Old:" in html
        assert "New:" in html
        assert "Occupancy:" in html
        assert "Revenue:" in html
        assert "Elasticity" in html

    def test_generate_map_returns_empty_string_when_gdf_empty(self, tmp_path, capsys):
        handler = OptimizationResultHandler(output_dir=str(tmp_path))
        gdf = FakeGDF(rows=[])

        out_path = handler.generate_map(gdf, "map.html")
        assert out_path == ""

        out = capsys.readouterr().out
        assert "Warning: GeoDataFrame is empty" in out

    def test_generate_map_saves_to_output_dir(self, tmp_path, monkeypatch):
        handler = OptimizationResultHandler(output_dir=str(tmp_path))

        # Prepare one valid row
        row = RowDict(
            {
                "new_fee": 3.0,
                "old_fee": 2.0,
                "predicted_occupancy": 0.7,
                "predicted_revenue": 50.0,
                "name": "Zone A",
            },
            geometry=FakeGeometry(8.4, 49.0),
        )
        gdf = FakeGDF(rows=[row])

        # Monkeypatch folium.Map.save to avoid relying on folium internals
        import folium
        saved = {"path": None}

        def fake_save(self, path):
            saved["path"] = path
            # create a file to simulate saving
            with open(path, "w", encoding="utf-8") as f:
                f.write("<html></html>")

        monkeypatch.setattr(folium.Map, "save", fake_save, raising=True)

        out_path = handler.generate_map(gdf, "map.html", method_label="Optimization")
        assert out_path == os.path.join(str(tmp_path), "map.html")
        assert saved["path"] == out_path
        assert os.path.exists(out_path)

    def test_export_csv_calls_loader_and_writes_file(self, tmp_path):
        handler = OptimizationResultHandler(output_dir=str(tmp_path))
        gdf = FakeGDF(rows=[])
        loader = FakeLoader(gdf)

        csv_path = handler.export_csv(loader, optimized_zones=[{"id": 1}], csv_filename="out.csv")

        assert csv_path == os.path.join(str(tmp_path), "out.csv")
        assert os.path.exists(csv_path)
        assert len(loader.export_calls) == 1
        assert loader.export_calls[0][1] == csv_path

    def test_handle_full_workflow_runs_all_steps(self, tmp_path, monkeypatch):
        handler = OptimizationResultHandler(output_dir=str(tmp_path))
        scenario = FakeScenario()

        # Prepare one valid row so map is generated
        row = RowDict(
            {
                "new_fee": 3.0,
                "old_fee": 2.0,
                "predicted_occupancy": 0.7,
                "predicted_revenue": 50.0,
                "name": "Zone A",
            },
            geometry=FakeGeometry(8.4, 49.0),
        )
        gdf = FakeGDF(rows=[row])
        loader = FakeLoader(gdf)

        # Monkeypatch folium save again
        import folium

        def fake_save(self, path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("<html></html>")

        monkeypatch.setattr(folium.Map, "save", fake_save, raising=True)

        map_path, csv_path = handler.handle_full_workflow(
            best_scenario=scenario,
            user_weights={"revenue": 100},
            loader=loader,
            map_filename="map.html",
            csv_filename="out.csv",
            method_label="Optimization",
        )

        assert os.path.exists(map_path)
        assert os.path.exists(csv_path)
        assert map_path.endswith("map.html")
        assert csv_path.endswith("out.csv")
