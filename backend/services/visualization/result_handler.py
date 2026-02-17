"""
Result Handler for Parking Optimization

This module provides a reusable class for handling optimization results:
- Presenting the winning scenario
- Generating interactive Folium maps
- Exporting data to CSV

Eliminates code duplication between different optimization runners.
"""

import os
from typing import Optional
import folium
from folium.plugins import MarkerCluster


class OptimizationResultHandler:
    """
    Handles presentation, visualization, and export of optimization results.
    """

    def __init__(
        self,
        center_location: tuple[float, float] = (49.0069, 8.4037),
        zoom_start: int = 14,
        output_dir: Optional[str] = None
    ):
        """
        Initialize the result handler.

        Args:
            center_location: Map center (latitude, longitude)
            zoom_start: Initial zoom level for map
            output_dir: Directory for output files (defaults to current directory)
        """
        self.center_location = center_location
        self.zoom_start = zoom_start
        self.output_dir = output_dir or os.getcwd()

    def present_winning_scenario(self, best_scenario, user_weights: dict) -> None:
        """
        Print the winning scenario details to console.

        Args:
            best_scenario: The selected PricingScenario
            user_weights: The weights used for selection
        """
        print(f"\n⚖️  Applying User Weights: {user_weights}")
        print("\n" + "-" * 70)
        print(f"🏁 WINNING RESULT (Scenario #{best_scenario.scenario_id})")
        print(f"💰 Revenue Score:      {best_scenario.score_revenue:.2f} €")
        print(f"🚗 Ø Occupancy Gap:    {best_scenario.score_occupancy_gap*100:.2f}%")
        print(f"📉 Demand Drop:        {best_scenario.score_demand_drop*100:.2f}%")
        print(f"⚖️  User Balance:       {best_scenario.score_user_balance:.2f}")
        print("-" * 70)

    def generate_map(
        self,
        res_gdf,
        output_filename: str,
        method_label: str = "Optimization"
    ) -> str:
        """
        Generate an interactive Folium map with optimization results.

        Args:
            res_gdf: GeoDataFrame with columns: name, new_fee, old_fee,
                     predicted_occupancy (optional), predicted_revenue (optional)
            output_filename: Name of output HTML file
            popup_generator: Optional custom function(row) -> popup_html
            method_label: Label to show in popup (e.g., "Driver Simulation", "Elasticity Model")

        Returns:
            Path to saved HTML file
        """
        print("\n3️⃣  Generating interactive map...")

        if res_gdf.empty:
            print("⚠️ Warning: GeoDataFrame is empty.")
            return ""

        # Initialize Folium Map
        m = folium.Map(
            location=self.center_location,
            zoom_start=self.zoom_start,
            tiles="cartodbpositron"
        )
        cluster = MarkerCluster().add_to(m)

        # Iterate through zones to add markers
        for _, row in res_gdf.iterrows():
            new_fee = row['new_fee']
            old_fee = row['old_fee']

            # Determine Color Logic based on current_fee change
            diff = new_fee - old_fee
            if diff > 0.1:
                color = 'red'       # current_fee Hike (Expensive)
                trend = "📈 Higher"
            elif diff < -0.1:
                color = 'green'     # current_fee Drop (Cheaper)
                trend = "📉 Lower"
            else:
                color = 'blue'      # Stable
                trend = "➡️ Stable"

            # Generate popup HTML
            popup_html = self._default_popup_html(row, trend, method_label)

            # Add marker to map cluster
            folium.CircleMarker(
                location=[row.geometry.centroid.y, row.geometry.centroid.x],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(cluster)

        # Save Map to disk
        output_path = os.path.join(self.output_dir, output_filename)
        m.save(output_path)
        print(f"✅ Map saved: {output_path}")

        return output_path

    def _default_popup_html(self, row, trend: str, method_label: str) -> str:
        """
        Generate default popup HTML.

        Args:
            row: GeoDataFrame row
            trend: current_fee trend string (e.g., "📈 Higher")
            method_label: Method label for display

        Returns:
            HTML string for popup
        """
        new_fee = row['new_fee']
        old_fee = row['old_fee']
        occupancy = row['predicted_occupancy']
        revenue = row['predicted_revenue']
        name = row.get('name', 'Zone')

        # Base popup content
        html = f"""
        <div style="font-family: Arial; min-width: 150px;">
            <b>{name}</b><hr>
            Status: <b>{trend}</b><br>
            Old: {old_fee:.2f} €<br>
            New: <b>{new_fee:.2f} €</b><br>
            Occupancy: <b>{occupancy * 100:.2f} %</b><br>
            Revenue: <b>{revenue:.2f} €</b><br>
            <i>({method_label})</i>\n</div>\n
        """
        return html

    def export_csv(
        self,
        loader,
        optimized_zones: list,
        csv_filename: str
    ) -> str:
        """
        Export optimization results to CSV.

        Args:
            loader: Data loader instance with export_results_for_superset method
            optimized_zones: List of OptimizedZoneResult objects
            csv_filename: Name of output CSV file

        Returns:
            Path to saved CSV file
        """
        print("\n4️⃣  Exporting Data...")
        csv_path = os.path.join(self.output_dir, csv_filename)

        loader.export_results_for_superset(optimized_zones, csv_path)
        print(f"✅ CSV exported: {csv_path}")

        return csv_path

    def handle_full_workflow(
        self,
        best_scenario,
        user_weights: dict,
        loader,
        map_filename: str,
        csv_filename: str,
        method_label: str = "Optimization"
    ) -> tuple[str, str]:
        """
        Execute the complete result handling workflow.

        Args:
            best_scenario: The selected PricingScenario
            user_weights: The weights used for selection
            loader: Data loader instance
            map_filename: Output HTML filename
            csv_filename: Output CSV filename
            popup_generator: Optional custom popup generator
            method_label: Method label for map popup

        Returns:
            Tuple of (map_path, csv_path)
        """
        # Present results
        self.present_winning_scenario(best_scenario, user_weights)

        # Generate map
        res_gdf = loader.get_gdf_with_results(best_scenario.zones)
        map_path = self.generate_map(
            res_gdf,
            map_filename,
            method_label
        )

        # Export CSV
        csv_path = self.export_csv(loader, best_scenario.zones, csv_filename)

        return map_path, csv_path
