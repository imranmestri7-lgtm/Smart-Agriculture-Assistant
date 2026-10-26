"""Compatibility package exposing the backend utilities."""

import os

_BACKEND_UTILS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "utils",
)

__path__ = [_BACKEND_UTILS]
