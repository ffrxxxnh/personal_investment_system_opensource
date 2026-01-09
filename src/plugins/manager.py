# Plugin Manager
# src/plugins/manager.py

"""
Plugin discovery, loading, and lifecycle management.

The PluginManager handles:
- Discovering plugins in the plugins directory
- Validating plugin manifests and code safety
- Loading and instantiating plugin connectors
- Managing plugin lifecycle (enable/disable/uninstall)
"""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

import yaml

from .base import BankIntegrationPlugin, PluginMetadata, PluginCapability
from .registry import PluginRegistry

logger = logging.getLogger(__name__)

# Modules that plugins are NOT allowed to import (security)
BLOCKED_IMPORTS = {
    'subprocess', 'os.system', 'eval', 'exec', 'compile',
    'ctypes', 'multiprocessing', 'socket', 'pickle'
}

# Default plugins directory relative to src/
DEFAULT_PLUGINS_DIR = "plugins/bank_plugins"


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""
    pass


class PluginValidationError(Exception):
    """Raised when plugin validation fails."""
    pass


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    The PluginManager scans the plugins directory for valid plugins,
    validates their manifests, and loads them into the registry.

    Example:
        manager = PluginManager()
        manager.discover_plugins()

        # List available plugins
        for plugin in manager.list_plugins():
            print(f"{plugin.name} v{plugin.version}")

        # Load and use a plugin
        connector = manager.load_plugin("icbc", config={"username": "...", "password": "..."})
        connector.authenticate()
        holdings = connector.get_holdings()

    Attributes:
        plugins_dir: Path to plugins directory
        registry: PluginRegistry instance
        _discovered: Cache of discovered plugin metadata
    """

    def __init__(
        self,
        plugins_dir: Optional[str] = None,
        registry: Optional[PluginRegistry] = None
    ):
        """
        Initialize plugin manager.

        Args:
            plugins_dir: Path to plugins directory (default: src/plugins/bank_plugins)
            registry: Optional PluginRegistry instance (creates new if not provided)
        """
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir)
        else:
            # Default to src/plugins/bank_plugins
            src_dir = Path(__file__).parent.parent
            self.plugins_dir = src_dir / "plugins" / "bank_plugins"

        self.registry = registry or PluginRegistry()
        self._discovered: Dict[str, Dict[str, Any]] = {}

    def discover_plugins(self, force_refresh: bool = False) -> List[PluginMetadata]:
        """
        Discover all plugins in the plugins directory.

        Scans for directories containing a manifest.yaml file and validates
        the plugin structure.

        Args:
            force_refresh: If True, re-scan even if already discovered

        Returns:
            List of PluginMetadata for discovered plugins
        """
        if self._discovered and not force_refresh:
            return [info['metadata'] for info in self._discovered.values()]

        self._discovered.clear()
        discovered_plugins = []

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return []

        logger.info(f"Scanning for plugins in {self.plugins_dir}")

        for entry in self.plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.startswith('_') or entry.name.startswith('.'):
                continue

            manifest_path = entry / "manifest.yaml"
            if not manifest_path.exists():
                logger.debug(f"Skipping {entry.name}: no manifest.yaml")
                continue

            try:
                plugin_info = self._load_manifest(manifest_path, entry)
                self._discovered[plugin_info['metadata'].id] = plugin_info
                discovered_plugins.append(plugin_info['metadata'])
                logger.info(f"Discovered plugin: {plugin_info['metadata'].name} v{plugin_info['metadata'].version}")
            except Exception as e:
                logger.error(f"Failed to load plugin {entry.name}: {e}")

        # Register discovered plugins
        for metadata in discovered_plugins:
            self.registry.register(metadata)

        return discovered_plugins

    def _load_manifest(self, manifest_path: Path, plugin_dir: Path) -> Dict[str, Any]:
        """
        Load and validate a plugin manifest.

        Args:
            manifest_path: Path to manifest.yaml
            plugin_dir: Plugin directory path

        Returns:
            Dictionary with plugin info including metadata

        Raises:
            PluginValidationError: If manifest is invalid
        """
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)

        # Validate required fields
        required_fields = ['id', 'name', 'version', 'author', 'description']
        for field in required_fields:
            if field not in manifest:
                raise PluginValidationError(f"Missing required field: {field}")

        # Parse capabilities
        capabilities = []
        for cap_str in manifest.get('capabilities', []):
            try:
                capabilities.append(PluginCapability[cap_str.upper()])
            except KeyError:
                logger.warning(f"Unknown capability: {cap_str}")

        # Create metadata
        metadata = PluginMetadata(
            id=manifest['id'],
            name=manifest['name'],
            version=manifest['version'],
            author=manifest['author'],
            description=manifest['description'],
            capabilities=capabilities,
            supported_countries=manifest.get('supported_countries', []),
            authentication_type=manifest.get('authentication_type', 'api_key'),
            required_fields=manifest.get('required_fields', []),
            optional_fields=manifest.get('optional_fields', []),
            documentation_url=manifest.get('documentation_url'),
            icon_url=manifest.get('icon_url'),
            min_system_version=manifest.get('min_system_version'),
        )

        return {
            'metadata': metadata,
            'path': plugin_dir,
            'manifest': manifest,
        }

    def list_plugins(self) -> List[PluginMetadata]:
        """
        List all discovered plugins.

        Returns:
            List of PluginMetadata for all plugins
        """
        if not self._discovered:
            self.discover_plugins()
        return [info['metadata'] for info in self._discovered.values()]

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Dictionary with plugin info or None if not found
        """
        if not self._discovered:
            self.discover_plugins()
        return self._discovered.get(plugin_id)

    def load_plugin(
        self,
        plugin_id: str,
        config: Dict[str, Any]
    ) -> BankIntegrationPlugin:
        """
        Load and instantiate a plugin connector.

        Args:
            plugin_id: Plugin identifier
            config: Configuration dictionary for the plugin

        Returns:
            Instantiated plugin connector

        Raises:
            PluginLoadError: If plugin cannot be loaded
            PluginValidationError: If plugin code is unsafe
        """
        if not self._discovered:
            self.discover_plugins()

        if plugin_id not in self._discovered:
            raise PluginLoadError(f"Plugin not found: {plugin_id}")

        plugin_info = self._discovered[plugin_id]
        plugin_dir = plugin_info['path']

        # Load the connector module
        connector_path = plugin_dir / "connector.py"
        if not connector_path.exists():
            raise PluginLoadError(f"Plugin connector not found: {connector_path}")

        # Validate code safety
        self._validate_plugin_code(connector_path)

        # Dynamically import the module
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_id}",
                connector_path
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Failed to create module spec for {plugin_id}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the connector class
            connector_class = self._find_connector_class(module)
            if connector_class is None:
                raise PluginLoadError(f"No BankIntegrationPlugin subclass found in {plugin_id}")

            # Instantiate and return
            return connector_class(config)

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            raise PluginLoadError(f"Plugin load failed: {e}") from e

    def _validate_plugin_code(self, connector_path: Path) -> None:
        """
        Validate plugin code for safety.

        Args:
            connector_path: Path to connector.py

        Raises:
            PluginValidationError: If code contains blocked patterns
        """
        with open(connector_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check for blocked imports/patterns
        for blocked in BLOCKED_IMPORTS:
            if blocked in code:
                raise PluginValidationError(
                    f"Plugin contains blocked pattern: {blocked}"
                )

        logger.debug(f"Plugin code validation passed: {connector_path}")

    def _find_connector_class(
        self,
        module: Any
    ) -> Optional[Type[BankIntegrationPlugin]]:
        """
        Find the BankIntegrationPlugin subclass in a module.

        Args:
            module: Loaded Python module

        Returns:
            Plugin class or None if not found
        """
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type) and
                issubclass(obj, BankIntegrationPlugin) and
                obj is not BankIntegrationPlugin
            ):
                return obj
        return None

    def validate_plugin(self, plugin_id: str) -> Tuple[bool, List[str]]:
        """
        Validate a plugin's structure and code.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Tuple of (valid: bool, issues: List[str])
        """
        issues = []

        if plugin_id not in self._discovered:
            return False, [f"Plugin not found: {plugin_id}"]

        plugin_info = self._discovered[plugin_id]
        plugin_dir = plugin_info['path']

        # Check required files
        required_files = ['connector.py', 'manifest.yaml', '__init__.py']
        for filename in required_files:
            if not (plugin_dir / filename).exists():
                issues.append(f"Missing required file: {filename}")

        # Check connector
        connector_path = plugin_dir / "connector.py"
        if connector_path.exists():
            try:
                self._validate_plugin_code(connector_path)
            except PluginValidationError as e:
                issues.append(str(e))

        return len(issues) == 0, issues
