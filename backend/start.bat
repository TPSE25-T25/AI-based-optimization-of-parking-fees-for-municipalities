@echo off
echo Upgrading pip to latest version...
python -m pip install --upgrade pip
echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Error installing dependencies. Trying alternative approach...
    echo Installing packages individually...
    pip install "fastapi>=0.110.0"
    pip install "uvicorn>=0.27.0" 
    pip install "python-multipart>=0.0.7"
    pip install "pydantic>=2.10.0"
)
echo.
echo Starting FastAPI server...
python main.py