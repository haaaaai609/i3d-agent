"""
Unified memory manager for i3d-agent-system.

This module provides a centralized memory management system using Redis
for short-term memory with stubs for long-term semantic memory.
"""

import json
from typing import Any, Dict, List, Optional

import redis
from redis import Redis

from i3d_agent.config.settings import get_settings
from i3d_agent.memory.store import MemoryStore


class RedisMemoryStore(MemoryStore):
    """
    Redis-based memory store implementation.

    Provides key-value storage with JSON serialization for complex types.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis memory store.

        Args:
            redis_url: Optional Redis connection URL
        """
        settings = get_settings()
        self._redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        """Get or create Redis client (lazy initialization)."""
        if self._client is None:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory."""
        value = self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value in memory."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.client.set(key, value, ex=ttl)

    def delete(self, key: str) -> bool:
        """Delete a value from memory."""
        return bool(self.client.delete(key))

    def exists(self, key: str) -> bool:
        """Check if a key exists in memory."""
        return bool(self.client.exists(key))

    def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            self._client.close()
            self._client = None


class MemoryManager:
    """
    Unified memory manager for the agent system.

    Provides different memory types with appropriate TTL:
    - Working memory (context): Short-lived, per-session
    - Short-term memory (preferences, search history): Hours to days
    - Long-term memory (semantic): Persistent (stub for now)
    """

    # TTL constants (in seconds)
    WORKING_MEMORY_TTL = 3600  # 1 hour
    SHORT_TERM_MEMORY_TTL = 86400  # 24 hours
    LONG_TERM_MEMORY_TTL = None  # No expiration

    # Key prefixes for different memory types
    CONTEXT_PREFIX = "memory:context:"
    PREFERENCE_PREFIX = "memory:preference:"
    SEARCH_HISTORY_PREFIX = "memory:search:"
    SEMANTIC_PREFIX = "memory:semantic:"

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize memory manager.

        Args:
            store: Optional MemoryStore implementation (defaults to RedisMemoryStore)
        """
        self._store = store or RedisMemoryStore()

    @property
    def store(self) -> MemoryStore:
        """Get the underlying memory store."""
        return self._store

    def _make_key(self, prefix: str, user_id: str, identifier: str = "") -> str:
        """
        Create a namespaced key.

        Args:
            prefix: Key prefix
            user_id: User identifier
            identifier: Optional additional identifier

        Returns:
            Full key string
        """
        if identifier:
            return f"{prefix}{user_id}:{identifier}"
        return f"{prefix}{user_id}"

    # Working Memory (Context)

    def set_context(self, user_id: str, context: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Store working memory context for a user.

        Args:
            user_id: User identifier
            context: Context data to store
            ttl: Optional TTL in seconds (defaults to WORKING_MEMORY_TTL)
        """
        key = self._make_key(self.CONTEXT_PREFIX, user_id)
        ttl = ttl if ttl is not None else self.WORKING_MEMORY_TTL
        self.store.set(key, context, ttl)

    def get_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve working memory context for a user.

        Args:
            user_id: User identifier

        Returns:
            Context data or None if not found
        """
        key = self._make_key(self.CONTEXT_PREFIX, user_id)
        return self.store.get(key)

    # Short-term Memory (Preferences)

    def set_user_preference(self, user_id: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a user preference.

        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value
            ttl: Optional TTL in seconds (defaults to SHORT_TERM_MEMORY_TTL)
        """
        full_key = self._make_key(self.PREFERENCE_PREFIX, user_id, key)
        ttl = ttl if ttl is not None else self.SHORT_TERM_MEMORY_TTL
        self.store.set(full_key, value, ttl)

    def get_user_preference(self, user_id: str, key: str) -> Optional[Any]:
        """
        Retrieve a user preference.

        Args:
            user_id: User identifier
            key: Preference key

        Returns:
            Preference value or None if not found
        """
        full_key = self._make_key(self.PREFERENCE_PREFIX, user_id, key)
        return self.store.get(full_key)

    # Short-term Memory (Search History)

    def add_search_history(self, user_id: str, query: str, results: Optional[List[Dict]] = None, ttl: Optional[int] = None) -> None:
        """
        Add a search query to user history.

        Args:
            user_id: User identifier
            query: Search query string
            results: Optional search results
            ttl: Optional TTL in seconds (defaults to SHORT_TERM_MEMORY_TTL)
        """
        key = self._make_key(self.SEARCH_HISTORY_PREFIX, user_id)
        ttl = ttl if ttl is not None else self.SHORT_TERM_MEMORY_TTL

        # Get existing history
        history = self.store.get(key) or []
        history.insert(0, {"query": query, "results": results, "timestamp": None})

        # Keep only last 100 entries
        history = history[:100]

        self.store.set(key, history, ttl)

    def get_recent_searches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent search queries for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of searches to return

        Returns:
            List of recent searches (most recent first)
        """
        key = self._make_key(self.SEARCH_HISTORY_PREFIX, user_id)
        history = self.store.get(key) or []
        return history[:limit]

    # Long-term Memory (Semantic) - Stubs for pgvector integration

    def store_semantic_memory(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store semantic memory (stub for pgvector integration).

        Args:
            user_id: User identifier
            text: Text content to store
            metadata: Optional metadata

        Returns:
            Memory ID (placeholder for now)
        """
        # TODO: Integrate with pgvector
        # This is a stub that stores in Redis temporarily
        key = self._make_key(self.SEMANTIC_PREFIX, user_id, "stub")
        existing = self.store.get(key) or []
        entry = {
            "id": f"semantic_{len(existing)}",
            "text": text,
            "metadata": metadata or {},
            "timestamp": None
        }
        existing.append(entry)
        self.store.set(key, existing)
        return entry["id"]

    def retrieve_semantic_memory(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve semantic memory by similarity (stub for pgvector integration).

        Args:
            user_id: User identifier
            query: Query text
            limit: Maximum results

        Returns:
            List of similar memories (placeholder for now)
        """
        # TODO: Implement vector search with pgvector
        # This stub returns empty list for now
        return []
