"""FastAPI application layer for Chess Coach.

This layer stays deliberately thin: routes parse the request, delegate to the
services / agent layers, and serialise the result. No business logic lives here.
"""

from __future__ import annotations
