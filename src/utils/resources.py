import os
import sys
from typing import Optional


def base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def resource_path(name: str) -> str:
    # Try alongside executable/MEIPASS, then current working dir
    candidates = [
        os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else base_path(), name),
        os.path.abspath(name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

