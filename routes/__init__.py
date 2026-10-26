"""Compatibility package exposing the backend routes."""

import os

_BACKEND_ROUTES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "routes",
)

__path__ = [_BACKEND_ROUTES]
