# Base Connector Interface
# src/data_manager/connectors/base_connector.py

"""
Abstract base classes for all data source connectors.

This module provides the foundation for building connectors to external
data sources including brokers, crypto exchanges, banks, and market data
providers. All connectors must implement the BaseConnector interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class ConnectorType(Enum):
    """Types of data source connectors."""
    BROKER = "broker"           # Schwab, IBKR, Fidelity
    CRYPTO_EXCHANGE = "crypto"  # Binance, Coinbase, Kraken
    MARKET_DATA = "market"      # Tiingo, Yahoo, Alpha Vantage
    BANK = "bank"               # ICBC, Chase, Wells Fargo
    PLUGIN = "plugin"           # Community-contributed


@dataclass
class ConnectorMetadata:
    """Metadata about a connector."""
    name: str
    connector_type: ConnectorType
    version: str
    description: str
    supported_assets: List[str] = field(default_factory=list)  # e.g., ["stocks", "etfs", "crypto"]
    requires_oauth: bool = False
    requires_api_key: bool = True
    rate_limit_per_minute: int = 60
    documentation_url: Optional[str] = None


# =============================================================================
# EXCEPTION CLASSES
# =============================================================================

class ConnectorError(Exception):
    """Base exception for all connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Raised when authentication with a data source fails."""
    def __init__(self, message: str, source: Optional[str] = None):
        self.source = source
        super().__init__(f"[{source}] {message}" if source else message)


class RateLimitError(ConnectorError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class DataFetchError(ConnectorError):
    """Raised when data fetching fails."""
    def __init__(self, message: str, source: Optional[str] = None, endpoint: Optional[str] = None):
        self.source = source
        self.endpoint = endpoint
        details = []
        if source:
            details.append(f"source={source}")
        if endpoint:
            details.append(f"endpoint={endpoint}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")


class ConfigurationError(ConnectorError):
    """Raised when connector configuration is invalid."""
    pass


# =============================================================================
# STANDARD COLUMN DEFINITIONS
# =============================================================================

# Standard columns for holdings DataFrame
HOLDINGS_COLUMNS = [
    'symbol',          # str - Ticker/symbol
    'name',            # str - Asset name
    'quantity',        # float - Number of shares/units
    'current_price',   # float - Latest price
    'market_value',    # float - quantity * current_price
    'cost_basis',      # float - Total cost (optional)
    'currency',        # str - Currency code (USD, CNY, etc.)
    'account_id',      # str - Source account (optional)
]

# Standard columns for transactions DataFrame
TRANSACTION_COLUMNS = [
    'date',              # datetime - Transaction date
    'symbol',            # str - Ticker/symbol
    'name',              # str - Asset name
    'transaction_type',  # str - Standard type (Buy, Sell, Dividend, etc.)
    'quantity',          # float - Number of shares/units
    'price',             # float - Price per unit
    'amount',            # float - Total amount (quantity * price)
    'currency',          # str - Currency code
    'fees',              # float - Transaction fees (optional)
    'source_id',         # str - Unique ID from source (for deduplication)
    'account_id',        # str - Source account (optional)
]

# Standard transaction types
TRANSACTION_TYPES = {
    'Buy': 'Purchase of asset',
    'Sell': 'Sale of asset',
    'Dividend': 'Dividend payment received',
    'Interest': 'Interest payment received',
    'Deposit': 'Cash/asset deposit',
    'Withdrawal': 'Cash/asset withdrawal',
    'Transfer': 'Internal transfer',
    'Fee': 'Transaction fee',
    'Split': 'Stock split',
    'Merger': 'Merger/acquisition',
}


# =============================================================================
# BASE CONNECTOR CLASS
# =============================================================================

class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    All connectors must implement:
    - authenticate(): Verify credentials and establish connection
    - get_holdings(): Fetch current portfolio holdings
    - get_transactions(): Fetch transaction history

    Optional overrides:
    - health_check(): Verify service availability
    - get_account_info(): Get account metadata
    - disconnect(): Clean up resources

    Example:
        class MyBrokerConnector(BaseConnector):
            metadata = ConnectorMetadata(
                name="My Broker",
                connector_type=ConnectorType.BROKER,
                version="1.0.0",
                description="Connect to My Broker API"
            )

            def authenticate(self) -> Tuple[bool, str]:
                # Implementation here
                pass

            def get_holdings(self, account_id=None) -> Optional[pd.DataFrame]:
                # Implementation here
                pass

            def get_transactions(self, account_id=None, since_date=None, until_date=None) -> Optional[pd.DataFrame]:
                # Implementation here
                pass
    """

    metadata: ConnectorMetadata

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.

        Args:
            config: Dictionary containing credentials and settings.
                   Structure varies by connector type but typically includes:
                   - api_key: API key for authentication
                   - api_secret: API secret (if required)
                   - account_numbers: List of account IDs (optional)
                   - sandbox: Use test/sandbox environment (optional)
        """
        self.config = config
        self._authenticated = False
        self._last_request_time: Optional[datetime] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if connector is currently authenticated."""
        return self._authenticated

    @abstractmethod
    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with the data source.

        Returns:
            Tuple of (success: bool, message: str)
            - success: True if authentication succeeded
            - message: Human-readable status message

        Raises:
            AuthenticationError: If authentication fails with specific error
        """
        pass

    @abstractmethod
    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch current holdings/positions.

        Args:
            account_id: Optional account identifier (for multi-account sources)

        Returns:
            DataFrame with columns:
            - symbol: str - Ticker/symbol
            - name: str - Asset name
            - quantity: float - Number of shares/units
            - current_price: float - Latest price
            - market_value: float - quantity * current_price
            - cost_basis: float - Total cost (optional)
            - currency: str - Currency code (USD, CNY, etc.)
            - account_id: str - Source account (optional)

            Returns None if fetch fails or no holdings.

        Raises:
            DataFetchError: If API call fails
            RateLimitError: If rate limit exceeded
        """
        pass

    @abstractmethod
    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transaction history.

        Args:
            account_id: Optional account identifier
            since_date: Start date for transaction range
            until_date: End date for transaction range

        Returns:
            DataFrame with columns:
            - date: datetime - Transaction date
            - symbol: str - Ticker/symbol
            - name: str - Asset name
            - transaction_type: str - Standard type (Buy, Sell, Dividend, etc.)
            - quantity: float - Number of shares/units
            - price: float - Price per unit
            - amount: float - Total amount (quantity * price)
            - currency: str - Currency code
            - fees: float - Transaction fees (optional)
            - source_id: str - Unique ID from source (for deduplication)
            - account_id: str - Source account (optional)

            Returns None if fetch fails or no transactions.

        Raises:
            DataFetchError: If API call fails
            RateLimitError: If rate limit exceeded
        """
        pass

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account metadata (optional override).

        Returns:
            Dictionary with account information:
            - account_id: str
            - account_type: str (Individual, Joint, IRA, etc.)
            - base_currency: str
            - status: str
            - nickname: str (optional)
        """
        return None

    def health_check(self) -> Tuple[bool, str]:
        """
        Check if the data source is available.

        Returns:
            Tuple of (healthy: bool, message: str)
        """
        return True, "OK"

    def disconnect(self) -> bool:
        """
        Clean up resources and logout.

        Returns:
            True if successful
        """
        self._authenticated = False
        return True

    def _validate_config(self, required_keys: List[str]) -> None:
        """
        Helper to validate required config keys are present.

        Args:
            required_keys: List of required configuration keys

        Raises:
            ConfigurationError: If any required keys are missing
        """
        missing = [k for k in required_keys if k not in self.config or not self.config[k]]
        if missing:
            raise ConfigurationError(f"Missing required config keys: {missing}")

    def _create_empty_holdings_df(self) -> pd.DataFrame:
        """Create an empty DataFrame with standard holdings columns."""
        return pd.DataFrame(columns=HOLDINGS_COLUMNS)

    def _create_empty_transactions_df(self) -> pd.DataFrame:
        """Create an empty DataFrame with standard transaction columns."""
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)
