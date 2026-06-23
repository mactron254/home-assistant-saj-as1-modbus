"""Configuracion comun de pytest para la integracion SAJ AS1."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT_DIR / "custom_components" / "saj_as1_modbus"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if str(INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_DIR))
