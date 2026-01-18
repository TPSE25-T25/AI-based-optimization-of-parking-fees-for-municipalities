import osmnx as ox
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import List, Dict

# Pfad-Fix für Imports, falls nötig
try:
    from schemas.optimization import ParkingZoneInput
except ImportError:
    import sys
    import os
    # Versuche Root zu finden
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from schemas.optimization import ParkingZoneInput

class KarlsruheLoader:
    def __init__(self):
        self.place_name = "Karlsruhe, Germany"
        # Zentrum: Karlsruher Schloss
        self.center_lat = 49.0134
        self.center_lon = 8.4044
        self.gdf = None
        self.id_mapping = {}
        self.zone_lookup = {}

    def load_zones(self, limit: int = 50) -> List[ParkingZoneInput]:
        print(f"📡 Lade Geodaten für {self.place_name} via OSM...")
        
        tags = {"amenity": "parking"}
        try:
            self.gdf = ox.features_from_place(self.place_name, tags)
        except Exception as e:
            print(f"❌ Fehler bei OSM-Abfrage: {e}")
            return []

        # 1. Projektion auf metrisches System (UTM 32N) für korrekte Mathe
        self.gdf = self.gdf.to_crs(epsg=32632)
        
        # 2. Centroid berechnen (auf metrischen Daten -> korrekt), DANN zu Lat/Lon für Distanz/Karte
        # Dies verhindert die UserWarning
        self.gdf["centroid"] = self.gdf.geometry.centroid.to_crs(epsg=4326)

        # Sortieren nach Größe (Fläche), damit wir bei Limit die großen Parkplätze bekommen
        self.gdf["sort_area"] = self.gdf.geometry.area
        top_zones = self.gdf.sort_values(by="sort_area", ascending=False).head(limit)

        zones_input = []
        
        # Iterieren
        for internal_id, (osm_index, row) in enumerate(top_zones.iterrows(), start=1):
            
            # --- Kapazitäts-Berechnung (Robust) ---
            capacity = 0 # Startwert
            
            # A) Versuche 'capacity' Tag aus OSM zu lesen
            if "capacity" in row and pd.notnull(row["capacity"]):
                try:
                    import re
                    nums = re.findall(r'\d+', str(row["capacity"]))
                    if nums: 
                        capacity = int(nums[0])
                except: 
                    pass
            
            # B) Fallback: Schätzung über Fläche, falls A gescheitert oder 0
            if capacity <= 0:
                if row.geometry.geom_type in ['Polygon', 'MultiPolygon']:
                    # Fläche durch 25m² pro Auto
                    capacity = max(5, int(row.geometry.area / 25))
                else:
                    # Punkt (Straßenrand)
                    capacity = 5 
            
            # C) SICHERHEITSNETZ: Pydantic verbietet 0. 
            # Selbst wenn alles schiefgeht, nehmen wir mindestens 2 Plätze an.
            capacity = max(2, capacity)

            # --- Simulation (Preise & Auslastung) ---
            # Wir nutzen das berechnete Centroid (Lat/Lon)
            c_lat = row["centroid"].y
            c_lon = row["centroid"].x
            
            dist_deg = np.sqrt((c_lat - self.center_lat)**2 + (c_lon - self.center_lon)**2)
            dist_km = dist_deg * 111.0
            
            # --- REALISTISCHE PREISE FÜR KARLSRUHE ---
            # Formel: Basis 1.00€ + Aufschlag (sanfterer Abfall)
            price_markup = 2.5 / (dist_km + 0.8) 
            simulated_fee = np.round(1.0 + price_markup, 1)
            
            # Realistisches Limit: Nicht teurer als 4.00€, nicht billiger als 1.00€
            simulated_fee = min(max(simulated_fee, 1.0), 4.0)
            
            # Auslastung: Zentrum voll (95%), Rand leerer
            simulated_occ = 0.95 - (dist_km * 0.1)
            simulated_occ = np.clip(simulated_occ, 0.1, 0.99)

            # Mapping speichern (für Rückweg zur Karte)
            self.id_mapping[internal_id] = osm_index
            
            name = row.get("name", "Unbenannt")
            if pd.isna(name): name = f"Parkzone {internal_id}"

            # Objekt erstellen
            zone = ParkingZoneInput(
                zone_id=internal_id,
                name=str(name)[0:50],
                capacity=capacity,
                current_fee=float(simulated_fee),
                current_occupancy=float(simulated_occ),
                min_fee=0.5,
                max_fee=10.0,
                elasticity=-0.5,
                short_term_share=0.5
            )
            zones_input.append(zone)
            self.zone_lookup[internal_id] = zone

        return zones_input

    def get_gdf_with_results(self, optimized_zones: list) -> gpd.GeoDataFrame:
        """Kombiniert Ergebnisse zurück ins GeoDataFrame"""
        # Wir arbeiten auf einer Kopie der originalen Daten
        result_gdf = self.gdf.copy()
        
        result_gdf["new_fee"] = np.nan
        result_gdf["old_fee"] = np.nan
        result_gdf["optimized"] = False

        for zone_res in optimized_zones:
            osm_id = self.id_mapping.get(zone_res.zone_id)
            original = self.zone_lookup.get(zone_res.zone_id)
            
            if osm_id is not None and osm_id in result_gdf.index:
                result_gdf.at[osm_id, "new_fee"] = zone_res.new_fee
                result_gdf.at[osm_id, "old_fee"] = original.current_fee
                result_gdf.at[osm_id, "optimized"] = True
                
        # Nur optimierte Zeilen zurückgeben und Projektion auf Lat/Lon für Folium
        return result_gdf[result_gdf["optimized"] == True].to_crs(epsg=4326)