import folium
from folium.plugins import MarkerCluster
from typing import List


from services.data.karlsruhe_loader import KarlsruheLoader
from backend.services.optimizer.schemas.optimization_schema import OptimizedZoneResult

class MappingService:
    def __init__(self, loader: KarlsruheLoader):
        """
        Der Service bekommt den Loader übergeben, damit er Zugriff 
        auf die Geometrie (lat/lon) der Zonen hat.
        """
        self.loader = loader

    def generate_map_html(self, optimized_zones: List[OptimizedZoneResult]) -> str:
        """
        Nimmt die Rechenergebnisse (Preise) und baut daraus den HTML-String für die Karte.
        """
        # 1. Wir holen uns ein GeoDataFrame, das Geometrie UND neue Preise enthält
        # Die Funktion get_gdf_with_results muss in deinem Loader existieren (vom Anfang)
        res_gdf = self.loader.get_gdf_with_results(optimized_zones)
        
        if res_gdf.empty:
            return "<div style='padding:20px'>⚠️ Keine Daten für die Karte verfügbar.</div>"

        # 2. Map Initialisierung (Zentriert auf Karlsruhe)
        m = folium.Map(location=[49.0069, 8.4037], zoom_start=14, tiles="cartodbpositron")
        cluster = MarkerCluster().add_to(m)

        # 3. Marker für jede Zone setzen
        for _, row in res_gdf.iterrows():
            new_fee = row['new_fee']
            old_fee = row['old_fee']
            diff = new_fee - old_fee
            
            # Farb-Logik: Rot = Teurer, Grün = Billiger
            if diff > 0.1:
                color = 'red'
                trend = "📈 Teurer"
            elif diff < -0.1:
                color = 'green'
                trend = "📉 Günstiger"
            else:
                color = 'blue'
                trend = "➡️ Stabil"

            # Das Popup-Fenster (HTML), wenn man auf den Punkt klickt
            popup_html = f"""
            <div style="font-family: Arial; min-width: 150px;">
                <b>{row.get('name', 'Zone')}</b><hr>
                Status: <b>{trend}</b><br>
                Alt: {old_fee:.2f} €<br>
                Neu: <b>{new_fee:.2f} €</b>
            </div>
            """

            folium.CircleMarker(
                location=[row.geometry.centroid.y, row.geometry.centroid.x],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(cluster)

        # 4. WICHTIG: Wir geben den HTML-Code als Text zurück (kein Speichern als Datei)
        return m.get_root().render()