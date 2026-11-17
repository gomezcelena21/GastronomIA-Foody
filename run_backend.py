"""
Gastro IA - Backend Server Starter
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Set paths
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Load .env
load_dotenv(backend_dir / ".env")

# Change to backend directory
os.chdir(backend_dir)

# Start server
import uvicorn
from main import app

print("=" * 50)
print("  Gastro IA Backend Server")
print("  http://127.0.0.1:8001")
print("  http://127.0.0.1:8001/docs")
print("=" * 50)

uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
