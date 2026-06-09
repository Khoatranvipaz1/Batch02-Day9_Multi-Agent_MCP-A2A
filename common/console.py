"""Console helpers for reliable UTF-8 output on Windows."""

from __future__ import annotations

import sys


def configure_utf8_console() -> None:
    """Use UTF-8 for stdout/stderr when the active stream supports reconfigure."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
