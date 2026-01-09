# Plugin Base Class
# src/plugins/base.py

"""
Base classes for plugin development.

Provides the abstract BankIntegrationPlugin class that community plugins
must extend, along with metadata and capability definitions.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.data_manager.connectors.base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorType,
)


class PluginCapability(Enum):
    """Capabilities that plugins can provide."""
    HOLDINGS = auto()           # Can fetch current holdings
    TRANSACTIONS = auto()       # Can fetch transaction history
    BALANCES = auto()           # Can fetch account balances
    TRANSFERS = auto()          # Can initiate transfers (rare)
    STATEMENTS = auto()         # Can download statements
    REAL_TIME = auto()          # Supports real-time updates


@dataclass
class PluginMetadata:
    """
    Metadata about a plugin.

    This information is typically loaded from the plugin's manifest.yaml
    and used for display in the plugin library UI.

    Attributes:
        id: Unique plugin identifier (e.g., "icbc", "chase")
        name: Display name (e.g., "ICBC Bank Integration")
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author name or organization
        description: Brief description of the plugin
        capabilities: List of PluginCapability values
        supported_countries: ISO country codes (e.g., ["CN", "US"])
        authentication_type: Type of auth ("api_key", "oauth", "credentials")
        required_fields: Config fields required for authentication
        optional_fields: Optional config fields
        documentation_url: Link to setup documentation
        icon_url: Optional plugin icon URL
        min_system_version: Minimum system version required
    """
    id: str
    name: str
    version: str
    author: str
    description: str
    capabilities: List[PluginCapability] = field(default_factory=list)
    supported_countries: List[str] = field(default_factory=list)
    authentication_type: str = "api_key"
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None
    min_system_version: Optional[str] = None


class BankIntegrationPlugin(BaseConnector):
    """
    Abstract base class for bank integration plugins.

    Extends BaseConnector with plugin-specific functionality including
    manifest loading, capability checking, and enhanced authentication.

    Plugin developers should:
    1. Create a subclass of BankIntegrationPlugin
    2. Define plugin_metadata class attribute
    3. Implement required abstract methods
    4. Create a manifest.yaml file

    Example:
        class ICBCPlugin(BankIntegrationPlugin):
            plugin_metadata = PluginMetadata(
                id="icbc",
                name="ICBC Bank Integration",
                version="1.0.0",
                author="Community",
                description="Connect to ICBC online banking",
                capabilities=[PluginCapability.HOLDINGS, PluginCapability.TRANSACTIONS],
                supported_countries=["CN"],
                authentication_type="credentials",
                required_fields=["username", "password"],
            )

            def authenticate(self) -> Tuple[bool, str]:
                # Implementation
                pass

            def get_holdings(self, account_id=None) -> Optional[pd.DataFrame]:
                # Implementation
                pass

            def get_transactions(self, account_id=None, since_date=None, until_date=None) -> Optional[pd.DataFrame]:
                # Implementation
                pass
    """

    # Plugin metadata - must be defined by subclass
    plugin_metadata: PluginMetadata

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin with configuration.

        Args:
            config: Dictionary containing authentication credentials
                   and plugin-specific settings.
        """
        # Create connector metadata from plugin metadata
        self.metadata = ConnectorMetadata(
            name=self.plugin_metadata.name,
            connector_type=ConnectorType.PLUGIN,
            version=self.plugin_metadata.version,
            description=self.plugin_metadata.description,
            supported_assets=["bank_account", "deposits"],
            requires_oauth=self.plugin_metadata.authentication_type == "oauth",
            requires_api_key=self.plugin_metadata.authentication_type == "api_key",
            documentation_url=self.plugin_metadata.documentation_url,
        )
        super().__init__(config)

    @property
    def plugin_id(self) -> str:
        """Get the unique plugin identifier."""
        return self.plugin_metadata.id

    @property
    def capabilities(self) -> List[PluginCapability]:
        """Get list of plugin capabilities."""
        return self.plugin_metadata.capabilities

    def has_capability(self, capability: PluginCapability) -> bool:
        """
        Check if plugin has a specific capability.

        Args:
            capability: The capability to check for

        Returns:
            True if plugin supports the capability
        """
        return capability in self.capabilities

    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate plugin configuration.

        Returns:
            Tuple of (valid: bool, missing_fields: List[str])
        """
        missing = []
        for field in self.plugin_metadata.required_fields:
            if field not in self.config or not self.config.get(field):
                missing.append(field)

        return len(missing) == 0, missing

    @abstractmethod
    def authenticate(self) -> Tuple[bool, str]:
        """Authenticate with the bank service."""
        pass

    @abstractmethod
    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Fetch current account balances/holdings."""
        pass

    @abstractmethod
    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[Any] = None,
        until_date: Optional[Any] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transaction history."""
        pass

    def get_balances(self, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get account balances (optional).

        Args:
            account_id: Optional specific account to query

        Returns:
            Dictionary with balance information or None
        """
        if not self.has_capability(PluginCapability.BALANCES):
            return None
        return None

    def logout(self) -> bool:
        """
        Logout from the bank service.

        Returns:
            True if logout successful
        """
        return self.disconnect()

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for the plugin.

        Returns:
            Dictionary describing required and optional fields
        """
        return {
            "required": self.plugin_metadata.required_fields,
            "optional": self.plugin_metadata.optional_fields,
            "authentication_type": self.plugin_metadata.authentication_type,
        }
