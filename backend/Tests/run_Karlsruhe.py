import sys
import os

# --- 1. PFAD-KONFIGURATION (WICHTIG!) ---
# Damit Python die Ordner 'schemas', 'services' und 'simulators' findet,
# müssen wir den übergeordneten Ordner ('backend') zum Suchpfad hinzufügen.

current_file_path = os.path.abspath(__file__)           # .../backend/Tests/run_Karlsruhe.py
current_dir = os.path.dirname(current_file_path)        # .../backend/Tests
backend_dir = os.path.dirname(current_dir)              # .../backend

if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Jetzt können wir sicher importieren
try:
    import folium
    from folium.plugins import MarkerCluster
    
    from simulators.karlsruhe_loader import KarlsruheLoader
    from services.nsga3_optimizer import NSGA3Optimizer
    from schemas.optimization import OptimizationRequest, OptimizationSettings
except ImportError as e:
    print("\n❌ KRITISCHER IMPORT-FEHLER!")
    print(f"Konnte Module nicht laden. Pfad ist gesetzt auf: {sys.path}")
    print(f"Fehlermeldung: {e}")
    sys.exit(1)

# --- 2. HAUPTPROGRAMM ---

def main():
    print("\n" + "="*60)
    print("🏙️  PARKRAUM-OPTIMIERUNG KARLSRUHE (TEST-LAUF)")
    print("="*60)

    # A. DATEN LADEN
    print("1️⃣  Initialisiere Loader für Karlsruhe...")
    loader = KarlsruheLoader()
    
    # limit=50 sorgt dafür, dass der Test schnell geht (nur die 50 größten Parkplätze)
    # Wenn alles klappt, kannst du 'limit=50' später entfernen.
    zones = loader.load_zones(limit=50) 
    
    if not zones:
        print("❌ Abbruch: Keine Zonen gefunden oder Internet-Fehler.")
        return

    print(f"✅ {len(zones)} Parkzonen erfolgreich geladen.")
    
    # Kleiner Einblick in die Daten
    sample = zones[0]
    print(f"   Beispiel: '{sample.name}' | Kapazität: {sample.capacity} | Aktueller Preis: {sample.current_fee}€")

    # B. OPTIMIERUNG VORBEREITEN
    print("\n2️⃣  Konfiguriere KI-Algorithmus (NSGA-III)...")
    settings = OptimizationSettings(
        population_size=200,    # Klein für Test (Später: 200+)
        generations=50,        # Klein für Test (Später: 100+)
        target_occupancy=0.85  # Ziel: 85% Auslastung
    )
    
    req = OptimizationRequest(zones=zones, settings=settings)

    # C. OPTIMIERER STARTEN
    print("🚀 Starte Berechnung... (Bitte warten)")
    optimizer = NSGA3Optimizer()
    response = optimizer.optimize(req)
    
    # Wir nehmen das erste Szenario der Pareto-Front
    best_scenario = response.scenarios[0]
    
    print("\n" + "-"*60)
    print("🏁 ERGEBNISSE (Szenario A)")
    print(f"💰 Umsatz-Score (Negativsumme): {best_scenario.score_revenue:.2f}")
    print(f"🚗 Durchschnittliche Lücke zur Zielauslastung: {best_scenario.score_occupancy_gap*100:.2f}%")
    print("-" * 60)

    # D. KARTE GENERIEREN
    print("\n3️⃣  Erstelle interaktive Karte...")
    
    # Hole Geo-Daten zurück, angereichert mit den neuen Preisen
    res_gdf = loader.get_gdf_with_results(best_scenario.zones)
    
    # Karte zentriert auf Karlsruhe
    m = folium.Map(location=[49.0069, 8.4037], zoom_start=14, tiles="cartodbpositron")
    
    # Cluster für Marker (damit die Karte bei vielen Punkten flüssig bleibt)
    cluster = MarkerCluster().add_to(m)

    for idx, row in res_gdf.iterrows():
        # Neue vs Alte Gebühr
        new_fee = row['new_fee']
        old_fee = row['old_fee']
        diff = new_fee - old_fee
        
        # Farbe bestimmen
        if diff > 0.2:
            color = 'red'      # Teurer geworden
            trend = "📈 Teurer"
        elif diff < -0.2:
            color = 'green'    # Billiger geworden
            trend = "📉 Billiger"
        else:
            color = 'blue'     # Stabil
            trend = "➡️ Stabil"

        # Popup-Inhalt (HTML)
        popup_html = f"""
        <div style="font-family: Arial; min-width: 150px;">
            <b>{row.get('name', 'Parkzone')}</b><hr>
            Status: <b>{trend}</b><br><br>
            Alt: {old_fee:.2f} €<br>
            Neu: <b>{new_fee:.2f} €</b><br>
            Differenz: {diff:+.2f} €
        </div>
        """

        # Marker setzen (nutze Zentroid für Position)
        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            radius=8,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(cluster)

    # Speichern
    output_filename = "karlsruhe_result.html"
    # Speichere im gleichen Ordner wie das Skript
    output_path = os.path.join(current_dir, output_filename)
    
    m.save(output_path)
    print(f"✅ Karte erfolgreich gespeichert!")
    print(f"👉 Datei: {output_path}")
    print("   (Öffne diese Datei einfach per Doppelklick)")

if __name__ == "__main__":
    main()