# Plugin Registry
# src/plugins/registry.py

"""
Central registry for tracking available and enabled plugins.

The PluginRegistry acts as a central database of plugin information,
tracking which plugins are discovered, enabled, and configured.
"""

import logging
from threading import Lock
from typing import Dict, List, Optional, Set

from .base import PluginMetadata, PluginCapability

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry of available plugins.

    The registry is a singleton that tracks all discovered plugins and
    their current status. It provides methods for querying plugins by
    various criteria.

    Example:
        registry = PluginRegistry()

        # Register a plugin
        registry.register(plugin_metadata)

        # Query plugins
        bank_plugins = registry.get_by_type(PluginCapability.HOLDINGS)
        us_plugins = registry.get_by_country("US")

        # Check status
        if registry.is_enabled("icbc"):
            connector = manager.load_plugin("icbc", config)

    Attributes:
        _plugins: Dictionary mapping plugin_id to PluginMetadata
        _enabled: Set of enabled plugin IDs
        _lock: Thread lock for concurrent access
    """

    _instance: Optional['PluginRegistry'] = None
    _lock: Lock = Lock()

    def __new__(cls) -> 'PluginRegistry':
        """Singleton pattern - return existing instance or create new."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._plugins: Dict[str, PluginMetadata] = {}
                cls._instance._enabled: Set[str] = set()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._plugins.clear()
                cls._instance._enabled.clear()

    def register(self, metadata: PluginMetadata) -> bool:
        """
        Register a plugin in the registry.

        Args:
            metadata: Plugin metadata to register

        Returns:
            True if newly registered, False if already existed
        """
        if metadata.id in self._plugins:
            logger.debug(f"Plugin already registered: {metadata.id}")
            return False

        self._plugins[metadata.id] = metadata
        logger.info(f"Registered plugin: {metadata.name} ({metadata.id})")
        return True

    def unregister(self, plugin_id: str) -> bool:
        """
        Remove a plugin from the registry.

        Args:
            plugin_id: Plugin identifier to remove

        Returns:
            True if removed, False if not found
        """
        if plugin_id not in self._plugins:
            return False

        del self._plugins[plugin_id]
        self._enabled.discard(plugin_id)
        logger.info(f"Unregistered plugin: {plugin_id}")
        return True

    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginMetadata or None if not found
        """
        return self._plugins.get(plugin_id)

    def get_all(self) -> List[PluginMetadata]:
        """
        Get all registered plugins.

        Returns:
            List of all PluginMetadata
        """
        return list(self._plugins.values())

    def get_by_capability(self, capability: PluginCapability) -> List[PluginMetadata]:
        """
        Get plugins with a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of plugins with the capability
        """
        return [
            meta for meta in self._plugins.values()
            if capability in meta.capabilities
        ]

    def get_by_country(self, country_code: str) -> List[PluginMetadata]:
        """
        Get plugins supporting a specific country.

        Args:
            country_code: ISO country code (e.g., "US", "CN")

        Returns:
            List of plugins supporting the country
        """
        return [
            meta for meta in self._plugins.values()
            if country_code in meta.supported_countries
        ]

    def get_by_auth_type(self, auth_type: str) -> List[PluginMetadata]:
        """
        Get plugins by authentication type.

        Args:
            auth_type: Authentication type ("api_key", "oauth", "credentials")

        Returns:
            List of plugins using that auth type
        """
        return [
            meta for meta in self._plugins.values()
            if meta.authentication_type == auth_type
        ]

    def enable(self, plugin_id: str) -> bool:
        """
        Mark a plugin as enabled.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if enabled, False if plugin not found
        """
        if plugin_id not in self._plugins:
            return False
        self._enabled.add(plugin_id)
        logger.debug(f"Enabled plugin: {plugin_id}")
        return True

    def disable(self, plugin_id: str) -> bool:
        """
        Mark a plugin as disabled.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if disabled, False if not found/not enabled
        """
        if plugin_id not in self._enabled:
            return False
        self._enabled.discard(plugin_id)
        logger.debug(f"Disabled plugin: {plugin_id}")
        return True

    def is_enabled(self, plugin_id: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if plugin exists and is enabled
        """
        return plugin_id in self._enabled

    def get_enabled(self) -> List[PluginMetadata]:
        """
        Get all enabled plugins.

        Returns:
            List of enabled PluginMetadata
        """
        return [
            self._plugins[pid] for pid in self._enabled
            if pid in self._plugins
        ]

    def count(self) -> int:
        """Get total number of registered plugins."""
        return len(self._plugins)

    def count_enabled(self) -> int:
        """Get number of enabled plugins."""
        return len(self._enabled)

    def stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with counts by category
        """
        return {
            "total": self.count(),
            "enabled": self.count_enabled(),
            "disabled": self.count() - self.count_enabled(),
        }
