# Data Connectors Module
# src/data_manager/connectors/__init__.py

"""
External data source connectors for the Personal Investment System.
Provides interfaces to connect with external financial data providers.

Exports:
    - BaseConnector: Abstract base class for all connectors
    - ConnectorMetadata, ConnectorType: Metadata types
    - ConnectorError, AuthenticationError, RateLimitError, DataFetchError: Exceptions
    - RateLimiter, ResponseCache: Utility classes
    - retry_with_backoff: Retry decorator
    - Broker/Crypto/Market connectors
"""

# Base classes and types
from .base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorType,
    ConnectorError,
    AuthenticationError,
    RateLimitError,
    DataFetchError,
    ConfigurationError,
    HOLDINGS_COLUMNS,
    TRANSACTION_COLUMNS,
    TRANSACTION_TYPES,
)

# Utility classes
from .utils import (
    RateLimiter,
    ResponseCache,
    retry_with_backoff,
    sanitize_api_key,
    generate_source_id,
)

# Existing connectors
from .schwab_connector import SchwabConnector
from .market_data_connector import MarketDataConnector

# New connectors (Phase 2-5)
from .ccxt_connector import CCXTConnector
from .tiingo_connector import TiingoConnector
from .ibkr_connector import IBKRConnector

__all__ = [
    # Base classes
    'BaseConnector',
    'ConnectorMetadata',
    'ConnectorType',
    # Exceptions
    'ConnectorError',
    'AuthenticationError',
    'RateLimitError',
    'DataFetchError',
    'ConfigurationError',
    # Constants
    'HOLDINGS_COLUMNS',
    'TRANSACTION_COLUMNS',
    'TRANSACTION_TYPES',
    # Utilities
    'RateLimiter',
    'ResponseCache',
    'retry_with_backoff',
    'sanitize_api_key',
    'generate_source_id',
    # Connectors
    'SchwabConnector',
    'MarketDataConnector',
    'CCXTConnector',
    'TiingoConnector',
    'IBKRConnector',
]


