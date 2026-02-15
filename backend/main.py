import sys
from pathlib import Path

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Add the project root directory to sys.path
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.services.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)