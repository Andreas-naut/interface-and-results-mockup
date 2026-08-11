"""Tab renderers. Each module exposes a single ``render()``."""

from app.views import generation, hydro, load, ntc, overview

__all__ = ["generation", "hydro", "load", "ntc", "overview"]
