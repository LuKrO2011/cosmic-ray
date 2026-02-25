"""Add this directory to sys.path so dummy tests can import sut directly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
