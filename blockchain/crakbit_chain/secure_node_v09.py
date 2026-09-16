from __future__ import annotations

# Compatibility shim: the CLI historically imported secure_node_v09 directly.
# Keep that import path working while the active development node advances to v0.10.
from .secure_node_v10 import app, create_app

__all__ = ["app", "create_app"]
