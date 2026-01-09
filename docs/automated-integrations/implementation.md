# Implementation Specification: Automated Data Integrations

This document provides detailed technical specifications for implementing automated data integrations. Use this as a reference when building each component.

---

## Table of Contents

1. [Directory Structure](#directory-structure)
2. [Base Connector Interface](#base-connector-interface)
3. [CCXT Connector Implementation](#ccxt-connector-implementation)
4. [IBKR Connector Implementation](#ibkr-connector-implementation)
5. [Schwab Connector Enhancement](#schwab-connector-enhancement)
6. [Market Data Connector](#market-data-connector)
7. [Plugin System](#plugin-system)
8. [Database Schema](#database-schema)
9. [Configuration Files](#configuration-files)
10. [Web Routes](#web-routes)
11. [Data Normalization](#data-normalization)

---

## Directory Structure

```
src/
├── data_manager/
│   ├── connectors/
│   │   ├── __init__.py                 # Export all connectors
│   │   ├── base_connector.py           # NEW: Abstract base class
│   │   ├── utils.py                    # NEW: Rate limiting, caching
│   │   ├── ccxt_connector.py           # NEW: Crypto exchanges
│   │   ├── ibkr_connector.py           # NEW: Interactive Brokers
│   │   ├── schwab_connector.py         # ENHANCED: Full OAuth2
│   │   ├── tiingo_connector.py         # NEW: Tiingo market data
│   │   ├── market_data_connector.py    # ENHANCED: Multi-provider
│   │   └── google_finance_connector.py # Existing
│   ├── readers.py                      # ENHANCED: Add API readers
│   ├── cleaners.py                     # ENHANCED: Add API cleaners
│   ├── import_orchestrator.py          # NEW: Unified import pipeline
│   ├── validation.py                   # NEW: Data validation engine
│   └── manager.py                      # Existing
│
├── plugins/                            # NEW: Plugin system
│   ├── __init__.py
│   ├── base.py                         # Plugin base class
│   ├── manager.py                      # Plugin loader
│   ├── registry.py                     # Plugin registry
│   └── bank_plugins/
│       ├── __init__.py
│       ├── icbc/
│       │   ├── __init__.py
│       │   ├── connector.py
│       │   └── manifest.yaml
│       ├── chase/
│       │   ├── __init__.py
│       │   ├── connector.py
│       │   └── manifest.yaml
│       └── template/
│           ├── __init__.py
│           ├── connector.py
│           └── manifest.yaml
│
├── database/
│   ├── models.py                       # ENHANCED: New tables
│   └── migrations/
│       └── xxx_add_import_tracking.py  # NEW: Migration script
│
└── web_app/
    └── blueprints/
        ├── crypto/                     # NEW: Crypto management
        │   ├── __init__.py
        │   └── routes.py
        ├── brokers/                    # NEW: Broker connections
        │   ├── __init__.py
        │   └── routes.py
        └── plugins/                    # NEW: Plugin management
            ├── __init__.py
            └── routes.py

config/
├── settings.yaml                       # ENHANCED: Add integration sections
├── data_sources.yaml                   # NEW: Central integration config
├── .env.example                        # NEW: All API keys documented
└── integrations/
    ├── ccxt.yaml.example
    ├── ibkr.yaml.example
    ├── schwab.yaml.example
    └── tiingo.yaml.example

docs/
└── automated-integrations/
    ├── task_plan.md
    ├── implementation.md               # THIS FILE
    ├── notes.md
    ├── plugin_development.md
    └── setup_guides/
        ├── ccxt_setup.md
        ├── ibkr_setup.md
        └── schwab_setup.md
```

---

## Base Connector Interface

### File: `src/data_manager/connectors/base_connector.py`

```python
"""
Base classes for all data source connectors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    supported_assets: List[str]  # e.g., ["stocks", "etfs", "crypto"]
    requires_oauth: bool
    requires_api_key: bool
    rate_limit_per_minute: int
    documentation_url: Optional[str] = None


class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""
    pass


class RateLimitError(ConnectorError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class DataFetchError(ConnectorError):
    """Raised when data fetching fails."""
    pass


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
    """

    metadata: ConnectorMetadata

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.

        Args:
            config: Dictionary containing credentials and settings.
                   Structure varies by connector type.
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
        Get account metadata (optional).

        Returns:
            Dictionary with account information:
            - account_id: str
            - account_type: str (Individual, Joint, IRA, etc.)
            - base_currency: str
            - status: str
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
        """Helper to validate required config keys are present."""
        missing = [k for k in required_keys if k not in self.config or not self.config[k]]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")
```

### File: `src/data_manager/connectors/utils.py`

```python
"""
Utility classes for connector implementations.
"""
import time
import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API calls.

    Usage:
        limiter = RateLimiter(calls_per_minute=60)
        limiter.wait()  # Blocks if rate limit exceeded
        response = api.call()
    """

    def __init__(self, calls_per_minute: int = 60, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls per minute
            calls_per_second: Minimum seconds between calls
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = max(1.0 / calls_per_second, 60.0 / calls_per_minute)
        self.last_call_time: Optional[float] = None
        self.call_times: list = []

    def wait(self) -> None:
        """Block until it's safe to make another API call."""
        now = time.time()

        # Clean old call times (older than 1 minute)
        self.call_times = [t for t in self.call_times if now - t < 60]

        # Check per-minute limit
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        # Check per-call interval
        if self.last_call_time:
            elapsed = now - self.last_call_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

        self.last_call_time = time.time()
        self.call_times.append(self.last_call_time)


class ResponseCache:
    """
    Simple in-memory cache for API responses.

    Usage:
        cache = ResponseCache(ttl_seconds=300)

        cached = cache.get("price_AAPL")
        if cached:
            return cached

        price = api.get_price("AAPL")
        cache.set("price_AAPL", price)
        return price
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live in seconds (default 5 minutes)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set cached value with TTL."""
        expiry = datetime.now() + self.ttl
        self._cache[key] = (value, expiry)

    def invalidate(self, key: str) -> None:
        """Remove specific key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying failed API calls with exponential backoff.

    Usage:
        @retry_with_backoff(max_retries=3, exceptions=(RateLimitError,))
        def fetch_data():
            return api.get_data()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")

            raise last_exception

        return wrapper
    return decorator
```

---

## CCXT Connector Implementation

### File: `src/data_manager/connectors/ccxt_connector.py`

```python
"""
CCXT-based connector for cryptocurrency exchanges.

Supports: Binance, Coinbase, Kraken, OKX, Huobi, Gate.io, and 100+ others.

Usage:
    config = {
        'exchanges': {
            'binance': {
                'api_key': 'xxx',
                'api_secret': 'xxx',
                'enabled': True
            }
        }
    }
    connector = CCXTConnector(config)
    connector.authenticate()
    holdings = connector.get_holdings()
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from .base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorType,
    AuthenticationError,
    DataFetchError,
    RateLimitError,
)
from .utils import RateLimiter, ResponseCache, retry_with_backoff

logger = logging.getLogger(__name__)


class CCXTConnector(BaseConnector):
    """
    Multi-exchange cryptocurrency connector using CCXT library.
    """

    metadata = ConnectorMetadata(
        name="CCXT Crypto Exchanges",
        connector_type=ConnectorType.CRYPTO_EXCHANGE,
        version="1.0.0",
        description="Connect to 100+ cryptocurrency exchanges via CCXT",
        supported_assets=["crypto"],
        requires_oauth=False,
        requires_api_key=True,
        rate_limit_per_minute=60,
        documentation_url="https://docs.ccxt.com/"
    )

    # Supported exchanges with specific configurations
    EXCHANGE_CONFIGS = {
        'binance': {'rateLimit': 1200, 'enableRateLimit': True},
        'coinbase': {'rateLimit': 350, 'enableRateLimit': True},
        'kraken': {'rateLimit': 3000, 'enableRateLimit': True},
        'okx': {'rateLimit': 100, 'enableRateLimit': True},
        'huobi': {'rateLimit': 500, 'enableRateLimit': True},
        'gateio': {'rateLimit': 900, 'enableRateLimit': True},
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CCXT connector.

        Args:
            config: Dictionary with structure:
                {
                    'exchanges': {
                        '<exchange_id>': {
                            'api_key': str,
                            'api_secret': str,
                            'password': str (optional, for some exchanges),
                            'enabled': bool,
                            'sandbox': bool (optional, for testing)
                        }
                    },
                    'cache_ttl': int (optional, seconds)
                }
        """
        super().__init__(config)

        if not CCXT_AVAILABLE:
            raise ImportError("CCXT library not installed. Run: pip install ccxt")

        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.cache = ResponseCache(ttl_seconds=config.get('cache_ttl', 300))

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with all configured exchanges.

        Returns:
            Tuple of (all_success: bool, message: str)
        """
        exchanges_config = self.config.get('exchanges', {})
        if not exchanges_config:
            return False, "No exchanges configured"

        results = []
        for exchange_id, ex_config in exchanges_config.items():
            if not ex_config.get('enabled', True):
                continue

            try:
                success, msg = self._authenticate_exchange(exchange_id, ex_config)
                results.append((exchange_id, success, msg))
            except Exception as e:
                results.append((exchange_id, False, str(e)))

        # Build summary message
        successful = [r[0] for r in results if r[1]]
        failed = [(r[0], r[2]) for r in results if not r[1]]

        if not results:
            return False, "No exchanges to authenticate"

        self._authenticated = len(successful) > 0

        if failed:
            fail_msg = "; ".join([f"{ex}: {msg}" for ex, msg in failed])
            if successful:
                return True, f"Connected to {successful}. Failed: {fail_msg}"
            return False, f"All connections failed: {fail_msg}"

        return True, f"Connected to {len(successful)} exchanges: {successful}"

    def _authenticate_exchange(
        self,
        exchange_id: str,
        ex_config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Authenticate with a single exchange."""
        if exchange_id not in ccxt.exchanges:
            raise AuthenticationError(f"Unknown exchange: {exchange_id}")

        # Get exchange class
        exchange_class = getattr(ccxt, exchange_id)

        # Build exchange config
        config = {
            'apiKey': ex_config.get('api_key'),
            'secret': ex_config.get('api_secret'),
            **self.EXCHANGE_CONFIGS.get(exchange_id, {'enableRateLimit': True})
        }

        # Add password if required (e.g., OKX)
        if 'password' in ex_config:
            config['password'] = ex_config['password']

        # Use sandbox/testnet if specified
        if ex_config.get('sandbox'):
            config['sandbox'] = True

        # Instantiate exchange
        exchange = exchange_class(config)

        # Test connection by fetching balance
        try:
            balance = exchange.fetch_balance()
            self.exchanges[exchange_id] = exchange
            return True, "OK"
        except ccxt.AuthenticationError as e:
            raise AuthenticationError(f"Authentication failed: {e}")
        except ccxt.ExchangeError as e:
            raise AuthenticationError(f"Exchange error: {e}")

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch holdings from all authenticated exchanges.

        Args:
            account_id: If provided, only fetch from this exchange

        Returns:
            DataFrame with columns: symbol, name, quantity, current_price,
            market_value, currency, exchange
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_holdings = []

        exchanges_to_query = (
            [account_id] if account_id else list(self.exchanges.keys())
        )

        for exchange_id in exchanges_to_query:
            if exchange_id not in self.exchanges:
                logger.warning(f"Exchange {exchange_id} not authenticated")
                continue

            try:
                holdings = self._fetch_exchange_holdings(exchange_id)
                if holdings is not None:
                    all_holdings.append(holdings)
            except Exception as e:
                logger.error(f"Failed to fetch holdings from {exchange_id}: {e}")

        if not all_holdings:
            return None

        return pd.concat(all_holdings, ignore_index=True)

    @retry_with_backoff(max_retries=3, exceptions=(ccxt.NetworkError,))
    def _fetch_exchange_holdings(self, exchange_id: str) -> Optional[pd.DataFrame]:
        """Fetch holdings from a single exchange."""
        exchange = self.exchanges[exchange_id]

        # Check cache
        cache_key = f"holdings_{exchange_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Fetch balance
        balance = exchange.fetch_balance()

        # Filter non-zero balances
        holdings = []
        for symbol, data in balance.get('total', {}).items():
            if data and float(data) > 0:
                # Skip small dust amounts
                if float(data) < 0.00001:
                    continue

                # Get current price
                price = self._get_price(exchange, symbol)

                holdings.append({
                    'symbol': symbol,
                    'name': self._get_asset_name(symbol),
                    'quantity': float(data),
                    'current_price': price,
                    'market_value': float(data) * price if price else 0,
                    'currency': 'USD',  # Most exchanges use USD as quote
                    'exchange': exchange_id,
                })

        if not holdings:
            return None

        df = pd.DataFrame(holdings)
        self.cache.set(cache_key, df)
        return df

    def _get_price(self, exchange: 'ccxt.Exchange', symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            # Try common quote currencies
            for quote in ['USDT', 'USD', 'BUSD', 'USDC']:
                pair = f"{symbol}/{quote}"
                if pair in exchange.markets:
                    ticker = exchange.fetch_ticker(pair)
                    return ticker.get('last') or ticker.get('close')

            # For stablecoins, return 1
            if symbol in ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD']:
                return 1.0

            return None
        except Exception:
            return None

    def _get_asset_name(self, symbol: str) -> str:
        """Map symbol to full asset name."""
        # Common mappings
        names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance Coin',
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'XRP': 'Ripple',
            'DOT': 'Polkadot',
            'DOGE': 'Dogecoin',
            'USDT': 'Tether',
            'USDC': 'USD Coin',
        }
        return names.get(symbol, symbol)

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transaction history from all authenticated exchanges.

        Args:
            account_id: If provided, only fetch from this exchange
            since_date: Start date for transactions
            until_date: End date for transactions

        Returns:
            DataFrame with columns: date, symbol, name, transaction_type,
            quantity, price, amount, currency, fees, source_id, exchange
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_transactions = []

        exchanges_to_query = (
            [account_id] if account_id else list(self.exchanges.keys())
        )

        for exchange_id in exchanges_to_query:
            if exchange_id not in self.exchanges:
                continue

            try:
                txns = self._fetch_exchange_transactions(
                    exchange_id, since_date, until_date
                )
                if txns is not None:
                    all_transactions.append(txns)
            except Exception as e:
                logger.error(f"Failed to fetch transactions from {exchange_id}: {e}")

        if not all_transactions:
            return None

        return pd.concat(all_transactions, ignore_index=True)

    @retry_with_backoff(max_retries=3, exceptions=(ccxt.NetworkError,))
    def _fetch_exchange_transactions(
        self,
        exchange_id: str,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transactions from a single exchange."""
        exchange = self.exchanges[exchange_id]

        # Convert dates to timestamps
        since_ts = int(since_date.timestamp() * 1000) if since_date else None

        transactions = []

        # Fetch trades for all symbols
        if exchange.has.get('fetchMyTrades'):
            try:
                # Get all traded symbols
                markets = exchange.load_markets()
                for symbol in list(markets.keys())[:50]:  # Limit to prevent timeout
                    try:
                        trades = exchange.fetch_my_trades(symbol, since=since_ts, limit=100)
                        for trade in trades:
                            trade_date = datetime.fromtimestamp(trade['timestamp'] / 1000)

                            # Apply date filter
                            if until_date and trade_date > until_date:
                                continue

                            base_symbol = trade['symbol'].split('/')[0]

                            transactions.append({
                                'date': trade_date,
                                'symbol': base_symbol,
                                'name': self._get_asset_name(base_symbol),
                                'transaction_type': 'Buy' if trade['side'] == 'buy' else 'Sell',
                                'quantity': abs(trade['amount']),
                                'price': trade['price'],
                                'amount': abs(trade['cost']),
                                'currency': 'USD',
                                'fees': trade.get('fee', {}).get('cost', 0) or 0,
                                'source_id': trade['id'],
                                'exchange': exchange_id,
                            })
                    except Exception:
                        continue  # Skip symbols that fail
            except Exception as e:
                logger.warning(f"Failed to fetch trades from {exchange_id}: {e}")

        # Fetch deposits and withdrawals
        if exchange.has.get('fetchDeposits'):
            try:
                deposits = exchange.fetch_deposits(since=since_ts)
                for dep in deposits:
                    dep_date = datetime.fromtimestamp(dep['timestamp'] / 1000)
                    if until_date and dep_date > until_date:
                        continue

                    transactions.append({
                        'date': dep_date,
                        'symbol': dep['currency'],
                        'name': self._get_asset_name(dep['currency']),
                        'transaction_type': 'Deposit',
                        'quantity': dep['amount'],
                        'price': 0,
                        'amount': 0,
                        'currency': dep['currency'],
                        'fees': dep.get('fee', {}).get('cost', 0) or 0,
                        'source_id': dep['id'] or dep['txid'],
                        'exchange': exchange_id,
                    })
            except Exception:
                pass

        if exchange.has.get('fetchWithdrawals'):
            try:
                withdrawals = exchange.fetch_withdrawals(since=since_ts)
                for wd in withdrawals:
                    wd_date = datetime.fromtimestamp(wd['timestamp'] / 1000)
                    if until_date and wd_date > until_date:
                        continue

                    transactions.append({
                        'date': wd_date,
                        'symbol': wd['currency'],
                        'name': self._get_asset_name(wd['currency']),
                        'transaction_type': 'Withdrawal',
                        'quantity': -abs(wd['amount']),
                        'price': 0,
                        'amount': 0,
                        'currency': wd['currency'],
                        'fees': wd.get('fee', {}).get('cost', 0) or 0,
                        'source_id': wd['id'] or wd['txid'],
                        'exchange': exchange_id,
                    })
            except Exception:
                pass

        if not transactions:
            return None

        return pd.DataFrame(transactions)

    def health_check(self) -> Tuple[bool, str]:
        """Check if all exchanges are accessible."""
        if not self.exchanges:
            return False, "No exchanges connected"

        results = []
        for exchange_id, exchange in self.exchanges.items():
            try:
                exchange.fetch_time()
                results.append((exchange_id, True))
            except Exception as e:
                results.append((exchange_id, False, str(e)))

        healthy = [r[0] for r in results if r[1]]
        unhealthy = [r for r in results if not r[1]]

        if unhealthy:
            return False, f"Unhealthy: {unhealthy}"

        return True, f"All {len(healthy)} exchanges healthy"

    def disconnect(self) -> bool:
        """Close all exchange connections."""
        self.exchanges.clear()
        self._authenticated = False
        self.cache.clear()
        return True
```

---

## IBKR Connector Implementation

### File: `src/data_manager/connectors/ibkr_connector.py`

```python
"""
Interactive Brokers connector.

Supports both Client Portal API (REST) and legacy TWS API.

Usage:
    config = {
        'auth_type': 'jwt',  # or 'gateway'
        'jwt_token': 'xxx',
        'accounts': ['U12345678']
    }
    connector = IBKRConnector(config)
    connector.authenticate()
    holdings = connector.get_holdings('U12345678')
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from .base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorType,
    AuthenticationError,
    DataFetchError,
)
from .utils import RateLimiter, ResponseCache, retry_with_backoff

logger = logging.getLogger(__name__)


class IBKRConnector(BaseConnector):
    """
    Interactive Brokers connector using Client Portal API.

    Documentation: https://www.interactivebrokers.com/api/doc.html
    """

    metadata = ConnectorMetadata(
        name="Interactive Brokers",
        connector_type=ConnectorType.BROKER,
        version="1.0.0",
        description="Connect to Interactive Brokers accounts",
        supported_assets=["stocks", "etfs", "bonds", "options", "futures", "forex", "crypto"],
        requires_oauth=False,
        requires_api_key=True,
        rate_limit_per_minute=60,
        documentation_url="https://www.interactivebrokers.com/api/doc.html"
    )

    # Client Portal API endpoints
    BASE_URL = "https://localhost:5000/v1/api"  # Default gateway URL

    # Asset type mapping
    ASSET_TYPE_MAP = {
        'STK': 'stocks',
        'ETF': 'etfs',
        'BOND': 'bonds',
        'OPT': 'options',
        'FUT': 'futures',
        'CASH': 'forex',
        'CRYPTO': 'crypto',
        'FUND': 'mutual_funds',
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IBKR connector.

        Args:
            config: Dictionary with structure:
                {
                    'base_url': str (optional, override gateway URL),
                    'auth_type': 'jwt' or 'gateway',
                    'jwt_token': str (if auth_type='jwt'),
                    'accounts': List[str] (account IDs to sync),
                    'transaction_lookback_days': int (optional, default 90)
                }
        """
        super().__init__(config)

        self.base_url = config.get('base_url', self.BASE_URL)
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(calls_per_minute=60)
        self.cache = ResponseCache(ttl_seconds=60)
        self._accounts: List[Dict] = []

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with IBKR Client Portal.

        For JWT auth: Validates token and fetches account list.
        For gateway auth: Assumes gateway is already authenticated.
        """
        auth_type = self.config.get('auth_type', 'gateway')

        try:
            if auth_type == 'jwt':
                jwt_token = self.config.get('jwt_token')
                if not jwt_token:
                    raise AuthenticationError("JWT token not provided")

                self.session.headers['Authorization'] = f'Bearer {jwt_token}'

            # Test authentication by fetching accounts
            response = self._make_request('GET', '/portfolio/accounts')

            if not response or 'error' in response:
                raise AuthenticationError(
                    response.get('error', 'Unknown authentication error')
                )

            self._accounts = response
            self._authenticated = True

            account_ids = [a.get('accountId') for a in self._accounts]
            return True, f"Connected to {len(account_ids)} accounts: {account_ids}"

        except requests.RequestException as e:
            raise AuthenticationError(f"Connection failed: {e}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Any:
        """Make authenticated API request."""
        self.rate_limiter.wait()

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=data,
                verify=False,  # Gateway uses self-signed cert
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Session expired. Re-authenticate required.")
            raise DataFetchError(f"API error: {e}")

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of connected accounts."""
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated")

        return self._accounts

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch holdings for one or all accounts.

        Args:
            account_id: Specific account, or None for all accounts
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated")

        accounts_to_query = (
            [account_id] if account_id
            else self.config.get('accounts', [a['accountId'] for a in self._accounts])
        )

        all_holdings = []

        for acct_id in accounts_to_query:
            try:
                holdings = self._fetch_account_holdings(acct_id)
                if holdings is not None:
                    all_holdings.append(holdings)
            except Exception as e:
                logger.error(f"Failed to fetch holdings for {acct_id}: {e}")

        if not all_holdings:
            return None

        return pd.concat(all_holdings, ignore_index=True)

    @retry_with_backoff(max_retries=2)
    def _fetch_account_holdings(self, account_id: str) -> Optional[pd.DataFrame]:
        """Fetch holdings for a single account."""
        # Check cache
        cache_key = f"holdings_{account_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        response = self._make_request(
            'GET',
            f'/portfolio/{account_id}/positions/0'
        )

        if not response:
            return None

        holdings = []
        for pos in response:
            asset_type = self.ASSET_TYPE_MAP.get(pos.get('assetClass'), 'other')

            holdings.append({
                'symbol': pos.get('contractDesc', pos.get('ticker', 'UNKNOWN')),
                'name': pos.get('name', pos.get('contractDesc', '')),
                'quantity': pos.get('position', 0),
                'current_price': pos.get('mktPrice', 0),
                'market_value': pos.get('mktValue', 0),
                'cost_basis': pos.get('avgCost', 0) * pos.get('position', 0),
                'currency': pos.get('currency', 'USD'),
                'unrealized_pnl': pos.get('unrealizedPnl', 0),
                'asset_type': asset_type,
                'account_id': account_id,
            })

        if not holdings:
            return None

        df = pd.DataFrame(holdings)
        self.cache.set(cache_key, df)
        return df

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transaction history."""
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated")

        accounts_to_query = (
            [account_id] if account_id
            else self.config.get('accounts', [a['accountId'] for a in self._accounts])
        )

        all_transactions = []

        for acct_id in accounts_to_query:
            try:
                txns = self._fetch_account_transactions(acct_id, since_date, until_date)
                if txns is not None:
                    all_transactions.append(txns)
            except Exception as e:
                logger.error(f"Failed to fetch transactions for {acct_id}: {e}")

        if not all_transactions:
            return None

        return pd.concat(all_transactions, ignore_index=True)

    def _fetch_account_transactions(
        self,
        account_id: str,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transactions for a single account."""
        lookback_days = self.config.get('transaction_lookback_days', 90)

        # IBKR uses period parameter (7d, 30d, 90d, etc.)
        period = f"{lookback_days}d"

        response = self._make_request(
            'GET',
            f'/iserver/account/{account_id}/orders',
            params={'period': period}
        )

        if not response or 'orders' not in response:
            return None

        transactions = []
        for order in response.get('orders', []):
            if order.get('status') != 'Filled':
                continue

            order_date = datetime.fromtimestamp(order.get('lastExecutionTime', 0) / 1000)

            # Apply date filters
            if since_date and order_date < since_date:
                continue
            if until_date and order_date > until_date:
                continue

            side = order.get('side', '').upper()
            txn_type = 'Buy' if side == 'BUY' else 'Sell' if side == 'SELL' else 'Other'

            transactions.append({
                'date': order_date,
                'symbol': order.get('ticker', 'UNKNOWN'),
                'name': order.get('companyName', ''),
                'transaction_type': txn_type,
                'quantity': abs(order.get('filledQuantity', 0)),
                'price': order.get('avgPrice', 0),
                'amount': abs(order.get('totalSize', 0)),
                'currency': order.get('cashCcy', 'USD'),
                'fees': order.get('commission', 0),
                'source_id': order.get('orderId', ''),
                'account_id': account_id,
            })

        if not transactions:
            return None

        return pd.DataFrame(transactions)

    def health_check(self) -> Tuple[bool, str]:
        """Check gateway connectivity."""
        try:
            response = self._make_request('GET', '/iserver/auth/status')
            if response.get('authenticated'):
                return True, "Gateway authenticated"
            return False, "Gateway not authenticated"
        except Exception as e:
            return False, f"Health check failed: {e}"
```

---

## Plugin System

### File: `src/plugins/base.py`

```python
"""
Base classes for the plugin system.

Plugins allow community-contributed integrations for banks and other
data sources not covered by built-in connectors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class AuthenticationType(Enum):
    """Types of authentication supported by plugins."""
    CREDENTIALS = "credentials"  # Username/password
    API_KEY = "api_key"          # API key only
    OAUTH2 = "oauth2"            # OAuth2 flow
    CERTIFICATE = "certificate"  # Client certificate


@dataclass
class AuthField:
    """Definition of an authentication field."""
    name: str
    field_type: str  # text, password, file
    label: str
    required: bool = True
    placeholder: str = ""
    help_text: str = ""


@dataclass
class PluginMetadata:
    """
    Metadata about a plugin.

    This information is displayed in the plugin library and used
    for discovery and compatibility checking.
    """
    id: str                              # Unique identifier (e.g., "icbc_personal")
    name: str                            # Display name
    version: str                         # Semantic version
    author: str                          # Author name or organization
    description: str                     # Short description
    supported_countries: List[str]       # ISO country codes (e.g., ["CN", "US"])
    asset_types: List[str]               # Supported asset types
    auth_type: AuthenticationType        # Authentication method
    auth_fields: List[AuthField] = field(default_factory=list)  # Auth form fields
    homepage: Optional[str] = None       # Project homepage
    min_python_version: str = "3.9"      # Minimum Python version
    dependencies: List[str] = field(default_factory=list)  # pip packages


class PluginError(Exception):
    """Base exception for plugin errors."""
    pass


class PluginAuthError(PluginError):
    """Authentication failed."""
    pass


class PluginDataError(PluginError):
    """Data fetching failed."""
    pass


class BankIntegrationPlugin(ABC):
    """
    Abstract base class for bank/data source plugins.

    To create a plugin:
    1. Create a new directory in src/plugins/bank_plugins/<your_plugin>/
    2. Create manifest.yaml with plugin metadata
    3. Create connector.py implementing this class
    4. Implement all abstract methods

    Example:
        class MyBankPlugin(BankIntegrationPlugin):
            metadata = PluginMetadata(
                id="mybank",
                name="My Bank",
                version="1.0.0",
                ...
            )

            def authenticate(self, credentials):
                # Your auth logic
                pass

            def get_accounts(self):
                # Fetch accounts
                pass

            # ... implement other methods
    """

    metadata: PluginMetadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin.

        Args:
            config: Optional plugin-specific configuration
        """
        self.config = config or {}
        self._authenticated = False
        self._session: Any = None  # Can hold requests.Session or other client

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated

    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Authenticate with the data source.

        Args:
            credentials: Dictionary with authentication fields
                        (as defined in metadata.auth_fields)

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            PluginAuthError: If authentication fails
        """
        pass

    @abstractmethod
    def get_accounts(self) -> Optional[pd.DataFrame]:
        """
        Fetch list of accounts.

        Returns:
            DataFrame with columns:
            - account_id: str - Unique account identifier
            - account_name: str - Display name
            - account_type: str - Type (Checking, Savings, Investment, etc.)
            - balance: float - Current balance
            - currency: str - Currency code
        """
        pass

    @abstractmethod
    def get_holdings(self, account_id: str) -> Optional[pd.DataFrame]:
        """
        Fetch holdings for an account.

        Args:
            account_id: Account to fetch holdings for

        Returns:
            DataFrame with columns:
            - symbol: str - Asset identifier
            - name: str - Asset name
            - quantity: float - Units held
            - current_price: float - Current price
            - market_value: float - Total value
            - currency: str - Currency code
        """
        pass

    @abstractmethod
    def get_transactions(
        self,
        account_id: str,
        since_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transaction history for an account.

        Args:
            account_id: Account to fetch transactions for
            since_date: Optional start date filter

        Returns:
            DataFrame with columns:
            - date: datetime - Transaction date
            - description: str - Transaction description
            - amount: float - Transaction amount (positive=inflow, negative=outflow)
            - transaction_type: str - Type (Deposit, Withdrawal, Transfer, etc.)
            - balance: float - Balance after transaction (optional)
            - currency: str - Currency code
        """
        pass

    def get_balance(self, account_id: str) -> Optional[Dict[str, float]]:
        """
        Get detailed balance information (optional).

        Returns:
            Dictionary with balance breakdown:
            - available: float
            - pending: float
            - total: float
        """
        return None

    def health_check(self) -> Tuple[bool, str]:
        """
        Check if the service is accessible (optional).

        Returns:
            Tuple of (healthy: bool, message: str)
        """
        return True, "OK"

    def logout(self) -> bool:
        """
        Clean up session and logout (optional).

        Returns:
            True if successful
        """
        self._authenticated = False
        self._session = None
        return True
```

### File: `src/plugins/manager.py`

```python
"""
Plugin discovery and management.
"""
import importlib.util
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .base import BankIntegrationPlugin, PluginMetadata

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Discovers, loads, and manages plugins.

    Usage:
        manager = PluginManager()
        plugins = manager.discover_plugins()

        plugin = manager.load_plugin('icbc_personal')
        plugin.authenticate({'username': 'xxx', 'password': 'xxx'})
        accounts = plugin.get_accounts()
    """

    DEFAULT_PLUGIN_DIR = Path(__file__).parent / 'bank_plugins'

    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize plugin manager.

        Args:
            plugin_dir: Custom plugin directory (optional)
        """
        self.plugin_dir = Path(plugin_dir) if plugin_dir else self.DEFAULT_PLUGIN_DIR
        self._plugins: Dict[str, BankIntegrationPlugin] = {}
        self._metadata: Dict[str, PluginMetadata] = {}

    def discover_plugins(self) -> List[Dict[str, Any]]:
        """
        Scan plugin directory for available plugins.

        Returns:
            List of plugin info dictionaries
        """
        plugins = []

        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {self.plugin_dir}")
            return plugins

        for item in self.plugin_dir.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue

            manifest_path = item / 'manifest.yaml'
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = yaml.safe_load(f)

                plugin_info = manifest.get('plugin', {})
                plugin_id = plugin_info.get('id', item.name)

                plugins.append({
                    'id': plugin_id,
                    'name': plugin_info.get('name', item.name),
                    'version': plugin_info.get('version', '0.0.0'),
                    'author': plugin_info.get('author', 'Unknown'),
                    'description': plugin_info.get('description', ''),
                    'countries': manifest.get('supported_countries', []),
                    'asset_types': manifest.get('asset_types', []),
                    'path': str(item),
                    'loaded': plugin_id in self._plugins,
                })
            except Exception as e:
                logger.error(f"Failed to read manifest for {item.name}: {e}")

        return plugins

    def load_plugin(self, plugin_id: str) -> Optional[BankIntegrationPlugin]:
        """
        Load a specific plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Loaded plugin instance, or None if loading fails
        """
        # Return cached instance if already loaded
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]

        # Find plugin directory
        plugin_path = None
        for item in self.plugin_dir.iterdir():
            if not item.is_dir():
                continue

            manifest_path = item / 'manifest.yaml'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
                if manifest.get('plugin', {}).get('id') == plugin_id:
                    plugin_path = item
                    break

        if not plugin_path:
            logger.error(f"Plugin not found: {plugin_id}")
            return None

        # Load the connector module
        connector_path = plugin_path / 'connector.py'
        if not connector_path.exists():
            logger.error(f"No connector.py found for plugin: {plugin_id}")
            return None

        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}",
                connector_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the plugin class (must inherit from BankIntegrationPlugin)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BankIntegrationPlugin) and
                    attr is not BankIntegrationPlugin):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No plugin class found in {connector_path}")
                return None

            # Instantiate and cache
            instance = plugin_class()
            self._plugins[plugin_id] = instance
            self._metadata[plugin_id] = instance.metadata

            logger.info(f"Loaded plugin: {plugin_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return None

    def get_plugin(self, plugin_id: str) -> Optional[BankIntegrationPlugin]:
        """Get a loaded plugin instance."""
        return self._plugins.get(plugin_id)

    def list_loaded_plugins(self) -> List[str]:
        """Get list of currently loaded plugin IDs."""
        return list(self._plugins.keys())

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin and clean up resources.

        Args:
            plugin_id: Plugin to unload

        Returns:
            True if successfully unloaded
        """
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        try:
            plugin.logout()
        except Exception:
            pass

        del self._plugins[plugin_id]
        self._metadata.pop(plugin_id, None)

        return True

    def validate_plugin(self, plugin_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a plugin before loading.

        Checks:
        - manifest.yaml exists and is valid
        - connector.py exists
        - Required methods are implemented
        - No dangerous imports

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        # Check manifest
        manifest_path = plugin_path / 'manifest.yaml'
        if not manifest_path.exists():
            errors.append("manifest.yaml not found")
        else:
            try:
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)

                required_fields = ['plugin.id', 'plugin.name', 'plugin.version']
                for field in required_fields:
                    parts = field.split('.')
                    obj = manifest
                    for part in parts:
                        obj = obj.get(part, {}) if isinstance(obj, dict) else None
                    if not obj:
                        errors.append(f"Missing required field: {field}")
            except yaml.YAMLError as e:
                errors.append(f"Invalid manifest YAML: {e}")

        # Check connector
        connector_path = plugin_path / 'connector.py'
        if not connector_path.exists():
            errors.append("connector.py not found")
        else:
            # Check for dangerous imports
            with open(connector_path, 'r') as f:
                content = f.read()

            dangerous_patterns = [
                'os.system',
                'subprocess.',
                'eval(',
                'exec(',
                '__import__',
            ]
            for pattern in dangerous_patterns:
                if pattern in content:
                    errors.append(f"Potentially dangerous pattern: {pattern}")

        return len(errors) == 0, errors
```

---

## Database Schema

### New Tables (Alembic Migration)

```python
"""
Add import tracking tables.

Revision ID: add_import_tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = 'add_import_tracking'
down_revision = 'previous_revision_id'

def upgrade():
    # ImportJob - Track import operations
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(50), nullable=False),  # ccxt, ibkr, schwab, plugin
        sa.Column('source_id', sa.String(100), nullable=False),   # exchange_id, account_id, plugin_id
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),       # running, completed, failed
        sa.Column('records_imported', sa.Integer(), default=0),
        sa.Column('records_updated', sa.Integer(), default=0),
        sa.Column('records_skipped', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),     # Additional context
    )
    op.create_index('ix_import_jobs_source', 'import_jobs', ['source_type', 'source_id'])
    op.create_index('ix_import_jobs_started', 'import_jobs', ['started_at'])

    # PluginConfig - Store plugin credentials and settings
    op.create_table(
        'plugin_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plugin_id', sa.String(100), unique=True, nullable=False),
        sa.Column('config_encrypted', sa.Text(), nullable=True),  # Encrypted credentials
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('sync_frequency', sa.String(20), default='daily'),  # hourly, daily, weekly
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # DataSourceLink - Link imported data to source
    op.create_table(
        'data_source_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('asset_id', sa.String(100), nullable=False),
        sa.Column('external_id', sa.String(200), nullable=True),  # ID in external system
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
    )
    op.create_index('ix_data_source_asset', 'data_source_links', ['asset_id'])
    op.create_unique_constraint(
        'uq_source_asset',
        'data_source_links',
        ['source_type', 'source_id', 'asset_id']
    )


def downgrade():
    op.drop_table('data_source_links')
    op.drop_table('plugin_configs')
    op.drop_table('import_jobs')
```

---

## Configuration Files

### File: `config/data_sources.yaml`

```yaml
# Data Sources Configuration
# This file configures all automated data integrations

# Global settings
global:
  sync_frequency: daily          # Default sync frequency
  retry_on_failure: true         # Retry failed syncs
  max_retries: 3                 # Maximum retry attempts
  cache_duration: 300            # Response cache TTL (seconds)

# Cryptocurrency Exchanges (via CCXT)
crypto_exchanges:
  enabled: false
  sync_frequency: daily

  exchanges:
    binance:
      enabled: false
      api_key: "${BINANCE_API_KEY}"
      api_secret: "${BINANCE_API_SECRET}"
      sandbox: false             # Use testnet for testing

    coinbase:
      enabled: false
      api_key: "${COINBASE_API_KEY}"
      api_secret: "${COINBASE_API_SECRET}"

    kraken:
      enabled: false
      api_key: "${KRAKEN_API_KEY}"
      api_secret: "${KRAKEN_API_SECRET}"

# Interactive Brokers
interactive_brokers:
  enabled: false
  auth_type: gateway             # gateway or jwt
  base_url: "https://localhost:5000/v1/api"

  # JWT authentication (if auth_type: jwt)
  jwt_token: "${IBKR_JWT_TOKEN}"

  accounts:
    - account_id: "${IBKR_ACCOUNT_ID}"
      sync: true
      sync_frequency: daily
      transaction_lookback_days: 90

# Charles Schwab
schwab:
  enabled: false
  auth_type: oauth2

  # OAuth2 credentials (from Schwab Developer Portal)
  client_id: "${SCHWAB_CLIENT_ID}"
  client_secret: "${SCHWAB_CLIENT_SECRET}"
  redirect_uri: "http://localhost:5000/auth/schwab/callback"

  # Fallback to CSV if API unavailable
  csv_fallback:
    enabled: true
    holdings_path: "data/schwab/positions.csv"
    transactions_path: "data/schwab/transactions.csv"

# Market Data Providers
market_data:
  primary_provider: yahoo        # yahoo, tiingo, alpha_vantage
  fallback_providers:
    - yahoo
    - alpha_vantage

  tiingo:
    enabled: false
    api_key: "${TIINGO_API_KEY}"
    cache_duration: 3600

  yahoo_finance:
    enabled: true
    cache_duration: 600

  alpha_vantage:
    enabled: false
    api_key: "${ALPHA_VANTAGE_KEY}"
    rate_limit: 5                # Requests per minute

# Plugins
plugins:
  enabled: true
  plugin_directory: "src/plugins/bank_plugins"
  auto_load: []                  # Plugin IDs to auto-load on startup
```

### File: `config/.env.example`

```bash
# Personal Investment System - Environment Variables
# Copy this file to .env and fill in your credentials

# =============================================================================
# Flask Application
# =============================================================================
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
APP_ENV=development

# =============================================================================
# Database
# =============================================================================
DB_PATH=data/investment_system.db

# =============================================================================
# Cryptocurrency Exchanges (CCXT)
# =============================================================================
# Get API keys from each exchange's settings
# IMPORTANT: Use read-only API keys for security

# Binance
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Coinbase
COINBASE_API_KEY=
COINBASE_API_SECRET=

# Kraken
KRAKEN_API_KEY=
KRAKEN_API_SECRET=

# =============================================================================
# Interactive Brokers
# =============================================================================
# Option 1: JWT Token (recommended)
IBKR_JWT_TOKEN=

# Option 2: Account credentials (for gateway auth)
IBKR_ACCOUNT_ID=

# =============================================================================
# Charles Schwab
# =============================================================================
# Register at https://developer.schwab.com/ to get credentials
SCHWAB_CLIENT_ID=
SCHWAB_CLIENT_SECRET=

# =============================================================================
# Market Data Providers
# =============================================================================
# Tiingo (free tier: 500 requests/day)
# Register at https://api.tiingo.com/
TIINGO_API_KEY=

# Alpha Vantage (free tier: 5 requests/minute)
# Register at https://www.alphavantage.co/
ALPHA_VANTAGE_KEY=

# FRED (Federal Reserve Economic Data)
# Register at https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY=
```

---

## Usage Examples

### Basic Crypto Sync

```python
from src.data_manager.connectors import CCXTConnector

# Configure
config = {
    'exchanges': {
        'binance': {
            'api_key': 'your_api_key',
            'api_secret': 'your_api_secret',
            'enabled': True
        }
    }
}

# Connect and fetch
connector = CCXTConnector(config)
success, msg = connector.authenticate()
print(f"Auth: {msg}")

holdings = connector.get_holdings()
print(holdings)

transactions = connector.get_transactions(since_date=datetime(2024, 1, 1))
print(transactions)
```

### Using the Plugin System

```python
from src.plugins.manager import PluginManager

# Discover available plugins
manager = PluginManager()
plugins = manager.discover_plugins()
print(f"Found {len(plugins)} plugins")

# Load and use a plugin
icbc = manager.load_plugin('icbc_personal')
if icbc:
    success, msg = icbc.authenticate({
        'username': 'your_username',
        'password': 'your_password'
    })

    if success:
        accounts = icbc.get_accounts()
        for _, acct in accounts.iterrows():
            holdings = icbc.get_holdings(acct['account_id'])
            transactions = icbc.get_transactions(acct['account_id'])
```

---

## Testing Guidelines

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch

from src.data_manager.connectors import CCXTConnector


class TestCCXTConnector:
    """Tests for CCXT connector."""

    def test_authenticate_success(self):
        """Test successful authentication."""
        config = {
            'exchanges': {
                'binance': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'enabled': True
                }
            }
        }

        with patch('ccxt.binance') as mock_binance:
            mock_exchange = Mock()
            mock_exchange.fetch_balance.return_value = {'total': {'BTC': 1.0}}
            mock_binance.return_value = mock_exchange

            connector = CCXTConnector(config)
            success, msg = connector.authenticate()

            assert success
            assert 'binance' in msg.lower()

    def test_get_holdings_not_authenticated(self):
        """Test holdings fetch when not authenticated."""
        connector = CCXTConnector({'exchanges': {}})

        with pytest.raises(DataFetchError):
            connector.get_holdings()

    def test_get_holdings_with_data(self):
        """Test holdings fetch with mock data."""
        # ... implementation
        pass
```

---

This implementation guide provides all the technical details needed to build each component. Refer to `task_plan.md` for the development sequence and `notes.md` for design decisions and research findings.
