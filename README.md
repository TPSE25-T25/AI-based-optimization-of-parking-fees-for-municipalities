# SmartFee: AI-based Optimization of Parking Fees for Municipalities

A **simulation and feasibility prototype** — not a production-ready system — that supports municipalities and regional authorities in setting efficient, fair, and adaptable parking prices. Municipal parking pricing is typically set manually, based on limited data and political considerations. Legal price caps, heterogeneous parking-space ownership, and diverse user groups (commuters, residents, tourists) make evidence-based pricing difficult.

This tool lets city planners load real or synthetic city parking data, run NSGA-III multi-objective optimization across four competing KPIs, and select and visualize the best Pareto-optimal scenario through a weight-based preference interface. It is designed to help municipalities **continuously evaluate and adjust pricing** and **predict the impact of new regulations before implementation**.

**Primary users:** municipal decision-makers, planners, and administrators responsible for pricing strategies and automation. The system indirectly affects citizens, tourists, and local businesses by influencing parking availability, accessibility, and pricing fairness.

---

## Architecture

```
┌─────────────────────────────────┐       HTTP / REST        ┌──────────────────────────────────┐
│           Frontend              │ ◄──────────────────────► │           Backend                │
│   React 18 + Vite (port 5173)   │                          │   Python FastAPI (port 6173)     │
│                                 │                          │                                  │
│  • Interactive Leaflet map      │                          │  • NSGA-III multi-obj optimizer  │
│  • Zoom-based zone clustering   │                          │  • Elasticity & agent-based sim  │
│  • Pareto front solution picker │                          │  • OSMnx / MobiData / synthetic  │
│  • Weight sliders (4 KPIs)      │                          │  • SQLAlchemy results store      │
└─────────────────────────────────┘                          └──────────────────────────────────┘
```

---

## Project Structure

```
├── docker-compose.yml                 # Default CPU-only Docker setup
├── docker-compose.cuda.yml            # CUDA override (GPU passthrough)
├── backend/
│   ├── main.py                        # FastAPI entry point (uvicorn, port 6173)
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Standard CPU image (python:3.11-slim)
│   ├── Dockerfile.cuda                # CUDA image (nvidia/cuda:12.3.2)
│   ├── start.bat                      # Windows startup script
│   └── services/
│       ├── api.py                     # All API route definitions
│       ├── models/
│       │   ├── city.py                # ParkingZone, City, PointOfInterest models
│       │   └── driver.py              # Driver behaviour model (agent-based sim)
│       ├── optimizer/
│       │   ├── nsga3_optimizer.py     # Base NSGA-III class
│       │   ├── nsga3_optimizer_elasticity.py  # Elasticity-based objective functions
│       │   ├── nsga3_optimizer_agent.py       # Agent-based objective functions
│       │   └── solution_selector.py   # Pareto-front selection by user weights
│       ├── simulation/
│       │   ├── simulation.py          # Core simulation engine
│       │   └── parallel_engine.py     # Parallel evaluation engine (joblib)
│       ├── datasources/
│       │   ├── osm/                   # OSMnx loader (OpenStreetMap parking data)
│       │   ├── mobidata/              # MobiData BW API integration
│       │   └── generator/             # Synthetic city & parking data generator
│       ├── database/
│       │   ├── models.py              # SimulationResult ORM model
│       │   ├── database.py            # SQLAlchemy session config
│       │   └── init_db.py             # Schema initialisation
│       └── payloads/                  # Request / response Pydantic models
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── App/                   # Main app, state management, layout
│   │   │   ├── ParkingMap/            # Interactive Leaflet map + clustering
│   │   │   ├── InfoPanel/             # Zone details & result display
│   │   │   ├── MenuPanel/             # Navigation & results history
│   │   │   └── ConfigurationPanel/    # City loading & parameter settings
│   │   └── index.jsx                  # React entry point
│   ├── vite.config.js                 # Dev server + API proxy config
│   └── package.json
├── tests/
│   └── backend_tests/                 # pytest test suite
├── docs/                              # Additional documentation
└── README.md
```

---

## Features

### Optimization
- **NSGA-III multi-objective optimizer** (via [pymoo](https://pymoo.org/)) with two simulation models:
  - **Elasticity model** — price-elasticity demand function with loss aversion (increases weighted 1.2×, decreases 0.8×) and short-term / long-term user group split
  - **Agent-based model** — individual driver agents with route-choice behaviour
- **Four optimization objectives** (all simultaneously):
  | KPI | Goal |
  |---|---|
  | Revenue | Maximise total fee income |
  | Occupancy | Minimize deviation from 85% target occupancy |
  | Demand | Minimize parking demand drop (avoid pricing out users) |
  | Fairness | Minimize fee shock, weighted by user group |
- **Pareto-front solution selection** via configurable weight sliders (Revenue / Occupancy / Demand / Fairness, default 50 / 30 / 10 / 10)

### Data Sources
- **OpenStreetMap** — real parking zone geometry and capacity via OSMnx
- **MobiData BW** — live occupancy and sensor data from Baden-Württemberg open mobility platform
- **Synthetic generator** — randomised city data for development and testing

### Interactive Map
- Color-coded zone circles: green (low occupancy) → yellow → red (high occupancy)
- **Zoom-based clustering**: at low zoom, zones with shared `cluster_id` (DBSCAN spatial grouping) collapse into aggregate bubbles; click or zoom in to expand
- Location picker for setting custom city centre coordinates

### Results & Persistence
- Compare multiple optimization scenarios on the Pareto front
- Save simulation results to SQLite via REST API
- Browse and reload previously saved results from the menu

---

## Prerequisites

| Component | Requirement |
|---|---|
| Python | 3.9 or higher |
| Node.js | 18 or higher |
| npm | 9 or higher |

---

## Installation & Setup

### Option 1: Docker (recommended)

**CPU mode (default):**
```bash
docker-compose up --build
```

**CUDA mode** (requires NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on the host):
```bash
docker-compose -f docker-compose.yml -f docker-compose.cuda.yml up --build
```

This starts both the backend (port 6173) and frontend (port 5173) in containers. Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

The two Compose files are **merged** by Docker Compose — the base `docker-compose.yml` provides the full service definitions (including the frontend), and `docker-compose.cuda.yml` only overrides the backend service to swap in the CUDA image (`backend/Dockerfile.cuda`, based on `nvidia/cuda:12.3.2`) and add GPU device reservation. The frontend starts exactly as in the default setup; no separate command is needed.

Without the CUDA override, the parallel engine automatically falls back to **CPU-parallel mode** (via joblib) and all functionality remains available.

### Option 2: Windows startup scripts

```bash
# Terminal 1 — Backend
cd backend
start.bat          # installs dependencies, starts FastAPI on http://localhost:6173

# Terminal 2 — Frontend
cd frontend
start.bat          # installs dependencies, starts Vite dev server on http://localhost:5173
```

### Option 3: Manual setup

**Backend**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend**
```bash
cd frontend
npm install
npm start          # or: npm run dev
```

The Vite dev server proxies all API calls (`/load_city`, `/optimize`, `/results`, `/reverse-geocode`, `/select_best_solution_by_weight`) to `http://localhost:6173`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health status |
| `GET` | `/optimization-settings` | Available optimizer configurations |
| `POST` | `/load_city` | Load city data (OSMnx / MobiData / generated) |
| `POST` | `/reverse-geocode` | Convert lat/lon to city name |
| `POST` | `/optimize` | Run NSGA-III optimization, returns Pareto front |
| `POST` | `/select_best_solution_by_weight` | Pick best scenario from Pareto front by weights |
| `GET` | `/results` | List stored simulation results |
| `GET` | `/results/{id}` | Fetch a specific stored result |
| `POST` | `/results` | Persist a simulation result |

Interactive API docs (Swagger UI) are available at `http://localhost:6173/docs` when the backend is running.

---

## Testing

```bash
cd backend
pytest              # runs all tests in tests/backend_tests/
pytest --cov        # with coverage report
```

The project targets **>80% statement coverage**. Tests are located in `tests/backend_tests/` and cover the core optimization logic, simulation engine, and API endpoints.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| CORS errors in browser | Ensure both servers are running; frontend must be on port 5173 |
| Port already in use | Backend: 6173 · Frontend: 5173 — free those ports before starting |
| OSMnx download fails | Requires internet access; large cities may time out — try a smaller radius |
| MobiData 401 errors | Check MobiData API key configuration in backend settings |
| Python dependency conflicts | Use a virtual environment: `python -m venv .venv && .venv\Scripts\activate` |

**Logs**
- Backend: uvicorn output in the terminal running `main.py`
- Frontend: browser DevTools console (F12)
- API docs: `http://localhost:6173/docs`

---

## Data Protection & Privacy

This project is designed to comply with the **European General Data Protection Regulation (GDPR / DSGVO)**:

- Synthetic data generated during simulation (e.g. mock driver records) is processed **in-memory only** and is **never persisted** to disk or database.
- The SQLite database stores only **anonymised, aggregated optimization results** (pricing scenarios, zone configurations, KPI snapshots) — no personally identifiable information (PII).
- The system follows the GDPR principles of **data minimisation** and **storage limitation**.

---

## Team

TPSE WiSe 2025/26 — Thema 95 | AG: [ui!] Urban Mobility Innovations GmbH

| Name | E-Mail |
|---|---|
| Dorothea Krahmann | dorothea.krahmann@gmail.com |
| Julius Pantel | julius-pantel@web.de |
| Igor Ricarte | igor.ricarte@stud.tu-darmstadt.de |
| Şebnem Uçar | ucar.sebnem@yahoo.com |
| Zied Miled | miled.zied01@gmail.com |

**Supervisors:** Judith Gessenhardt, Stephan Borgert | **Advisor:** David Brauch

---

## License

Released under the **MIT License** — see [LICENSE](LICENSE) for details.

This permissive open-source license allows anyone to freely use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software. University course project (T25 / TPSE, WiSe 2025/26).
