"""
pytest configuration and fixtures for YORI test suite
"""
import sys
from pathlib import Path

# Add python directory to path so we can import yori modules
python_dir = Path(__file__).parent / "python"
sys.path.insert(0, str(python_dir))
