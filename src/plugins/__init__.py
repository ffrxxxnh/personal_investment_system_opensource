# Plugin System
# src/plugins/__init__.py

"""
Plugin system for extensible data integrations.

This module provides the framework for community-contributed data source
connectors (banks, regional brokers, etc.) that can be discovered and
loaded at runtime.

Exports:
    - BankIntegrationPlugin: Base class for bank plugins
    - PluginMetadata: Plugin metadata dataclass
    - PluginManager: Plugin discovery and lifecycle management
    - PluginRegistry: Central registry of available plugins
"""

from .base import BankIntegrationPlugin, PluginMetadata, PluginCapability
from .manager import PluginManager
from .registry import PluginRegistry

__all__ = [
    'BankIntegrationPlugin',
    'PluginMetadata',
    'PluginCapability',
    'PluginManager',
    'PluginRegistry',
]
