"""Retrieval-Augmented Generation: Wikichess knowledge base preprocessing.

This package turns the curated Markdown opening articles (``data/openings``)
into embedded, searchable chunks stored in Milvus. The flow is intentionally
explicit and sequential:

    load articles  ->  chunk text  ->  embed chunks  ->  index in Milvus
"""

from __future__ import annotations
