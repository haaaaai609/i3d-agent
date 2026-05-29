"""
Memory storage abstractions for i3d-agent-system.

This module defines abstract base classes for memory storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryStore(ABC):
    """
    Abstract base class for memory storage backends.

    Provides a simple key-value interface for storing and retrieving
    memory data with TTL support.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from memory.

        Args:
            key: The key to retrieve

        Returns:
            The stored value or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in memory.

        Args:
            key: The key to store under
            value: The value to store
            ttl: Optional time-to-live in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from memory.

        Args:
            key: The key to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in memory.

        Args:
            key: The key to check

        Returns:
            True if exists, False otherwise
        """
        pass


class VectorStore(ABC):
    """
    Abstract base class for vector storage backends.

    Provides semantic memory capabilities through vector search.
    This is a stub for future pgvector integration.
    """

    @abstractmethod
    def add(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """
        Add vectors to the store.

        Args:
            vectors: List of vector embeddings
            metadata: List of metadata dicts for each vector
        """
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: The query vector embedding
            top_k: Number of results to return

        Returns:
            List of results with metadata and similarity scores
        """
        pass
