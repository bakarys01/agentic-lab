"""Resolve application resources kept outside the Python package."""

import os
from pathlib import Path


PROJECT_ROOT = Path(
    os.environ.get("MEDINOVA_PROJECT_ROOT", Path(__file__).resolve().parents[2])
).resolve()
