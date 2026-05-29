"""
Tests for memory manager.

Following TDD approach - tests validate memory functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock

from i3d_agent.memory.manager import MemoryManager, RedisMemoryStore
from i3d_agent.memory.store import MemoryStore


class MockMemoryStore(MemoryStore):
    """Mock memory store for testing."""

    def __init__(self):
        self._data = {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value, ttl=None):
        self._data[key] = value

    def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str):
        return key in self._data


class TestMemoryStore:
    """Test MemoryStore ABC implementation."""

    def test_mock_store_get(self):
        """Test mock store get method."""
        store = MockMemoryStore()
        store.set("test_key", "test_value")
        assert store.get("test_key") == "test_value"

    def test_mock_store_get_missing(self):
        """Test mock store returns None for missing key."""
        store = MockMemoryStore()
        assert store.get("missing_key") is None

    def test_mock_store_set(self):
        """Test mock store set method."""
        store = MockMemoryStore()
        store.set("key", "value")
        assert "key" in store._data

    def test_mock_store_delete(self):
        """Test mock store delete method."""
        store = MockMemoryStore()
        store.set("key", "value")
        assert store.delete("key") is True
        assert store.delete("key") is False

    def test_mock_store_exists(self):
        """Test mock store exists method."""
        store = MockMemoryStore()
        assert store.exists("key") is False
        store.set("key", "value")
        assert store.exists("key") is True


class TestRedisMemoryStore:
    """Test RedisMemoryStore implementation."""

    def test_redis_store_init(self):
        """Test RedisMemoryStore initialization."""
        store = RedisMemoryStore()
        assert store._redis_url is not None
        assert store._client is None

    def test_redis_store_custom_url(self):
        """Test RedisMemoryStore with custom URL."""
        store = RedisMemoryStore("redis://custom:6379/1")
        assert store._redis_url == "redis://custom:6379/1"

    def test_redis_store_lazy_client(self):
        """Test Redis client is lazily initialized."""
        store = RedisMemoryStore()
        assert store._client is None
        # Accessing client property should create it
        # Note: This will fail without Redis running, but tests initialization


class TestMemoryManager:
    """Test MemoryManager functionality."""

    def test_manager_init_default_store(self):
        """Test MemoryManager initialization with default store."""
        manager = MemoryManager()
        assert isinstance(manager.store, RedisMemoryStore)

    def test_manager_init_custom_store(self):
        """Test MemoryManager with custom store."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)
        assert manager.store is mock_store

    def test_make_key(self):
        """Test internal key generation."""
        manager = MemoryManager()
        key = manager._make_key("test:", "user123", "extra")
        assert key == "test:user123:extra"

        key_no_extra = manager._make_key("test:", "user123")
        assert key_no_extra == "test:user123"


class TestSetContext:
    """Test set_context working memory method."""

    def test_set_context(self):
        """Test storing context data."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        context = {"session_id": "123", "state": "active"}
        manager.set_context("user1", context)

        retrieved = mock_store.get("memory:context:user1")
        assert retrieved == context

    def test_set_context_with_custom_ttl(self):
        """Test storing context with custom TTL."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        context = {"key": "value"}
        manager.set_context("user1", context, ttl=100)

        # Verify TTL was passed to store (we can't verify actual value in mock)
        assert "memory:context:user1" in mock_store._data

    def test_set_context_overwrite(self):
        """Test that set_context overwrites existing context."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.set_context("user1", {"old": "data"})
        manager.set_context("user1", {"new": "data"})

        retrieved = mock_store.get("memory:context:user1")
        assert retrieved == {"new": "data"}


class TestGetContext:
    """Test get_context working memory method."""

    def test_get_context(self):
        """Test retrieving context data."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        context = {"session_id": "123", "state": "active"}
        mock_store.set("memory:context:user1", context)

        retrieved = manager.get_context("user1")
        assert retrieved == context

    def test_get_context_missing(self):
        """Test get_context returns None for missing data."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        retrieved = manager.get_context("nonexistent")
        assert retrieved is None


class TestSetUserPreference:
    """Test set_user_preference short-term memory method."""

    def test_set_user_preference(self):
        """Test storing user preference."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.set_user_preference("user1", "theme", "dark")

        retrieved = mock_store.get("memory:preference:user1:theme")
        assert retrieved == "dark"

    def test_set_user_preference_complex_value(self):
        """Test storing complex preference value."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        pref_value = {"colors": ["blue", "green"], "size": "large"}
        manager.set_user_preference("user1", "display", pref_value)

        retrieved = mock_store.get("memory:preference:user1:display")
        assert retrieved == pref_value

    def test_set_user_preference_with_custom_ttl(self):
        """Test storing preference with custom TTL."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.set_user_preference("user1", "key", "value", ttl=7200)

        assert "memory:preference:user1:key" in mock_store._data


class TestGetUserPreference:
    """Test get_user_preference short-term memory method."""

    def test_get_user_preference(self):
        """Test retrieving user preference."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        mock_store.set("memory:preference:user1:theme", "light")

        retrieved = manager.get_user_preference("user1", "theme")
        assert retrieved == "light"

    def test_get_user_preference_missing(self):
        """Test get_user_preference returns None for missing data."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        retrieved = manager.get_user_preference("user1", "missing")
        assert retrieved is None

    def test_get_user_preference_different_users(self):
        """Test preferences are isolated per user."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        mock_store.set("memory:preference:user1:theme", "dark")
        mock_store.set("memory:preference:user2:theme", "light")

        assert manager.get_user_preference("user1", "theme") == "dark"
        assert manager.get_user_preference("user2", "theme") == "light"


class TestAddSearchHistory:
    """Test add_search_history short-term memory method."""

    def test_add_search_history(self):
        """Test adding search to history."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.add_search_history("user1", "test query")

        history = mock_store.get("memory:search:user1")
        assert len(history) == 1
        assert history[0]["query"] == "test query"

    def test_add_search_history_with_results(self):
        """Test adding search with results."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        results = [{"id": 1, "title": "Result 1"}]
        manager.add_search_history("user1", "test query", results)

        history = mock_store.get("memory:search:user1")
        assert history[0]["results"] == results

    def test_add_search_history_multiple(self):
        """Test adding multiple searches."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.add_search_history("user1", "query1")
        manager.add_search_history("user1", "query2")
        manager.add_search_history("user1", "query3")

        history = mock_store.get("memory:search:user1")
        assert len(history) == 3
        # Most recent first
        assert history[0]["query"] == "query3"
        assert history[1]["query"] == "query2"
        assert history[2]["query"] == "query1"


class TestGetRecentSearches:
    """Test get_recent_searches short-term memory method."""

    def test_get_recent_searches(self):
        """Test retrieving recent searches."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        history = [
            {"query": "query1", "results": None, "timestamp": None},
            {"query": "query2", "results": None, "timestamp": None},
        ]
        mock_store.set("memory:search:user1", history)

        retrieved = manager.get_recent_searches("user1")
        assert len(retrieved) == 2
        assert retrieved[0]["query"] == "query1"

    def test_get_recent_searches_with_limit(self):
        """Test retrieving recent searches with limit."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        history = [
            {"query": f"query{i}", "results": None, "timestamp": None}
            for i in range(10)
        ]
        mock_store.set("memory:search:user1", history)

        retrieved = manager.get_recent_searches("user1", limit=5)
        assert len(retrieved) == 5

    def test_get_recent_searches_empty(self):
        """Test retrieving searches when none exist."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        retrieved = manager.get_recent_searches("user1")
        assert retrieved == []


class TestStoreSemanticMemory:
    """Test store_semantic_memory long-term memory method (stub)."""

    def test_store_semantic_memory(self):
        """Test storing semantic memory (stub)."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        memory_id = manager.store_semantic_memory("user1", "test content")

        # Should return a memory ID
        assert memory_id is not None
        assert memory_id.startswith("semantic_")

    def test_store_semantic_memory_with_metadata(self):
        """Test storing semantic memory with metadata (stub)."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        metadata = {"source": "chat", "importance": "high"}
        memory_id = manager.store_semantic_memory("user1", "content", metadata)

        assert memory_id is not None

    def test_store_semantic_memory_persistence(self):
        """Test semantic memory is stored (stub)."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        manager.store_semantic_memory("user1", "first content")
        manager.store_semantic_memory("user1", "second content")

        # Check stub storage
        stub_data = mock_store.get("memory:semantic:user1:stub")
        assert stub_data is not None
        assert len(stub_data) == 2


class TestRetrieveSemanticMemory:
    """Test retrieve_semantic_memory long-term memory method (stub)."""

    def test_retrieve_semantic_memory(self):
        """Test retrieving semantic memory (stub)."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        results = manager.retrieve_semantic_memory("user1", "test query")

        # Stub returns empty list
        assert results == []

    def test_retrieve_semantic_memory_with_limit(self):
        """Test retrieving semantic memory with limit (stub)."""
        mock_store = MockMemoryStore()
        manager = MemoryManager(mock_store)

        results = manager.retrieve_semantic_memory("user1", "query", limit=10)

        # Stub returns empty list regardless of limit
        assert results == []
