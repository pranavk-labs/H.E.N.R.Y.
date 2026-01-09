"""Simple in-memory cache service with optional TTL.

This is intentionally lightweight and local-only; it's mainly here to
establish the service pattern for caching frequently accessed data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: Optional[float]  # UNIX timestamp or None for no expiry


class CacheService:
    """Basic process-local cache service."""

    _instance: Optional["CacheService"] = None

    def __init__(self) -> None:
        self._store: Dict[str, CacheEntry] = {}

    @classmethod
    def get_instance(cls) -> "CacheService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        self._store[key] = CacheEntry(value=value, expires_at=expires_at)

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at < time.time():
            # Expired
            self._store.pop(key, None)
            return None
        return entry.value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


__all__ = ["CacheService"]


